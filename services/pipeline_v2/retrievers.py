from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List


def _sort_hits(candidates: Dict[str, Dict[str, Any]], primary_field: str, fallback_field: str) -> List[Dict[str, Any]]:
    hits = list(candidates.values())
    hits.sort(
        key=lambda item: (
            float(item.get(primary_field, 0.0) or 0.0),
            float(item.get(fallback_field, 0.0) or 0.0),
            float(item.get("title_match_score", 0.0) or 0.0),
            float(item.get("keyword_match_score", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return hits


def _vector_channel(rag_engine: Any, expanded_queries: List[str], filter_category: str | None, limit: int) -> List[Dict[str, Any]]:
    if not rag_engine or not hasattr(rag_engine, "_collect_vector_candidates"):
        return []
    candidates = rag_engine._collect_vector_candidates(
        expanded_queries,
        top_k=limit,
        filter_category=filter_category,
        candidate_multiplier=2,
    )
    return _sort_hits(candidates, "vector_score", "keyword_match_score")[:limit]


def _bm25_channel(rag_engine: Any, query: str, filter_category: str | None, limit: int) -> List[Dict[str, Any]]:
    if not rag_engine or not hasattr(rag_engine, "_collect_bm25_candidates"):
        return []
    candidates = rag_engine._collect_bm25_candidates(query, filter_category=filter_category, limit=limit)
    return _sort_hits(candidates, "bm25_score", "keyword_match_score")[:limit]


def _lexical_channel(rag_engine: Any, query: str, expanded_queries: List[str], filter_category: str | None, limit: int) -> List[Dict[str, Any]]:
    if not rag_engine:
        return []
    combined: Dict[str, Dict[str, Any]] = {}
    if hasattr(rag_engine, "_collect_title_matches"):
        rag_engine._merge_candidates(combined, rag_engine._collect_title_matches(query, filter_category=filter_category, limit=limit))
    if hasattr(rag_engine, "_collect_exact_keyword_matches"):
        for expanded in expanded_queries:
            rag_engine._merge_candidates(combined, rag_engine._collect_exact_keyword_matches(expanded, filter_category=filter_category))
    return _sort_hits(combined, "keyword_match_score", "title_match_score")[:limit]


def run_parallel_retrievers(
    rag_engine: Any,
    query: str,
    expanded_queries: List[str],
    filter_category: str | None,
    per_channel_limit: int = 20,
) -> Dict[str, List[Dict[str, Any]]]:
    if not rag_engine:
        return {"vector": [], "bm25": [], "lexical": []}

    if not hasattr(rag_engine, "_collect_vector_candidates"):
        legacy = []
        if hasattr(rag_engine, "retrieve_with_fallbacks"):
            legacy = (rag_engine.retrieve_with_fallbacks(query, top_k=per_channel_limit, filter_category=filter_category) or {}).get("results", [])
        elif hasattr(rag_engine, "retrieve"):
            legacy = rag_engine.retrieve(query, top_k=per_channel_limit, filter_category=filter_category, min_score=0.0) or []
        return {"vector": legacy[:per_channel_limit], "bm25": [], "lexical": []}

    with ThreadPoolExecutor(max_workers=3) as executor:
        vector_future = executor.submit(_vector_channel, rag_engine, expanded_queries, filter_category, per_channel_limit)
        bm25_future = executor.submit(_bm25_channel, rag_engine, query, filter_category, per_channel_limit)
        lexical_future = executor.submit(_lexical_channel, rag_engine, query, expanded_queries, filter_category, per_channel_limit)
        return {
            "vector": vector_future.result(),
            "bm25": bm25_future.result(),
            "lexical": lexical_future.result(),
        }
