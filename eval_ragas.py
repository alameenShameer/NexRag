import os
import json
import pandas as pd
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
from langchain_community.embeddings import HuggingFaceEmbeddings

# 1. Setup Local Models (No OpenAI Key needed!)
print("Loading local models...")
# Wrapper for Ragas to use Ollama
langchain_llm = ChatOllama(model="llama3.2:3b")
wrapper_llm = LangchainLLMWrapper(langchain_llm)

# Wrapper for Ragas to use Local Embeddings
langchain_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
wrapper_embeddings = LangchainEmbeddingsWrapper(langchain_embeddings)

# 2. Load Dataset
print("Loading dataset...")
with open("data/mesitam_golden_dataset.json", "r") as f:
    data = json.load(f)

# Initialize RAG Engine
from rag import get_rag_engine
from kg import query_kg
from llm import generate_answer

rag_engine = get_rag_engine()

# Generate Answers and Contexts
questions = [item["question"] for item in data]
ground_truths = [item["ground_truth"] for item in data] # Unwrap list for SingleTurnSample compatibility
answers = []
contexts = []

print("Generating RAG responses for evaluation...")
for q in questions:
    print(f"Processing: {q}")
    # Hybrid Retrieval Logic (Simplified from app.py)
    # 1. KG
    kg_ans = query_kg(q)
    
    # 2. Vector
    # Determine category keyword for better retrieval (simple heuristic)
    cat = "General"
    if "syllabus" in q.lower(): cat = "SYLLABUS"
    elif "rule" in q.lower() or "attendance" in q.lower(): cat = "REGULATION"
    
    vec_results = rag_engine.retrieve(q, top_k=3, filter_category=cat if cat != "General" else None)
    
    # Context Construction
    ctx_parts = []
    if kg_ans: ctx_parts.append(f"KG: {kg_ans}")
    if vec_results: ctx_parts.append("\n".join([r["text"] for r in vec_results]))
    
    full_ctx = "\n\n".join(ctx_parts)
    contexts.append([full_ctx]) # Ragas expects list of strings
    
    # Generate Answer
    ans = ""
    try:
        if not full_ctx:
            ans = "I don't know."
        else:
            # Consume generator
            for chunk in generate_answer(q, full_ctx):
                ans += chunk
    except Exception as e:
        ans = "Error generating answer."
        print(e)
        
    answers.append(ans)

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
print("Results saved to logs/ragas_results.csv")
