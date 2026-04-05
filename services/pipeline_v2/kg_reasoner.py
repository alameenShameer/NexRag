from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from kg import _run_query, query_kg_facts
from rag import extract_keywords

from ..upload_kg import get_upload_kg_service
from .types import EntitySeed, KGFact


def _escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _friendly_predicate(uri_or_name: str) -> str:
    raw = uri_or_name.split("#")[-1].split("/")[-1]
    raw = raw.replace("_", " ")
    raw = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    raw = raw.strip()
    if not raw:
        return "related to"
    return raw[0].upper() + raw[1:]


ENTITY_TYPE_TO_CLASS = {
    "department": "Department",
    "faculty": "Faculty",
    "course": "Course",
    "facility": "Facility",
    "upload_entity": "UploadEntity",
    "uploaded_document": "UploadedDocument",
}
LOW_SIGNAL_PREDICATES = {"Type", "Source Url"}


def _entity_lookup_query(label: str, entity_type: str | None = None) -> str:
    escaped = _escape_literal(label.lower())
    type_clause = ""
    if entity_type and ENTITY_TYPE_TO_CLASS.get(entity_type):
        expected_class = ENTITY_TYPE_TO_CLASS[entity_type]
        type_clause = f"FILTER(?type = :{expected_class})"
    return f"""
    PREFIX : <http://mesitam.ac.in/ns#>

    SELECT ?entity ?label ?type WHERE {{
      {{ ?entity :hasName ?label . }}
      UNION
      {{ ?entity :hasCode ?label . }}
      ?entity a ?type .
      {type_clause}
      FILTER(CONTAINS(LCASE(?label), "{escaped}"))
    }}
    LIMIT 6
    """


def _relation_query(entity_uri: str, depth: int) -> str:
    if depth <= 1:
        return f"""
        PREFIX : <http://mesitam.ac.in/ns#>

        SELECT ?subject ?subjectLabel ?predicate ?object ?objectLabel ?objectType ?depth WHERE {{
          VALUES ?subject {{ <{entity_uri}> }}
          OPTIONAL {{ ?subject :hasName ?subjectLabel . }}
          ?subject ?predicate ?object .
          FILTER(!STRENDS(STR(?predicate), "hasName") && !STRENDS(STR(?predicate), "description"))
          OPTIONAL {{ ?object :hasName ?objectLabel . }}
          OPTIONAL {{ ?object a ?objectType . }}
          BIND(1 AS ?depth)
        }}
        LIMIT 18
        """
    return f"""
    PREFIX : <http://mesitam.ac.in/ns#>

    SELECT ?subject ?subjectLabel ?predicate ?object ?objectLabel ?objectType ?depth WHERE {{
      VALUES ?seed {{ <{entity_uri}> }}
      OPTIONAL {{ ?seed :hasName ?subjectLabel . }}
      {{
        ?seed ?predicate ?object .
        BIND(?seed AS ?subject)
        BIND(1 AS ?depth)
      }}
      UNION
      {{
        ?seed ?p1 ?mid .
        ?mid ?predicate ?object .
        BIND(?mid AS ?subject)
        BIND(2 AS ?depth)
      }}
      FILTER(!STRENDS(STR(?predicate), "hasName") && !STRENDS(STR(?predicate), "description"))
      OPTIONAL {{ ?object :hasName ?objectLabel . }}
      OPTIONAL {{ ?object a ?objectType . }}
    }}
    LIMIT 26
    """


def _bindings_to_graph_fact(bindings: List[Dict[str, Any]], default_subject: str, source: str) -> Tuple[List[KGFact], Dict[str, Any]]:
    facts: List[KGFact] = []
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Dict[str, Dict[str, Any]] = {}

    for row in bindings:
        subject_uri = row.get("subject", {}).get("value")
        object_uri = row.get("object", {}).get("value")
        subject = row.get("subjectLabel", {}).get("value") or default_subject
        predicate = _friendly_predicate(row.get("predicate", {}).get("value", "relatedTo"))
        obj = row.get("objectLabel", {}).get("value") or object_uri or row.get("object", {}).get("value", "")
        depth = int(row.get("depth", {}).get("value", 1) or 1)
        if not predicate or not obj:
            continue
        score = 0.94 if depth == 1 else 0.84
        facts.append(
            KGFact(
                subject=subject,
                predicate=predicate,
                object=obj,
                depth=depth,
                score=score,
                source=source,
                subject_uri=subject_uri,
                object_uri=object_uri,
            )
        )
        if subject_uri:
            nodes.setdefault(subject_uri, {"id": subject_uri, "label": subject, "type": "entity"})
        if object_uri:
            nodes.setdefault(object_uri, {"id": object_uri, "label": obj, "type": row.get("objectType", {}).get("value", "entity").split("#")[-1]})
        if subject_uri and object_uri:
            edge_id = f"{subject_uri}|{predicate}|{object_uri}|{depth}"
            edges.setdefault(
                edge_id,
                {
                    "id": edge_id,
                    "source": subject_uri,
                    "target": object_uri,
                    "label": predicate,
                    "depth": depth,
                },
            )

    return facts, {"nodes": list(nodes.values()), "edges": list(edges.values())}


def _fact_rank(query_plan: Dict[str, Any], fact: KGFact) -> float:
    question = (query_plan.get("original_query") or query_plan.get("rewritten_query") or "").lower()
    question_tokens = {token for token in extract_keywords(question) if len(token) >= 3}
    fact_blob = f"{fact.subject} {fact.predicate} {fact.object}".lower()
    token_hits = sum(1 for token in question_tokens if token in fact_blob)
    rank = fact.score + token_hits * 0.05
    if fact.predicate in LOW_SIGNAL_PREDICATES:
        rank -= 0.35
    if any(term in question for term in ("hod", "head of department")):
        if "hod" in fact_blob or "head of department" in fact_blob:
            rank += 0.7
        if "designation" in fact.predicate.lower():
            rank += 0.25
    if fact.depth == 1:
        rank += 0.05
    return rank


def run_kg_reasoning(query_plan: Dict[str, Any], *, max_depth: int = 2, max_facts: int = 12) -> Dict[str, Any]:
    kg_queries: List[Dict[str, Any]] = []
    collected_facts: List[KGFact] = []
    graph_nodes: Dict[str, Dict[str, Any]] = {}
    graph_edges: Dict[str, Dict[str, Any]] = {}
    entities = [EntitySeed(**entity) if isinstance(entity, dict) else entity for entity in query_plan.get("entities", [])]

    for seed in entities[:3]:
        bindings: List[Dict[str, Any]] = []
        for lookup_value in [seed.alias or seed.label, seed.label]:
            lookup_query = _entity_lookup_query(lookup_value, seed.entity_type)
            kg_queries.append({"type": "entity_lookup", "seed": seed.label, "lookup": lookup_value, "sparql": lookup_query.strip()})
            bindings = _run_query(lookup_query)
            if bindings:
                break
        if not bindings:
            continue
        best = bindings[0]
        entity_uri = best.get("entity", {}).get("value")
        if not entity_uri:
            continue
        seed.uri = entity_uri
        subject_label = best.get("label", {}).get("value") or seed.label
        relation_query = _relation_query(entity_uri, max_depth)
        kg_queries.append({"type": "graph_traversal", "seed": seed.label, "sparql": relation_query.strip()})
        relation_bindings = _run_query(relation_query)
        facts, graph = _bindings_to_graph_fact(relation_bindings, subject_label, "fuseki")
        collected_facts.extend(facts)
        for node in graph["nodes"]:
            graph_nodes[node["id"]] = node
        for edge in graph["edges"]:
            graph_edges[edge["id"]] = edge

    if not collected_facts:
        fallback_facts = query_kg_facts(query_plan.get("rewritten_query", ""))[:max_facts]
        return {
            "facts": fallback_facts,
            "graph_view": {"nodes": [], "edges": []},
            "trace": kg_queries,
        }

    deduped: Dict[tuple[str, str, str], KGFact] = {}
    for fact in collected_facts:
        key = (fact.subject, fact.predicate, fact.object)
        if key not in deduped or deduped[key].score < fact.score:
            deduped[key] = fact

    ordered = sorted(deduped.values(), key=lambda item: _fact_rank(query_plan, item), reverse=True)[:max_facts]
    return {
        "facts": [fact.to_fact_dict() for fact in ordered],
        "graph_view": {
            "nodes": list(graph_nodes.values())[:24],
            "edges": list(graph_edges.values())[:24],
        },
        "trace": kg_queries,
    }


def run_fast_kg_facts(query_plan: Dict[str, Any], *, max_facts: int = 8) -> Dict[str, Any]:
    query = query_plan.get("rewritten_query", "") or query_plan.get("original_query", "")
    response_type = query_plan.get("response_type")
    upload_entity_query = any(entity.get("entity_type") == "upload_entity" for entity in query_plan.get("entities", []))
    upload_facts = (
        get_upload_kg_service().query_facts(query, max_facts=max_facts)
        if response_type in {"fact", "definition"}
        else []
    )
    if upload_facts:
        return {
            "facts": upload_facts,
            "graph_view": {"nodes": [], "edges": []},
            "trace": [{"type": "fast_upload_fact_lookup", "query": query}],
        }
    lowered = query.lower()
    should_query = bool(query_plan.get("entities")) or query_plan.get("intent") == "FACULTY_INFO" or any(
        term in lowered
        for term in (
            "hod",
            "head of department",
            "principal",
            "vice principal",
            "dean",
            "director",
            "placement",
            "career guidance",
            "faculty",
            "teacher",
            "instructor",
            "department",
        )
    )
    if not should_query:
        return {
            "facts": [],
            "graph_view": {"nodes": [], "edges": []},
            "trace": [{"type": "fast_fact_lookup_skipped", "query": query}],
        }
    if response_type == "explanation" and upload_entity_query:
        return {
            "facts": [],
            "graph_view": {"nodes": [], "edges": []},
            "trace": [{"type": "fast_upload_fact_lookup_skipped_for_explanation", "query": query}],
        }
    facts = query_kg_facts(query)[:max_facts]
    return {
        "facts": facts,
        "graph_view": {"nodes": [], "edges": []},
        "trace": [{"type": "fast_fact_lookup", "query": query}],
    }
