from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, Optional


class PipelineTraceStore:
    def __init__(self, max_entries: int = 200) -> None:
        self.max_entries = max_entries
        self._entries: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = Lock()

    def save(self, trace_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            if trace_id in self._entries:
                self._entries.pop(trace_id)
            self._entries[trace_id] = payload
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def get(self, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            payload = self._entries.get(trace_id)
            if payload is None:
                return None
            self._entries.move_to_end(trace_id)
            return payload


_trace_store = PipelineTraceStore()


def save_pipeline_trace(trace_id: str, payload: Dict[str, Any]) -> None:
    _trace_store.save(trace_id, payload)


def get_pipeline_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    return _trace_store.get(trace_id)
