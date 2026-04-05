from __future__ import annotations

import math
import re
import time
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from kg import query_kg_facts
from llm import generate_answer
from rag import compact_alphanumeric, compact_query_forms, extract_keywords, get_retrieval_version, is_noise_line, repair_extracted_spacing
from router import get_intent

from .cache import get_response_cache
from .department_aliases import department_aliases, normalize_department_text, question_mentions_alias
from .knowledge_base import get_knowledge_base_service
from .pipeline_v2.context_fusion import optimize_context_budget
from .pipeline_v2.orchestrator import run_hybrid_pipeline


FOLLOW_UP_REFERENCE_PATTERN = re.compile(
    r"\b(he|she|they|them|their|theirs|his|her|hers|its|it|this|that|these|those|former|latter)\b"
)
FOLLOW_UP_STARTERS = (
    "and ",
    "also ",
    "then ",
    "what about",
    "how about",
    "what is his",
    "what is her",
    "what is their",
    "what about his",
    "what about her",
    "tell me more",
    "more about",
)
INTENT_CATEGORY_FILTERS = {
    "REGULATION": "Regulation",
    "COURSE_INFO": "Course",
}
STRICT_REFUSAL = "I don't have enough information in the knowledge base"
DEPARTMENT_QUERY_TERMS = ("department", "dept", "hod", "head of department")
QUALIFIER_ALIASES = {
    "artificial intelligence": {"artificial intelligence", " ai ", "(ai)", " ai)", "( ai ", " cse ai ", "cseai"},
}
QUESTION_TYPE_FACT = "fact"
QUESTION_TYPE_DEFINITION = "definition"
QUESTION_TYPE_EXPLANATION = "explanation"
CHAT_PIPELINE_VERSION = "chat-v3"
MAX_RETRIEVED_CHUNKS = 5
MAX_FILTERED_SENTENCES = 5
MAX_EXPLANATION_RETRIEVED_CHUNKS = 8
MAX_EXPLANATION_FILTERED_SENTENCES = 8
GENERATION_CONFIDENCE_THRESHOLD = 0.72
SEMANTIC_SIMILARITY_THRESHOLD = 0.34
KG_FACT_SCORE_FLOOR = 0.78
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|(?<=:)\s+(?=[A-Z0-9])|\n+")
TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")
PERSON_NAME_PATTERN = re.compile(
    r"(?:Prof(?:\s*\(Dr\)|\s+Dr\.?)?\.?|Dr\.?|Mr\.?|Mrs\.?|Ms\.?)\s+[A-Z][A-Za-z.\-]*(?:\s+[A-Z][A-Za-z.\-()]*){0,6}"
)
UPLOAD_PERSON_REGISTER_PATTERN = re.compile(r"\b[A-Z]{2,5}\d{2}[A-Z]{2,4}\d{2,4}\b")
UPLOAD_PERSON_YEAR_PATTERN = re.compile(r"\b20\d{2}\s*[–-]\s*20\d{2}\b")
UPLOAD_PERSON_PROJECT_PATTERNS = (
    re.compile(r'(?is)entitled\s+[“"]?(?P<title>[A-Z0-9][A-Z0-9:,&()\'/\-\s]{8,180}?)[”"]?\s+is\s+the\s+report'),
    re.compile(r"(?is)(?P<title>[A-Z0-9][A-Z0-9:,&()'/\-\s]{8,180}?)\s+PROJECT\s+REPORT"),
)
UPLOAD_PERSON_DEPARTMENT_PATTERN = re.compile(r"\bDepartment of [A-Za-z&(), ]{6,120}")
ROLE_QUERY_LABELS = (
    (("vice principal",), "Vice Principal"),
    (("head of department", "hod"), "Head of Department"),
    (("principal",), "Principal"),
    (("dean",), "Dean"),
    (("director",), "Director"),
)
GROUNDING_QUERY_STOPWORDS = {
    "about",
    "can",
    "could",
    "define",
    "definition",
    "describe",
    "explain",
    "find",
    "give",
    "how",
    "list",
    "meaning",
    "me",
    "name",
    "overview",
    "please",
    "show",
    "summarize",
    "summary",
    "tell",
    "walk",
    "when",
    "where",
    "which",
    "who",
    "why",
    "what",
    "would",
    "you",
    "your",
}
HEADING_NOISE_TERMS = (
    "department news and announcements",
    "downloads",
    "head of department",
    "key personnel",
    "laboratory facilities",
    "members of faculty",
    "objectives",
    "summary",
)
LOW_VALUE_FACT_PREFIXES = (
    "declaration",
    "in addition to",
    "place:",
    "project report",
    "submitted by",
)
LOW_VALUE_FACT_PHRASES = (
    "acknowledgements",
    "award of the degree",
    "certificate",
    "countersigned",
    "dateofbirth",
    "hereby declare",
    "name of guide",
    "name of the student",
    "partial fulfillment of the requirements",
    "presented by",
    "register no",
    "report of project",
    "signature",
    "submittedby",
    "university register no",
)
LOW_SIGNAL_EXPLANATION_TERMS = (
    "case study",
    "future scope",
    "graphical analysis",
    "performance analysis",
    "results and discussion",
)
INCOMPLETE_SENTENCE_ENDINGS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "with",
}
HONORIFIC_PLACEHOLDERS = {
    "Dr.": "Dr§",
    "Prof.": "Prof§",
    "Mr.": "Mr§",
    "Mrs.": "Mrs§",
    "Ms.": "Ms§",
}
INITIAL_PLACEHOLDER = "__DOT__"
LOW_VALUE_RECORD_PATTERN = re.compile(
    r"\b(?:aicteid|ktuid|mek\s*\d{2}\s*[a-z]{2}\s*\d+|register\s*no|university\s*register\s*no)\b",
    re.IGNORECASE,
)
SPACING_ARTIFACT_PATTERN = re.compile(r"[A-Za-z]{24,}")
GROUNDING_STOPWORDS = {
    "about",
    "after",
    "all",
    "also",
    "among",
    "and",
    "answer",
    "are",
    "because",
    "been",
    "being",
    "below",
    "between",
    "both",
    "but",
    "can",
    "direct",
    "does",
    "for",
    "from",
    "have",
    "information",
    "into",
    "its",
    "knowledge",
    "management",
    "more",
    "most",
    "must",
    "not",
    "only",
    "provided",
    "question",
    "relevant",
    "response",
    "same",
    "sentence",
    "sentences",
    "should",
    "than",
    "that",
    "the",
    "their",
    "them",
    "there",
    "these",
    "this",
    "those",
    "through",
    "under",
    "using",
    "with",
}
KG_METADATA_PREFIXES = (
    "department:",
    "source url:",
    "source:",
    "posted on:",
    "date:",
    "is conducts of:",
)
EXPLANATION_STRONG_COVERAGE = 0.5


def normalize_question(text: str) -> str:
    return " ".join((text or "").split()).strip()


def extract_recent_user_questions(history: Optional[List[Dict[str, str]]], limit: int = 3) -> List[str]:
    questions = []
    for item in history or []:
        if item.get("role") != "user":
            continue
        content = normalize_question(item.get("content", ""))
        if content:
            questions.append(content)
    return questions[-limit:]


def is_follow_up_question(question: str) -> bool:
    lowered = normalize_question(question).lower()
    if not lowered:
        return False
    return bool(FOLLOW_UP_REFERENCE_PATTERN.search(lowered)) or any(lowered.startswith(prefix) for prefix in FOLLOW_UP_STARTERS)


def build_retrieval_query(question: str, history: Optional[List[Dict[str, str]]]) -> tuple[str, Optional[str]]:
    normalized_question = normalize_question(question)
    prior_user_questions = extract_recent_user_questions(history)
    if not prior_user_questions or not is_follow_up_question(normalized_question):
        return normalized_question, None

    reference_question = prior_user_questions[-1]
    if reference_question.lower() == normalized_question.lower():
        return normalized_question, None

    retrieval_query = f"{reference_question}\nFollow-up question: {normalized_question}"
    follow_up_note = (
        f"Conversation hint: the current question refers to the earlier user question "
        f"'{reference_question}'. Use this only to resolve references. It is not evidence."
    )
    return retrieval_query, follow_up_note


def build_generation_history(history: Optional[List[Dict[str, str]]], limit: int = 4) -> List[Dict[str, str]]:
    if not history:
        return []
    return [{"role": item.get("role", "user"), "content": item.get("content", "")} for item in history[-limit:]]


def evidence_scoring_question(question: str, retrieval_query: Optional[str]) -> str:
    normalized_retrieval = normalize_question(retrieval_query or "")
    if "\nfollow-up question:" in (retrieval_query or "").lower():
        reference_question = normalize_question((retrieval_query or "").split("\n", 1)[0])
        if reference_question:
            focus = question_focus_phrase(reference_question)
            return focus or reference_question
    base_question = normalized_retrieval or normalize_question(question)
    focus = question_focus_phrase(base_question)
    return focus or base_question


def confidence_label_for(score: float) -> str:
    if score > 0.8:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


def normalize_entity_text(text: str) -> str:
    normalized = f" {normalize_question(text).lower()} "
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9()]+", " ", normalized)
    return f" {' '.join(normalized.split())} "


def is_department_target_question(question: str) -> bool:
    lowered = normalize_question(question).lower()
    return any(term in lowered for term in DEPARTMENT_QUERY_TERMS)


def qualifier_aliases_for(text: str) -> set[str]:
    normalized = normalize_entity_text(text)
    aliases: set[str] = set()
    for canonical, variants in QUALIFIER_ALIASES.items():
        if canonical in normalized:
            aliases.add(canonical)
            aliases.update(variant.strip() for variant in variants)
    return {alias for alias in aliases if alias}


def resolve_department_focus(question: str) -> Optional[Dict[str, Any]]:
    if not is_department_target_question(question):
        return None

    question_text = normalize_entity_text(question)
    question_department_text = normalize_department_text(question)
    best_match: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for department in get_knowledge_base_service().public_sections().get("departments", []):
        name = department.get("name") or ""
        if not name:
            continue
        normalized_name = normalize_entity_text(name)
        base_name = normalize_entity_text(re.sub(r"\s*\([^)]*\)", "", name))
        aliases = department_aliases(name)
        score = 0.0
        if normalized_name.strip() and normalized_name in question_text:
            score += 6.0
        elif base_name.strip() and base_name in question_text:
            score += 4.0

        alias_bonus = 0.0
        for alias in aliases:
            if not question_mentions_alias(question_department_text, alias):
                continue
            if " " not in alias:
                alias_bonus = max(alias_bonus, 5.0)
            else:
                alias_bonus = max(alias_bonus, 3.0 + min(alias.count(" ") + 1, 3) * 0.4)
        score += alias_bonus

        qualifier_bonus = 0.0
        for alias in qualifier_aliases_for(name):
            if alias and f" {alias} " in question_text:
                qualifier_bonus = max(qualifier_bonus, 2.0)
        score += qualifier_bonus

        department_tokens = {
            token
            for token in re.findall(r"[a-z0-9]{3,}", normalized_name)
            if token not in {"department", "dept", "head", "hod"}
        }
        overlap = sum(1 for token in department_tokens if f" {token} " in question_text)
        score += overlap * 0.4

        if score > best_score:
            best_score = score
            best_match = {
                "name": name,
                "normalized_name": normalized_name.strip(),
                "base_name": base_name.strip(),
                "qualifier_aliases": qualifier_aliases_for(name),
                "match_aliases": aliases,
            }

    return best_match if best_match and best_score > 1.5 else None


def result_matches_department_focus(item: Dict[str, Any], focus: Dict[str, Any]) -> bool:
    title_source = " ".join([item.get("title") or "", item.get("source") or ""]).strip()
    title_blob = normalize_entity_text(title_source)
    body_blob = normalize_entity_text(item.get("text", "")[:320])
    combined_blob = normalize_entity_text(f"{title_source} {item.get('text', '')[:320]}")
    combined_department_blob = normalize_department_text(f"{title_source} {item.get('text', '')[:320]}")
    content_aliases = {
        alias
        for alias in focus.get("match_aliases", set())
        if " " in alias or len(alias) >= 5
    }
    has_department_match = any(question_mentions_alias(combined_department_blob, alias) for alias in content_aliases)

    if not has_department_match:
        return False

    focus_qualifiers = {alias for alias in focus.get("qualifier_aliases", set()) if len(alias) >= 2}
    if not focus_qualifiers:
        all_known_qualifier_aliases = {
            alias
            for variants in QUALIFIER_ALIASES.values()
            for alias in variants
            if len(alias.strip()) >= 2
        }
        if any(question_mentions_alias(combined_department_blob, alias) for alias in all_known_qualifier_aliases):
            return False
        return (
            (focus["normalized_name"] and f" {focus['normalized_name']} " in title_blob)
            or (focus["base_name"] and f" {focus['base_name']} " in title_blob)
            or has_department_match
            or (focus["base_name"] and f" {focus['base_name']} " in body_blob and not title_source)
        )

    return any(question_mentions_alias(combined_department_blob, alias) for alias in focus_qualifiers)


def filter_vector_results(question: str, vector_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    focus = resolve_department_focus(question)
    if not focus or not vector_results:
        return vector_results

    exact_matches = [item for item in vector_results if result_matches_department_focus(item, focus)]
    return exact_matches or vector_results


def rerank_vector_results_for_answer(
    question: str,
    vector_results: List[Dict[str, Any]],
    kg_facts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not vector_results:
        return vector_results

    lowered_question = normalize_question(question).lower()
    is_hod_question = "hod" in lowered_question or "head of department" in lowered_question
    question_type = question_type_for(question)
    entity_names = [normalize_entity_text(item.get("entity", "")).strip() for item in kg_facts if item.get("entity")]

    def score_item(item: Dict[str, Any]) -> tuple[float, float, float]:
        chunk_text = item.get("text", "")[:420]
        text_blob = normalize_entity_text(" ".join([item.get("title") or "", item.get("source") or "", chunk_text]))
        bonus = 0.0
        if is_hod_question and (" head of department " in text_blob or " hod " in text_blob):
            bonus += 3.0
        if entity_names and any(entity and f" {entity} " in text_blob for entity in entity_names):
            bonus += 2.0
        if " menu mobile home " in text_blob:
            bonus -= 2.0
        if " members of faculty " in text_blob and is_hod_question:
            bonus += 0.5
        if question_type == QUESTION_TYPE_DEFINITION:
            definition_signal = chunk_definition_signal(question, chunk_text)
            bonus += definition_signal * 0.9
            if definition_signal >= 2.5 and any(term in text_blob for term in (" abstract ", " systemoverview ", " overview ")):
                bonus += 1.2
            if " declaration " in text_blob and definition_signal < 2.5:
                bonus -= 1.8
            if " results and discussion " in text_blob and definition_signal < 2.5:
                bonus -= 1.0
            if sentence_has_spacing_artifacts(chunk_text) and definition_signal < 2.5:
                bonus -= 0.5
        elif question_type == QUESTION_TYPE_EXPLANATION:
            explanation_hits = _whole_word_hits(grounding_query_terms(question), chunk_text)
            definition_signal = chunk_definition_signal(question, chunk_text)
            complete_sentences = sum(
                1
                for sentence in split_into_sentences(chunk_text)[:4]
                if clean_extractive_sentence(sentence, question)
                and not is_incomplete_sentence(clean_extractive_sentence(sentence, question))
                and not is_low_value_fact_sentence(clean_extractive_sentence(sentence, question))
            )
            bonus += min(explanation_hits, 3) * 0.35 + min(complete_sentences, 3) * 0.18 + min(definition_signal, 3.0) * 0.24
            if any(term in text_blob for term in (" abstract ", " overview ", " introduction ", " system overview ", " vision behind ")):
                bonus += 0.8
            if any(term in text_blob for term in (" results and discussion ", " graphical analysis ", " performance analysis ", " case study ")):
                bonus -= 1.1
            if any(term in text_blob for term in (" declaration ", " acknowledgements ", " certificate ", " project report ")):
                bonus -= 2.0
            if sentence_has_spacing_artifacts(chunk_text):
                bonus -= 0.45
        return (
            bonus,
            float(item.get("reranker_score", item.get("score", 0.0)) or 0.0),
            float(item.get("score", 0.0) or 0.0),
        )

    return sorted(vector_results, key=score_item, reverse=True)


def _call_retriever(rag_engine: Any, query: str, filter_category: Optional[str]) -> Dict[str, Any]:
    if not rag_engine:
        return {
            "query": query,
            "expanded_queries": [query],
            "passes": [],
            "results": [],
            "retrieval_version": get_retrieval_version(),
            "has_evidence": False,
        }

    if hasattr(rag_engine, "retrieve_with_fallbacks"):
        return rag_engine.retrieve_with_fallbacks(query, top_k=MAX_RETRIEVED_CHUNKS, filter_category=filter_category)

    results = rag_engine.retrieve(query, top_k=MAX_RETRIEVED_CHUNKS, filter_category=filter_category, min_score=0.0)
    return {
        "query": query,
        "expanded_queries": [query],
        "passes": [{"name": "legacy_retrieve", "candidates": len(results), "top_score": results[0]["score"] if results else 0.0}],
        "results": results,
        "retrieval_version": "legacy-retrieve",
        "has_evidence": bool(results),
    }


def question_type_for(question: str) -> str:
    lowered = normalize_question(question).lower()
    if lowered.startswith(("how many", "how much", "how long")):
        return QUESTION_TYPE_FACT
    if is_role_lookup_question(question):
        return QUESTION_TYPE_FACT
    if lowered.startswith(("what is ", "what are ", "define ", "definition of ", "meaning of ")):
        return QUESTION_TYPE_DEFINITION
    if any(term in lowered for term in ("explain", "describe", "summarize", "summary", "overview", "tell me about", "walk me through")):
        return QUESTION_TYPE_EXPLANATION
    if lowered.startswith(("how ", "why ")):
        return QUESTION_TYPE_EXPLANATION
    if lowered.startswith(("who ", "what ", "when ", "where ", "which ", "list ", "name ")):
        return QUESTION_TYPE_FACT
    if any(term in lowered for term in ("minimum", "maximum", "email", "phone", "contact")):
        return QUESTION_TYPE_FACT
    return QUESTION_TYPE_DEFINITION


def is_role_lookup_question(question: str) -> bool:
    label = role_label_for_question(question)
    if not label:
        return False

    lowered = normalize_question(question).lower()
    definition_starters = ("what is ", "what are ", "define ", "definition of ", "meaning of ")
    explicit_definition = lowered.startswith(definition_starters)
    role_terms = {
        "Head of Department": {"hod", "head of department", "the hod", "the head of department"},
        "Principal": {"principal", "the principal"},
        "Vice Principal": {"vice principal", "the vice principal"},
        "Dean": {"dean", "the dean"},
        "Director": {"director", "the director"},
    }.get(label, {label.lower(), f"the {label.lower()}"})

    if explicit_definition:
        remainder = lowered
        for starter in definition_starters:
            if lowered.startswith(starter):
                remainder = lowered[len(starter) :].strip()
                break
        if remainder in role_terms:
            return False

    if lowered.startswith(("who ", "name ", "list ")):
        return True
    if any(term in lowered for term in (" of ", " for ", " in ", " at ", " from ")):
        return True
    if any(term in lowered for term in ("department", "dept", "mesitam")):
        return True
    return not explicit_definition


def retrieval_chunk_limit_for(question_type: str) -> int:
    if question_type == QUESTION_TYPE_EXPLANATION:
        return MAX_EXPLANATION_RETRIEVED_CHUNKS
    return MAX_RETRIEVED_CHUNKS


def filtered_sentence_limit_for(question_type: str) -> int:
    if question_type == QUESTION_TYPE_EXPLANATION:
        return MAX_EXPLANATION_FILTERED_SENTENCES
    return MAX_FILTERED_SENTENCES


def grounding_query_terms(question: str) -> List[str]:
    focus = question_focus_phrase(question) or normalize_question(question)
    tokens = [token for token in extract_keywords(focus) if token not in GROUNDING_QUERY_STOPWORDS]
    if not tokens:
        tokens = [token for token in _token_set(focus) if token not in GROUNDING_QUERY_STOPWORDS]
    if not tokens and focus != normalize_question(question):
        tokens = [token for token in extract_keywords(question) if token not in GROUNDING_QUERY_STOPWORDS]
    return list(dict.fromkeys(tokens))


def explanation_prefers_overview(question: str) -> bool:
    lowered = normalize_question(question).lower()
    lowered = re.sub(r"^(?:(?:can|could|would)\s+you\s+|please\s+)+", "", lowered).strip()
    if any(term in lowered for term in ("process", "procedure", "steps", "workflow", "guidelines", "rules", "regulations")):
        return False
    return any(
        lowered.startswith(prefix)
        for prefix in ("explain ", "describe ", "summarize ", "summary of ", "overview of ", "tell me about ")
    )


def is_location_question(question: str) -> bool:
    lowered = normalize_question(question).lower()
    padded = f" {lowered} "
    return lowered.startswith("where ") or " located" in padded or " location " in padded or " address " in padded


def is_heading_like_sentence(sentence: str) -> bool:
    lowered = normalize_question(sentence).lower()
    if not lowered:
        return True
    if lowered in {"downloads", "key personnel", "members of faculty", "objectives", "summary"}:
        return True
    if "summary objectives head of department" in lowered:
        return True

    heading_hits = sum(1 for term in HEADING_NOISE_TERMS if term in lowered)
    has_person = bool(PERSON_NAME_PATTERN.search(sentence or ""))
    has_signal = bool(
        re.search(r"\b(is|are|was|were|has|have|had|located|established|started|working|serving)\b", lowered)
        or re.search(r"[@%+\d]", sentence or "")
    )
    return heading_hits >= 2 and not has_person and not has_signal


def normalize_person_name(text: str) -> str:
    cleaned = normalize_question(text)
    cleaned = re.sub(r"(?i)\b(?:phone number|email|highest degree|field of specialization)\b.*$", "", cleaned)
    cleaned = re.sub(r"(?i)\s+(?:Assistant|Associate)\s+Professor.*$", "", cleaned)
    cleaned = re.sub(r"(?i)\s+Professor\s*&\s*HOD.*$", "", cleaned)
    cleaned = re.sub(r"(?i)\s*&\s*HOD.*$", "", cleaned)
    cleaned = re.sub(r"\b([A-Z])\.([A-Z])\.", r"\1. \2.", cleaned)
    cleaned = re.sub(r"\b([A-Z])\s+([A-Z])\b", r"\1. \2.", cleaned)
    cleaned = cleaned.strip(" ,;:-")
    return normalize_question(cleaned)


def question_focus_phrase(question: str) -> str:
    lowered = normalize_question(question).rstrip(" ?")
    polite_prefix = r"(?:(?:can|could|would)\s+you\s+|please\s+)*"
    patterns = (
        rf"^{polite_prefix}(?:what|who|where|when|which)\s+(?:is|are|was|were)\s+",
        rf"^{polite_prefix}define\s+",
        rf"^{polite_prefix}describe\s+",
        rf"^{polite_prefix}explain\s+",
        rf"^{polite_prefix}meaning of\s+",
        rf"^{polite_prefix}summary of\s+",
        rf"^{polite_prefix}summarize\s+",
        rf"^{polite_prefix}overview of\s+",
        rf"^{polite_prefix}tell me about\s+",
        rf"^{polite_prefix}walk me through\s+",
    )
    focus = lowered
    for pattern in patterns:
        focus = re.sub(pattern, "", focus, flags=re.IGNORECASE)
    focus = re.sub(r"^(?:the|a|an)\s+", "", focus, flags=re.IGNORECASE)
    return normalize_question(focus)


def sentence_has_spacing_artifacts(sentence: str) -> bool:
    return bool(SPACING_ARTIFACT_PATTERN.search(sentence or ""))


def explanation_section_bias(title: str, sentence: str) -> float:
    lowered = normalize_question(f"{title} {sentence}").lower()
    bonus = 0.0
    if any(term in lowered for term in ("abstract", "introduction", "overview", "system overview", "vision behind")):
        bonus += 0.28
    if any(term in lowered for term in LOW_SIGNAL_EXPLANATION_TERMS):
        bonus -= 0.42
    if any(term in lowered for term in LOW_VALUE_FACT_PHRASES):
        bonus -= 0.9
    return bonus


def clean_extractive_sentence(sentence: str, question: str = "") -> str:
    cleaned = normalize_question(repair_extracted_spacing(sentence))
    if not cleaned:
        return ""

    cleaned = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", cleaned)
    cleaned = cleaned.replace("VisionBehind", "Vision Behind ")
    cleaned = cleaned.replace("SystemOverview", "System Overview ")
    cleaned = cleaned.replace("ResultsandDiscussion", "Results and Discussion ")
    cleaned = re.sub(r"(?i)^[A-Za-z]+\s+Date:\s*[A-Za-z0-9-]+\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^Place:\s*[A-Za-z0-9-]+\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^(?:[ivxlcdm]+)\s+ABSTRACT\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^ABSTRACT\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^DECLARATION\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^CHAPTER\s+\d+(?::\s*)?", "", cleaned)
    cleaned = re.sub(r"(?i)^INTRODUCTION\s+\d+(?:\.\d+)*(?:\s*OVERVIEW)?\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^PROPOSED SYSTEM\s+\d+(?:\.\d+)*(?:SYSTEMOVERVIEW)?\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^SYSTEMOVERVIEW\s+", "", cleaned)
    cleaned = re.sub(r"(?i)^In addition to [^,]{4,120},\s+(?=NeuroNest\b)", "", cleaned)
    cleaned = re.sub(r"(?i)^require patients to visit hospitals", "Traditional systems require patients to visit hospitals", cleaned)
    cleaned = re.sub(r"(?i)^\d+(?:\.\d+)+(?:\s*[A-Za-z][A-Za-z ]{3,40})?\s+", "", cleaned)
    cleaned = re.sub(r"(?i)\bthe winner is not one who never fails but one who never quits\b", "", cleaned)
    cleaned = re.sub(r"(?i)^([A-Za-z][A-Za-z& ]{6,80})\s+MESITAM\s+\1\b", r"\1", cleaned)

    focus = question_focus_phrase(question)
    if focus:
        focus_lower = focus.lower()
        position = cleaned.lower().find(focus_lower)
        if position > 0:
            prefix = cleaned[:position].lower()
            if any(term in prefix for term in ("abstract", "declaration", "introduction", "overview", "vision behind", "proposed system", "chapter", "date:", "place:")):
                cleaned = cleaned[position:]

    cleaned = re.sub(r"^([^,]{1,80}),\s+(is|are)\b", r"\1 \2", cleaned)
    cleaned = cleaned.strip(" -:;")
    return normalize_question(cleaned)


def is_incomplete_sentence(sentence: str) -> bool:
    cleaned = normalize_question(sentence)
    if not cleaned:
        return True

    lowered = cleaned.lower()
    if lowered.startswith("in addition to ") and re.search(r"\b(provides|includes|offers|supports|allows|enables|combines)\b", lowered):
        return False
    if any(lowered.startswith(prefix) for prefix in LOW_VALUE_FACT_PREFIXES):
        return True
    if re.match(r"^r\s*\d+(?:\.\d+)+\s+[a-z]", lowered):
        return True
    if cleaned.count("(") > cleaned.count(")"):
        return True
    if re.search(r"[.!?]$", cleaned):
        return False

    words = re.findall(r"[a-z]+", lowered)
    if not words:
        return True
    if words[-1] in INCOMPLETE_SENTENCE_ENDINGS:
        return True
    if lowered.startswith("in addition to "):
        return True
    return False


def is_low_value_fact_sentence(sentence: str) -> bool:
    lowered = normalize_question(sentence).lower()
    if lowered.startswith("in addition to ") and re.search(r"\b(provides|includes|offers|supports|allows|enables|combines)\b", lowered):
        return False
    if any(lowered.startswith(prefix) for prefix in LOW_VALUE_FACT_PREFIXES):
        return True
    compact = re.sub(r"[^a-z0-9]+", "", lowered)
    if any(phrase in lowered for phrase in LOW_VALUE_FACT_PHRASES):
        return True
    if any(marker in compact for marker in ("submittedby", "nameofthestudent", "universityregisterno")):
        return True
    if LOW_VALUE_RECORD_PATTERN.search(lowered) and not re.search(r"\b(is|are|was|were|serves as|works as)\b", lowered):
        return True
    if sentence_has_spacing_artifacts(sentence) and "is" not in lowered and "are" not in lowered:
        return True
    return any(
        phrase in lowered
        for phrase in (
            "hereby declare",
            "project report entitled",
            "submittedby",
        )
    )


def definition_match_score(question: str, sentence: str) -> float:
    focus = question_focus_phrase(question)
    if not focus:
        return 0.0

    normalized_sentence = f" {re.sub(r'[^a-z0-9]+', ' ', normalize_question(sentence).lower())} "
    normalized_focus = re.sub(r"[^a-z0-9]+", " ", focus.lower()).strip()
    focus_tokens = grounding_query_terms(focus)
    compact_sentence = compact_alphanumeric(sentence)
    compact_focuses = compact_query_forms(focus or question)
    score = 0.0

    if normalized_focus and f" {normalized_focus} " in normalized_sentence:
        score += 2.0
        if re.search(
            rf"\b{re.escape(normalized_focus)}\b\s+(?:is|are|was|were|refers to|means|stands for|describes|defines)\b",
            normalized_sentence,
        ):
            score += 2.0
    elif compact_focuses and any(compact_focus in compact_sentence for compact_focus in compact_focuses):
        score += 2.8

    token_hits = _whole_word_hits(focus_tokens, sentence)
    score += min(token_hits, 4) * 0.45
    if focus_tokens and token_hits >= max(1, len(focus_tokens) - 1):
        score += 0.6
    if re.search(r"\b(is|are|was|were|refers to|means|stands for|designed to|combines|provides)\b", sentence, flags=re.IGNORECASE):
        score += 0.35
    if normalized_focus and normalize_question(sentence).lower().startswith(normalized_focus):
        score += 1.0
    return round(score, 2)


def matches_focus_statement(question: str, sentence: str) -> bool:
    focus = question_focus_phrase(question)
    focus_tokens = re.findall(r"[a-z0-9]+", normalize_question(focus).lower())
    if not focus_tokens:
        return True

    focus_pattern = r"\s*".join(re.escape(token) for token in focus_tokens)
    normalized_sentence = normalize_question(sentence).lower()
    return bool(
        re.search(
            rf"^{focus_pattern}\s+(?:is|are|was|were|refers to|means|stands for|describes|provides|combines|allows|offers)\b",
            normalized_sentence,
        )
    )


def select_best_fact_sentence(question: str, filtered_evidence: List[Dict[str, Any]]) -> Optional[str]:
    candidates: List[tuple[float, int, str]] = []
    for index, item in enumerate(filtered_evidence):
        sentence = clean_extractive_sentence(item.get("sentence", ""), question)
        if not sentence or is_heading_like_sentence(sentence):
            continue

        candidate_score = float(item.get("score", 0.0) or 0.0)
        definition_score = definition_match_score(question, sentence)
        incomplete = is_incomplete_sentence(sentence)
        low_value = is_low_value_fact_sentence(sentence)
        if low_value:
            continue
        if item.get("match_type") == "structured":
            candidate_score += 0.8
        candidate_score += definition_score
        if incomplete:
            candidate_score -= 3.0
        candidates.append((candidate_score, -index, sentence))

    if candidates:
        best_score, _, best_sentence = max(candidates)
        if best_score > 0:
            return best_sentence
    return None


def select_definition_evidence(question: str, filtered_evidence: List[Dict[str, Any]], limit: int = 2) -> List[Dict[str, Any]]:
    candidates: List[tuple[float, int, Dict[str, Any]]] = []
    for index, item in enumerate(filtered_evidence):
        sentence = clean_extractive_sentence(item.get("sentence", ""), question)
        if not sentence or is_heading_like_sentence(sentence) or is_low_value_fact_sentence(sentence):
            continue

        definition_score = definition_match_score(question, sentence)
        if definition_score < 1.6:
            continue

        candidate_score = float(item.get("score", 0.0) or 0.0) + definition_score
        lowered = sentence.lower()
        if is_incomplete_sentence(sentence):
            candidate_score -= 2.5
        if sentence_has_spacing_artifacts(sentence):
            candidate_score -= 0.45
        if lowered.startswith(("in conclusion", "overall", "the study", "this study")):
            candidate_score -= 1.1
        if any(term in lowered for term in LOW_SIGNAL_EXPLANATION_TERMS):
            candidate_score -= 0.7
        if matches_focus_statement(question, sentence):
            candidate_score += 0.6
        elif question_focus_phrase(question):
            candidate_score -= 0.7
        if re.search(r"\b(is|are|was|were|refers to|means|stands for|designed to)\b", sentence, flags=re.IGNORECASE):
            candidate_score += 0.45
        candidates.append((candidate_score, -index, {**item, "sentence": sentence}))

    if not candidates:
        fallback = select_best_fact_sentence(question, filtered_evidence)
        if not fallback:
            return []
        for item in filtered_evidence:
            sentence = clean_extractive_sentence(item.get("sentence", ""), question)
            if sentence == fallback:
                return [{**item, "sentence": sentence}]
        return []

    ranked = sorted(candidates, reverse=True)
    selected: List[Dict[str, Any]] = []
    best_score = ranked[0][0]
    for candidate_score, _, item in ranked:
        if selected and candidate_score < best_score - 1.2:
            continue
        if any(sentence_content_overlap(item["sentence"], existing["sentence"]) >= 5 for existing in selected):
            continue
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def select_definition_sentences(question: str, filtered_evidence: List[Dict[str, Any]]) -> List[str]:
    return [item["sentence"] for item in select_definition_evidence(question, filtered_evidence, limit=2)]


def select_overview_evidence(question: str, filtered_evidence: List[Dict[str, Any]], limit: int = 2) -> List[Dict[str, Any]]:
    candidates: List[tuple[float, int, Dict[str, Any]]] = []
    focus = question_focus_phrase(question).lower()
    for index, item in enumerate(filtered_evidence):
        sentence = clean_extractive_sentence(item.get("sentence", ""), question)
        if not sentence or is_low_value_fact_sentence(sentence) or is_incomplete_sentence(sentence):
            continue
        if sentence_has_spacing_artifacts(sentence):
            continue
        if focus and not matches_focus_statement(question, sentence):
            continue

        definition_score = definition_match_score(question, sentence)
        if definition_score < 2.4:
            continue

        candidate_score = float(item.get("score", 0.0) or 0.0) + definition_score + explanation_section_bias(
            item.get("title") or item.get("source") or "",
            sentence,
        )
        if focus and sentence.lower().startswith(focus):
            candidate_score += 0.8
        candidates.append((candidate_score, -index, {**item, "sentence": sentence}))

    if not candidates:
        return select_explanation_evidence(question, filtered_evidence, limit=limit)

    candidates.sort(reverse=True)
    selected: List[Dict[str, Any]] = []
    for _, _, item in candidates:
        if any(sentence_content_overlap(item["sentence"], existing["sentence"]) >= 6 for existing in selected):
            continue
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected or select_explanation_evidence(question, filtered_evidence, limit=limit)


def is_kg_metadata_fact(fact: str) -> bool:
    lowered = normalize_question(fact).lower()
    return not lowered or any(lowered.startswith(prefix) for prefix in KG_METADATA_PREFIXES)


def chunk_definition_signal(question: str, text: str) -> float:
    sentences = split_into_sentences(text)[:4]
    if not sentences:
        return 0.0
    return max(
        (
            definition_match_score(question, clean_extractive_sentence(sentence, question))
            for sentence in sentences
            if clean_extractive_sentence(sentence, question)
        ),
        default=0.0,
    )


def explanation_sentence_metrics(question: str, item: Dict[str, Any]) -> Dict[str, float]:
    sentence = clean_extractive_sentence(item.get("sentence", ""), question)
    question_terms = grounding_query_terms(question)
    sentence_terms = _token_set(sentence) - GROUNDING_STOPWORDS
    title_terms = _token_set(item.get("title") or item.get("source") or "")
    matched_terms = {term for term in question_terms if term in sentence_terms or term in title_terms}
    coverage = len(matched_terms) / max(len(question_terms), 1) if question_terms else 0.0
    compact_support = bool(
        compact_query_forms(question)
        and any(
            compact_query in compact_alphanumeric(f"{item.get('title') or item.get('source') or ''} {sentence}")
            for compact_query in compact_query_forms(question)
        )
    )
    if compact_support:
        coverage = max(coverage, 0.5 if question_terms else 0.4)
    semantic_score = float(item.get("semantic_score", 0.0) or 0.0)
    base_score = float(item.get("score", 0.0) or 0.0)
    definition_score = definition_match_score(question, sentence)
    quality_score = base_score + coverage * 0.55 + semantic_score * 0.2 + min(definition_score, 3.0) * 0.12
    if item.get("match_type") == "structured":
        quality_score += 0.15
        if len(sentence_terms) < 8:
            quality_score -= 0.45
    lowered_sentence = sentence.lower()
    if any(phrase in lowered_sentence for phrase in ("features such as", "provides features", "includes", "combines")):
        quality_score += 0.2
    if any(phrase in lowered_sentence for phrase in ("online appointment booking", "digital prescriptions", "medical record management", "video consultation")):
        quality_score += 0.18
    if lowered_sentence.startswith(("overall", "in conclusion", "to conclude")):
        quality_score -= 0.4
    if is_incomplete_sentence(sentence):
        quality_score -= 0.8
    if is_low_value_fact_sentence(sentence):
        quality_score -= 0.8
    quality_score += explanation_section_bias(item.get("title") or item.get("source") or "", sentence)
    if sentence_has_spacing_artifacts(sentence):
        quality_score -= 0.35
    return {
        "coverage": round(coverage, 4),
        "definition_score": round(definition_score, 4),
        "quality": round(quality_score, 4),
        "sentence": sentence,
    }


def sentence_content_overlap(left: str, right: str) -> int:
    left_terms = _token_set(left) - GROUNDING_STOPWORDS
    right_terms = _token_set(right) - GROUNDING_STOPWORDS
    return len(left_terms & right_terms)


def select_explanation_evidence(question: str, filtered_evidence: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    ranked: List[tuple[float, int, Dict[str, Any]]] = []
    for index, item in enumerate(filtered_evidence):
        metrics = explanation_sentence_metrics(question, item)
        sentence = metrics["sentence"]
        if not sentence or is_heading_like_sentence(sentence):
            continue
        if metrics["quality"] < 0.45:
            continue
        ranked.append((metrics["quality"], -index, {**item, "sentence": sentence, "coverage": metrics["coverage"]}))

    ranked.sort(reverse=True)
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for _, _, item in ranked:
        normalized_sentence = re.sub(r"[^a-z0-9]+", " ", item["sentence"].lower()).strip()
        if not normalized_sentence or normalized_sentence in seen:
            continue
        if any(sentence_content_overlap(item["sentence"], selected_item["sentence"]) >= 5 for selected_item in selected):
            continue
        seen.add(normalized_sentence)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def select_answer_explanation_evidence(question: str, filtered_evidence: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    prefer_overview = explanation_prefers_overview(question)
    candidates: List[Dict[str, Any]] = []
    if prefer_overview:
        candidates.extend(select_overview_evidence(question, filtered_evidence, limit=min(2, limit)))

    ranked_explanation: List[tuple[float, int, Dict[str, Any]]] = []
    for index, item in enumerate(filtered_evidence):
        metrics = explanation_sentence_metrics(question, item)
        sentence = metrics["sentence"]
        if not sentence or is_heading_like_sentence(sentence) or is_low_value_fact_sentence(sentence):
            continue
        score = metrics["quality"]
        lowered_sentence = sentence.lower()
        if prefer_overview and definition_match_score(question, sentence) >= 2.4:
            score -= 0.2
        if any(phrase in lowered_sentence for phrase in ("features such as", "provides features", "online appointment booking", "digital prescriptions", "medical record management", "video consultation")):
            score += 0.35
        if lowered_sentence.startswith(("overall", "in conclusion", "to conclude")):
            score -= 0.45
        ranked_explanation.append((score, -index, {**item, "sentence": sentence}))

    ranked_explanation.sort(reverse=True)
    candidates.extend(item for _, _, item in ranked_explanation)
    if not candidates:
        candidates.extend(select_overview_evidence(question, filtered_evidence, limit=min(2, limit)))

    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        sentence = clean_extractive_sentence(item.get("sentence", ""), question)
        if not sentence:
            continue
        lowered_sentence = sentence.lower()
        normalized_sentence = re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()
        if not normalized_sentence or normalized_sentence in seen:
            continue
        if len(selected) >= max(2, limit - 2) and (
            "future scope" in lowered_sentence
            or lowered_sentence.startswith(("overall", "in conclusion", "this will make"))
        ):
            continue
        if any(sentence_content_overlap(sentence, existing["sentence"]) >= 6 for existing in selected):
            continue
        if item.get("match_type") == "structured" and len(sentence.split()) < 10 and selected:
            continue
        seen.add(normalized_sentence)
        selected.append({**item, "sentence": sentence})
        if len(selected) >= limit:
            break
    return selected


def has_sufficient_explanation_evidence(question: str, filtered_evidence: List[Dict[str, Any]]) -> bool:
    selected = select_answer_explanation_evidence(question, filtered_evidence, limit=3)
    if not selected:
        return False

    procedural_query = any(
        term in normalize_question(question).lower()
        for term in ("rules", "regulations", "guidelines", "process", "procedure", "steps")
    )
    lead_metrics = explanation_sentence_metrics(question, selected[0])
    if lead_metrics["quality"] < 0.6:
        return False

    if selected[0].get("match_type") == "structured" and lead_metrics["coverage"] >= 0.34:
        if procedural_query:
            return len(selected) >= 2 and explanation_sentence_metrics(question, selected[1])["coverage"] >= 0.34
        return True

    if len(selected) == 1:
        if procedural_query:
            return False
        return lead_metrics["coverage"] >= EXPLANATION_STRONG_COVERAGE or float(selected[0].get("semantic_score", 0.0) or 0.0) >= 0.52

    second_metrics = explanation_sentence_metrics(question, selected[1])
    overlap = sentence_content_overlap(selected[0]["sentence"], selected[1]["sentence"])
    if procedural_query:
        return overlap >= 2 or (lead_metrics["coverage"] >= EXPLANATION_STRONG_COVERAGE and second_metrics["coverage"] >= 0.4)
    return overlap >= 2 or max(lead_metrics["coverage"], second_metrics["coverage"]) >= EXPLANATION_STRONG_COVERAGE


def structured_kg_context_evidence(
    question: str,
    question_type: str,
    filtered_kg_facts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if question_type not in {QUESTION_TYPE_DEFINITION, QUESTION_TYPE_EXPLANATION}:
        return []

    grouped: Dict[str, Dict[str, Any]] = {}
    for item in filtered_kg_facts:
        entity = normalize_question(item.get("entity", "")) or "Knowledge Base"
        entry = grouped.setdefault(entity, {"entity": entity, "source_url": None, "facts": [], "score": 0.0})
        entry["score"] = max(entry["score"], float(item.get("relevance_score", item.get("score", 0.0)) or 0.0))
        fact = normalize_question(item.get("fact", ""))
        lowered_fact = fact.lower()
        if lowered_fact.startswith("source url:"):
            entry["source_url"] = fact.split(":", 1)[1].strip() or None
            continue
        if is_kg_metadata_fact(fact):
            continue
        entry["facts"].append(fact)

    candidates: List[tuple[float, str, Dict[str, Any]]] = []
    for entry in grouped.values():
        title = entry["entity"]
        title_hits = _whole_word_hits(grounding_query_terms(question), title)
        for fact in entry["facts"]:
            for sentence in split_into_sentences(fact):
                cleaned_sentence = clean_extractive_sentence(sentence, question)
                if not cleaned_sentence or is_heading_like_sentence(cleaned_sentence) or is_low_value_fact_sentence(cleaned_sentence):
                    continue
                if is_incomplete_sentence(cleaned_sentence):
                    continue
                keyword_hits = _whole_word_hits(grounding_query_terms(question), cleaned_sentence)
                definition_score = definition_match_score(question, cleaned_sentence)
                if keyword_hits == 0 and title_hits == 0 and definition_score < 1.6:
                    continue
                score = entry["score"] + keyword_hits * 0.18 + title_hits * 0.22 + definition_score * 0.12
                if question_type == QUESTION_TYPE_EXPLANATION and title_hits and keyword_hits == 0:
                    score += 0.12
                if question_type == QUESTION_TYPE_EXPLANATION and "process" in normalize_question(question).lower():
                    lowered_sentence = cleaned_sentence.lower()
                    if lowered_sentence.startswith(("it is being", "a total of")):
                        score -= 0.4
                    if re.search(r"\b(aim|duty|training|prepare|arrange|guidance|placement|interviews|industry)\b", lowered_sentence):
                        score += 0.2
                if score < 0.75:
                    continue
                candidates.append(
                    (
                        round(score, 4),
                        re.sub(r"[^a-z0-9]+", " ", cleaned_sentence.lower()).strip(),
                        make_structured_evidence(
                            cleaned_sentence,
                            title,
                            source_url=entry["source_url"],
                            score=min(1.0, score),
                            source_type="knowledge_graph",
                        ),
                    )
                )

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for _, key, item in candidates:
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= 3:
            break
    return selected


def supplemental_definition_results(question: str, rag_engine: Any, limit: int = 4) -> List[Dict[str, Any]]:
    if not rag_engine or not getattr(rag_engine, "chunks_metadata", None):
        return []

    query_terms = grounding_query_terms(question_focus_phrase(question) or question)
    candidates: List[tuple[float, float, Dict[str, Any]]] = []
    for raw_item in getattr(rag_engine, "chunks_metadata", []) or []:
        text = normalize_question(raw_item.get("text", ""))
        if not text:
            continue

        title = normalize_question(raw_item.get("title") or raw_item.get("source") or "Official Source")
        title_hits = _whole_word_hits(query_terms, title)
        keyword_hits = _whole_word_hits(query_terms, text)
        definition_signal = chunk_definition_signal(question, text)
        lowered_text = text.lower()
        front_matter_penalty = 0.0
        if any(term in lowered_text for term in ("declaration", "certificate", "submittedby", "project report")) and "abstract" not in lowered_text:
            front_matter_penalty = 1.0

        score = definition_signal + keyword_hits * 0.35 + title_hits * 0.25 - front_matter_penalty
        if score < 2.0:
            continue

        candidates.append(
            (
                round(score, 4),
                round(definition_signal, 4),
                {
                    **raw_item,
                    "title": title,
                    "source": title,
                    "score": round(min(1.0, 0.55 + score * 0.08), 2),
                    "vector_score": float(raw_item.get("vector_score", 0.0) or 0.0),
                    "reranker_score": round(min(1.0, 0.45 + definition_signal * 0.08 + keyword_hits * 0.05), 2),
                    "keyword_match_score": round(min(1.0, 0.4 + keyword_hits * 0.15 + title_hits * 0.08), 2),
                    "match_type": "definition_scan",
                },
            )
        )

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected: List[Dict[str, Any]] = []
    seen: set[tuple[str, Optional[int]]] = set()
    for _, _, item in candidates:
        key = (item.get("title") or item.get("source") or "Official Source", item.get("page"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def make_structured_evidence(
    sentence: str,
    title: str,
    source_url: Optional[str] = None,
    score: float = 1.0,
    source_type: str = "knowledge_base",
    department: Optional[str] = None,
) -> Dict[str, Any]:
    source_title = normalize_question(title) or "Official Source"
    return {
        "sentence": normalize_question(sentence),
        "title": source_title,
        "source": source_title,
        "page": None,
        "source_type": source_type,
        "source_url": source_url,
        "match_type": "structured",
        "chunk_score": round(score, 2),
        "reranker_score": round(score, 2),
        "semantic_score": round(score, 2),
        "keyword_hits": 4,
        "exact_phrase": True,
        "score": round(score, 2),
        "department": department,
    }


def merge_evidence_lists(*groups: List[Dict[str, Any]], limit: int = MAX_FILTERED_SENTENCES) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, Optional[int]]] = set()
    for group in groups:
        for item in group:
            sentence = normalize_question(item.get("sentence", ""))
            title = normalize_question(item.get("title") or item.get("source") or "Official Source")
            if not sentence:
                continue
            key = (re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip(), title, item.get("page"))
            if key in seen:
                continue
            seen.add(key)
            merged.append({**item, "sentence": sentence, "title": title, "source": title})
            if len(merged) >= limit:
                return merged
    return merged


def text_matches_department_focus(text: str, focus: Optional[Dict[str, Any]]) -> bool:
    if not focus:
        return True
    department_blob = normalize_department_text(text)
    qualifier_blob = department_blob.replace("(", " ").replace(")", " ")
    if not any(question_mentions_alias(department_blob, alias) for alias in focus.get("match_aliases", set())):
        return False

    focus_qualifiers = {alias.strip().lower() for alias in focus.get("qualifier_aliases", set()) if alias.strip()}
    all_qualifiers = {
        alias.strip().lower()
        for variants in QUALIFIER_ALIASES.values()
        for alias in variants
        if alias.strip()
    }
    if focus_qualifiers:
        return any(question_mentions_alias(qualifier_blob, alias) for alias in focus_qualifiers)
    return not any(question_mentions_alias(qualifier_blob, alias) for alias in all_qualifiers)


def document_priority_for_fact_lookup(document: Dict[str, Any]) -> float:
    title = normalize_question(document.get("title") or document.get("source") or "").lower()
    if "news" in title or "events" in title:
        return -2.0
    if "mandatory disclosure" in title:
        return 4.5
    if "about mesitam" in title:
        return 4.3
    if "hod" in title or "head of departments" in title:
        return 4.1
    if title.startswith("department of "):
        return 2.4
    return 0.0


def faculty_matches_role(label: str, designation: str) -> bool:
    lowered = normalize_question(designation).lower()
    if label == "Principal":
        return bool(re.search(r"\bprincipal\b", lowered)) and "vice principal" not in lowered and "principal in charge" not in lowered
    if label == "Vice Principal":
        return "vice principal" in lowered
    if label == "Head of Department":
        return bool(re.search(r"\bhead of (?:the )?department\b", lowered) or re.search(r"\bhod\b", lowered))
    return label.lower() in lowered


def person_name_tokens(text: str) -> List[str]:
    cleaned = normalize_person_name(text)
    cleaned = re.sub(r"(?i)\b(?:prof|dr|mr|mrs|ms)\.?\b", " ", cleaned)
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]{2,}", cleaned.lower())
        if token not in {"mes", "mesitam", "department", "faculty", "staff"}
    ]
    return list(dict.fromkeys(tokens))


def matched_faculty_profile(question: str) -> Optional[Dict[str, Any]]:
    if role_label_for_question(question) or is_location_question(question):
        return None

    focus = question_focus_phrase(question)
    query_tokens = [token for token in person_name_tokens(focus) if len(token) >= 3]
    if not query_tokens:
        return None

    candidates: List[tuple[float, Dict[str, Any]]] = []
    normalized_focus = normalize_person_name(focus).lower()
    for faculty in get_knowledge_base_service().public_sections().get("faculty", []):
        name = normalize_person_name(faculty.get("name") or "")
        if not name:
            continue
        name_tokens = person_name_tokens(name)
        if not name_tokens:
            continue

        overlap = len(set(query_tokens) & set(name_tokens))
        if overlap == 0:
            continue

        score = overlap / max(len(query_tokens), 1)
        lowered_name = name.lower()
        if normalized_focus and normalized_focus in lowered_name:
            score += 1.0
        if all(token in name_tokens for token in query_tokens):
            score += 0.8
        designation = normalize_question(faculty.get("designation", ""))
        if designation and designation.lower() != "faculty":
            score += 0.2
        candidates.append((round(score, 3), faculty))

    if not candidates:
        return None

    best_score, best_faculty = max(candidates, key=lambda item: item[0])
    if best_score < 0.75:
        return None
    return best_faculty


def _contains_focus_tokens(text: str, focus_tokens: List[str]) -> bool:
    normalized = f" {re.sub(r'[^a-z0-9]+', ' ', (text or '').lower())} "
    return any(f" {token} " in normalized for token in focus_tokens)


def _extract_upload_person_name(text: str, focus_tokens: List[str]) -> Optional[str]:
    if not text or not focus_tokens:
        return None

    lines = [normalize_question(line) for line in text.splitlines() if normalize_question(line)]
    candidates: List[tuple[float, str]] = []
    for index, line in enumerate(lines):
        if not _contains_focus_tokens(line, focus_tokens):
            continue

        score = 0.0
        if re.search(r"[A-Z]{2,}", line):
            score += 0.6
        if UPLOAD_PERSON_REGISTER_PATTERN.search(line):
            score += 0.4
        if len(line.split()) <= 5:
            score += 0.5

        previous_line = lines[index - 1] if index > 0 else ""
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        blob = f"{previous_line} {line} {next_line}".strip()
        if UPLOAD_PERSON_REGISTER_PATTERN.search(blob):
            score += 0.5

        if re.fullmatch(r"[A-Z][A-Za-z]*(?:\s+[A-Z]){1,3}", line):
            candidates.append((score + 1.0, normalize_person_name(line)))
            continue
        if re.fullmatch(r"[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]+){1,3}", line):
            candidates.append((score + 0.9, normalize_person_name(line)))
            continue

        match = re.search(
            rf"(?i)\b(?P<name>{re.escape(focus_tokens[0])}(?:\s+[A-Z][A-Za-z]*){{0,3}})\b",
            line,
        )
        if match:
            candidates.append((score + 0.4, normalize_person_name(match.group("name"))))

    if not candidates:
        return None

    best_name = max(candidates, key=lambda item: item[0])[1]
    return best_name if len(person_name_tokens(best_name)) >= len(focus_tokens) else None


def _format_upload_person_name(name: str) -> str:
    formatted_parts: List[str] = []
    for token in normalize_question(name).split():
        stripped = token.rstrip(".")
        if not stripped:
            continue
        if len(stripped) == 1:
            formatted_parts.append(stripped.upper() + ".")
        elif stripped.isupper():
            formatted_parts.append(stripped[0].upper() + stripped[1:].lower())
        else:
            formatted_parts.append(stripped[0].upper() + stripped[1:])
    return normalize_question(" ".join(formatted_parts))


def _extract_upload_person_register(text: str, focus_tokens: List[str]) -> Optional[str]:
    if not text:
        return None

    lines = [normalize_question(line) for line in text.splitlines() if normalize_question(line)]
    for index, line in enumerate(lines):
        if not _contains_focus_tokens(line, focus_tokens):
            continue
        nearby = " ".join(lines[max(0, index - 1) : min(len(lines), index + 2)])
        match = UPLOAD_PERSON_REGISTER_PATTERN.search(nearby)
        if match:
            return match.group(0)

    match = UPLOAD_PERSON_REGISTER_PATTERN.search(text)
    return match.group(0) if match else None


def _project_title_score(title: str) -> float:
    lowered = title.lower()
    if any(phrase in lowered for phrase in ("declare that this", "hereby declare", "report entitled", "submitted by")):
        return -1.0
    token_count = len(TOKEN_PATTERN.findall(lowered))
    score = 0.0
    if ":" in title:
        score += 0.7
    if title.isupper():
        score += 0.2
    if 4 <= token_count <= 12:
        score += 0.6
    elif 2 <= token_count <= 3:
        score += 0.1
    if len(title) >= 28:
        score += 0.4
    if re.search(r"\b(system|platform|monitoring|assistant|health|project|analysis|framework)\b", lowered):
        score += 0.5
    return score


def _normalize_upload_project_title(title: str) -> Optional[str]:
    cleaned = normalize_question(title.strip(' "\''))
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"(?i)^(?:certified that this report entitled|this project report entitled)\s+", "", cleaned)
    cleaned = re.sub(r"(?i)\s+(?:project report|submitted by|presented by).*$", "", cleaned)
    cleaned = cleaned.strip(" ,.;:-")
    return cleaned or None


def _extract_upload_person_project(texts: List[str]) -> Optional[str]:
    candidates: List[tuple[float, str]] = []
    for text in texts:
        if not text:
            continue
        for pattern in UPLOAD_PERSON_PROJECT_PATTERNS:
            for match in pattern.finditer(text):
                title = _normalize_upload_project_title(match.group("title"))
                if not title:
                    continue
                score = _project_title_score(title)
                if score > 0:
                    candidates.append((score, title))

    if candidates:
        return max(candidates, key=lambda item: (item[0], len(item[1])))[1]
    return None


def _extract_upload_person_department(texts: List[str]) -> Optional[str]:
    boundary_pattern = re.compile(
        r"(?i)\b(?:MES Institute|during|submitted by|presented by|april|may|june|july|august|september|october|november|december|20\d{2}|MEK\d{2}[A-Z]{2}\d{2,4})\b"
    )
    candidates: List[str] = []
    for text in texts:
        if not text:
            continue
        for line in text.splitlines():
            match = UPLOAD_PERSON_DEPARTMENT_PATTERN.search(line)
            if not match:
                continue
            department = normalize_question(match.group(0))
            boundary = boundary_pattern.search(department)
            if boundary:
                department = normalize_question(department[: boundary.start()])
            candidates.append(department.strip(" ,.;:-"))
    return max(candidates, key=len) if candidates else None


def build_upload_person_answer(question: str, payload: Dict[str, Any]) -> Optional[str]:
    if payload.get("question_type") != QUESTION_TYPE_FACT:
        return None
    if role_label_for_question(question) or matched_faculty_profile(question) or is_location_question(question):
        return None

    focus = question_focus_phrase(question)
    focus_tokens = [token for token in person_name_tokens(focus) if len(token) >= 3]
    if not focus_tokens:
        return None

    upload_results = [
        item
        for item in payload.get("vector_results", [])
        if item.get("source_type") == "upload" and _contains_focus_tokens(item.get("text", ""), focus_tokens)
    ]
    if not upload_results:
        return None

    relevant_texts = [item.get("text", "") for item in upload_results[:4]]
    combined_text = "\n".join(relevant_texts)
    name = _extract_upload_person_name(combined_text, focus_tokens)
    if not name:
        return None

    register_number = _extract_upload_person_register(combined_text, focus_tokens)
    project_title = _extract_upload_person_project(relevant_texts)
    department = _extract_upload_person_department(relevant_texts)
    year_match = UPLOAD_PERSON_YEAR_PATTERN.search(combined_text)
    year = normalize_question(year_match.group(0)) if year_match else None
    source_title = normalize_question(upload_results[0].get("title") or upload_results[0].get("source") or "")

    detail_signals = sum(bool(value) for value in (register_number, project_title, department, year))
    if detail_signals < 2:
        return None

    answer = _format_upload_person_name(name)
    if register_number:
        answer += f" ({register_number})"
    answer += " appears in the uploaded document"
    if source_title:
        answer += f" {source_title}"
    answer += " as one of the students"
    if project_title:
        answer += f' who presented the project "{project_title}"'
    if department:
        answer += f" in the {department}"
    if year:
        answer += f" during {year}"
    answer += "."
    return answer


def structured_person_profile_evidence(question: str) -> List[Dict[str, Any]]:
    faculty = matched_faculty_profile(question)
    if not faculty:
        return []

    name = normalize_person_name(faculty.get("name") or "")
    designation = normalize_question(faculty.get("designation") or "")
    department = normalize_question(faculty.get("department") or "")
    if designation and department:
        sentence = f"{name} is {designation} in the {department}."
    elif designation:
        sentence = f"{name} is {designation}."
    elif department:
        sentence = f"{name} is in the {department}."
    else:
        return []

    return [
        make_structured_evidence(
            sentence,
            department or name or "Faculty Records",
            source_url=faculty.get("source_url"),
            score=1.0,
            department=department or None,
        )
    ]


def structured_location_evidence() -> List[Dict[str, Any]]:
    overview = get_knowledge_base_service().public_sections().get("overview", {})
    summary = normalize_question(overview.get("summary", ""))
    location_match = re.search(r"\b(?:located at|located near)\s+(?P<place>[^.]+)", summary, flags=re.IGNORECASE)
    if location_match:
        place = normalize_question(location_match.group("place"))
        if place:
            return [make_structured_evidence(f"Location: {place}.", "Knowledge Base Overview", score=1.0)]

    location = normalize_question(overview.get("location", ""))
    if location:
        return [make_structured_evidence(f"Location: {location}.", "Knowledge Base Overview", score=1.0)]
    return []


def structured_role_evidence_from_faculty(question: str, label: str, focus: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if label == "Head of Department" and not focus:
        return []

    evidence: List[Dict[str, Any]] = []
    for faculty in get_knowledge_base_service().public_sections().get("faculty", []):
        designation = faculty.get("designation") or ""
        if not faculty_matches_role(label, designation):
            continue
        department = faculty.get("department") or ""
        if focus and not text_matches_department_focus(department, focus):
            continue
        name = normalize_person_name(faculty.get("name") or "")
        if not name:
            continue
        title = "MESITAM HODs" if "hods.php" in (faculty.get("source_url") or "").lower() else department or "Faculty Records"
        evidence.append(
            make_structured_evidence(
                f"{label}: {name}",
                title,
                source_url=faculty.get("source_url"),
                score=1.0,
                department=department,
            )
        )
    return evidence


def structured_role_evidence_from_documents(question: str, label: str, focus: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    documents = get_knowledge_base_service().public_sections().get("documents", [])
    for document in documents:
        priority = document_priority_for_fact_lookup(document)
        if priority < 0:
            continue
        title = document.get("title") or document.get("source") or "Official Source"
        if focus and not text_matches_department_focus(title, focus):
            continue

        text = document.get("text") or ""
        if not text:
            continue

        if label == "Principal" and "mandatory disclosure" in title.lower():
            match = re.search(
                r"Name of the Principal\s+(?P<name>.+?)\s+Exact Designation\s+Principal",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                name = normalize_person_name(match.group("name"))
                if name:
                    evidence.append(
                        make_structured_evidence(
                            f"{label}: {name}",
                            title,
                            source_url=document.get("url") or document.get("source_url"),
                            score=min(1.0, 0.9 + priority * 0.02),
                            source_type="official",
                        )
                    )

        for sentence in split_into_sentences(text):
            if is_heading_like_sentence(sentence):
                continue
            name = extract_name_for_role_question(question, sentence)
            if not name:
                continue
            evidence.append(
                make_structured_evidence(
                    f"{label}: {name}",
                    title,
                    source_url=document.get("url") or document.get("source_url"),
                    score=min(1.0, 0.9 + priority * 0.02),
                    source_type="official",
                )
            )
            break

    evidence.sort(
        key=lambda item: (
            float(item.get("score", 0.0) or 0.0),
            "mandatory disclosure" in (item.get("title") or "").lower(),
            "about mesitam" in (item.get("title") or "").lower(),
        ),
        reverse=True,
    )
    return evidence


def structured_fact_evidence(question: str) -> List[Dict[str, Any]]:
    if is_location_question(question):
        return structured_location_evidence()

    label = role_label_for_question(question)
    if not label:
        return structured_person_profile_evidence(question)

    focus = resolve_department_focus(question)
    return merge_evidence_lists(
        structured_role_evidence_from_faculty(question, label, focus),
        structured_role_evidence_from_documents(question, label, focus),
    )


def _protect_honorifics(text: str) -> str:
    protected = text or ""
    for original, placeholder in HONORIFIC_PLACEHOLDERS.items():
        protected = protected.replace(original, placeholder)
    return protected


def _restore_honorifics(text: str) -> str:
    restored = text or ""
    for original, placeholder in HONORIFIC_PLACEHOLDERS.items():
        restored = restored.replace(placeholder, original)
    return restored


def _protect_initials(text: str) -> str:
    return re.sub(r"\b([A-Z])\.", rf"\1{INITIAL_PLACEHOLDER}", text or "")


def _restore_initials(text: str) -> str:
    return (text or "").replace(INITIAL_PLACEHOLDER, ".")


def split_into_sentences(text: str) -> List[str]:
    working = normalize_question(re.sub(r"\[PAGE\s+\d+\]", " ", text or ""))
    if not working:
        return []

    protected = _protect_initials(_protect_honorifics(working))
    sub_blocks = re.split(r"\s+(?=(?:Dr§|Prof§|Mr§|Mrs§|Ms§))", protected)
    sentences: List[str] = []
    for block in sub_blocks:
        for part in SENTENCE_SPLIT_PATTERN.split(block):
            sentence = normalize_question(_restore_initials(_restore_honorifics(part)))
            sentence = sentence.strip("-:| ")
            if sentence:
                sentences.append(sentence)
    return sentences


def _token_set(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall((text or "").lower()))


def _whole_word_hits(tokens: List[str], text: str) -> int:
    lowered = f" {re.sub(r'[^a-z0-9]+', ' ', (text or '').lower())} "
    return sum(1 for token in tokens if f" {token} " in lowered)


def _semantic_scores(query: str, candidates: List[str], rag_engine: Any) -> List[float]:
    if not candidates or not rag_engine or not getattr(rag_engine, "encoder", None):
        return [0.0] * len(candidates)
    try:
        query_vector = rag_engine.encoder.encode([query], convert_to_numpy=True)[0]
        query_norm = float(np.linalg.norm(query_vector)) or 1.0
        sentence_vectors = rag_engine.encoder.encode(candidates, convert_to_numpy=True)
        scores: List[float] = []
        for sentence_vector in sentence_vectors:
            sentence_norm = float(np.linalg.norm(sentence_vector)) or 1.0
            score = float(np.dot(query_vector, sentence_vector) / (query_norm * sentence_norm))
            scores.append(round(max(-1.0, min(1.0, score)), 4))
        return scores
    except Exception:
        return [0.0] * len(candidates)


def filter_kg_facts(question: str, kg_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    query_tokens = grounding_query_terms(question)
    scored_facts: List[Dict[str, Any]] = []
    for item in kg_facts[:6]:
        fact_text = f"{item.get('entity', '')} {item.get('fact', '')}".strip()
        if not fact_text:
            continue
        hits = _whole_word_hits(query_tokens, fact_text)
        base_score = float(item.get("score", 0.0) or 0.0)
        if hits == 0 and query_tokens:
            continue
        scored_facts.append(
            {
                **item,
                "relevance_score": round(min(1.0, max(base_score, KG_FACT_SCORE_FLOOR if hits else base_score) + hits * 0.04), 2),
            }
        )
    scored_facts.sort(key=lambda item: float(item.get("relevance_score", item.get("score", 0.0)) or 0.0), reverse=True)
    return scored_facts[:3]


def merge_kg_facts(*fact_groups: List[Dict[str, Any]], limit: int = 6) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for group in fact_groups:
        for item in group or []:
            entity = normalize_question(item.get("entity", ""))
            fact = normalize_question(item.get("fact", ""))
            if not entity or not fact:
                continue
            key = (entity.lower(), fact.lower())
            if key in seen:
                continue
            seen.add(key)
            merged.append({**item, "entity": entity, "fact": fact})
            if len(merged) >= limit:
                return merged
    return merged


def filter_context_evidence(query: str, vector_results: List[Dict[str, Any]], rag_engine: Any) -> List[Dict[str, Any]]:
    query_tokens = grounding_query_terms(query)
    question_type = question_type_for(query)
    retrieval_limit = retrieval_chunk_limit_for(question_type)
    filtered_limit = filtered_sentence_limit_for(question_type)
    per_source_limit = 3 if question_type == QUESTION_TYPE_EXPLANATION else 2
    candidates: List[Dict[str, Any]] = []
    for chunk in vector_results[:retrieval_limit]:
        for sentence in split_into_sentences(chunk.get("text", "")):
            sentence = clean_extractive_sentence(sentence, query)
            if len(sentence.split()) < 4 and not re.search(r"[@%+\d]", sentence):
                continue
            if is_noise_line(sentence):
                continue
            if is_heading_like_sentence(sentence):
                continue
            if question_type in {QUESTION_TYPE_DEFINITION, QUESTION_TYPE_EXPLANATION} and is_low_value_fact_sentence(sentence):
                continue
            candidates.append(
                {
                    "sentence": sentence,
                    "title": chunk.get("title") or chunk.get("source") or "Official Source",
                    "source": chunk.get("source") or chunk.get("title") or "Official Source",
                    "page": chunk.get("page"),
                    "source_type": chunk.get("source_type", "official"),
                    "source_url": chunk.get("source_url"),
                    "match_type": chunk.get("match_type", "vector"),
                    "chunk_score": float(chunk.get("score", 0.0) or 0.0),
                    "reranker_score": float(chunk.get("reranker_score", chunk.get("score", 0.0)) or 0.0),
                }
            )

    semantic_scores = _semantic_scores(query, [item["sentence"] for item in candidates], rag_engine)
    kept: List[Dict[str, Any]] = []
    compact_queries = compact_query_forms(query)
    for item, semantic_score in zip(candidates, semantic_scores):
        compact_phrase = bool(
            compact_queries
            and any(compact_query in compact_alphanumeric(item["sentence"]) for compact_query in compact_queries)
        )
        keyword_hits = _whole_word_hits(query_tokens, item["sentence"])
        if compact_phrase and keyword_hits == 0:
            keyword_hits = min(2, max(1, len(query_tokens)))
        exact_phrase = normalize_question(query).lower() in normalize_question(item["sentence"]).lower() or compact_phrase
        definition_score = definition_match_score(query, item["sentence"])
        incomplete = is_incomplete_sentence(item["sentence"])
        if keyword_hits == 0 and semantic_score < SEMANTIC_SIMILARITY_THRESHOLD:
            continue
        if incomplete and definition_score < 1.4:
            continue
        relevance = min(
            1.0,
            max(
                float(item["chunk_score"]),
                semantic_score * 0.55 + min(keyword_hits, 3) * 0.14 + (0.1 if exact_phrase else 0.0) + min(definition_score, 3.0) * 0.08,
            ),
        )
        if sentence_has_spacing_artifacts(item["sentence"]):
            relevance = max(0.0, relevance - 0.12)
        kept.append(
            {
                **item,
                "semantic_score": round(semantic_score, 4),
                "keyword_hits": keyword_hits,
                "definition_score": definition_score,
                "exact_phrase": exact_phrase,
                "incomplete": incomplete,
                "score": round(relevance, 2),
            }
        )

    if question_type == QUESTION_TYPE_DEFINITION:
        kept.sort(
            key=lambda item: (
                not item["incomplete"],
                item.get("definition_score", 0.0),
                item["exact_phrase"],
                item["keyword_hits"],
                item["semantic_score"],
                item["reranker_score"],
                item["chunk_score"],
            ),
            reverse=True,
        )
    elif question_type == QUESTION_TYPE_EXPLANATION:
        kept.sort(
            key=lambda item: (
                not item["incomplete"],
                item["keyword_hits"],
                item["semantic_score"],
                item["reranker_score"],
                item["chunk_score"],
                item.get("definition_score", 0.0),
            ),
            reverse=True,
        )
    else:
        kept.sort(
            key=lambda item: (
                not item["incomplete"],
                item["keyword_hits"],
                item["exact_phrase"],
                item.get("definition_score", 0.0),
                item["semantic_score"],
                item["reranker_score"],
                item["chunk_score"],
            ),
            reverse=True,
        )

    filtered: List[Dict[str, Any]] = []
    seen_sentences: set[str] = set()
    per_source_counts: Dict[tuple[str, Optional[int]], int] = {}
    for item in kept:
        normalized_sentence = re.sub(r"[^a-z0-9]+", " ", item["sentence"].lower()).strip()
        if not normalized_sentence or normalized_sentence in seen_sentences:
            continue
        source_key = (item["title"], item.get("page"))
        if per_source_counts.get(source_key, 0) >= per_source_limit:
            continue
        seen_sentences.add(normalized_sentence)
        per_source_counts[source_key] = per_source_counts.get(source_key, 0) + 1
        filtered.append(item)
        if len(filtered) >= filtered_limit:
            break

    return filtered


def compute_confidence(
    filtered_evidence: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]],
    filtered_kg_facts: List[Dict[str, Any]],
) -> float:
    sentence_score = float(filtered_evidence[0].get("score", 0.0) or 0.0) if filtered_evidence else 0.0
    top_result = vector_results[0] if vector_results else {}
    chunk_score = max(
        float(top_result.get("score", 0.0) or 0.0),
        float(top_result.get("reranker_score", 0.0) or 0.0),
        float(top_result.get("keyword_match_score", 0.0) or 0.0),
    )
    if filtered_evidence and filtered_evidence[0].get("match_type") == "structured":
        sentence_score = max(sentence_score, 0.98)
        chunk_score = max(chunk_score, sentence_score)
    kg_score = max((float(item.get("relevance_score", item.get("score", 0.0)) or 0.0) for item in filtered_kg_facts), default=0.0)
    if filtered_evidence and filtered_kg_facts:
        confidence = sentence_score * 0.5 + chunk_score * 0.3 + kg_score * 0.2
    elif filtered_evidence:
        confidence = sentence_score * 0.7 + chunk_score * 0.3
    else:
        confidence = kg_score
    return round(min(1.0, max(0.0, confidence)), 2)


def build_sources(
    vector_results: List[Dict[str, Any]],
    filtered_evidence: List[Dict[str, Any]],
    question: str = "",
    question_type: str = QUESTION_TYPE_FACT,
) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    seen: set[tuple[str, Optional[int], str]] = set()
    if question_type == QUESTION_TYPE_EXPLANATION:
        preferred_evidence = select_answer_explanation_evidence(question, filtered_evidence, limit=4) or filtered_evidence
    elif question_type == QUESTION_TYPE_DEFINITION:
        preferred_evidence = select_definition_evidence(question, filtered_evidence, limit=1) or filtered_evidence
    else:
        preferred_evidence = [item for item in filtered_evidence if item.get("match_type") == "structured"] or filtered_evidence
    preferred_evidence = [item for item in preferred_evidence if not item.get("incomplete")] or preferred_evidence
    preferred_evidence = [item for item in preferred_evidence if not is_low_value_fact_sentence(item.get("sentence", ""))] or preferred_evidence

    for item in preferred_evidence:
        excerpt_key = (
            re.sub(r"[^a-z0-9]+", " ", (item.get("sentence", "") or "").lower()).strip()[:80]
            if question_type == QUESTION_TYPE_EXPLANATION
            else ""
        )
        key = (item["title"], item.get("page"), excerpt_key)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "title": item["title"],
                "page": item.get("page"),
                "excerpt": item["sentence"][:280],
                "score": round(float(item.get("score", 0.0) or 0.0), 2),
                "match_type": item.get("match_type", "vector"),
                "source_type": item.get("source_type", "official"),
                "source_url": item.get("source_url"),
            }
        )
        if len(sources) >= 4:
            return sources

    if sources:
        return sources

    for item in vector_results[:4]:
        excerpt_key = (
            re.sub(r"[^a-z0-9]+", " ", (item.get("text", "") or "").lower()).strip()[:80]
            if question_type == QUESTION_TYPE_EXPLANATION and item.get("page") is None
            else ""
        )
        key = ((item.get("title") or item.get("source") or "Official Source"), item.get("page"), excerpt_key)
        if key in seen:
            continue
        if is_low_value_fact_sentence(item.get("text", "")[:280]):
            continue
        sources.append(
            {
                "title": item.get("title") or item.get("source") or "Official Source",
                "page": item.get("page"),
                "excerpt": item.get("text", "")[:280],
                "score": round(float(item.get("score", 0.0) or 0.0), 2),
                "match_type": item.get("match_type", "vector"),
                "source_type": item.get("source_type", "official"),
                "source_url": item.get("source_url"),
            }
        )
        if len(sources) >= 4:
            break
    return sources


def select_generation_evidence(filtered_evidence: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    per_source_counts: Dict[tuple[str, Optional[int]], int] = {}
    for item in filtered_evidence:
        if item.get("incomplete"):
            continue
        source_key = (item.get("title") or item.get("source") or "Official Source", item.get("page"))
        if per_source_counts.get(source_key, 0) >= 2:
            continue
        per_source_counts[source_key] = per_source_counts.get(source_key, 0) + 1
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected or filtered_evidence[:limit]


def build_generation_context(payload: Dict[str, Any]) -> str:
    sections = []
    evidence_question = evidence_scoring_question(payload.get("question", ""), payload.get("retrieval_query"))
    explanation_question = payload.get("question", "") or evidence_question
    if payload.get("follow_up_note"):
        sections.append(payload["follow_up_note"])

    if payload.get("direct_answer"):
        sections.append("Direct answer candidate:\n" + payload["direct_answer"])

    if payload.get("context_sections"):
        sections.extend(section for section in payload["context_sections"] if section)
        if payload.get("question_type") != QUESTION_TYPE_EXPLANATION:
            return "\n\n".join(section for section in sections if section)

    if payload.get("filtered_kg_facts"):
        fact_lines = [f"- {item['entity']}: {item['fact']}" for item in payload["filtered_kg_facts"][:2]]
        sections.append("Structured evidence:\n" + "\n".join(fact_lines))

    if payload.get("filtered_evidence"):
        document_lines = []
        response_type = payload.get("question_type", QUESTION_TYPE_EXPLANATION)
        if response_type == QUESTION_TYPE_DEFINITION:
            selected_evidence = select_definition_evidence(
                evidence_question,
                payload["filtered_evidence"],
                limit=1,
            )
        elif response_type == QUESTION_TYPE_EXPLANATION:
            selected_evidence = select_answer_explanation_evidence(
                explanation_question,
                payload["filtered_evidence"],
                limit=6,
            )
        else:
            selected_evidence = select_generation_evidence(payload["filtered_evidence"], limit=4)
        for item in selected_evidence:
            title = item.get("title") or item.get("source") or "Official Source"
            page = f", page {item['page']}" if item.get("page") else ""
            document_lines.append(f"[{title}{page}] {item.get('sentence', '')}")
        sections.append("Relevant context:\n" + "\n".join(document_lines))

    return "\n\n".join(section for section in sections if section)


def build_no_hit_response(payload: Dict[str, Any], answer_mode: str | None = None) -> Dict[str, Any]:
    _ = answer_mode
    return {
        "answer": STRICT_REFUSAL,
        "sources": [],
        "kg_facts": [],
        "confidence": 0.0,
        "confidence_label": "Low",
        "status": "refused",
        "type": payload.get("question_type", QUESTION_TYPE_FACT),
        "trace_id": payload.get("trace_id"),
        "query_plan": payload.get("query_plan"),
        "retrieval_trace": payload.get("retrieval_trace"),
        "graph_view": payload.get("graph_view", {"nodes": [], "edges": []}),
        "source_groups": {"documents": [], "kg_facts": []},
    }


def build_chat_payload(
    question: str,
    history: Optional[List[Dict[str, str]]],
    rag_engine: Any,
    kg_query_fn: Callable[[str], List[Dict[str, Any]]] = query_kg_facts,
    stage_callback: Optional[Callable[[str, str], None]] = None,
    include_graph: bool = False,
) -> Dict[str, Any]:
    start_time = time.time()
    pipeline_result = run_hybrid_pipeline(
        question=question,
        history=history or [],
        rag_engine=rag_engine,
        stage_callback=stage_callback,
        include_graph=include_graph,
    )
    retrieval_query = pipeline_result.get("retrieval_query") or question
    follow_up_note = pipeline_result.get("follow_up_note")
    intent = pipeline_result.get("intent") or get_intent(retrieval_query or question)
    retrieval = pipeline_result.get("retrieval", {})
    question_type = question_type_for(question)
    retrieval_limit = retrieval_chunk_limit_for(question_type)
    evidence_question = evidence_scoring_question(question, retrieval_query)
    vector_results = filter_vector_results(question, pipeline_result.get("vector_results", []) or [])[:retrieval_limit]
    retrieval["results"] = vector_results

    pipeline_kg_facts = pipeline_result.get("kg_facts") or []
    fallback_kg_facts = kg_query_fn(retrieval_query or question) or []
    if role_label_for_question(question):
        kg_facts = merge_kg_facts(fallback_kg_facts, pipeline_kg_facts, limit=6)
    else:
        kg_facts = merge_kg_facts(pipeline_kg_facts, fallback_kg_facts, limit=6)
    vector_results = rerank_vector_results_for_answer(question, vector_results, kg_facts)[:retrieval_limit]
    retrieval["results"] = vector_results

    if stage_callback:
        stage_callback("filtering_context", "Filtering evidence...")
    filtered_kg_facts = filter_kg_facts(question, kg_facts)
    fact_structured_evidence = structured_fact_evidence(question) if question_type == QUESTION_TYPE_FACT else []
    context_structured_evidence = structured_kg_context_evidence(question, question_type, filtered_kg_facts)
    retrieved_evidence = filter_context_evidence(evidence_question, vector_results, rag_engine)
    supplemental_definition_evidence = []
    if question_type == QUESTION_TYPE_DEFINITION or (question_type == QUESTION_TYPE_EXPLANATION and explanation_prefers_overview(question)):
        supplemental_results = supplemental_definition_results(question, rag_engine)
        supplemental_definition_evidence = filter_context_evidence(evidence_question, supplemental_results, rag_engine)
    if role_label_for_question(question):
        filtered_evidence = merge_evidence_lists(
            retrieved_evidence[:2],
            fact_structured_evidence,
            retrieved_evidence[2:],
            limit=filtered_sentence_limit_for(question_type),
        )
    elif question_type == QUESTION_TYPE_EXPLANATION:
        filtered_evidence = merge_evidence_lists(
            supplemental_definition_evidence,
            context_structured_evidence,
            retrieved_evidence,
            limit=filtered_sentence_limit_for(question_type),
        )
    else:
        filtered_evidence = merge_evidence_lists(
            supplemental_definition_evidence,
            fact_structured_evidence,
            context_structured_evidence,
            retrieved_evidence,
            limit=filtered_sentence_limit_for(question_type),
        )
    filtered_kg_facts, filtered_evidence, context_budget = optimize_context_budget(filtered_kg_facts, filtered_evidence)
    confidence = compute_confidence(filtered_evidence, vector_results, filtered_kg_facts)
    confidence_label = confidence_label_for(confidence)
    explanation_ready = (
        has_sufficient_explanation_evidence(evidence_scoring_question(question, retrieval_query), filtered_evidence)
        if question_type == QUESTION_TYPE_EXPLANATION
        else False
    )
    payload = {
        "question": question,
        "history": history or [],
        "intent": intent,
        "question_type": question_type,
        "start_time": start_time,
        "retrieval_query": retrieval_query,
        "follow_up_note": follow_up_note,
        "retrieval": retrieval,
        "vector_results": vector_results,
        "kg_facts": filtered_kg_facts,
        "kg_facts_raw": kg_facts,
        "filtered_kg_facts": filtered_kg_facts,
        "filtered_evidence": filtered_evidence,
        "confidence": confidence,
        "confidence_label": confidence_label,
        "explanation_ready": explanation_ready,
        "trace_id": pipeline_result.get("trace_id"),
        "query_plan": pipeline_result.get("query_plan"),
        "retrieval_trace": pipeline_result.get("pipeline_trace"),
        "graph_view": pipeline_result.get("graph_view", {"nodes": [], "edges": []}),
        "context_budget": context_budget,
    }
    direct_answer = build_direct_answer(question, payload)
    has_grounded_evidence = bool(filtered_evidence or filtered_kg_facts or direct_answer)
    if not has_grounded_evidence:
        status = "refused"
    elif question_type in {QUESTION_TYPE_FACT, QUESTION_TYPE_DEFINITION} and not direct_answer:
        status = "refused"
    elif question_type == QUESTION_TYPE_EXPLANATION and not explanation_ready:
        status = "refused"
    else:
        status = "limited" if confidence_label == "Low" else "complete"

    response_strategy = "extractive"
    if status != "refused" and (filtered_evidence or filtered_kg_facts or direct_answer):
        response_strategy = "generate"

    payload.update(
        {
            "direct_answer": direct_answer,
            "status": status,
            "response_strategy": response_strategy,
            "sources": build_sources(vector_results, filtered_evidence, question=question, question_type=question_type),
            "type": question_type,
            "context_sections": context_budget.get("context_sections", []),
            "context_parts": [
                section
                for section in [
                    follow_up_note,
                    "Structured evidence:\n" + "\n".join(f"- {item['entity']}: {item['fact']}" for item in filtered_kg_facts) if filtered_kg_facts else "",
                    "Relevant context:\n" + "\n".join(item.get("sentence", "") for item in filtered_evidence) if filtered_evidence else "",
                ]
                if section
            ],
            "source_groups": {
                "kg_facts": filtered_kg_facts,
                "documents": build_sources(vector_results, filtered_evidence, question=question, question_type=question_type),
            },
        }
    )
    return payload


def cleanup_response_text(text: str) -> str:
    replacements = {
        " ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢ ": "\n- ",
        "Ã¢â‚¬Â¢ ": "\n- ",
        "ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¢ ": "\n- ",
        " ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¢ ": "\n- ",
        "ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¢ ": "\n- ",
        "ÃƒÆ’Ã‚Â¢Ãƒâ€¦Ã‚Â¾Ãƒâ€šÃ‚Â¤ ": "\n\n",
        "ÃƒÂ¢Ã…Â¾Ã‚Â¤ ": "\n\n",
    }
    cleaned = text or ""
    for needle, replacement in replacements.items():
        cleaned = cleaned.replace(needle, replacement)
    cleaned = re.sub(r"(?i)\baccording to (this|the document|the documents|the knowledge graph|the provided context),?\s*", "", cleaned)
    return cleaned.strip()


def format_final_answer(payload: Dict[str, Any], generated_answer: str) -> str:
    _ = payload
    return cleanup_response_text(generated_answer)


def build_extractive_fallback(payload: Dict[str, Any], answer_mode: str | None = None) -> str:
    if payload.get("direct_answer"):
        return format_final_answer(payload, payload["direct_answer"])

    evidence_question = evidence_scoring_question(payload.get("question", ""), payload.get("retrieval_query"))
    explanation_question = payload.get("question", "") or evidence_question
    evidence_sentences = [item["sentence"] for item in payload.get("filtered_evidence", [])]
    if evidence_sentences:
        response_type = payload.get("question_type", QUESTION_TYPE_DEFINITION)
        if response_type == QUESTION_TYPE_FACT:
            best_sentence = select_best_fact_sentence(payload.get("question", ""), payload.get("filtered_evidence", []))
            return format_final_answer(payload, best_sentence or evidence_sentences[0])
        if response_type == QUESTION_TYPE_DEFINITION:
            definition_sentences = select_definition_sentences(evidence_question, payload.get("filtered_evidence", []))
            if definition_sentences:
                return format_final_answer(payload, definition_sentences[0])
        explanation_limit = 5 if answer_mode == "detailed" else 4
        explanation_evidence = (
            select_answer_explanation_evidence(
                explanation_question,
                payload.get("filtered_evidence", []),
                limit=explanation_limit,
            )
            if response_type == QUESTION_TYPE_EXPLANATION
            else select_explanation_evidence(evidence_question, payload.get("filtered_evidence", []), limit=explanation_limit)
        )
        if explanation_evidence:
            return format_final_answer(payload, " ".join(item["sentence"] for item in explanation_evidence[:explanation_limit]))
        return format_final_answer(payload, " ".join(evidence_sentences[: min(len(evidence_sentences), 4)]))

    fact_lines = [f"{item['entity']}: {item['fact']}" for item in payload.get("filtered_kg_facts", [])[:2]]
    return format_final_answer(payload, " ".join(fact_lines))


def _token_supported(token: str, allowed_tokens: set[str]) -> bool:
    if token in allowed_tokens:
        return True
    variants = {
        token.rstrip("s"),
        token[:-2] if token.endswith("es") else token,
        token[:-2] if token.endswith("ed") else token,
        token[:-3] if token.endswith("ing") else token,
    }
    return any(variant in allowed_tokens for variant in variants if variant)


def unsupported_answer_tokens(answer: str, payload: Dict[str, Any]) -> List[str]:
    allowed_tokens = _token_set(build_generation_context(payload))
    allowed_tokens.update(_token_set(payload.get("question", "")))
    extras: List[str] = []
    for token in TOKEN_PATTERN.findall((answer or "").lower()):
        if token in GROUNDING_STOPWORDS:
            continue
        if _token_supported(token, allowed_tokens):
            continue
        if token not in extras:
            extras.append(token)
    return extras


def is_answer_grounded(answer: str, payload: Dict[str, Any]) -> bool:
    if not answer:
        return False
    confidence = float(payload.get("confidence", 0.0) or 0.0)
    has_structured_support = any(item.get("match_type") == "structured" for item in payload.get("filtered_evidence", []))
    if confidence < GENERATION_CONFIDENCE_THRESHOLD:
        role_label = role_label_for_question(payload.get("question", ""))
        if not (payload.get("question_type") == QUESTION_TYPE_FACT and role_label and has_structured_support):
            return False
    if unsupported_answer_tokens(answer, payload):
        return False

    response_type = payload.get("question_type", QUESTION_TYPE_EXPLANATION)
    overlap_ratio = 0.25 if response_type in {QUESTION_TYPE_FACT, QUESTION_TYPE_DEFINITION} else 0.4
    min_overlap = 1 if response_type in {QUESTION_TYPE_FACT, QUESTION_TYPE_DEFINITION} else 2
    answer_sentences = [item for item in split_into_sentences(answer) if item]
    evidence_texts = [item["sentence"] for item in payload.get("filtered_evidence", [])]
    if payload.get("direct_answer"):
        evidence_texts.insert(0, payload["direct_answer"])
    for sentence in answer_sentences:
        answer_tokens = _token_set(sentence) - GROUNDING_STOPWORDS
        if not answer_tokens:
            continue
        supported = False
        for evidence in evidence_texts:
            evidence_tokens = _token_set(evidence)
            overlap = len(answer_tokens & evidence_tokens)
            if overlap >= max(min_overlap, math.ceil(len(answer_tokens) * overlap_ratio)):
                supported = True
                break
        if not supported and payload.get("filtered_kg_facts"):
            for fact in payload["filtered_kg_facts"]:
                fact_tokens = _token_set(f"{fact.get('entity', '')} {fact.get('fact', '')}")
                overlap = len(answer_tokens & fact_tokens)
                if overlap >= max(min_overlap, math.ceil(len(answer_tokens) * overlap_ratio)):
                    supported = True
                    break
        if not supported:
            return False
    return True


def finalize_answer_text(payload: Dict[str, Any], generated_text: str, answer_mode: str = "concise") -> str:
    raw_text = generated_text or ""
    if raw_text.strip().startswith("LLM Generation Error:"):
        raw_text = ""
    cleaned_raw = cleanup_response_text(raw_text)
    normalized_cleaned = normalize_question(cleaned_raw).lower()
    if normalized_cleaned == STRICT_REFUSAL.lower() or normalized_cleaned.startswith(STRICT_REFUSAL.lower()):
        return build_extractive_fallback(payload, answer_mode=answer_mode)
    if not cleaned_raw:
        return build_extractive_fallback(payload, answer_mode=answer_mode)
    if payload.get("question_type") == QUESTION_TYPE_FACT:
        if not is_answer_grounded(cleaned_raw, payload):
            return build_extractive_fallback(payload, answer_mode=answer_mode)
    return format_final_answer(payload, cleaned_raw)


def maybe_expand_detailed_answer(question: str, payload: Dict[str, Any], answer: str, answer_mode: str | None) -> str:
    _ = question
    _ = answer_mode
    if payload.get("response_strategy") == "extractive" and payload.get("question_type") == QUESTION_TYPE_EXPLANATION:
        return build_extractive_fallback(payload, answer_mode=answer_mode)
    return answer


def role_label_for_question(question: str) -> Optional[str]:
    lowered = normalize_question(question).lower()
    for aliases, label in ROLE_QUERY_LABELS:
        if any(alias in lowered for alias in aliases):
            return label
    return None


def role_sentence_matches_label(label: str, sentence: str) -> bool:
    lowered = normalize_question(sentence).lower()
    if label == "Principal":
        return bool(re.search(r"\bprincipal\b", lowered)) and "vice principal" not in lowered and "principal in charge" not in lowered
    if label == "Vice Principal":
        return "vice principal" in lowered
    if label == "Head of Department":
        return bool(re.search(r"\bhead of (?:the )?department\b", lowered) or re.search(r"\bhod\b", lowered))
    return label.lower() in lowered


def extract_name_for_role_question(question: str, sentence: str) -> Optional[str]:
    label = role_label_for_question(question)
    if not label:
        return None
    if not role_sentence_matches_label(label, sentence):
        return None

    role_regex = {
        "Principal": r"principal(?!\s+in\s+charge)",
        "Vice Principal": r"vice principal",
        "Head of Department": r"(?:head of (?:the )?department|hod(?:\s*\([^)]*\))?)",
        "Dean": r"dean",
        "Director": r"director",
    }[label]
    honorific_name = PERSON_NAME_PATTERN.pattern
    patterns = (
        rf"(?P<name>{honorific_name})\s+(?:is\s+(?:the\s+)?)?{role_regex}\b",
        rf"\b{role_regex}\b\s*[:,-]?\s*(?P<name>{honorific_name})",
    )
    for pattern in patterns:
        match = re.search(pattern, sentence, flags=re.IGNORECASE)
        if match:
            return normalize_question(match.group("name"))

    if re.search(role_regex, sentence, flags=re.IGNORECASE):
        fallback_match = re.search(honorific_name, sentence)
        if fallback_match:
            return normalize_question(fallback_match.group(0))
    return None


def build_direct_answer(question: str, payload: Dict[str, Any]) -> Optional[str]:
    response_type = payload.get("question_type")
    if response_type == QUESTION_TYPE_DEFINITION:
        definition_sentences = select_definition_sentences(question, payload.get("filtered_evidence", []))
        if definition_sentences:
            return definition_sentences[0]
    elif response_type != QUESTION_TYPE_FACT:
        return None

    matched_faculty = matched_faculty_profile(question)
    if matched_faculty:
        preferred_name = normalize_person_name(matched_faculty.get("name") or "")
        preferred_tokens = set(person_name_tokens(preferred_name))
        for item in payload.get("filtered_evidence", []):
            sentence = normalize_question(item.get("sentence", ""))
            if item.get("match_type") != "structured":
                continue
            if preferred_tokens and preferred_tokens & set(person_name_tokens(sentence)):
                return sentence

    uploaded_person_answer = build_upload_person_answer(question, payload)
    if uploaded_person_answer:
        return uploaded_person_answer

    label = role_label_for_question(question)
    if label:
        focus = resolve_department_focus(question) if label == "Head of Department" else None
        candidates: List[tuple[float, int, str]] = []
        for index, item in enumerate(payload.get("filtered_evidence", [])):
            name = extract_name_for_role_question(question, item["sentence"])
            if not name:
                continue
            focus_text = item.get("department") or item.get("title") or item.get("sentence") or ""
            if focus and not text_matches_department_focus(focus_text, focus):
                continue

            candidate_score = float(item.get("score", 0.0) or 0.0)
            sentence_text = normalize_question(item.get("sentence", "")).lower()
            if item.get("match_type") == "structured":
                candidate_score += 1.0
            title = normalize_question(item.get("title") or item.get("source") or "").lower()
            if label == "Principal" and "about mesitam" in title:
                candidate_score += 0.6
            if label == "Principal" and "mandatory disclosure" in title:
                candidate_score += 0.3
            if len(sentence_text.split()) <= 8 and not any(
                term in sentence_text for term in ("assistant professor", "associate professor", "principal in charge")
            ):
                candidate_score += 2.0
            if label == "Head of Department" and focus and text_matches_department_focus(title, focus):
                candidate_score += 0.8
            if label == "Head of Department" and "hod" in title:
                candidate_score += 1.2
            candidates.append((candidate_score, -index, normalize_person_name(name)))

        if candidates:
            best_name = max(candidates)[2]
            return f"{label}: {best_name}"
    else:
        best_sentence = select_best_fact_sentence(question, payload.get("filtered_evidence", []))
        if best_sentence:
            return best_sentence

    for item in payload.get("filtered_kg_facts", []):
        if label and item.get("entity"):
            return f"{label}: {normalize_question(item['entity'])}"
        return normalize_question(f"{item.get('entity', '')}: {item.get('fact', '')}".strip(": "))

    return None


def chat_response_from_payload(
    question: str,
    payload: Dict[str, Any],
    answer_mode: str | None,
    history: Optional[List[Dict[str, str]]],
    generate_answer_fn=generate_answer,
) -> Dict[str, Any]:
    if payload.get("status") == "refused":
        return build_no_hit_response(payload, answer_mode=answer_mode)

    if payload.get("response_strategy") != "generate":
        answer = build_extractive_fallback(payload, answer_mode=answer_mode)
    else:
        final_context = build_generation_context(payload)
        generation_history = build_generation_history(history)
        response_text = ""
        try:
            generator = generate_answer_fn(
                question,
                final_context,
                generation_history,
                response_type=payload.get("question_type", QUESTION_TYPE_EXPLANATION),
                answer_mode=answer_mode,
            )
        except TypeError:
            generator = generate_answer_fn(question, final_context, generation_history, answer_mode=answer_mode)
        for chunk in generator:
            response_text += chunk
        answer = finalize_answer_text(payload, response_text, answer_mode=answer_mode)

    answer = maybe_expand_detailed_answer(question, payload, answer, answer_mode)
    if not answer:
        answer = STRICT_REFUSAL
        payload = dict(payload)
        payload["status"] = "refused"
        payload["confidence"] = 0.0
        payload["confidence_label"] = "Low"

    return {
        "answer": answer,
        "sources": payload.get("sources", []),
        "kg_facts": payload.get("kg_facts", []),
        "confidence": payload.get("confidence", 0.0),
        "confidence_label": payload.get("confidence_label", "Low"),
        "status": payload.get("status", "complete"),
        "type": payload.get("question_type", QUESTION_TYPE_FACT),
        "trace_id": payload.get("trace_id"),
        "query_plan": payload.get("query_plan"),
        "retrieval_trace": payload.get("retrieval_trace"),
        "graph_view": payload.get("graph_view", {"nodes": [], "edges": []}),
        "source_groups": payload.get("source_groups", {"documents": [], "kg_facts": []}),
    }


def build_legacy_response(response: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    source_bullets = ""
    for source in response.get("sources", []):
        page = f", page {source['page']}" if source.get("page") else ""
        source_bullets += f"- `{source['title']}`{page}\n"

    routing = "No Retrieval Hit"
    if response.get("kg_facts") and response.get("sources"):
        routing = "KG + Vector"
    elif response.get("kg_facts"):
        routing = "Knowledge Graph"
    elif response.get("sources"):
        routing = "Vector DB Search"

    snippets = [
        {
            "source": source["title"],
            "page": source.get("page"),
            "score": source.get("score", 0.0),
            "text": source.get("excerpt", ""),
        }
        for source in response.get("sources", [])
    ]
    kg_text = None
    if response.get("kg_facts"):
        kg_text = " | ".join(f"{item['entity']}: {item['fact']}" for item in response["kg_facts"])

    return {
        "answer": response["answer"],
        "confidence": int(round(float(response.get("confidence", 0.0)) * 100)),
        "sources": source_bullets,
        "reasoning": f"Routing: **{routing}**",
        "routing": routing,
        "kg_source": {"source": "Knowledge Graph", "score": 1.0, "text": kg_text[:260]} if kg_text else None,
        "snippets": snippets,
        "mode": "Combined Mode" if response.get("kg_facts") and response.get("sources") else "Knowledge Graph Mode" if response.get("kg_facts") else "Vector Search Mode" if response.get("sources") else "No DB hit",
        "status": response.get("status", payload.get("status", "complete")),
    }


def build_cache_key(question: str, answer_mode: str | None, index_version: str, retrieval_version: Optional[str] = None) -> str:
    _ = answer_mode
    retrieval_key = retrieval_version or f"{get_retrieval_version()}::{CHAT_PIPELINE_VERSION}"
    return f"{normalize_question(question).lower()}::{index_version}::{retrieval_key}"


def get_cached_response(question: str, answer_mode: str | None, index_version: str, retrieval_version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    return get_response_cache().get(build_cache_key(question, answer_mode, index_version, retrieval_version))


def set_cached_response(question: str, answer_mode: str | None, index_version: str, response: Dict[str, Any], retrieval_version: Optional[str] = None) -> None:
    get_response_cache().set(build_cache_key(question, answer_mode, index_version, retrieval_version), response)
