from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from rag import extract_keywords, normalize_retrieval_query
from router import get_intent, correct_spelling

from ..department_aliases import department_aliases, normalize_department_text, question_mentions_alias
from ..knowledge_base import get_knowledge_base_service
from ..upload_kg import get_upload_kg_service
from .types import EntitySeed, QueryPlan


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
QUESTION_TYPE_FACT = "fact"
QUESTION_TYPE_DEFINITION = "definition"
QUESTION_TYPE_EXPLANATION = "explanation"


def normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def question_type_for(query: str) -> str:
    lowered = normalize_text(query).lower()
    if lowered.startswith(("how many", "how much", "how long")):
        return QUESTION_TYPE_FACT
    if lowered.startswith(("what is ", "what are ", "define ", "definition of ", "meaning of ")):
        return QUESTION_TYPE_DEFINITION
    if any(term in lowered for term in ("explain", "describe", "summarize", "summary", "overview", "tell me about", "walk me through")):
        return QUESTION_TYPE_EXPLANATION
    if lowered.startswith(("how ", "why ")):
        return QUESTION_TYPE_EXPLANATION
    return QUESTION_TYPE_FACT


def extract_recent_user_questions(history: Optional[List[Dict[str, str]]], limit: int = 3) -> List[str]:
    items: List[str] = []
    for entry in history or []:
        if entry.get("role") != "user":
            continue
        content = normalize_text(entry.get("content", ""))
        if content:
            items.append(content)
    return items[-limit:]


def is_follow_up_question(question: str) -> bool:
    lowered = normalize_text(question).lower()
    return bool(
        lowered
        and (
            FOLLOW_UP_REFERENCE_PATTERN.search(lowered)
            or any(lowered.startswith(prefix) for prefix in FOLLOW_UP_STARTERS)
        )
    )


def resolve_follow_up(question: str, history: Optional[List[Dict[str, str]]]) -> tuple[str, Optional[str], bool]:
    normalized_question = normalize_text(question)
    prior_user_questions = extract_recent_user_questions(history)
    if not prior_user_questions or not is_follow_up_question(normalized_question):
        return normalized_question, None, False

    reference_question = prior_user_questions[-1]
    if reference_question.lower() == normalized_question.lower():
        return normalized_question, None, False

    rewritten = f"{reference_question}\nFollow-up question: {normalized_question}"
    note = (
        f"Conversation hint: the current question refers to the earlier user question "
        f"'{reference_question}'. Use this only to resolve references. It is not evidence."
    )
    return rewritten, note, True


def _score_keyword_overlap(query_tokens: List[str], candidate_tokens: List[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    overlap = len(set(query_tokens) & set(candidate_tokens))
    if overlap == 0:
        return 0.0
    return overlap / max(len(set(query_tokens)), 1)


def _entity_candidates() -> List[Dict[str, Any]]:
    kb = get_knowledge_base_service().public_sections()
    candidates: List[Dict[str, Any]] = []

    for department in kb.get("departments", []):
        name = normalize_text(department.get("name", ""))
        if not name:
            continue
        candidates.append(
            {
                "label": name,
                "entity_type": "department",
                "aliases": list(department_aliases(name)),
            }
        )

    for faculty in kb.get("faculty", []):
        name = normalize_text(faculty.get("name", ""))
        if name:
            candidates.append(
                {
                    "label": name,
                    "entity_type": "faculty",
                    "aliases": [name.lower()],
                }
            )

    for course in kb.get("courses", []):
        name = normalize_text(course.get("name", ""))
        code = normalize_text(course.get("code", ""))
        aliases = [name.lower()] if name else []
        if code:
            aliases.append(code.lower())
        if name:
            candidates.append(
                {
                    "label": code or name,
                    "entity_type": "course",
                    "aliases": aliases,
                }
            )

    for facility in kb.get("facilities", []):
        name = normalize_text(facility.get("name", ""))
        if name:
            candidates.append(
                {
                    "label": name,
                    "entity_type": "facility",
                    "aliases": [name.lower()],
                }
            )

    for upload_entity in get_upload_kg_service().entity_candidates():
        name = normalize_text(upload_entity.get("label", ""))
        if name:
            candidates.append(
                {
                    "label": name,
                    "entity_type": upload_entity.get("entity_type", "upload_entity"),
                    "aliases": upload_entity.get("aliases") or [name.lower()],
                }
            )

    return candidates


def extract_entities(query: str, limit: int = 5) -> List[EntitySeed]:
    normalized_query = normalize_department_text(query)
    query_tokens = [token for token in extract_keywords(query) if len(token) >= 3]
    hits: List[EntitySeed] = []
    seen: set[tuple[str, str]] = set()

    for candidate in _entity_candidates():
        best_alias = None
        best_score = 0.0
        for alias in candidate.get("aliases", []):
            alias_text = normalize_department_text(alias)
            if not alias_text:
                continue
            alias_tokens = [token for token in extract_keywords(alias_text) if len(token) >= 2]
            score = 0.0
            if " " in alias_text:
                if question_mentions_alias(normalized_query, alias_text):
                    score += 0.8
            elif f" {alias_text} " in f" {normalized_query} ":
                score += 0.7
            score += _score_keyword_overlap(query_tokens, alias_tokens) * 0.4
            if score > best_score:
                best_score = score
                best_alias = alias
        qualifier_match = re.search(r"\(([^)]+)\)", candidate.get("label", ""))
        if qualifier_match:
            qualifier_text = normalize_department_text(qualifier_match.group(1))
            if qualifier_text:
                if question_mentions_alias(normalized_query, qualifier_text):
                    best_score += 0.12
                else:
                    best_score -= 0.18
        if best_score < 0.45:
            continue
        key = (candidate["label"], candidate["entity_type"])
        if key in seen:
            continue
        seen.add(key)
        hits.append(
            EntitySeed(
                label=candidate["label"],
                entity_type=candidate["entity_type"],
                score=round(best_score, 3),
                alias=best_alias,
            )
        )

    hits.sort(
        key=lambda item: (
            item.score,
            "(" not in item.label,
            len(item.label),
        ),
        reverse=True,
    )
    return hits[:limit]


def expand_queries(rewritten_query: str, entities: List[EntitySeed]) -> List[str]:
    expanded: List[str] = []
    seen: set[str] = set()

    def add_query(value: str) -> None:
        normalized = normalize_text(value)
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            expanded.append(normalized)

    add_query(rewritten_query)
    keywords = extract_keywords(rewritten_query)
    if keywords:
        add_query(" ".join(keywords))
    if entities:
        entity_phrase = " ".join(entity.label for entity in entities[:2])
        residual = [token for token in keywords if token not in extract_keywords(entity_phrase)]
        add_query(" ".join([entity_phrase, *residual]).strip())
    return expanded[:3]


def build_query_plan(question: str, history: Optional[List[Dict[str, str]]]) -> QueryPlan:
    question, _ = correct_spelling(question)
    rewritten_query, follow_up_note, history_resolved = resolve_follow_up(question, history)
    normalized_query = normalize_text(rewritten_query or question)
    retrieval_query = normalize_retrieval_query(normalized_query) if not history_resolved else normalized_query
    entities = extract_entities(retrieval_query)
    intent = get_intent(retrieval_query or question)
    response_type = question_type_for(question)
    return QueryPlan(
        original_query=normalize_text(question),
        rewritten_query=retrieval_query,
        intent=intent,
        response_type=response_type,
        follow_up_note=follow_up_note,
        entities=entities,
        expanded_queries=expand_queries(retrieval_query or question, entities),
        history_resolved=history_resolved,
        filter_category=INTENT_CATEGORY_FILTERS.get(intent),
    )
