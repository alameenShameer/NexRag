from __future__ import annotations

import json
from typing import Any, Dict

from kg import ping_kg
from llm import get_llm_info
from rag import get_vector_store_stats

from .config import INGESTION_STATUS_PATH, KNOWLEDGE_BASE_PATH, OFFICIAL_DOCUMENTS_PATH, UPLOAD_DIR
from .knowledge_base import get_knowledge_base_service
from .uploads import get_upload_service


def _load_ingestion_status() -> Dict[str, Any]:
    default_status = {
        "state": "idle",
        "message": "Initializing backend / Indexing documents...",
        "active_job": None,
        "last_refresh_at": None,
        "index_version": "uninitialized",
        "last_error": None,
    }
    if not INGESTION_STATUS_PATH.exists():
        return default_status

    with INGESTION_STATUS_PATH.open("r", encoding="utf-8") as file_handle:
        status = json.load(file_handle)

    if status.get("state") == "running":
        index_version = status.get("index_version") or "uninitialized"
        has_ready_kb = KNOWLEDGE_BASE_PATH.exists() and OFFICIAL_DOCUMENTS_PATH.exists() and index_version != "uninitialized"
        if has_ready_kb:
            healed_status = {
                **status,
                "state": "idle",
                "message": "Knowledge base ready.",
                "active_job": None,
            }
            with INGESTION_STATUS_PATH.open("w", encoding="utf-8") as file_handle:
                json.dump(healed_status, file_handle, indent=2, ensure_ascii=False)
            return healed_status

    return status


def get_readiness_snapshot() -> Dict[str, Any]:
    vector_stats = get_vector_store_stats()
    llm_info = get_llm_info()
    ingestion_status = _load_ingestion_status()
    knowledge_base = get_knowledge_base_service().get_data()
    upload_service = get_upload_service()
    uploaded_docs = len([path for path in UPLOAD_DIR.iterdir() if path.suffix.lower() == ".pdf"]) if UPLOAD_DIR.exists() else 0
    official_docs = len(knowledge_base.get("documents", []))
    kg_ready = ping_kg()
    documents_indexed = upload_service.documents_indexed()
    uploads_in_progress = upload_service.pending_count()

    state = "loading"
    message = ingestion_status.get("message") or "Initializing backend / Indexing documents..."
    index_version = ingestion_status.get("index_version") or get_knowledge_base_service().index_version()

    if ingestion_status.get("state") == "running":
        state = "loading"
        message = ingestion_status.get("message") or "Initializing backend / Indexing documents..."
    elif ingestion_status.get("last_error") and (vector_stats["chunks"] == 0 or not kg_ready):
        state = "error"
        message = ingestion_status.get("last_error")
    elif index_version == "uninitialized" or official_docs == 0:
        state = "loading"
        message = ingestion_status.get("message") or "Initializing backend / Indexing documents..."
    elif vector_stats["vector_ready"] and vector_stats["chunks"] > 0:
        state = "ready"
        message = "System ready to answer queries"
    elif official_docs > 0:
        state = "loading"
        message = "Finishing knowledge base indexing..."

    checks = {
        "backend": {"ok": True, "label": "Backend Running", "detail": "API reachable"},
        "llm": {"ok": bool(llm_info["model"]), "label": "LLM Loaded", "detail": llm_info["model"]},
        "vector": {"ok": vector_stats["vector_ready"], "label": "Vector Index Ready", "detail": f"{vector_stats['chunks']} chunks"},
        "kg": {"ok": kg_ready, "label": "Knowledge Graph Ready", "detail": "Connected" if kg_ready else "Unavailable"},
        "documents": {"ok": (official_docs + documents_indexed) > 0, "label": "Documents Indexed", "detail": str(official_docs + documents_indexed)},
        "index_version": {"ok": index_version != "uninitialized", "label": "Index version", "detail": index_version},
    }

    return {
        "state": state,
        "message": message,
        "pdfs": uploaded_docs,
        "official_documents": official_docs,
        "documents_indexed": documents_indexed,
        "uploads_in_progress": uploads_in_progress,
        "chunks": vector_stats["chunks"],
        "vector_ready": vector_stats["vector_ready"],
        "kg_ready": kg_ready,
        "llm_provider": llm_info["provider"],
        "llm_model": llm_info["model"],
        "active_job": ingestion_status.get("active_job"),
        "last_refresh_at": ingestion_status.get("last_refresh_at"),
        "index_version": index_version,
        "last_error": ingestion_status.get("last_error"),
        "checks": checks,
    }
