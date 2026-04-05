from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, Optional

from rag import get_retrieval_version

from .context_fusion import optimize_context_budget
from .fusion import DEFAULT_CHANNEL_WEIGHTS, DEFAULT_RRF_K, weighted_rrf
from .kg_reasoner import run_fast_kg_facts, run_kg_reasoning
from .query_understanding import build_query_plan
from .rerank import rerank_hits
from .retrievers import run_parallel_retrievers
from .trace_store import save_pipeline_trace
from .types import PipelineTrace


def _channel_summary(hits: list[dict[str, Any]]) -> Dict[str, Any]:
    return {
        "candidates": len(hits),
        "top_title": hits[0].get("title") if hits else None,
        "top_score": round(float(hits[0].get("score", hits[0].get("rrf_score", 0.0)) or 0.0), 4) if hits else 0.0,
    }


def run_hybrid_pipeline(
    *,
    question: str,
    history: list[dict[str, str]] | None,
    rag_engine: Any,
    stage_callback: Optional[Callable[[str, str], None]] = None,
    include_graph: bool = False,
) -> Dict[str, Any]:
    trace_id = uuid.uuid4().hex[:12]
    trace = PipelineTrace(trace_id=trace_id, query_plan={})

    started = time.perf_counter()
    query_plan = build_query_plan(question, history)
    trace.query_plan = query_plan.to_dict()
    trace.timings_ms["query_understanding"] = int((time.perf_counter() - started) * 1000)

    if stage_callback:
        stage_callback("query_understanding", "Understanding query...")

    retrieval_started = time.perf_counter()
    if stage_callback:
        stage_callback("retrieving_documents", "Running hybrid retrieval...")
    channels = run_parallel_retrievers(
        rag_engine,
        query_plan.rewritten_query,
        query_plan.expanded_queries,
        query_plan.filter_category,
        per_channel_limit=20,
    )
    fused = weighted_rrf(channels, rrf_k=DEFAULT_RRF_K, channel_weights=DEFAULT_CHANNEL_WEIGHTS, limit=40)
    reranked = rerank_hits(rag_engine, query_plan.rewritten_query, fused, top_n=8)
    trace.timings_ms["retrieval"] = int((time.perf_counter() - retrieval_started) * 1000)
    trace.retrieval_channels = {name: _channel_summary(hits) for name, hits in channels.items()}
    trace.retrieval_channels["fused"] = {
        "candidates": len(fused),
        "rrf_k": DEFAULT_RRF_K,
        "weights": DEFAULT_CHANNEL_WEIGHTS,
        "top_title": fused[0].get("title") if fused else None,
        "top_score": round(float(fused[0].get("rrf_score", 0.0) or 0.0), 6) if fused else 0.0,
    }
    trace.retrieval_channels["reranked"] = _channel_summary(reranked)

    kg_started = time.perf_counter()
    if stage_callback:
        stage_callback(
            "querying_knowledge_graph",
            "Traversing knowledge graph..." if include_graph else "Checking knowledge graph...",
        )
    if include_graph:
        kg_result = run_kg_reasoning(query_plan.to_dict(), max_depth=2, max_facts=12)
    else:
        kg_result = run_fast_kg_facts(query_plan.to_dict(), max_facts=8)
    trace.timings_ms["knowledge_graph"] = int((time.perf_counter() - kg_started) * 1000)
    trace.kg_queries = kg_result.get("trace", [])
    trace.graph_summary = {
        "nodes": len(kg_result.get("graph_view", {}).get("nodes", [])),
        "edges": len(kg_result.get("graph_view", {}).get("edges", [])),
        "facts": len(kg_result.get("facts", [])),
    }

    if stage_callback:
        stage_callback("fusing_context", "Fusing graph and document evidence...")
    _, _, context_budget = optimize_context_budget(kg_result.get("facts", []), [])
    trace.context_budget = context_budget

    payload = {
        "trace_id": trace_id,
        "query_plan": query_plan.to_dict(),
        "retrieval_query": query_plan.rewritten_query,
        "follow_up_note": query_plan.follow_up_note,
        "intent": query_plan.intent,
        "graph_view": kg_result.get("graph_view", {"nodes": [], "edges": []}),
        "kg_facts": kg_result.get("facts", []),
        "vector_results": reranked,
        "retrieval": {
            "query": query_plan.rewritten_query,
            "expanded_queries": query_plan.expanded_queries,
            "passes": [
                {"name": "vector", **trace.retrieval_channels.get("vector", {})},
                {"name": "bm25", **trace.retrieval_channels.get("bm25", {})},
                {"name": "lexical", **trace.retrieval_channels.get("lexical", {})},
                {"name": "weighted_rrf", **trace.retrieval_channels.get("fused", {})},
                {"name": "cross_encoder_rerank", **trace.retrieval_channels.get("reranked", {})},
            ],
            "results": reranked,
            "retrieval_version": f"{get_retrieval_version()}::pipeline-v2-rrf",
            "has_evidence": bool(reranked or kg_result.get("facts")),
            "rrf_k": DEFAULT_RRF_K,
            "weights": DEFAULT_CHANNEL_WEIGHTS,
        },
        "pipeline_trace": trace.to_dict(),
    }
    save_pipeline_trace(trace_id, payload["pipeline_trace"])
    return payload
