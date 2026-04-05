from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Any, Optional


class ResponseCache:
    def __init__(self, max_entries: int = 128) -> None:
        self.max_entries = max_entries
        self._entries: "OrderedDict[str, Any]" = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._entries:
                return None
            value = self._entries.pop(key)
            self._entries[key] = value
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._entries:
                self._entries.pop(key)
            self._entries[key] = value
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_response_cache = ResponseCache()


def get_response_cache() -> ResponseCache:
    return _response_cache

