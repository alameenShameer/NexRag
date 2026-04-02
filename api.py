import os
import time
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict

from rag import get_rag_engine
from kg import query_kg, ping_kg
from llm import generate_answer, get_llm_info
from router import get_intent
from logger import log_interaction

app = FastAPI(title="NexRag API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PDF_DIR = "data/pdfs"
LOG_FILE = "logs/query_history.csv"
os.makedirs(PDF_DIR, exist_ok=True)


def get_rag_engine_safe():
    try:
        return get_rag_engine()
    except Exception:
        return None


def compute_confidence(kg_answer, vector_results):
    if kg_answer and vector_results:
        top_score = vector_results[0]["score"] if vector_results else 0.0
        return min(98, max(90, int(90 + top_score * 8)))
    if kg_answer:
        return 94
    if vector_results:
        top_score = vector_results[0]["score"]
        return min(92, max(35, int(top_score * 100)))
    return 0

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = []

@app.get("/api/status")
def get_status():
    try:
        rag_engine = get_rag_engine_safe()
        total_pdfs = len([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')])
        total_chunks = len(rag_engine.chunks_metadata) if rag_engine and rag_engine.chunks_metadata else 0
        vector_ready = bool(rag_engine and rag_engine.index is not None)
        llm_info = get_llm_info()
        return {
            "pdfs": total_pdfs,
            "chunks": total_chunks,
            "vector_ready": vector_ready,
            "kg_ready": ping_kg(),
            "llm_provider": llm_info["provider"],
            "llm_model": llm_info["model"],
        }
    except Exception:
        llm_info = get_llm_info()
        return {
            "pdfs": 0,
            "chunks": 0,
            "vector_ready": False,
            "kg_ready": False,
            "llm_provider": llm_info["provider"],
            "llm_model": llm_info["model"],
        }

@app.get("/api/documents")
def get_documents():
    return {"files": [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]}

@app.get("/api/history")
def get_history():
    if os.path.exists(LOG_FILE):
        try:
            df = pd.read_csv(LOG_FILE)
            top_queries = df['Question'].tail(5).tolist()
            return {"history": list(reversed(top_queries))}
        except Exception:
            return {"history": []}
    return {"history": []}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form("General")):
    try:
        rag_engine = get_rag_engine()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    path = os.path.join(PDF_DIR, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    rag_engine.index_pdf(path, category=category)
    return {"message": "Success"}

@app.post("/api/chat")
def chat(request: ChatRequest):
    question = request.query
    history = request.history
    start_time = time.time()
    rag_engine = get_rag_engine_safe()
    
    intent = get_intent(question)
    kg_answer = None
    vector_results = []
    
    if intent in ["FACULTY_INFO", "COURSE_INFO", "REGULATION", "DEFINITION"]:
        kg_answer = query_kg(question)
    if rag_engine:
        vector_results = rag_engine.retrieve(question)

    context_parts = []
    routing_mode = "KG + Vector" if kg_answer and vector_results else "Knowledge Graph" if kg_answer else "Vector DB Search" if vector_results else "No Retrieval Hit"
    confidence = compute_confidence(kg_answer, vector_results)
    reasoning_log = f"Intent Detected: **{intent}**\nRouting: **{routing_mode}**\nConfidence: **{confidence}%**"
    source_bullets = ""

    if kg_answer:
        context_parts.append(f"Fact from Knowledge Graph:\n{kg_answer}")
        source_bullets += "- *Knowledge Graph* (Fuseki DB)\n"

    unique_sources = set()
    snippets = []
    if vector_results:
        for i, item in enumerate(vector_results[:4]):
             source_file = item.get('source', 'Unknown PDF')
             unique_sources.add(source_file)
             snippets.append({"source": source_file, "score": item["score"], "text": item["text"][:150]})
        
        doc_context = "\n\n".join([item["text"] for item in vector_results[:4]])
        context_parts.append(f"Context from PDF Documents:\n{doc_context}")
        
        for src in unique_sources:
            source_bullets += f"- `{src}` (Vector DB)\n"

    if not context_parts and not history:
        return {
            "answer": "I couldn't find any relevant information.",
            "mode": "No DB hit",
            "confidence": confidence,
            "sources": "",
            "reasoning": reasoning_log,
            "snippets": []
        }

    final_context = "\n\n---\n\n".join(context_parts) if context_parts else "No specific documentation context found for this immediate query. Rely on existing memory if present."
    
    response_msg = ""
    try:
        for chunk in generate_answer(question, final_context, history):
            response_msg += chunk
    except Exception as e:
        response_msg = f"LLM Generation Error: {e}"
        
    response_msg = response_msg.replace(' • ', '\n  - ').replace('• ', '\n- ').replace('➤ ', '\n\n**➤** ')
    log_interaction(question, response_msg, intent, time.time() - start_time)

    return {
        "answer": response_msg,
        "confidence": confidence,
        "sources": source_bullets,
        "reasoning": reasoning_log,
        "snippets": snippets,
        "mode": "Combined Mode" if kg_answer and vector_results else "Knowledge Graph Mode" if kg_answer else "Vector Search Mode"
    }

class KGFileUpdate(BaseModel):
    content: str

@app.get("/api/kg-files")
def get_kg_files():
    try:
        files = [f for f in os.listdir("data") if f.endswith(".ttl") and f != "merged_kg.ttl"]
        return {"files": files}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/kg-source/{filename}")
def get_kg_source(filename: str):
    if not filename.endswith(".ttl") or ".." in filename:
        return {"error": "Invalid filename"}
    path = os.path.join("data", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return {"error": "File not found"}

@app.post("/api/kg-source/{filename}")
def update_kg_source(filename: str, payload: KGFileUpdate):
    if not filename.endswith(".ttl") or ".." in filename:
        return {"error": "Invalid filename"}
    path = os.path.join("data", filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(payload.content)
    return {"message": "Success"}

@app.post("/api/kg-restart")
def restart_kg():
    import subprocess
    try:
        # First, rebuild the merged graph
        subprocess.run(["venv\\Scripts\\python.exe", "merge_kg.py"], check=True)
        
        # Kill existing fuseki server
        subprocess.run("taskkill /F /IM java.exe /T", shell=True, stderr=subprocess.DEVNULL)
        
        time.sleep(2)
        
        # Start Fuseki with merged_kg.ttl
        start_cmd = 'start "Fuseki Server" cmd /c "java -jar fuseki\\apache-jena-fuseki-5.6.0\\fuseki-server.jar --file=data/merged_kg.ttl /mesitam_kg"'
        subprocess.run(start_cmd, shell=True)
        
        return {"message": "KG Restarted successfully"}
    except Exception as e:
        return {"error": str(e)}
