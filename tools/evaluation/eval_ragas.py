import os
import json
import sys
import pandas as pd
from pathlib import Path
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_community.chat_models import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

STATUS_PATH = os.environ.get("NEXRAG_EVALUATION_STATUS_PATH")


def write_status(progress_percent, message, state="running", latest_summary=None):
    if not STATUS_PATH:
        return
    payload = {
        "state": state,
        "progress_percent": progress_percent,
        "message": message,
        "started_at": None,
        "latest_summary": latest_summary,
        "last_error": None,
    }
    if os.path.exists(STATUS_PATH):
        try:
            with open(STATUS_PATH, "r", encoding="utf-8") as file_handle:
                existing = json.load(file_handle)
            payload["started_at"] = existing.get("started_at")
            payload["latest_summary"] = latest_summary or existing.get("latest_summary")
        except Exception:
            pass
    with open(STATUS_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2)

# 1. Setup Local Models (No OpenAI Key needed!)
print("Loading local models...")
write_status(5, "Loading evaluation models...")
# Wrapper for Ragas to use Ollama
langchain_llm = ChatOllama(model="llama3.2:3b")
wrapper_llm = LangchainLLMWrapper(langchain_llm)

# Wrapper for Ragas to use Local Embeddings
langchain_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
wrapper_embeddings = LangchainEmbeddingsWrapper(langchain_embeddings)

# 2. Load Dataset
print("Loading dataset...")
write_status(15, "Loading evaluation dataset...")
with open("data/mesitam_golden_dataset.json", "r") as f:
    data = json.load(f)

import api

# Generate Answers and Contexts
questions = [item["question"] for item in data]
ground_truths = [item["ground_truth"] for item in data] # Unwrap list for SingleTurnSample compatibility
answers = []
contexts = []

print("Generating RAG responses for evaluation...")
total_questions = max(len(questions), 1)
for index, q in enumerate(questions, start=1):
    print(f"Processing: {q}")
    write_status(20 + int((index - 1) / total_questions * 50), f"Generating evaluation answers ({index}/{total_questions})...")
    payload = api.build_chat_payload(q, history=[], answer_mode="detailed")
    full_ctx = api.build_generation_context(payload) if payload["context_parts"] else ""
    contexts.append([full_ctx] if full_ctx else [""])

    if not payload["context_parts"]:
        answers.append("I don't have enough information in the knowledge base")
        continue

    response = api.chat(api.ChatRequest(query=q, history=[], answer_mode="detailed"))
    answers.append(response["answer"])

# Constructing the dataset dictionary
dataset_dict = {
    "question": questions,
    "answer": answers,
    "contexts": contexts,
    "ground_truth": ground_truths
}

ds = Dataset.from_dict(dataset_dict)

# 3. Run Evaluation
print("Running Ragas evaluation (this may take time on CPU/GPU)...")
write_status(80, "Running RAGAS metrics...")
results = evaluate(
    ds,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ],
    llm=wrapper_llm, 
    embeddings=wrapper_embeddings, 
)

# 4. Save Results
print("\nEvaluation Results:")
print(results)
df = results.to_pandas()
df.to_csv("logs/ragas_results.csv", index=False)
summary = {
    "status": "ready",
    "message": "Latest RAGAS evaluation summary loaded.",
    "metrics": df.iloc[-1].dropna().to_dict() if not df.empty else {},
    "rows": len(df),
    "source": "ragas_results.csv",
}
with open("logs/ragas_summary.json", "w", encoding="utf-8") as file_handle:
    json.dump(summary, file_handle, indent=2)
write_status(100, "Evaluation completed.", state="completed", latest_summary=summary)
print("Results saved to logs/ragas_results.csv")
