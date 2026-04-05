from __future__ import annotations

from typing import Any, Dict, List


DEFAULT_RRF_K = 60
DEFAULT_CHANNEL_WEIGHTS = {
    "vector": 1.0,
    "bm25": 1.0,
    "lexical": 0.8,
}


def weighted_rrf(
    channels: Dict[str, List[Dict[str, Any]]],
    *,
    rrf_k: int = DEFAULT_RRF_K,
    channel_weights: Dict[str, float] | None = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    weights = channel_weights or DEFAULT_CHANNEL_WEIGHTS
    merged: Dict[str, Dict[str, Any]] = {}

    for channel_name, hits in channels.items():
        channel_weight = float(weights.get(channel_name, 1.0))
        for rank, hit in enumerate(hits, start=1):
            chunk_id = hit.get("chunk_id") or f"{hit.get('title')}::{hit.get('page')}::{rank}"
            contribution = channel_weight / (rrf_k + rank)
            current = merged.get(chunk_id, dict(hit))
            current.setdefault("channel_ranks", {})
            current.setdefault("channel_scores", {})
            current.setdefault("rrf_contributions", {})
            current.setdefault("matched_passes", [])
            current["channel_ranks"][channel_name] = rank
            current["channel_scores"][channel_name] = round(float(hit.get(f"{channel_name}_score", hit.get("score", 0.0)) or 0.0), 4)
            current["rrf_contributions"][channel_name] = round(contribution, 6)
            current["rrf_score"] = round(float(current.get("rrf_score", 0.0) or 0.0) + contribution, 6)
            if channel_name not in current["matched_passes"]:
                current["matched_passes"].append(channel_name)
            current.setdefault("match_type", hit.get("match_type", channel_name))
            merged[chunk_id] = current

    fused = list(merged.values())
    fused.sort(
        key=lambda item: (
            float(item.get("rrf_score", 0.0) or 0.0),
            -min(item.get("channel_ranks", {}).values()) if item.get("channel_ranks") else 0,
            float(item.get("vector_score", 0.0) or 0.0),
            float(item.get("bm25_score", 0.0) or 0.0),
            float(item.get("keyword_match_score", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return fused[:limit]
