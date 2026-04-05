from __future__ import annotations

import json
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

from kg import query_kg_facts
from llm import generate_answer
from rag import CHUNKS_METADATA_PATH, VECTOR_DB_PATH, get_rag_engine

from ..chat import build_chat_payload, chat_response_from_payload, is_answer_grounded
from ..config import DATA_DIR, EVALUATION_METRICS_PATH, MERGED_KG_PATH


DATASET_FILES = [
    DATA_DIR / "golden_dataset.json",
    DATA_DIR / "mesitam_golden_dataset.json",
]

_metrics_cache_lock = Lock()
_metrics_cache: Dict[str, Any] | None = None
_metrics_cache_key: str | None = None


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split()).strip()


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def _load_samples() -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    for dataset_file in DATASET_FILES:
        if not dataset_file.exists():
            continue
        with dataset_file.open("r", encoding="utf-8") as file_handle:
            loaded = json.load(file_handle)
        if isinstance(loaded, list):
            samples.extend(item for item in loaded if isinstance(item, dict) and item.get("question"))
    return samples


def _mtime(path: Path) -> float | None:
    return path.stat().st_mtime if path.exists() else None


def _build_cache_key(limit: int | None = None) -> str:
    fingerprint = {
        "limit": limit,
        "datasets": {dataset_file.name: _mtime(dataset_file) for dataset_file in DATASET_FILES},
        "merged_kg": _mtime(MERGED_KG_PATH),
        "vector_store": _mtime(Path(VECTOR_DB_PATH)),
        "chunks_metadata": _mtime(Path(CHUNKS_METADATA_PATH)),
    }
    return json.dumps(fingerprint, sort_keys=True)


def _load_cached_snapshot(cache_key: str) -> Dict[str, Any] | None:
    if not EVALUATION_METRICS_PATH.exists():
        return None
    try:
        with EVALUATION_METRICS_PATH.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("cache_key") != cache_key:
        return None

    snapshot = payload.get("snapshot")
    return snapshot if isinstance(snapshot, dict) else None


def _write_cached_snapshot(cache_key: str, snapshot: Dict[str, Any]) -> None:
    payload = {
        "cache_key": cache_key,
        "snapshot": snapshot,
    }
    with EVALUATION_METRICS_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2)


def _match_rank(payload: Dict[str, Any], sample: Dict[str, Any]) -> int | None:
    targets = [_normalize(sample.get("ground_truth", ""))]
    targets.extend(_normalize(item) for item in sample.get("context", []) if item)
    ranked_evidence = payload.get("filtered_evidence", [])
    for rank, item in enumerate(ranked_evidence, start=1):
        candidate = _normalize(item.get("sentence", ""))
        if not candidate:
            continue
        if any(target and (target in candidate or candidate in target or _similarity(candidate, target) >= 0.72) for target in targets):
            return rank
    return None


def _compute_metrics_snapshot(limit: int | None = None) -> Dict[str, Any]:
    samples = _load_samples()
    if limit:
        samples = samples[:limit]
    if not samples:
        return {
            "status": "empty",
            "message": "No evaluation samples available.",
            "metrics": {},
            "samples": 0,
            "details": [],
        }

    rag_engine = get_rag_engine()
    details: List[Dict[str, Any]] = []
    recall_at_3 = 0
    recall_at_5 = 0
    recall_at_10 = 0
    reciprocal_rank_sum = 0.0
    correctness_sum = 0.0
    hallucination_count = 0

    for sample in samples:
        question = sample["question"]
        payload = build_chat_payload(question, [], rag_engine, kg_query_fn=query_kg_facts)
        response = chat_response_from_payload(question, payload, "detailed", [], generate_answer_fn=generate_answer)
        match_rank = _match_rank(payload, sample)
        answer = response.get("answer", "")
        ground_truth = sample.get("ground_truth", "")
        correctness = 1.0 if _normalize(ground_truth) in _normalize(answer) else (_similarity(answer, ground_truth) if ground_truth else 0.0)
        hallucinated = bool(answer and "i don't have enough information" not in _normalize(answer) and not is_answer_grounded(answer, payload))

        if match_rank is not None:
            reciprocal_rank_sum += 1.0 / match_rank
            if match_rank <= 3:
                recall_at_3 += 1
            if match_rank <= 5:
                recall_at_5 += 1
            if match_rank <= 10:
                recall_at_10 += 1
        correctness_sum += min(1.0, correctness)
        hallucination_count += int(hallucinated)

        details.append(
            {
                "question": question,
                "match_rank": match_rank,
                "answer_correctness": round(min(1.0, correctness), 4),
                "hallucinated": hallucinated,
                "status": response.get("status"),
            }
        )

    sample_count = len(samples)
    metrics = {
        "retrieval_recall@3": round(recall_at_3 / sample_count, 4),
        "retrieval_recall@5": round(recall_at_5 / sample_count, 4),
        "retrieval_recall@10": round(recall_at_10 / sample_count, 4),
        "mrr@10": round(reciprocal_rank_sum / sample_count, 4),
        "answer_correctness": round(correctness_sum / sample_count, 4),
        "hallucination_rate": round(hallucination_count / sample_count, 4),
    }
    return {
        "status": "ready",
        "message": "Hybrid retrieval metrics computed from the local golden datasets.",
        "metrics": metrics,
        "samples": sample_count,
        "details": details,
    }


def compute_metrics_snapshot(limit: int | None = None, force_refresh: bool = False) -> Dict[str, Any]:
    global _metrics_cache, _metrics_cache_key

    cache_key = _build_cache_key(limit)
    with _metrics_cache_lock:
        if not force_refresh and _metrics_cache_key == cache_key and _metrics_cache is not None:
            return dict(_metrics_cache)

        if not force_refresh:
            cached = _load_cached_snapshot(cache_key)
            if cached is not None:
                _metrics_cache = cached
                _metrics_cache_key = cache_key
                return dict(cached)

    snapshot = _compute_metrics_snapshot(limit=limit)
    snapshot = {
        **snapshot,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with _metrics_cache_lock:
        _metrics_cache = snapshot
        _metrics_cache_key = cache_key
        _write_cached_snapshot(cache_key, snapshot)

    return dict(snapshot)
