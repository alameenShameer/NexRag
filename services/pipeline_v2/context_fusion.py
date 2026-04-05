from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def _estimate_tokens(text: str) -> int:
    return max(1, int(len((text or "").split()) * 1.3))


def _normalize_sentence(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _document_context_line(item: Dict[str, Any]) -> str:
    source = item.get("title") or item.get("source") or "Official Source"
    page = item.get("page")
    page_label = f" | page {page}" if page else ""
    return f"- [{source}{page_label}] {item.get('sentence', '')}"


def optimize_context_budget(
    kg_facts: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
    *,
    total_budget: int = 1400,
    kg_budget: int = 300,
    doc_budget: int = 1000,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    kept_facts: List[Dict[str, Any]] = []
    kept_evidence: List[Dict[str, Any]] = []
    kg_tokens = 0
    doc_tokens = 0
    seen_fact_keys: set[str] = set()
    seen_evidence: set[str] = set()
    per_source_counts: Dict[tuple[str, Any], int] = {}

    for fact in kg_facts:
        fact_text = f"{fact.get('entity', '')} {fact.get('fact', '')}".strip()
        if not fact_text:
            continue
        fact_key = _normalize_sentence(fact_text)
        if fact_key in seen_fact_keys:
            continue
        estimated = _estimate_tokens(fact_text)
        if kg_tokens + estimated > kg_budget:
            continue
        seen_fact_keys.add(fact_key)
        kept_facts.append(fact)
        kg_tokens += estimated

    for item in evidence:
        sentence = item.get("sentence", "")
        if not sentence:
            continue
        normalized = _normalize_sentence(sentence)
        if not normalized or normalized in seen_evidence:
            continue
        source_key = (item.get("title") or item.get("source") or "Official Source", item.get("page"))
        per_source_limit = 3 if item.get("page") is None else 2
        if per_source_counts.get(source_key, 0) >= per_source_limit:
            continue
        estimated = _estimate_tokens(sentence)
        if doc_tokens + estimated > doc_budget:
            continue
        seen_evidence.add(normalized)
        per_source_counts[source_key] = per_source_counts.get(source_key, 0) + 1
        kept_evidence.append(item)
        doc_tokens += estimated
        if kg_tokens + doc_tokens >= total_budget:
            break

    context_sections: List[str] = []
    if kept_facts:
        context_sections.append(
            "[Knowledge Graph Facts]\n" + "\n".join(
                f"- {fact.get('entity', 'Entity')} -> {fact.get('predicate', 'related to')} -> {fact.get('object', fact.get('fact', ''))}"
                if fact.get("predicate") and fact.get("object")
                else f"- {fact.get('entity', 'Entity')}: {fact.get('fact', '')}"
                for fact in kept_facts
            )
        )
    if kept_evidence:
        context_sections.append(
            "[Relevant Documents]\n" + "\n".join(
                _document_context_line(item) for item in kept_evidence
            )
        )

    return kept_facts, kept_evidence, {
        "total_budget": total_budget,
        "kg_budget": kg_budget,
        "doc_budget": doc_budget,
        "kg_tokens_used": kg_tokens,
        "doc_tokens_used": doc_tokens,
        "context_sections": context_sections,
    }
