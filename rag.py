from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import re
import threading
import unicodedata
from collections import Counter
from typing import Any, Callable, Dict, Iterable, List, Optional

import faiss
import numpy as np
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from services.config import OFFICIAL_DOCUMENTS_PATH, UPLOAD_DIR
from services.department_aliases import department_aliases, question_mentions_alias
from services.knowledge_base import get_knowledge_base_service


EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
VECTOR_DB_PATH = "data/vector_store.index"
CHUNKS_METADATA_PATH = "data/chunks_metadata.pkl"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300
DEFAULT_MIN_SCORE = 0.2
INDEX_DIMENSION = 384
PAGE_MARKER_PATTERN = re.compile(r"\[PAGE\s+\d+\]")
SEARCH_STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "can",
    "could",
    "department",
    "define",
    "definition",
    "details",
    "describe",
    "dept",
    "do",
    "does",
    "explain",
    "for",
    "from",
    "head",
    "how",
    "hod",
    "in",
    "is",
    "meaning",
    "me",
    "of",
    "on",
    "overview",
    "please",
    "summarize",
    "summary",
    "tell",
    "the",
    "this",
    "to",
    "would",
    "what",
    "who",
    "with",
    "you",
    "your",
}
SPECIAL_QUERY_TERMS = ("nexrag", "rag system", "chatbot")
RETRIEVAL_VERSION = "intent-hybrid-fusion-v8"
SEMANTIC_FUSION_WEIGHT = 0.28
BM25_FUSION_WEIGHT = 0.16
KEYWORD_FUSION_WEIGHT = 0.18
RERANK_FUSION_WEIGHT = 0.38
ENTITY_COVERAGE_BONUS = 0.08
TITLE_SUPPORT_BONUS = 0.04
NOISE_PENALTY = 0.18
PRIMARY_VECTOR_TOP_K = 10
PRIMARY_BM25_TOP_K = 10
TITLE_FALLBACK_TOP_K = 6
MESITAM_BOILERPLATE_BLOCK_PATTERNS = (
    re.compile(
        r"(?:-->\s*)?Menu mobile Home About Administration Management Principal Vice Principal HODs "
        r"Administrative Staff.*?Contact Us Login\s*",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"Institution Code\s*:?\s*MEK\s+Important Links .*?All rights reserved\.?", re.IGNORECASE | re.DOTALL),
    re.compile(r"©\s*MESITAM\s*2017\..*?All rights reserved\.?", re.IGNORECASE | re.DOTALL),
    re.compile(r"(?:Read More\s*\.\s*){2,}", re.IGNORECASE),
)
NAVIGATION_TOKENS = {
    "about",
    "academic",
    "academics",
    "accreditation",
    "admission",
    "admissions",
    "administration",
    "administrative",
    "alumni",
    "anti",
    "approvals",
    "association",
    "campus",
    "cell",
    "central",
    "close",
    "code",
    "college",
    "committee",
    "committees",
    "contact",
    "contacts",
    "departments",
    "digital",
    "downloads",
    "events",
    "facilities",
    "gallery",
    "grievance",
    "header",
    "hods",
    "home",
    "image",
    "important",
    "industry",
    "institution",
    "iqac",
    "jobs",
    "library",
    "links",
    "login",
    "management",
    "menu",
    "mobile",
    "nptel",
    "nss",
    "online",
    "other",
    "photo",
    "placement",
    "portal",
    "previous",
    "programs",
    "questions",
    "ragging",
    "selection",
    "staff",
    "study",
    "syllabus",
    "telephone",
    "tenders",
    "tour",
    "video",
    "view",
    "website",
}
CONTACT_HINT_TOKENS = {"address", "admission", "contact", "email", "office", "phone", "postal", "principal"}
COMMON_NOISE_PHRASES = (
    "all rights reserved",
    "developed by",
    "important links",
    "menu mobile",
    "other links",
    "take a campus tour",
    "view image",
    "view all news",
    "view all events",
)
COMMON_TEXT_REPAIRS = {
    "andresponsetime": "and response time",
    "moreadvanced,asitincludesanautomatedalertmechanismthatnotifiesdoctorsor": "more advanced, as it includes an automated alert mechanism that notifies doctors or ",
    "submittedby": "submitted by",
    "nameofthe": "name of the ",
    "remotemonitoringandaccesstopatientdatathroughawebormobileinterface": "remote monitoring and access to patient data through a web or mobile interface",
    "universityregisterno": "university register no",
    "theAPJAbdulKalamTechnologicalUniversity": "the APJ Abdul Kalam Technological University",
    "inpartialfulfillmentoftherequirementsfortheawardof": "in partial fulfillment of the requirements for the award of ",
    "inComputerScienceandEngineering": "in Computer Science and Engineering",
    "ResultsandDiscussion": "Results and Discussion",
    "GraphicalAnalysis": "Graphical Analysis",
    "PerformanceAnalysis": "Performance Analysis",
    "SystemOverview": "System Overview",
    "VisionBehind": "Vision Behind ",
    "Listof": "List of ",
}
FRONT_MATTER_HINTS = (
    "acknowledgements",
    "certificate",
    "contents",
    "declaration",
    "list of figures",
    "list of tables",
    "name of the student",
    "project report",
    "signature",
    "submitted by",
    "university register no",
)
LOW_SIGNAL_SECTION_HINTS = (
    "case study",
    "graphical analysis",
    "performance analysis",
    "results and discussion",
    "result discussion",
)
COMPACT_QUERY_MIN_LENGTH = 8
RETRIEVAL_INTENT_PREFIX_PATTERN = re.compile(
    r"^(?:what\s+is|what['’]s|define|definition\s+of|meaning\s+of|explain|describe|tell\s+me\s+about|overview\s+of|summary\s+of|summarize)\s+",
    re.IGNORECASE,
)
RETRIEVAL_POLITE_PREFIX_PATTERN = re.compile(r"^(?:(?:can|could|would)\s+you\s+|please\s+)+", re.IGNORECASE)


def _model_load_kwargs() -> Dict[str, Any]:
    if os.environ.get("NEXRAG_ALLOW_MODEL_DOWNLOAD") == "1":
        return {}
    return {"local_files_only": True}


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def normalize_whitespace(text: str) -> str:
    return " ".join((text or "").split()).strip()


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").replace("\x00", " ")


def repair_extracted_spacing(text: str) -> str:
    repaired = normalize_text(text)
    repaired = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", repaired)
    repaired = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", repaired)
    for needle, replacement in COMMON_TEXT_REPAIRS.items():
        repaired = re.sub(re.escape(needle), replacement, repaired, flags=re.IGNORECASE)
    return repaired


def normalize_retrieval_query(query: str) -> str:
    normalized = normalize_whitespace(query)
    if not normalized:
        return ""
    stripped = RETRIEVAL_POLITE_PREFIX_PATTERN.sub("", normalized).strip()
    stripped = RETRIEVAL_INTENT_PREFIX_PATTERN.sub("", stripped).strip(" -:;,.?")
    return stripped or normalized


def strip_known_boilerplate(text: str) -> str:
    cleaned = normalize_text(text)
    for pattern in MESITAM_BOILERPLATE_BLOCK_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned


def is_noise_line(line: str) -> bool:
    normalized = normalize_whitespace(line)
    if not normalized:
        return True
    if PAGE_MARKER_PATTERN.fullmatch(normalized):
        return False

    lowered = normalized.lower()
    if any(phrase in lowered for phrase in COMMON_NOISE_PHRASES):
        return True

    tokens = re.findall(r"[a-z0-9]+", lowered)
    if not tokens:
        return True

    nav_hits = sum(1 for token in tokens if token in NAVIGATION_TOKENS)
    contact_hits = sum(1 for token in tokens if token in CONTACT_HINT_TOKENS)
    if len(tokens) >= 8 and nav_hits >= max(5, int(len(tokens) * 0.45)) and contact_hits == 0:
        return True

    if len(tokens) >= 6 and len(set(tokens)) <= max(2, len(tokens) // 4):
        return True

    return False


def clean_pdf_page_text(text: str) -> str:
    cleaned = repair_extracted_spacing(strip_known_boilerplate(text))
    lines: List[str] = []
    seen: set[str] = set()
    for raw_line in cleaned.splitlines():
        line = normalize_whitespace(raw_line)
        if not line or is_noise_line(line):
            continue
        key = line.lower()
        if key in seen and len(line.split()) <= 10:
            continue
        seen.add(key)
        lines.append(line)

    if lines:
        return "\n".join(lines)

    collapsed = normalize_whitespace(cleaned)
    if not collapsed or is_noise_line(collapsed):
        return ""
    return collapsed


def clean_document_text(text: str) -> str:
    cleaned = repair_extracted_spacing(strip_known_boilerplate(text))
    cleaned = PAGE_MARKER_PATTERN.sub(lambda match: f"\n{match.group(0)}\n", cleaned)

    normalized_lines = [normalize_whitespace(line) for line in cleaned.splitlines()]
    counts = Counter(
        line.lower()
        for line in normalized_lines
        if line and not PAGE_MARKER_PATTERN.fullmatch(line)
    )

    filtered_lines: List[str] = []
    last_key = ""
    for line in normalized_lines:
        if not line:
            continue
        if PAGE_MARKER_PATTERN.fullmatch(line):
            if filtered_lines and filtered_lines[-1] == line:
                continue
            filtered_lines.append(line)
            last_key = line.lower()
            continue
        if is_noise_line(line):
            continue
        key = line.lower()
        if counts[key] > 2 and len(line.split()) <= 6:
            continue
        if key == last_key and len(line.split()) <= 20:
            continue
        filtered_lines.append(line)
        last_key = key

    return "\n".join(filtered_lines).strip()


def make_chunk_id(source: str, page: Optional[int], text: str) -> str:
    digest = hashlib.sha1(f"{source}|{page}|{normalize_whitespace(text)[:240]}".encode("utf-8")).hexdigest()
    return digest[:16]


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def extract_keywords(query: str) -> List[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (query or "").lower())
    keywords = []
    for token in cleaned.split():
        if len(token) < 3 or token in SEARCH_STOPWORDS:
            continue
        if token not in keywords:
            keywords.append(token)
    return keywords


def normalize_for_search(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())


def compact_alphanumeric(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def compact_query_forms(query: str) -> List[str]:
    keywords = extract_keywords(query)
    compact_forms: List[str] = []
    if len(keywords) >= 2:
        joined_keywords = "".join(keywords)
        if len(joined_keywords) >= COMPACT_QUERY_MIN_LENGTH:
            compact_forms.append(joined_keywords)
    return compact_forms


def chunk_section_penalty(text: str) -> float:
    lowered = normalize_whitespace(text).lower()
    compact = compact_alphanumeric(text)
    penalty = 0.0

    if any(term in lowered for term in FRONT_MATTER_HINTS):
        penalty += 0.26
    if any(compact_term in compact for compact_term in ("submittedby", "nameofthestudent", "universityregisterno")):
        penalty += 0.2
    if any(term in lowered for term in LOW_SIGNAL_SECTION_HINTS):
        penalty += 0.12

    long_alpha_tokens = re.findall(r"[a-z]{24,}", lowered)
    if long_alpha_tokens:
        penalty += min(0.12, 0.04 * len(long_alpha_tokens))

    return penalty


def split_document_sections(text: str) -> List[tuple[Optional[int], str]]:
    cleaned = clean_document_text(text)
    if not cleaned:
        return []

    matches = list(PAGE_MARKER_PATTERN.finditer(cleaned))
    if not matches:
        return [(None, cleaned)]

    sections: List[tuple[Optional[int], str]] = []
    for index, match in enumerate(matches):
        page_match = re.search(r"\[PAGE\s+(\d+)\]", match.group(0))
        page = int(page_match.group(1)) if page_match else None
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        section_text = normalize_whitespace(cleaned[start:end])
        if section_text:
            sections.append((page, section_text))
    return sections


class RAGEngine:
    def __init__(self) -> None:
        model_kwargs = _model_load_kwargs()
        print("Loading embedding model...")
        self.encoder = SentenceTransformer(EMBEDDING_MODEL_NAME, **model_kwargs)
        print("Loading reranker...")
        self.reranker = CrossEncoder(RERANK_MODEL_NAME, **model_kwargs)
        self.index: faiss.Index | None = None
        self.index_metric = "ip"
        self.chunks_metadata: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        self._mutation_lock = threading.RLock()
        self._query_expansion_cache: Dict[str, List[str]] = {}
        self._load_index()

    def _preprocess(self, text: str) -> str:
        return normalize_for_search(text)

    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        normalized = np.asarray(embeddings, dtype="float32")
        if normalized.ndim == 1:
            normalized = normalized.reshape(1, -1)
        faiss.normalize_L2(normalized)
        return normalized

    def _score_from_distance(self, distance: float) -> float:
        if self.index_metric == "ip":
            return clamp_score((distance + 1.0) / 2.0)
        return clamp_score(1.0 / (1.0 + float(distance)))

    def _ensure_index(self) -> None:
        if self.index is None:
            self.index = faiss.IndexFlatIP(INDEX_DIMENSION)
            self.index_metric = "ip"

    def _rebuild_bm25(self) -> None:
        if not self.chunks_metadata:
            self.bm25 = None
            return
        tokenized_docs = [self._preprocess(chunk["text"]).split() for chunk in self.chunks_metadata]
        self.bm25 = BM25Okapi(tokenized_docs)

    def _load_index(self) -> None:
        if os.path.exists(VECTOR_DB_PATH) and os.path.exists(CHUNKS_METADATA_PATH):
            print("Loading vector store from disk...")
            self.index = faiss.read_index(VECTOR_DB_PATH)
            self.index_metric = "ip" if getattr(self.index, "metric_type", faiss.METRIC_L2) == faiss.METRIC_INNER_PRODUCT else "l2"
            with open(CHUNKS_METADATA_PATH, "rb") as file_handle:
                self.chunks_metadata = pickle.load(file_handle)
            for chunk in self.chunks_metadata:
                chunk.setdefault("title", chunk.get("source", "Official Source"))
                chunk.setdefault("chunk_id", make_chunk_id(chunk.get("source", "Official Source"), chunk.get("page"), chunk.get("text", "")))
            self._rebuild_bm25()
            return

        print("No existing vector store found. Initializing new one.")
        self.index = faiss.IndexFlatIP(INDEX_DIMENSION)
        self.index_metric = "ip"
        self.chunks_metadata = []
        self.bm25 = None

    def _save_index(self) -> None:
        os.makedirs("data", exist_ok=True)
        if self.index is None:
            self._ensure_index()
        faiss.write_index(self.index, VECTOR_DB_PATH)
        with open(CHUNKS_METADATA_PATH, "wb") as file_handle:
            pickle.dump(self.chunks_metadata, file_handle)

    def extract_text(self, pdf_path: str) -> str:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                page_text = clean_pdf_page_text(page.extract_text() or "")
                if page_text:
                    text += f"[PAGE {page_index}]\n{page_text}\n"
        return text

    def chunk_text(self, text: str, source: str = "unknown") -> List[Dict[str, Any]]:
        sections = split_document_sections(text)
        if not sections:
            return []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", " ", ""],
        )
        payloads: List[Dict[str, Any]] = []
        chunk_index = 0
        for page, section_text in sections:
            for chunk in splitter.split_text(section_text):
                cleaned_chunk = chunk.strip()
                if not cleaned_chunk:
                    continue
                payloads.append(
                    {
                        "chunk_id": make_chunk_id(source, page, f"{chunk_index}:{cleaned_chunk}"),
                        "text": cleaned_chunk,
                        "source": source,
                        "title": source,
                        "page": page,
                    }
                )
                chunk_index += 1
        return payloads

    def reset_store(self) -> None:
        with self._mutation_lock:
            self.index = faiss.IndexFlatIP(INDEX_DIMENSION)
            self.index_metric = "ip"
            self.chunks_metadata = []
            self.bm25 = None

    def _encode_and_add(self, chunks: List[Dict[str, Any]], progress_callback: Optional[Callable[[str, Optional[str]], None]] = None) -> int:
        if not chunks:
            return 0
        if progress_callback:
            progress_callback("embedding", "Generating embeddings...")
        embeddings = self.encoder.encode([chunk["text"] for chunk in chunks], convert_to_numpy=True)
        normalized_embeddings = self._normalize_embeddings(embeddings)
        self._ensure_index()
        self.index.add(normalized_embeddings)
        self.chunks_metadata.extend(chunks)
        return len(chunks)

    def _build_chunks_from_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        text = document.get("text", "")
        source = document.get("title") or document.get("source") or "Official Source"
        category = document.get("category", "General")
        source_url = document.get("url")
        source_type = document.get("source_type", "official")
        chunk_payloads = self.chunk_text(text, source=source)
        for chunk in chunk_payloads:
            chunk["category"] = category
            chunk["source_url"] = source_url
            chunk["source_type"] = source_type
            chunk["title"] = source
        return chunk_payloads

    def index_pdf(
        self,
        pdf_path: str,
        category: str = "General",
        progress_callback: Optional[Callable[[str, Optional[str]], None]] = None,
    ) -> int:
        with self._mutation_lock:
            text = self.extract_text(pdf_path)
            if progress_callback:
                progress_callback("chunking", "Chunking document...")
            source = os.path.basename(pdf_path)
            new_chunks = self.chunk_text(text, source=source)
            if not new_chunks:
                return 0

            for chunk in new_chunks:
                chunk["category"] = category
                chunk["source_type"] = "upload"
                chunk["source_url"] = None
                chunk["title"] = source

            indexed_count = self._encode_and_add(new_chunks, progress_callback=progress_callback)
            self._rebuild_bm25()
            self._save_index()
            return indexed_count

    def rebuild_from_directory(self, pdf_dir: str, category: str = "General") -> int:
        return self.rebuild_from_sources(upload_dir=pdf_dir, official_documents=None, upload_category=category)

    def rebuild_from_sources(
        self,
        upload_dir: Optional[str] = None,
        official_documents: Optional[List[Dict[str, Any]]] = None,
        upload_category: str = "General",
    ) -> int:
        upload_dir = upload_dir or str(UPLOAD_DIR)
        if official_documents is None:
            official_documents = self.load_official_documents()

        pdf_paths = [
            os.path.join(upload_dir, file_name)
            for file_name in sorted(os.listdir(upload_dir))
            if file_name.lower().endswith(".pdf")
        ] if os.path.exists(upload_dir) else []

        with self._mutation_lock:
            self.reset_store()
            total_chunks = 0

            for document in official_documents:
                total_chunks += self._encode_and_add(self._build_chunks_from_document(document))

            for pdf_path in pdf_paths:
                text = self.extract_text(pdf_path)
                new_chunks = self.chunk_text(text, source=os.path.basename(pdf_path))
                if not new_chunks:
                    continue
                for chunk in new_chunks:
                    chunk["category"] = upload_category
                    chunk["source_type"] = "upload"
                    chunk["source_url"] = None
                    chunk["title"] = os.path.basename(pdf_path)
                total_chunks += self._encode_and_add(new_chunks)

            self._rebuild_bm25()
            self._save_index()
            return total_chunks

    def load_official_documents(self) -> List[Dict[str, Any]]:
        if not os.path.exists(OFFICIAL_DOCUMENTS_PATH):
            return []
        with open(OFFICIAL_DOCUMENTS_PATH, "r", encoding="utf-8") as file_handle:
            documents = json.load(file_handle)
        return [item for item in documents if item.get("text")]

    def _metadata_for_index(self, idx: int) -> Dict[str, Any]:
        item = dict(self.chunks_metadata[idx])
        item.setdefault("title", item.get("source", "Official Source"))
        item.setdefault("chunk_id", make_chunk_id(item.get("source", "Official Source"), item.get("page"), item.get("text", "")))
        return item

    def _passes_filter(self, item: Dict[str, Any], filter_category: Optional[str]) -> bool:
        if filter_category and item.get("category", "General") != filter_category:
            return False
        return True

    def _expand_department_aliases(self, query: str) -> List[str]:
        normalized_query = normalize_for_search(query)
        best_match: Optional[Dict[str, Any]] = None
        best_score = 0.0

        for department in get_knowledge_base_service().public_sections().get("departments", []):
            name = normalize_whitespace(department.get("name") or "")
            if not name:
                continue
            aliases = department_aliases(name)
            score = 0.0
            for alias in aliases:
                if not question_mentions_alias(normalized_query, alias):
                    continue
                if " " not in alias:
                    score = max(score, 4.0)
                else:
                    score = max(score, 5.0 + min(alias.count(" ") + 1, 3) * 0.2)
            if score > best_score:
                best_score = score
                best_match = {"name": name, "aliases": aliases}

        if not best_match:
            return []

        expanded = [best_match["name"]]
        descriptive_aliases = [
            alias
            for alias in best_match["aliases"]
            if " " in alias and "department" not in alias and "dept" not in alias and len(alias) >= 8
        ]
        descriptive_aliases.sort(key=len, reverse=True)
        expanded.extend(descriptive_aliases[:1])
        return expanded[:2]

    def expand_query(self, query: str) -> List[str]:
        normalized_query = normalize_whitespace(query)
        if not normalized_query:
            return []
        if normalized_query in self._query_expansion_cache:
            return self._query_expansion_cache[normalized_query]

        department_alias_terms = self._expand_department_aliases(normalized_query)
        keywords = extract_keywords(query)
        keyword_query = " ".join(keywords) if keywords else ""
        compact_queries = compact_query_forms(query)
        lowered_query = normalized_query.lower()

        merged_terms: List[str] = []
        seen_terms = set()
        for term in [normalized_query, lowered_query, *department_alias_terms, keyword_query, *compact_queries]:
            normalized_term = normalize_whitespace(term)
            if not normalized_term or normalized_term in seen_terms:
                continue
            seen_terms.add(normalized_term)
            merged_terms.append(normalized_term)

        self._query_expansion_cache[normalized_query] = merged_terms[:3]
        return self._query_expansion_cache[normalized_query]

    def _keywords_for_query(self, query: str) -> List[str]:
        keywords = extract_keywords(query)
        if keywords:
            return keywords

        alias_keywords: List[str] = []
        for alias_term in self._expand_department_aliases(query):
            for token in extract_keywords(alias_term):
                if token not in alias_keywords:
                    alias_keywords.append(token)
        return alias_keywords

    def _query_vector(self, query: str) -> np.ndarray:
        embedding = self.encoder.encode([query], convert_to_numpy=True)
        return self._normalize_embeddings(embedding)

    def _collect_vector_candidates(
        self,
        query_variants: Iterable[str],
        top_k: int,
        filter_category: Optional[str],
        candidate_multiplier: int = 6,
    ) -> Dict[str, Dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return {}

        collected: Dict[str, Dict[str, Any]] = {}
        candidate_limit = max(top_k * candidate_multiplier, top_k)
        for query_variant in query_variants:
            distances, indices = self.index.search(self._query_vector(query_variant), candidate_limit)
            for rank_index, idx in enumerate(indices[0]):
                if idx == -1 or idx >= len(self.chunks_metadata):
                    continue
                item = self._metadata_for_index(int(idx))
                if not self._passes_filter(item, filter_category):
                    continue
                key = item["chunk_id"]
                vector_score = self._score_from_distance(float(distances[0][rank_index]))
                current = collected.get(key, dict(item))
                current["vector_score"] = max(vector_score, current.get("vector_score", 0.0))
                current.setdefault("keyword_match_score", 0.0)
                current.setdefault("title_match_score", 0.0)
                current.setdefault("bm25_score", 0.0)
                current.setdefault("reranker_score", 0.0)
                current.setdefault("forced_match", False)
                current.setdefault("match_type", "vector")
                current.setdefault("matched_passes", [])
                if "vector" not in current["matched_passes"]:
                    current["matched_passes"].append("vector")
                collected[key] = current
        return collected

    def _collect_bm25_candidates(
        self,
        query: str,
        filter_category: Optional[str],
        limit: int = 20,
    ) -> Dict[str, Dict[str, Any]]:
        if self.bm25 is None or not self.chunks_metadata:
            return {}

        query_terms = self._keywords_for_query(query)
        if not query_terms:
            query_terms = self._preprocess(query).split()
        scores = self.bm25.get_scores(query_terms)
        ranked_indices = np.argsort(scores)[::-1][:limit]
        max_score = max([float(scores[idx]) for idx in ranked_indices], default=0.0)
        collected: Dict[str, Dict[str, Any]] = {}
        for idx in ranked_indices:
            raw_score = float(scores[idx])
            if raw_score <= 0:
                continue
            item = self._metadata_for_index(int(idx))
            if not self._passes_filter(item, filter_category):
                continue
            key = item["chunk_id"]
            current = collected.get(key, dict(item))
            current.setdefault("vector_score", 0.0)
            current.setdefault("keyword_match_score", 0.0)
            current.setdefault("title_match_score", 0.0)
            current.setdefault("reranker_score", 0.0)
            current.setdefault("forced_match", False)
            current["bm25_score"] = max(raw_score / max_score if max_score else 0.0, current.get("bm25_score", 0.0))
            current["match_type"] = "keyword"
            current.setdefault("matched_passes", [])
            if "bm25" not in current["matched_passes"]:
                current["matched_passes"].append("bm25")
            collected[key] = current
        return collected

    def _compute_title_match_score(self, query: str, item: Dict[str, Any]) -> float:
        keywords = self._keywords_for_query(query)
        compact_queries = compact_query_forms(query)
        if not keywords and not compact_queries:
            return 0.0
        search_target = normalize_for_search(f"{item.get('title', '')} {item.get('source', '')}")
        matches = sum(1 for keyword in keywords if re.search(rf"(^|[^a-z0-9]){re.escape(keyword)}([^a-z0-9]|$)", search_target))
        compact_target = compact_alphanumeric(search_target)
        compact_matches = sum(1 for compact_query in compact_queries if compact_query and compact_query in compact_target)
        matches += compact_matches
        if not matches:
            return 0.0
        total_terms = max(len(keywords) + len(compact_queries), 1)
        return clamp_score(0.35 + (matches / total_terms) * 0.45)

    def _collect_title_matches(self, query: str, filter_category: Optional[str], limit: int = 12) -> Dict[str, Dict[str, Any]]:
        collected: Dict[str, Dict[str, Any]] = {}
        for idx in range(len(self.chunks_metadata)):
            metadata = self._metadata_for_index(idx)
            if not self._passes_filter(metadata, filter_category):
                continue
            title_match_score = self._compute_title_match_score(query, metadata)
            if title_match_score <= 0:
                continue
            key = metadata["chunk_id"]
            current = collected.get(key, dict(metadata))
            current.setdefault("vector_score", 0.0)
            current.setdefault("bm25_score", 0.0)
            current.setdefault("keyword_match_score", 0.0)
            current.setdefault("reranker_score", 0.0)
            current.setdefault("forced_match", False)
            current["title_match_score"] = max(title_match_score, current.get("title_match_score", 0.0))
            current["match_type"] = "title"
            current.setdefault("matched_passes", [])
            if "title" not in current["matched_passes"]:
                current["matched_passes"].append("title")
            collected[key] = current
            if len(collected) >= limit:
                break
        return collected

    def _keyword_match_score(self, query: str, item: Dict[str, Any]) -> tuple[float, Optional[str]]:
        keywords = self._keywords_for_query(query)
        compact_queries = compact_query_forms(query)
        if not keywords and not compact_queries:
            return 0.0, None

        searchable_text = normalize_for_search(f"{item.get('text', '')} {item.get('title', '')} {item.get('source', '')}")
        normalized_query = normalize_for_search(query).strip()
        if normalized_query and re.search(rf"(^|[^a-z0-9]){re.escape(normalized_query)}([^a-z0-9]|$)", searchable_text):
            return 1.0, "exact_keyword"

        compact_searchable = compact_alphanumeric(searchable_text)
        if compact_queries and any(compact_query in compact_searchable for compact_query in compact_queries):
            return 0.84, "compact_phrase"

        whole_word_hits = sum(
            1 for keyword in keywords
            if re.search(rf"(^|[^a-z0-9]){re.escape(keyword)}([^a-z0-9]|$)", searchable_text)
        )
        if whole_word_hits:
            score = clamp_score(0.75 + (whole_word_hits / len(keywords)) * 0.2)
            return score, "exact_keyword"

        if normalized_query and normalized_query in searchable_text:
            return 0.72, "phrase"

        partial_hits = sum(1 for keyword in keywords if keyword in searchable_text)
        if partial_hits:
            score = clamp_score(0.52 + (partial_hits / len(keywords)) * 0.16)
            return score, "partial"

        return 0.0, None

    def _collect_exact_keyword_matches(self, query: str, filter_category: Optional[str]) -> Dict[str, Dict[str, Any]]:
        collected: Dict[str, Dict[str, Any]] = {}
        for idx in range(len(self.chunks_metadata)):
            item = self._metadata_for_index(idx)
            if not self._passes_filter(item, filter_category):
                continue
            keyword_score, match_type = self._keyword_match_score(query, item)
            if keyword_score <= 0:
                continue
            key = item["chunk_id"]
            current = collected.get(key, dict(item))
            current.setdefault("vector_score", 0.0)
            current.setdefault("bm25_score", 0.0)
            current.setdefault("title_match_score", 0.0)
            current.setdefault("reranker_score", 0.0)
            current["keyword_match_score"] = max(keyword_score, current.get("keyword_match_score", 0.0))
            current["forced_match"] = True
            current["match_type"] = match_type or "keyword"
            current.setdefault("matched_passes", [])
            if "exact_keyword" not in current["matched_passes"]:
                current["matched_passes"].append("exact_keyword")
            collected[key] = current
        return collected

    def _apply_special_query_boost(self, query: str, filter_category: Optional[str]) -> Dict[str, Dict[str, Any]]:
        lowered = (query or "").lower()
        if not any(term in lowered for term in SPECIAL_QUERY_TERMS):
            return {}

        collected: Dict[str, Dict[str, Any]] = {}
        for idx in range(len(self.chunks_metadata)):
            item = self._metadata_for_index(idx)
            if not self._passes_filter(item, filter_category):
                continue
            title_blob = f"{item.get('title', '')} {item.get('source', '')}".lower()
            body_blob = item.get("text", "").lower()
            if "nexrag" not in title_blob and "report" not in title_blob and "nexrag" not in body_blob:
                continue
            key = item["chunk_id"]
            current = dict(item)
            current.setdefault("vector_score", 0.0)
            current.setdefault("bm25_score", 0.0)
            current["title_match_score"] = max(current.get("title_match_score", 0.0), 0.85 if "nexrag" in title_blob else 0.65)
            current["keyword_match_score"] = max(current.get("keyword_match_score", 0.0), 0.65 if "nexrag" in body_blob else 0.45)
            current["reranker_score"] = current.get("reranker_score", 0.0)
            current["forced_match"] = True
            current["match_type"] = "title"
            current["matched_passes"] = ["special_boost"]
            collected[key] = current
        return dict(sorted(collected.items(), key=lambda item: item[1].get("title_match_score", 0.0), reverse=True)[:4])

    def _merge_candidates(self, base: Dict[str, Dict[str, Any]], incoming: Dict[str, Dict[str, Any]]) -> None:
        for key, item in incoming.items():
            if key not in base:
                base[key] = dict(item)
                continue
            current = base[key]
            for field in ["vector_score", "bm25_score", "title_match_score", "keyword_match_score", "reranker_score"]:
                current[field] = max(current.get(field, 0.0), item.get(field, 0.0))
            current["forced_match"] = current.get("forced_match", False) or item.get("forced_match", False)
            if item.get("match_type") == "exact_keyword":
                current["match_type"] = "exact_keyword"
            elif current.get("match_type") != "exact_keyword":
                current["match_type"] = item.get("match_type", current.get("match_type", "vector"))
            current.setdefault("matched_passes", [])
            for matched_pass in item.get("matched_passes", []):
                if matched_pass not in current["matched_passes"]:
                    current["matched_passes"].append(matched_pass)

    def _entity_coverage_score(self, query: str, item: Dict[str, Any]) -> float:
        focus_terms = extract_keywords(query)
        if not focus_terms:
            return 0.0

        searchable_text = normalize_for_search(f"{item.get('title', '')} {item.get('source', '')} {item.get('text', '')[:400]}")
        matched_terms = sum(
            1
            for term in focus_terms
            if re.search(rf"(^|[^a-z0-9]){re.escape(term)}([^a-z0-9]|$)", searchable_text)
        )
        if not matched_terms:
            return 0.0
        return clamp_score(matched_terms / max(len(focus_terms), 1))

    def _rerank_candidates(self, query: str, candidates: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        candidate_list = list(candidates.values())
        if not candidate_list:
            return []

        pairs = [[query, candidate["text"]] for candidate in candidate_list]
        raw_scores = self.reranker.predict(pairs)
        for index, raw_score in enumerate(raw_scores):
            candidate_list[index]["reranker_score"] = max(candidate_list[index].get("reranker_score", 0.0), sigmoid(float(raw_score)))
        for candidate in candidate_list:
            keyword_score, keyword_match_type = self._keyword_match_score(query, candidate)
            candidate["keyword_match_score"] = max(candidate.get("keyword_match_score", 0.0), keyword_score)
            candidate["title_match_score"] = max(candidate.get("title_match_score", 0.0), self._compute_title_match_score(query, candidate))
            candidate["entity_coverage"] = self._entity_coverage_score(query, candidate)
            noise_penalty = NOISE_PENALTY if is_noise_line(candidate.get("text", "")[:220]) else 0.0
            section_penalty = chunk_section_penalty(candidate.get("text", ""))
            candidate["noise_penalty"] = noise_penalty
            candidate["section_penalty"] = section_penalty
            if keyword_match_type and candidate.get("match_type") == "vector":
                candidate["match_type"] = keyword_match_type
            fusion_score = (
                candidate.get("vector_score", 0.0) * SEMANTIC_FUSION_WEIGHT
                + candidate.get("bm25_score", 0.0) * BM25_FUSION_WEIGHT
                + candidate.get("keyword_match_score", 0.0) * KEYWORD_FUSION_WEIGHT
                + candidate.get("reranker_score", 0.0) * RERANK_FUSION_WEIGHT
                + candidate.get("entity_coverage", 0.0) * ENTITY_COVERAGE_BONUS
                + candidate.get("title_match_score", 0.0) * TITLE_SUPPORT_BONUS
                - noise_penalty
                - section_penalty
            )
            candidate["score"] = clamp_score(fusion_score)
            candidate["sort_tuple"] = (
                candidate["score"],
                candidate.get("reranker_score", 0.0),
                candidate.get("entity_coverage", 0.0),
                candidate.get("vector_score", 0.0),
                candidate.get("bm25_score", 0.0),
                candidate.get("title_match_score", 0.0),
                candidate.get("keyword_match_score", 0.0),
            )
        candidate_list.sort(key=lambda item: item["sort_tuple"], reverse=True)
        return candidate_list

    def _is_strong_evidence(self, results: List[Dict[str, Any]]) -> bool:
        if not results:
            return False
        top = results[0]
        return bool(
            top.get("forced_match")
            or top.get("reranker_score", 0.0) >= 0.82
            or top.get("vector_score", 0.0) >= 0.8
            or top.get("title_match_score", 0.0) >= 0.9
        )

    def _is_usable_evidence(self, results: List[Dict[str, Any]]) -> bool:
        if not results:
            return False
        top = results[0]
        return bool(
            top.get("forced_match")
            or top.get("keyword_match_score", 0.0) >= 0.5
            or top.get("title_match_score", 0.0) >= 0.45
            or top.get("reranker_score", 0.0) >= 0.4
            or top.get("vector_score", 0.0) >= 0.38
        )

    def _filter_final_results(self, results: List[Dict[str, Any]], top_k: int, min_score: float) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for item in results:
            keep = (
                item.get("score", 0.0) >= max(min_score, 0.3)
                and (
                    item.get("keyword_match_score", 0.0) >= 0.52
                    or item.get("reranker_score", 0.0) >= 0.45
                    or item.get("vector_score", 0.0) >= 0.42
                    or item.get("bm25_score", 0.0) >= 0.18
                    or item.get("title_match_score", 0.0) >= 0.5
                )
            )
            if keep:
                filtered.append(item)
            if len(filtered) >= top_k:
                break
        return filtered

    def retrieve_with_fallbacks(
        self,
        query: str,
        top_k: int = 5,
        filter_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        diagnostics: Dict[str, Any] = {
            "query": query,
            "expanded_queries": [],
            "passes": [],
            "results": [],
            "retrieval_version": RETRIEVAL_VERSION,
        }
        if self.index is None or self.index.ntotal == 0:
            return diagnostics

        search_query = normalize_retrieval_query(query)
        diagnostics["normalized_query"] = search_query
        query_variants = self.expand_query(search_query) or [search_query]
        diagnostics["expanded_queries"] = query_variants
        merged_candidates: Dict[str, Dict[str, Any]] = {}

        vector_candidates = self._collect_vector_candidates(
            query_variants,
            top_k=PRIMARY_VECTOR_TOP_K,
            filter_category=filter_category,
            candidate_multiplier=1,
        )
        bm25_candidates = self._collect_bm25_candidates(
            search_query,
            filter_category=filter_category,
            limit=PRIMARY_BM25_TOP_K,
        )
        exact_keyword_candidates: Dict[str, Dict[str, Any]] = {}
        for query_variant in query_variants:
            self._merge_candidates(
                exact_keyword_candidates,
                self._collect_exact_keyword_matches(query_variant, filter_category=filter_category),
            )
        self._merge_candidates(merged_candidates, vector_candidates)
        self._merge_candidates(merged_candidates, bm25_candidates)
        self._merge_candidates(merged_candidates, exact_keyword_candidates)
        ranked = self._rerank_candidates(search_query, merged_candidates)
        diagnostics["passes"].append(
            {
                "name": "hybrid_union",
                "candidates": len(merged_candidates),
                "top_score": ranked[0]["score"] if ranked else 0.0,
            }
        )
        diagnostics["passes"].append(
            {
                "name": "exact_keyword_scan",
                "candidates": len(exact_keyword_candidates),
                "top_score": max((item.get("keyword_match_score", 0.0) for item in exact_keyword_candidates.values()), default=0.0),
            }
        )

        if len(ranked) < max(3, min(top_k, 6)):
            title_candidates = self._collect_title_matches(search_query, filter_category=filter_category, limit=TITLE_FALLBACK_TOP_K)
            self._merge_candidates(merged_candidates, title_candidates)
            ranked = self._rerank_candidates(search_query, merged_candidates)
            diagnostics["passes"].append(
                {
                    "name": "title_fallback",
                    "candidates": len(title_candidates),
                    "top_score": ranked[0]["score"] if ranked else 0.0,
                }
            )

        diagnostics["results"] = self._filter_final_results(ranked, top_k=top_k, min_score=DEFAULT_MIN_SCORE)
        diagnostics["has_evidence"] = bool(diagnostics["results"])
        return diagnostics

    def retrieve(self, query: str, top_k: int = 5, filter_category: Optional[str] = None, min_score: float = DEFAULT_MIN_SCORE) -> List[Dict[str, Any]]:
        diagnostics = self.retrieve_with_fallbacks(query, top_k=top_k, filter_category=filter_category)
        return self._filter_final_results(diagnostics["results"], top_k=top_k, min_score=min_score)


_global_engine: Optional[RAGEngine] = None
_global_engine_error: Optional[Exception] = None
_vector_store_stats_cache: Dict[str, Any] | None = None
_vector_store_stats_cache_key: tuple[bool, float | None] | None = None


def get_rag_engine(force_reload: bool = False) -> RAGEngine:
    global _global_engine, _global_engine_error

    if force_reload:
        _global_engine = None
        _global_engine_error = None

    if _global_engine is None and _global_engine_error is None:
        try:
            _global_engine = RAGEngine()
        except Exception as exc:
            _global_engine_error = exc
            raise

    if _global_engine_error is not None:
        raise RuntimeError(f"RAG engine unavailable: {_global_engine_error}") from _global_engine_error

    return _global_engine


def _get_global_engine() -> Optional[RAGEngine]:
    return _global_engine


def index_pdf(pdf_path: str, category: str = "General") -> int:
    return get_rag_engine().index_pdf(pdf_path, category)


def retrieve(query: str, top_k: int = 5, filter_category: Optional[str] = None, min_score: float = DEFAULT_MIN_SCORE) -> List[Dict[str, Any]]:
    return get_rag_engine().retrieve(query, top_k, filter_category, min_score)


def get_retrieval_version() -> str:
    return RETRIEVAL_VERSION


def get_vector_store_stats() -> Dict[str, Any]:
    global _vector_store_stats_cache, _vector_store_stats_cache_key

    chunk_count = 0
    vector_ready = os.path.exists(VECTOR_DB_PATH) and os.path.exists(CHUNKS_METADATA_PATH)
    metadata_mtime = os.path.getmtime(CHUNKS_METADATA_PATH) if os.path.exists(CHUNKS_METADATA_PATH) else None
    cache_key = (vector_ready, metadata_mtime)

    if _vector_store_stats_cache_key == cache_key and _vector_store_stats_cache is not None:
        return dict(_vector_store_stats_cache)

    if os.path.exists(CHUNKS_METADATA_PATH):
        try:
            with open(CHUNKS_METADATA_PATH, "rb") as file_handle:
                metadata = pickle.load(file_handle)
            chunk_count = len(metadata)
        except Exception:
            engine = _get_global_engine()
            if engine and engine.chunks_metadata:
                chunk_count = len(engine.chunks_metadata)

    payload = {
        "chunks": chunk_count,
        "vector_ready": vector_ready,
        "retrieval_version": RETRIEVAL_VERSION,
    }
    _vector_store_stats_cache = payload
    _vector_store_stats_cache_key = cache_key
    return dict(payload)
