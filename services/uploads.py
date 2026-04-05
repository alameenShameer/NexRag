from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from rag import get_rag_engine

from .config import UPLOAD_DIR, UPLOAD_STATUS_PATH
from .upload_kg import get_upload_kg_service


UPLOAD_PROGRESS_BY_STAGE = {
    "uploaded": 15,
    "chunking": 40,
    "embedding": 75,
    "kg_sync": 90,
    "indexed": 100,
    "failed": 100,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_record(name: str) -> Dict[str, Any]:
    timestamp = utc_now_iso()
    return {
        "id": name,
        "name": name,
        "status": "indexed",
        "progress": 100,
        "job_id": None,
        "message": "Indexed and searchable",
        "error": None,
        "uploaded_at": timestamp,
        "updated_at": timestamp,
    }


class UploadService:
    def __init__(self, status_path: Path = UPLOAD_STATUS_PATH) -> None:
        self.status_path = status_path
        self._lock = threading.Lock()
        self._jobs: Dict[str, threading.Thread] = {}
        self._ensure_status_file()

    def _ensure_status_file(self) -> None:
        if not self.status_path.exists():
            self._write_records({})
        self._sync_with_disk()

    def _read_records(self) -> Dict[str, Dict[str, Any]]:
        if not self.status_path.exists():
            return {}
        try:
            with self.status_path.open("r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_records(self, records: Dict[str, Dict[str, Any]]) -> None:
        with self.status_path.open("w", encoding="utf-8") as file_handle:
            json.dump(records, file_handle, indent=2, ensure_ascii=False)

    def _sync_with_disk(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            records = self._read_records()
            disk_files = {
                path.name
                for path in UPLOAD_DIR.iterdir()
                if path.is_file() and path.suffix.lower() == ".pdf"
            } if UPLOAD_DIR.exists() else set()

            for missing_name in set(records) - disk_files:
                records.pop(missing_name, None)

            for file_name in disk_files:
                if file_name not in records:
                    records[file_name] = _default_record(file_name)

            self._write_records(records)
            return records

    def _update_record(self, file_name: str, **updates: Any) -> Dict[str, Any]:
        with self._lock:
            records = self._read_records()
            record = records.get(file_name, _default_record(file_name))
            record.update(updates)
            record["updated_at"] = utc_now_iso()
            if record.get("status") in UPLOAD_PROGRESS_BY_STAGE:
                record["progress"] = UPLOAD_PROGRESS_BY_STAGE[record["status"]]
            records[file_name] = record
            self._write_records(records)
            return dict(record)

    def list_documents(self) -> List[Dict[str, Any]]:
        records = self._sync_with_disk()
        documents = list(records.values())
        documents.sort(key=lambda item: (item.get("updated_at") or "", item.get("name") or ""), reverse=True)
        return documents

    def pending_count(self) -> int:
        return sum(1 for item in self.list_documents() if item.get("status") in {"uploaded", "chunking", "embedding"})

    def documents_indexed(self) -> int:
        return sum(1 for item in self.list_documents() if item.get("status") == "indexed")

    def save_upload(self, file_name: str) -> Dict[str, Any]:
        safe_name = Path(file_name).name
        timestamp = utc_now_iso()
        return self._update_record(
            safe_name,
            id=safe_name,
            name=safe_name,
            status="uploaded",
            progress=UPLOAD_PROGRESS_BY_STAGE["uploaded"],
            job_id=f"upload-{uuid4().hex[:12]}",
            message="File uploaded",
            error=None,
            uploaded_at=timestamp,
        )

    def remove_document(self, file_name: str) -> None:
        with self._lock:
            records = self._read_records()
            records.pop(file_name, None)
            self._write_records(records)

    def schedule_index(self, file_name: str, category: str = "User Upload") -> Dict[str, Any]:
        safe_name = Path(file_name).name
        file_path = UPLOAD_DIR / safe_name
        record = self.save_upload(safe_name)

        def progress_callback(stage: str, message: Optional[str] = None) -> None:
            if stage not in UPLOAD_PROGRESS_BY_STAGE:
                return
            self._update_record(
                safe_name,
                status=stage,
                message=message or self._message_for_stage(stage),
                error=None,
            )

        def runner() -> None:
            try:
                rag_engine = get_rag_engine()
                progress_callback("chunking", "Chunking document...")
                rag_engine.index_pdf(str(file_path), category=category, progress_callback=progress_callback)
                progress_callback("kg_sync", "Updating knowledge graph...")
                get_upload_kg_service().rebuild_from_uploads()
                progress_callback("indexed", "Indexed and searchable")
            except Exception as exc:
                self._update_record(
                    safe_name,
                    status="failed",
                    message="Indexing failed",
                    error=str(exc),
                )
            finally:
                with self._lock:
                    self._jobs.pop(safe_name, None)

        thread = threading.Thread(target=runner, daemon=True, name=f"upload-index-{safe_name}")
        with self._lock:
            self._jobs[safe_name] = thread
        thread.start()
        return record

    def _message_for_stage(self, stage: str) -> str:
        return {
            "uploaded": "File uploaded",
            "chunking": "Chunking document...",
            "embedding": "Generating embeddings...",
            "kg_sync": "Updating knowledge graph...",
            "indexed": "Indexed and searchable",
            "failed": "Indexing failed",
        }.get(stage, "Processing document...")


_upload_service = UploadService()


def get_upload_service() -> UploadService:
    return _upload_service
