from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EntitySeed:
    label: str
    entity_type: str
    score: float
    alias: Optional[str] = None
    uri: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryPlan:
    original_query: str
    rewritten_query: str
    intent: str
    response_type: str
    follow_up_note: Optional[str]
    entities: List[EntitySeed] = field(default_factory=list)
    expanded_queries: List[str] = field(default_factory=list)
    history_resolved: bool = False
    filter_category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["entities"] = [entity.to_dict() for entity in self.entities]
        return payload


@dataclass
class RetrievalHit:
    chunk_id: str
    title: str
    text: str
    page: Optional[int]
    source: str
    source_type: str
    source_url: Optional[str]
    category: str
    match_type: str
    channel_ranks: Dict[str, int] = field(default_factory=dict)
    channel_scores: Dict[str, float] = field(default_factory=dict)
    rrf_score: float = 0.0
    reranker_score: float = 0.0
    score: float = 0.0
    matched_passes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KGFact:
    subject: str
    predicate: str
    object: str
    depth: int
    score: float
    source: str
    subject_uri: Optional[str] = None
    object_uri: Optional[str] = None

    def to_fact_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.subject,
            "fact": f"{self.predicate}: {self.object}",
            "score": round(float(self.score), 2),
            "predicate": self.predicate,
            "object": self.object,
            "depth": self.depth,
            "source": self.source,
            "subject_uri": self.subject_uri,
            "object_uri": self.object_uri,
        }


@dataclass
class PipelineTrace:
    trace_id: str
    query_plan: Dict[str, Any]
    timings_ms: Dict[str, int] = field(default_factory=dict)
    retrieval_channels: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    kg_queries: List[Dict[str, Any]] = field(default_factory=list)
    graph_summary: Dict[str, Any] = field(default_factory=dict)
    context_budget: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
