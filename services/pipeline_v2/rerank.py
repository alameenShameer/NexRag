from __future__ import annotations

from typing import Any, Dict, List

from rag import chunk_section_penalty, clamp_score, is_noise_line, sigmoid


def rerank_hits(rag_engine: Any, query: str, hits: List[Dict[str, Any]], top_n: int = 8) -> List[Dict[str, Any]]:
    if not hits:
        return []
    if not rag_engine or not getattr(rag_engine, "reranker", None):
        for hit in hits[:top_n]:
            hit["reranker_score"] = round(float(hit.get("rrf_score", 0.0) or 0.0), 4)
            hit["score"] = round(float(hit.get("rrf_score", 0.0) or 0.0), 4)
        return hits[:top_n]

    rerank_pool = hits[: min(len(hits), max(top_n * 4, 12))]
    pairs = [[query, hit.get("text", "")] for hit in rerank_pool]
    raw_scores = rag_engine.reranker.predict(pairs)

    for hit, raw_score in zip(rerank_pool, raw_scores):
        reranker_score = clamp_score(sigmoid(float(raw_score)))
        penalty = 0.0
        if is_noise_line((hit.get("text") or "")[:220]):
            penalty += 0.08
        penalty += min(0.12, float(chunk_section_penalty(hit.get("text", "")) or 0.0) * 0.55)
        hit["reranker_score"] = round(reranker_score, 4)
        hit["score"] = round(clamp_score(reranker_score - penalty), 4)

    rerank_pool.sort(
        key=lambda item: (
            float(item.get("score", 0.0) or 0.0),
            float(item.get("rrf_score", 0.0) or 0.0),
            float(item.get("keyword_match_score", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return rerank_pool[:top_n]
