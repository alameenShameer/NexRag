from __future__ import annotations

import json
import os
import threading
import time
import math
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from kg import inspect_ttl_update, ping_kg, query_kg_facts
from llm import generate_answer
from logger import log_interaction
from rag import get_rag_engine
from services.chat import (
    build_chat_payload as service_build_chat_payload,
    build_legacy_response,
    build_generation_context,
    build_no_hit_response,
    chat_response_from_payload,
    finalize_answer_text,
    format_final_answer,
    get_cached_response,
    set_cached_response,
)
from services.config import OFFICIAL_KG_PATH, QUERY_HISTORY_FILE, UPLOAD_DIR
from services.evaluation import get_evaluation_service
from services.ingestion import get_ingestion_service
from services.knowledge_base import get_knowledge_base_service
from services.pipeline_v2.metrics import compute_metrics_snapshot
from services.pipeline_v2.trace_store import get_pipeline_trace
from services.readiness import get_readiness_snapshot
from services.upload_kg import get_upload_kg_service
from services.uploads import get_upload_service
from merge_kg import merge_ttl_files


query_kg = query_kg_facts


app = FastAPI(title="NexRag API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, str]] = Field(default_factory=list)
    answer_mode: Optional[str] = None


class KGFileUpdate(BaseModel):
    content: str


class KGValidatedUpdate(BaseModel):
    content: str
    confirm_deletions: bool = False


class IngestionRunRequest(BaseModel):
    force: bool = False


class GraphQueryRequest(BaseModel):
    query: str
    history: List[Dict[str, str]] = Field(default_factory=list)


def get_rag_engine_safe():
    try:
        return get_rag_engine()
    except Exception:
        return None


def build_chat_payload(
    question: str,
    history: Optional[List[Dict[str, str]]],
    answer_mode: Optional[str] = None,
    stage_callback=None,
    include_graph: bool = False,
):
    _ = answer_mode
    rag_engine = get_rag_engine_safe()
    return service_build_chat_payload(
        question,
        history,
        rag_engine,
        kg_query_fn=query_kg,
        stage_callback=stage_callback,
        include_graph=include_graph,
    )


def _index_version() -> str:
    return get_knowledge_base_service().index_version()


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return value


def _log_and_cache(question: str, answer_mode: Optional[str], payload: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    latency = time.time() - payload["start_time"]
    log_interaction(
        question,
        response["answer"],
        payload["intent"],
        latency,
        metadata={
            "answer_mode": answer_mode,
            "question_type": payload.get("question_type"),
            "status": response.get("status"),
            "confidence": response.get("confidence"),
            "confidence_label": response.get("confidence_label"),
            "retrieval_version": payload.get("retrieval", {}).get("retrieval_version"),
            "retrieval_query": payload.get("retrieval_query"),
            "trace_id": response.get("trace_id") or payload.get("trace_id"),
            "source_titles": [source.get("title") for source in response.get("sources", [])],
        },
    )
    set_cached_response(
        question,
        answer_mode,
        _index_version(),
        response,
        retrieval_version=payload.get("retrieval", {}).get("retrieval_version"),
    )
    return response


def _rebuild_vector_store_after_upload_change() -> None:
    try:
        rag_engine = get_rag_engine()
        rag_engine.rebuild_from_sources(upload_dir=UPLOAD_DIR)
        get_upload_kg_service().rebuild_from_uploads()
    except Exception as exc:
        print(f"Upload reindex failed: {exc}")


@app.on_event("startup")
def initialize_knowledge_base() -> None:
    readiness = get_readiness_snapshot()
    if readiness["chunks"] == 0 or readiness["index_version"] == "uninitialized":
        threading.Thread(target=lambda: get_ingestion_service().schedule_run(force=False), daemon=True).start()
    if get_upload_service().list_documents():
        threading.Thread(target=lambda: get_upload_kg_service().rebuild_from_uploads(), daemon=True).start()


@app.get("/api/status")
def get_status():
    return get_readiness_snapshot()


@app.get("/api/readiness")
def get_readiness():
    return get_readiness_snapshot()


@app.get("/api/documents")
def get_documents():
    return {"documents": get_upload_service().list_documents()}


@app.delete("/api/documents/{filename}")
def delete_document(filename: str, background_tasks: BackgroundTasks):
    safe_name = os.path.basename(filename)
    if safe_name != filename or not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = UPLOAD_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    file_path.unlink()
    get_upload_service().remove_document(safe_name)
    background_tasks.add_task(_rebuild_vector_store_after_upload_change)
    return {"message": f"Deleted {safe_name}", "reindex": "scheduled"}


@app.get("/api/history")
def get_history():
    if QUERY_HISTORY_FILE.exists():
        try:
            df = pd.read_csv(QUERY_HISTORY_FILE)
            records = df.tail(100).to_dict(orient="records")
            history = []
            for idx, row in enumerate(reversed(records)):
                history.append(
                    {
                        "id": f"history-{idx}",
                        "timestamp": _json_safe_value(row.get("Timestamp", "")),
                        "question": _json_safe_value(row.get("Question", "")),
                        "answer": _json_safe_value(row.get("Answer", "")),
                        "intent": _json_safe_value(row.get("Intent", "")),
                        "latency": _json_safe_value(row.get("Latency (s)", "")),
                    }
                )
            return {"history": history}
        except Exception:
            return {"history": []}
    return {"history": []}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form("User Upload")):
    file_path = UPLOAD_DIR / os.path.basename(file.filename)
    with file_path.open("wb") as file_handle:
        file_handle.write(await file.read())
    document = get_upload_service().schedule_index(file_path.name, category=category)
    return {"message": "Upload accepted", "document": document}


@app.get("/api/knowledge-base")
def get_knowledge_base():
    return get_knowledge_base_service().public_sections()


@app.get("/api/knowledge-base/overview")
def get_knowledge_overview():
    return {"overview": get_knowledge_base_service().public_sections()["overview"]}


@app.get("/api/knowledge-base/departments")
def get_knowledge_departments():
    return {"departments": get_knowledge_base_service().public_sections()["departments"]}


@app.get("/api/knowledge-base/faculty")
def get_knowledge_faculty():
    return {"faculty": get_knowledge_base_service().public_sections()["faculty"]}


@app.get("/api/knowledge-base/faqs")
def get_knowledge_faqs():
    return {"faqs": get_knowledge_base_service().public_sections()["faqs"]}


@app.get("/api/knowledge-base/facilities")
def get_knowledge_facilities():
    return {"facilities": get_knowledge_base_service().public_sections()["facilities"]}


@app.get("/api/knowledge-base/placements")
def get_knowledge_placements():
    return {"placements": get_knowledge_base_service().public_sections()["placements"]}


@app.get("/api/knowledge-base/events")
def get_knowledge_events():
    return {"events": get_knowledge_base_service().public_sections()["events"]}


@app.get("/api/knowledge-base/graph")
def get_knowledge_graph():
    return get_knowledge_base_service().get_graph()


@app.get("/api/ingestion/status")
def get_ingestion_status():
    return get_ingestion_service().get_status()


@app.post("/api/ingestion/run")
def run_ingestion(request: IngestionRunRequest):
    return get_ingestion_service().schedule_run(force=request.force)


@app.get("/api/evaluation/summary")
def get_evaluation_summary():
    return get_evaluation_service().refresh_summary_from_csv()


@app.get("/api/evaluation/metrics")
def get_evaluation_metrics(force: bool = False):
    return compute_metrics_snapshot(force_refresh=force)


@app.post("/api/evaluation/run")
def run_evaluation():
    return get_evaluation_service().run()


@app.get("/api/evaluation/status")
def get_evaluation_status():
    return get_evaluation_service().get_status()


@app.get("/api/pipeline/trace/{trace_id}")
def get_chat_pipeline_trace(trace_id: str):
    trace = get_pipeline_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@app.post("/api/graph/query")
def graph_query(request: GraphQueryRequest):
    payload = build_chat_payload(request.query, request.history, answer_mode="detailed", include_graph=True)
    retrieval_trace = payload.get("retrieval_trace", {}) or {}
    return {
        "trace_id": payload.get("trace_id"),
        "query_plan": payload.get("query_plan"),
        "kg_facts": payload.get("kg_facts", []),
        "graph_view": payload.get("graph_view", {"nodes": [], "edges": []}),
        "kg_queries": retrieval_trace.get("kg_queries", []),
        "graph_summary": retrieval_trace.get("graph_summary", {}),
    }


@app.post("/api/graph/view")
def graph_view(request: GraphQueryRequest):
    payload = build_chat_payload(request.query, request.history, answer_mode="detailed", include_graph=True)
    return {
        "trace_id": payload.get("trace_id"),
        "graph_view": payload.get("graph_view", {"nodes": [], "edges": []}),
        "kg_facts": payload.get("kg_facts", []),
    }


@app.get("/api/kg-files")
def get_kg_files():
    files = [OFFICIAL_KG_PATH.name] if OFFICIAL_KG_PATH.exists() else []
    return {"files": files}


@app.get("/api/kg-source/{filename}")
def get_kg_source(filename: str):
    if filename != OFFICIAL_KG_PATH.name:
        return {"error": "Invalid filename"}
    if OFFICIAL_KG_PATH.exists():
        with OFFICIAL_KG_PATH.open("r", encoding="utf-8") as file_handle:
            return {"content": file_handle.read()}
    return {"error": "File not found"}


@app.post("/api/kg-source/{filename}")
def update_kg_source(filename: str, payload: KGFileUpdate):
    if filename != OFFICIAL_KG_PATH.name:
        return {"error": "Invalid filename"}
    with OFFICIAL_KG_PATH.open("w", encoding="utf-8") as file_handle:
        file_handle.write(payload.content)
    merge_ttl_files()
    return {"message": "Success", "merged": True, "kg_ready": ping_kg()}


@app.post("/api/kg-save/{filename}")
def save_kg_source(filename: str, payload: KGValidatedUpdate):
    if filename != OFFICIAL_KG_PATH.name:
        return {"error": "Invalid filename"}
    if not OFFICIAL_KG_PATH.exists():
        raise HTTPException(status_code=404, detail="File not found")

    existing_content = OFFICIAL_KG_PATH.read_text(encoding="utf-8")
    try:
        inspection = inspect_ttl_update(existing_content, payload.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Turtle content: {exc}") from exc

    if inspection["removed_count"] > 0 and not payload.confirm_deletions:
        return {
            "requires_confirmation": True,
            "message": "This edit removes existing knowledge graph data.",
            "removed_count": inspection["removed_count"],
            "removed_preview": inspection["removed_preview"],
        }

    OFFICIAL_KG_PATH.write_text(payload.content, encoding="utf-8")
    merge_ttl_files()
    return {
        "message": "Success",
        "removed_count": inspection["removed_count"],
        "removed_preview": inspection["removed_preview"],
        "validation": "passed",
        "merged": True,
        "kg_ready": ping_kg(),
    }


@app.post("/api/kg-restart")
def restart_kg():
    merge_ttl_files()
    return {
        "message": "The generated knowledge graph file has been updated. Fuseki reload remains optional because NexRag now falls back to the local RDF graph when needed.",
        "kg_ready": ping_kg(),
    }


@app.post("/api/chat-legacy")
def chat_legacy(request: ChatRequest):
    cached = None if request.history else get_cached_response(request.query, request.answer_mode, _index_version())
    if cached:
        payload = build_chat_payload(request.query, request.history, request.answer_mode)
        return build_legacy_response(cached, payload)

    payload = build_chat_payload(request.query, request.history, request.answer_mode)
    response = chat_response_from_payload(
        request.query,
        payload,
        request.answer_mode,
        request.history,
        generate_answer_fn=generate_answer,
    )
    _log_and_cache(request.query, request.answer_mode, payload, response)
    return build_legacy_response(response, payload)


@app.post("/api/chat")
def chat(request: ChatRequest):
    cached = None if request.history else get_cached_response(request.query, request.answer_mode, _index_version())
    if cached:
        return cached

    payload = build_chat_payload(request.query, request.history, request.answer_mode)
    response = chat_response_from_payload(
        request.query,
        payload,
        request.answer_mode,
        request.history,
        generate_answer_fn=generate_answer,
    )
    return _log_and_cache(request.query, request.answer_mode, payload, response)


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    cached = None if request.history else get_cached_response(request.query, request.answer_mode, _index_version())
    if cached:
        def cached_stream():
            yield f"data: {json.dumps({'type': 'done', 'payload': cached})}\n\n"

        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    def event_stream():
        stage_events = []

        def stage_callback(stage: str, label: str) -> None:
            stage_events.append({"type": "stage", "stage": stage, "label": label})

        payload = build_chat_payload(request.query, request.history, request.answer_mode, stage_callback=stage_callback)
        for event in stage_events:
            yield f"data: {json.dumps(event)}\n\n"

        if payload["status"] == "refused":
            result = build_no_hit_response(payload, answer_mode=request.answer_mode)
            _log_and_cache(request.query, request.answer_mode, payload, result)
            yield f"data: {json.dumps({'type': 'done', 'payload': result})}\n\n"
            return

        stage_name = "generating_answer" if payload.get("response_strategy") == "generate" else "extracting_answer"
        stage_label = "Generating answer..." if payload.get("response_strategy") == "generate" else "Extracting grounded answer..."
        yield f"data: {json.dumps({'type': 'stage', 'stage': stage_name, 'label': stage_label})}\n\n"

        result = chat_response_from_payload(
            request.query,
            payload,
            request.answer_mode,
            request.history,
            generate_answer_fn=generate_answer,
        )

        answer_text = result.get("answer", "") or ""
        if answer_text:
            words = answer_text.split()
            if not words:
                yield f"data: {json.dumps({'type': 'chunk', 'content': answer_text})}\n\n"
            else:
                for start in range(0, len(words), 8):
                    chunk = " ".join(words[start : start + 8])
                    if start + 8 < len(words):
                        chunk += " "
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        _log_and_cache(request.query, request.answer_mode, payload, result)
        yield f"data: {json.dumps({'type': 'done', 'payload': result})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
