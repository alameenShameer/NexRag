from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

import pdfplumber

from merge_kg import merge_ttl_files
from rag import clean_document_text, clean_pdf_page_text, compact_alphanumeric, compact_query_forms, extract_keywords

from .config import UPLOAD_DIR, UPLOAD_KG_PATH, UPLOAD_KNOWLEDGE_PATH


SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
LOW_VALUE_PHRASES = (
    "acknowledgements",
    "award of the degree",
    "certificate",
    "declaration",
    "hereby declare",
    "name of the student",
    "partial fulfillment of the requirements",
    "presented by",
    "project report",
    "register no",
    "results and discussion",
    "signature",
    "submitted by",
    "submittedby",
    "university register no",
)
GENERIC_ENTITY_LABELS = {
    "key words",
    "keywords",
    "project",
    "report",
    "smart health care",
    "system",
    "the system",
    "this project",
    "this report",
    "this work",
    "the project",
}
DEFINITION_PATTERNS = (
    re.compile(r"^(?P<subject>[A-Z][A-Za-z0-9()&/\- ]{1,80}?)\s+(?:is|are)\s+(?P<body>.+)$"),
    re.compile(r"^(?P<subject>[A-Z][A-Za-z0-9()&/\- ]{1,80}?)\s*:\s*(?P<body>.+)$"),
)
FEATURE_VERBS = ("allows", "combines", "enables", "helps", "includes", "offers", "provides", "supports", "uses")


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "item"


def _split_sentences(text: str) -> List[str]:
    return [_normalize_text(part) for part in SENTENCE_SPLIT_PATTERN.split(text or "") if _normalize_text(part)]


def _sentence_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _is_low_value_sentence(sentence: str) -> bool:
    lowered = _normalize_text(sentence).lower()
    compact = compact_alphanumeric(lowered)
    if not lowered:
        return True
    if any(phrase in lowered for phrase in LOW_VALUE_PHRASES):
        return True
    if any(marker in compact for marker in ("submittedby", "nameofthestudent", "universityregisterno")):
        return True
    if len(lowered.split()) < 5:
        return True
    return False


def _canonical_subject(subject: str) -> str:
    cleaned = _normalize_text(subject).strip(" -:;,.\"'()[]")
    if ":" in cleaned:
        left, right = [part.strip() for part in cleaned.split(":", 1)]
        if 1 <= len(left.split()) <= 4:
            cleaned = left
        else:
            cleaned = right or left
    if cleaned.lower().startswith("the ") and " of " in cleaned.lower():
        suffix_match = re.search(r"\bof\s+([A-Z][A-Za-z0-9-]{2,40})$", cleaned)
        if suffix_match:
            return suffix_match.group(1)
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _looks_like_entity_label(label: str) -> bool:
    cleaned = _canonical_subject(label)
    lowered = cleaned.lower()
    if not cleaned or lowered in GENERIC_ENTITY_LABELS:
        return False
    if len(cleaned.split()) > 8:
        return False
    if len(cleaned) < 3:
        return False
    if not re.search(r"[A-Za-z]", cleaned):
        return False
    if not re.search(r"[A-Z]", cleaned):
        return False
    if any(phrase in lowered for phrase in LOW_VALUE_PHRASES):
        return False
    return True


def _entity_aliases(label: str) -> List[str]:
    aliases = {_normalize_text(label).lower()}
    camel_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", label)
    if camel_split != label:
        aliases.add(_normalize_text(camel_split).lower())
    compact = compact_alphanumeric(label)
    if compact:
        aliases.add(compact)
    return [alias for alias in aliases if alias]


def _extract_pdf_text(pdf_path: Path) -> str:
    pages: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            page_text = clean_pdf_page_text(page.extract_text() or "")
            if page_text:
                pages.append(f"[PAGE {page_index}]\n{page_text}")
    return clean_document_text("\n".join(pages))


def _best_summary(sentences: List[str]) -> str:
    for sentence in sentences[:24]:
        if _is_low_value_sentence(sentence):
            continue
        word_count = len(sentence.split())
        if 8 <= word_count <= 48:
            return sentence
    for sentence in sentences[:24]:
        if not _is_low_value_sentence(sentence):
            return sentence
    return ""


def _extract_entities(sentences: List[str], source_file: str, document_id: str) -> List[Dict[str, Any]]:
    entities: Dict[str, Dict[str, Any]] = {}
    seen_features: set[tuple[str, str]] = set()

    for index, sentence in enumerate(sentences[:240]):
        if _is_low_value_sentence(sentence):
            continue
        for pattern in DEFINITION_PATTERNS:
            match = pattern.match(sentence)
            if not match:
                continue
            subject = _canonical_subject(match.group("subject"))
            if not _looks_like_entity_label(subject):
                continue
            body = _normalize_text(match.group("body"))
            if len(body.split()) < 6:
                continue
            key = subject.lower()
            description = sentence if sentence.lower().startswith(subject.lower()) else f"{subject} is {body}"
            entry = entities.get(
                key,
                {
                    "id": _slugify(f"{source_file}-{subject}"),
                    "label": subject,
                    "description": description,
                    "features": [],
                    "source_file": source_file,
                    "document_id": document_id,
                    "aliases": _entity_aliases(subject),
                    "rank": index,
                },
            )
            if index < entry.get("rank", index):
                entry["description"] = description
                entry["rank"] = index
            entities[key] = entry
            break

    for entity in entities.values():
        label_lower = entity["label"].lower()
        label_compact = compact_alphanumeric(entity["label"])
        for sentence in sentences[:80]:
            if _is_low_value_sentence(sentence):
                continue
            if _sentence_key(sentence) == _sentence_key(entity["description"]):
                continue
            lowered = sentence.lower()
            compact_sentence = compact_alphanumeric(sentence)
            if label_lower not in lowered and (not label_compact or label_compact not in compact_sentence):
                continue
            if not any(f" {verb} " in f" {lowered} " for verb in FEATURE_VERBS):
                continue
            feature_key = (entity["id"], _sentence_key(sentence))
            if feature_key in seen_features:
                continue
            seen_features.add(feature_key)
            entity["features"].append(sentence)
            if len(entity["features"]) >= 3:
                break

    ordered = sorted(entities.values(), key=lambda item: (item.get("rank", 999), len(item["label"])))
    for item in ordered:
        item.pop("rank", None)
    return ordered[:8]


def _build_graph(documents: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for document in documents:
        nodes.append({"id": document["id"], "label": document["title"], "type": "UploadedDocument"})

    for entity in entities:
        nodes.append({"id": entity["id"], "label": entity["label"], "type": "UploadEntity"})
        edges.append(
            {
                "id": f"{entity['id']}|appears_in|{entity['document_id']}",
                "source": entity["id"],
                "target": entity["document_id"],
                "type": "appears_in",
            }
        )

    return {"nodes": nodes, "edges": edges}


def _escape_ttl_literal(value: str) -> str:
    return _normalize_text(value).replace("\\", "\\\\").replace('"', '\\"')


def _build_ttl(documents: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> str:
    lines = [
        "@prefix : <http://mesitam.ac.in/ns#> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "",
        ":UploadedDocument a rdfs:Class .",
        ":UploadEntity a rdfs:Class .",
        ":hasName a rdf:Property .",
        ":description a rdf:Property .",
        ":sourceFile a rdf:Property .",
        ":appearsIn a rdf:Property .",
        ":keyFeature a rdf:Property .",
        "",
    ]

    for document in documents:
        resource = f":UploadDocument_{_slugify(document['id'])}"
        lines.extend(
            [
                f"{resource} a :UploadedDocument ;",
                f'    :hasName "{_escape_ttl_literal(document["title"])}" ;',
                f'    :description "{_escape_ttl_literal(document.get("summary", ""))}" ;',
                f'    :sourceFile "{_escape_ttl_literal(document.get("source_file", ""))}" .',
                "",
            ]
        )

    for entity in entities:
        entity_resource = f":UploadEntity_{_slugify(entity['id'])}"
        document_resource = f":UploadDocument_{_slugify(entity['document_id'])}"
        lines.extend(
            [
                f"{entity_resource} a :UploadEntity ;",
                f'    :hasName "{_escape_ttl_literal(entity["label"])}" ;',
                f'    :description "{_escape_ttl_literal(entity.get("description", ""))}" ;',
                f'    :sourceFile "{_escape_ttl_literal(entity.get("source_file", ""))}" ;',
                f"    :appearsIn {document_resource} ;",
            ]
        )
        features = entity.get("features", [])[:3]
        if features:
            for feature_index, feature in enumerate(features):
                terminator = " ;" if feature_index < len(features) - 1 else " ."
                lines.append(f'    :keyFeature "{_escape_ttl_literal(feature)}"{terminator}')
        else:
            lines[-1] = lines[-1][:-2] + " ."
        lines.append("")

    return "\n".join(lines)


class UploadKGService:
    def __init__(
        self,
        data_path: Path = UPLOAD_KNOWLEDGE_PATH,
        ttl_path: Path = UPLOAD_KG_PATH,
        upload_dir: Path = UPLOAD_DIR,
    ) -> None:
        self.data_path = data_path
        self.ttl_path = ttl_path
        self.upload_dir = upload_dir
        self._cache: Dict[str, Any] | None = None
        self._mtime: float | None = None
        self._lock = Lock()

    def _default_payload(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "index_version": "empty",
            "documents": [],
            "entities": [],
            "graph": {"nodes": [], "edges": []},
        }

    def _load_from_disk(self) -> Dict[str, Any]:
        if not self.data_path.exists():
            return self._default_payload()
        try:
            with self.data_path.open("r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except (json.JSONDecodeError, OSError):
            return self._default_payload()
        return payload if isinstance(payload, dict) else self._default_payload()

    def get_data(self, force_reload: bool = False) -> Dict[str, Any]:
        if (force_reload or not self.data_path.exists()) and any(self.upload_dir.glob("*.pdf")):
            return self.rebuild_from_uploads()
        with self._lock:
            mtime = self.data_path.stat().st_mtime if self.data_path.exists() else None
            if force_reload or self._cache is None or self._mtime != mtime:
                self._cache = self._load_from_disk()
                self._mtime = mtime
            return self._cache

    def rebuild_from_uploads(self) -> Dict[str, Any]:
        documents: List[Dict[str, Any]] = []
        entities: List[Dict[str, Any]] = []

        pdf_paths = sorted(path for path in self.upload_dir.glob("*.pdf") if path.is_file())
        for pdf_path in pdf_paths:
            text = _extract_pdf_text(pdf_path)
            sentences = _split_sentences(text)
            if not sentences:
                continue
            document_id = _slugify(pdf_path.name)
            document_entities = _extract_entities(sentences, pdf_path.name, document_id)
            document = {
                "id": document_id,
                "title": pdf_path.name,
                "source_file": pdf_path.name,
                "summary": document_entities[0]["description"] if document_entities else _best_summary(sentences),
            }
            document["entity_ids"] = [item["id"] for item in document_entities]
            documents.append(document)
            entities.extend(document_entities)

        digest_source = "|".join(
            f"{document['title']}:{document.get('summary', '')}:{','.join(document.get('entity_ids', []))}"
            for document in documents
        )
        index_version = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:12] if documents else "empty"
        graph = _build_graph(documents, entities)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat() if documents else None,
            "index_version": index_version,
            "documents": documents,
            "entities": entities,
            "graph": graph,
        }

        with self.data_path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2, ensure_ascii=False)
        self.ttl_path.write_text(_build_ttl(documents, entities), encoding="utf-8")
        merge_ttl_files()

        with self._lock:
            self._cache = payload
            self._mtime = self.data_path.stat().st_mtime if self.data_path.exists() else None
        return payload

    def entity_candidates(self) -> List[Dict[str, Any]]:
        return [
            {
                "label": entity.get("label", ""),
                "entity_type": "upload_entity",
                "aliases": entity.get("aliases") or _entity_aliases(entity.get("label", "")),
            }
            for entity in self.get_data().get("entities", [])
            if entity.get("label")
        ]

    def query_facts(self, question: str, max_facts: int = 6) -> List[Dict[str, Any]]:
        data = self.get_data()
        entities = data.get("entities", [])
        if not entities:
            return []

        keywords = extract_keywords(question)
        compact_queries = compact_query_forms(question)
        normalized_question = _normalize_text(question).lower()
        matches: List[tuple[float, Dict[str, Any]]] = []

        for entity in entities:
            label = entity.get("label", "")
            label_lower = label.lower()
            label_compact = compact_alphanumeric(label)
            score = 0.0
            if label_lower and label_lower in normalized_question:
                score += 1.0
            if label_compact and any(compact_query == label_compact or compact_query in label_compact for compact_query in compact_queries):
                score += 0.9
            overlap = len(set(keywords) & set(extract_keywords(label)))
            if keywords:
                score += overlap / max(len(set(keywords)), 1)
            if score >= 0.45:
                matches.append((score, entity))

        if not matches and len(keywords) == 1:
            token = keywords[0]
            for entity in entities:
                searchable = f"{entity.get('label', '')} {entity.get('description', '')}".lower()
                if token in searchable:
                    matches.append((0.5, entity))

        if not matches:
            return []

        matches.sort(key=lambda item: item[0], reverse=True)
        best_entity = matches[0][1]
        facts = [
            {
                "entity": best_entity.get("label", "Uploaded Entity"),
                "fact": best_entity.get("description", ""),
                "score": 0.94,
            }
        ]
        for feature in best_entity.get("features", [])[: max(0, max_facts - 1)]:
            facts.append({"entity": best_entity.get("label", "Uploaded Entity"), "fact": feature, "score": 0.88})
        return [fact for fact in facts if fact.get("fact")][:max_facts]


_upload_kg_service = UploadKGService()


def get_upload_kg_service() -> UploadKGService:
    return _upload_kg_service
