from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List

from .config import KNOWLEDGE_BASE_PATH


DEFAULT_KNOWLEDGE_BASE: Dict[str, Any] = {
    "updated_at": None,
    "index_version": "uninitialized",
    "overview": {
        "college": "MES Institute of Technology and Management",
        "location": "Chathannoor, Kollam",
        "summary": "Knowledge base initialization is pending.",
    },
    "departments": [],
    "faculty": [],
    "courses": [],
    "facilities": [],
    "placements": [],
    "faqs": [],
    "events": [],
    "documents": [],
    "graph": {"nodes": [], "edges": []},
}

GENERIC_ALLOWED_TOKENS = {
    "mes",
    "mesitam",
    "college",
    "campus",
    "admission",
    "admissions",
    "faculty",
    "staff",
    "department",
    "departments",
    "course",
    "courses",
    "placement",
    "placements",
    "library",
    "hostel",
    "hostels",
    "lab",
    "labs",
    "facility",
    "facilities",
    "event",
    "events",
    "news",
    "announcement",
    "announcements",
    "iqac",
    "nss",
    "ragging",
    "attendance",
    "regulation",
    "regulations",
    "ktu",
    "semester",
    "exam",
    "exams",
    "hod",
    "principal",
    "grievance",
    "digital",
    "physical",
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")


class KnowledgeBaseService:
    def __init__(self, path: Path = KNOWLEDGE_BASE_PATH) -> None:
        self.path = path
        self._lock = Lock()
        self._cache: Dict[str, Any] | None = None
        self._mtime: float | None = None

    def _load_from_disk(self) -> Dict[str, Any]:
        if not self.path.exists():
            return json.loads(json.dumps(DEFAULT_KNOWLEDGE_BASE))
        with self.path.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
        return data

    def get_data(self, force_reload: bool = False) -> Dict[str, Any]:
        with self._lock:
            mtime = self.path.stat().st_mtime if self.path.exists() else None
            if force_reload or self._cache is None or self._mtime != mtime:
                self._cache = self._load_from_disk()
                self._mtime = mtime
            return self._cache

    def index_version(self) -> str:
        return str(self.get_data().get("index_version") or "uninitialized")

    def get_graph(self) -> Dict[str, Any]:
        return self.get_data().get("graph", {"nodes": [], "edges": []})

    def _iter_domain_texts(self, data: Dict[str, Any]) -> Iterable[str]:
        overview = data.get("overview", {})
        yield overview.get("college", "")
        yield overview.get("summary", "")
        yield overview.get("location", "")

        for section_name in ["departments", "faculty", "courses", "facilities", "placements", "faqs", "events"]:
            for item in data.get(section_name, []):
                if not isinstance(item, dict):
                    continue
                for key, value in item.items():
                    if isinstance(value, str):
                        yield value
                    elif isinstance(value, list):
                        for entry in value:
                            if isinstance(entry, str):
                                yield entry

    def domain_lexicon(self) -> set[str]:
        data = self.get_data()
        tokens = set(GENERIC_ALLOWED_TOKENS)
        for text in self._iter_domain_texts(data):
            lowered = text.lower()
            for token in TOKEN_PATTERN.findall(lowered):
                tokens.add(token)
        return tokens

    def is_domain_question(self, question: str) -> bool:
        tokens = set(TOKEN_PATTERN.findall((question or "").lower()))
        if not tokens:
            return False
        lexicon = self.domain_lexicon()
        return bool(tokens & lexicon)

    def public_sections(self) -> Dict[str, Any]:
        data = self.get_data()
        return {
            "overview": data.get("overview", {}),
            "departments": data.get("departments", []),
            "faculty": data.get("faculty", []),
            "courses": data.get("courses", []),
            "facilities": data.get("facilities", []),
            "placements": data.get("placements", []),
            "faqs": data.get("faqs", []),
            "events": data.get("events", []),
            "documents": data.get("documents", []),
            "updated_at": data.get("updated_at"),
            "index_version": data.get("index_version"),
        }


_knowledge_base_service = KnowledgeBaseService()


def get_knowledge_base_service() -> KnowledgeBaseService:
    return _knowledge_base_service

