from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from SPARQLWrapper import JSON, SPARQLWrapper
from rdflib import Graph

from services.config import MERGED_KG_PATH
from services.department_aliases import (
    department_aliases,
    meaningful_department_tokens,
    normalize_department_text,
    question_mentions_alias,
)
from services.knowledge_base import get_knowledge_base_service
from services.upload_kg import get_upload_kg_service


FUSEKI_ENDPOINT = "http://localhost:3030/mesitam_kg/sparql"
KG_REMOTE_TIMEOUT_SECONDS = 2

STOPWORDS = {
    "what",
    "is",
    "who",
    "describe",
    "tell",
    "me",
    "about",
    "details",
    "of",
    "the",
    "for",
    "rule",
    "define",
    "meaning",
    "course",
    "subject",
    "faculty",
    "teacher",
    "teaches",
    "taught",
    "instructor",
    "department",
    "professor",
    "prof",
    "dr",
    "mr",
    "mrs",
    "ms",
}

_local_graph: Graph | None = None
_local_graph_mtime: float | None = None


def _extract_search_terms(question: str) -> List[str]:
    cleaned = question.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    tokens = [token for token in cleaned.split() if token not in STOPWORDS]
    joined = " ".join(tokens).strip()

    phrases = []
    if joined:
        phrases.append(joined)

    for size in range(min(4, len(tokens)), 0, -1):
        for start in range(0, len(tokens) - size + 1):
            phrase = " ".join(tokens[start : start + size]).strip()
            if size == 1 and len(phrase) < 3 and not any(ch.isdigit() for ch in phrase):
                continue
            if phrase and phrase not in phrases:
                phrases.append(phrase)

    return phrases


def _get_local_graph() -> Graph:
    global _local_graph, _local_graph_mtime
    if not MERGED_KG_PATH.exists():
        graph = Graph()
        return graph

    mtime = MERGED_KG_PATH.stat().st_mtime
    if _local_graph is None or _local_graph_mtime != mtime:
        graph = Graph()
        graph.parse(MERGED_KG_PATH, format="turtle")
        _local_graph = graph
        _local_graph_mtime = mtime
    return _local_graph


def ping_kg() -> bool:
    try:
        sparql = SPARQLWrapper(FUSEKI_ENDPOINT)
        sparql.setQuery("ASK { ?s ?p ?o }")
        sparql.setReturnFormat(JSON)
        if hasattr(sparql, "setTimeout"):
            sparql.setTimeout(KG_REMOTE_TIMEOUT_SECONDS)
        sparql.query().convert()
        return True
    except Exception:
        try:
            return len(_get_local_graph()) > 0
        except Exception:
            return False


def _run_remote_query(query: str) -> List[Dict[str, Any]]:
    sparql = SPARQLWrapper(FUSEKI_ENDPOINT)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    if hasattr(sparql, "setTimeout"):
        sparql.setTimeout(KG_REMOTE_TIMEOUT_SECONDS)
    return sparql.query().convert()["results"]["bindings"]


def _run_local_query(query: str) -> List[Dict[str, Any]]:
    graph = _get_local_graph()
    bindings = []
    for row in graph.query(query):
        binding = {}
        for key, value in row.asdict().items():
            binding[str(key)] = {"type": "literal", "value": str(value)}
        bindings.append(binding)
    return bindings


def _run_query(query: str) -> List[Dict[str, Any]]:
    try:
        remote_results = _run_remote_query(query)
        if remote_results:
            return remote_results
    except Exception:
        pass
    try:
        local_graph = _get_local_graph()
        if len(local_graph) > 0:
            return _run_local_query(query)
    except Exception:
        pass
    return []


def _escape_sparql_regex(text: str) -> str:
    escaped = re.escape(text.lower())
    escaped = escaped.replace("\\ ", " ")
    return escaped


def _label_match_filter(keyword: str) -> str:
    escaped_keyword = _escape_sparql_regex(keyword)
    return f'REGEX(LCASE(?label), "(^|[^a-z0-9]){escaped_keyword}([^a-z0-9]|$)")'


def _find_course_bindings(question: str) -> List[Dict[str, Any]]:
    keywords = _extract_search_terms(question)
    if not keywords:
        return []

    for keyword in keywords:
        if len(keyword) < 2:
            continue
        query = f"""
        PREFIX : <http://mesitam.ac.in/ns#>

        SELECT ?course ?label ?code WHERE {{
            ?course a :Course ;
                :hasName ?label .
            OPTIONAL {{ ?course :hasCode ?code . }}

            FILTER (
                CONTAINS(LCASE(?label), "{keyword}") ||
                (BOUND(?code) && CONTAINS(LCASE(?code), "{keyword}"))
            )
        }}
        LIMIT 5
        """
        bindings = _run_query(query)
        if bindings:
            return bindings
    return []


def _answer_teaches_question(question: str) -> str | None:
    course_bindings = _find_course_bindings(question)
    if not course_bindings:
        return None

    course_uri = course_bindings[0]["course"]["value"]
    course_name = course_bindings[0]["label"]["value"]
    course_code = course_bindings[0].get("code", {}).get("value")

    query = f"""
    PREFIX : <http://mesitam.ac.in/ns#>

    SELECT ?facultyName ?designation WHERE {{
        ?faculty a :Faculty ;
            :hasName ?facultyName ;
            :belongs_to ?department .
        OPTIONAL {{ ?faculty :hasDesignation ?designation . }}
        ?course a :Course .
        FILTER(?course = <{course_uri}>)
    }}
    LIMIT 10
    """

    bindings = _run_query(query)
    if bindings:
        faculty_lines = []
        for row in bindings:
            name = row["facultyName"]["value"]
            designation = row.get("designation", {}).get("value")
            faculty_lines.append(f"- {name}" + (f" ({designation})" if designation else ""))

        heading = f"{course_name}"
        if course_code:
            heading += f" ({course_code})"
        heading += " is currently linked to:"
        return "\n".join([heading, *faculty_lines])

    response = f"{course_name}"
    if course_code:
        response += f" ({course_code})"
    response += " exists in the knowledge graph, but no faculty member is currently linked to teach it."
    return response


def _normalize_department(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _answer_hod_question(question: str) -> List[str]:
    question_text = normalize_department_text(question)
    question_tokens = set(meaningful_department_tokens(question))
    faculty_records = get_knowledge_base_service().public_sections().get("faculty", [])
    
    matches = []
    
    for faculty in faculty_records:
        designation = (faculty.get("designation") or "").lower()
        if "head of department" not in designation and "hod" not in designation:
            continue
        department = faculty.get("department") or ""
        aliases = department_aliases(department)
        department_tokens = set(meaningful_department_tokens(department))
        score = 0

        alias_hits = [alias for alias in aliases if question_mentions_alias(question_text, alias)]
        if alias_hits:
            longest_alias = max(alias_hits, key=lambda alias: (alias.count(" "), len(alias)))
            score += 7 if " " not in longest_alias else 6
            score += min(longest_alias.count(" ") + 1, 3)

        if question_tokens and department_tokens:
            score += int(1.5 * len(question_tokens & department_tokens))

        qualifier_match = re.search(r"\(([^)]+)\)", department)
        if qualifier_match:
            qualifier_text = normalize_department_text(qualifier_match.group(1))
            if qualifier_text and not question_mentions_alias(question_text, qualifier_text):
                score -= 3
        matches.append((score, faculty))

    if not matches:
        return []

    best_score = max(score for score, _ in matches)
    threshold = best_score if best_score > 0 else -100

    answers = []
    for score, faculty in sorted(matches, key=lambda x: x[0], reverse=True):
        if score >= threshold:
            answers.append(f"{faculty['name']} is the Head of the Department for {faculty['department']}.")

    return answers


def _friendly_prop_name(prop_name: str) -> str:
    friendly = {
        "hasDesignation": "Designation",
        "belongsTo": "Department",
        "belongs_to": "Department",
        "governedBy": "Governed By",
        "hasCredit": "Credits",
        "hasCode": "Code",
        "abbreviation": "Abbreviation",
        "teaches": "Teaches",
        "has_faculty": "Faculty",
        "has_facility": "Facility",
        "frequently_asked": "FAQ",
        "postedOn": "Posted On",
        "sourceUrl": "Source URL",
    }
    return friendly.get(prop_name, prop_name)


def inspect_ttl_update(existing_content: str, new_content: str) -> Dict[str, Any]:
    old_graph = Graph()
    new_graph = Graph()
    old_graph.parse(data=existing_content, format="turtle")
    new_graph.parse(data=new_content, format="turtle")

    removed_triples = sorted(set(old_graph) - set(new_graph), key=lambda triple: tuple(str(part) for part in triple))
    preview = []
    for subj, pred, obj in removed_triples[:5]:
        preview.append(f"{subj.n3()} {pred.n3()} {obj.n3()}")

    return {"removed_count": len(removed_triples), "removed_preview": preview}


def _make_fact(entity: str, fact: str, score: float = 1.0) -> Dict[str, Any]:
    return {"entity": entity, "fact": fact, "score": score}


def query_kg_facts(question: str) -> List[Dict[str, Any]]:
    lowered = question.lower()
    kb = get_knowledge_base_service().public_sections()

    if any(term in lowered for term in ["placement", "career guidance", "cgpc"]):
        placements = kb.get("placements", [])
        if placements:
            placement = placements[0]
            facts = [_make_fact(placement.get("title", "Career Guidance & Placement Cell"), placement.get("summary", ""), 0.92)]
            source_url = placement.get("source_url")
            if source_url:
                facts.append(_make_fact(placement.get("title", "Career Guidance & Placement Cell"), f"Source URL: {source_url}", 0.88))
            return facts

    if any(term in lowered for term in ["where is mesitam", "mesitam located", "location of mesitam", "where is the college"]):
        overview = kb.get("overview", {})
        location = overview.get("location")
        if location:
            return [_make_fact("MES Institute of Technology and Management", f"Location: {location}", 0.92)]

    if "hod" in lowered or "head of department" in lowered:
        hod_answers = _answer_hod_question(question)
        if hod_answers:
            facts = []
            for hod_answer in hod_answers:
                parts = hod_answer.split(" is ", 1)
                if len(parts) == 2:
                    facts.append(_make_fact(parts[0], f"is {parts[1]}"))
                else:
                    facts.append(_make_fact("Knowledge Graph", hod_answer))
            return facts
    if any(term in lowered for term in ["who teaches", "who handles", "who is teaching", "teacher for", "faculty for"]):
        teaches_answer = _answer_teaches_question(question)
        if teaches_answer:
            lines = [line.strip("- ").strip() for line in teaches_answer.splitlines() if line.strip()]
            if not lines:
                return []
            heading = lines[0]
            facts = []
            for line in lines[1:]:
                facts.append(_make_fact(heading, line))
            return facts or [_make_fact("Knowledge Graph", heading)]

    explanation_like = any(term in lowered for term in ["explain", "describe", "summarize", "summary", "overview", "tell me about", "walk me through"])
    upload_facts = [] if explanation_like else get_upload_kg_service().query_facts(question)
    if upload_facts:
        return upload_facts

    keywords = _extract_search_terms(question)
    if not keywords:
        return []

    bindings = []
    for keyword in keywords:
        if len(keyword) < 2:
            continue

        query = f"""
        PREFIX : <http://mesitam.ac.in/ns#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?label ?type ?desc ?prop ?valname ?invProp ?invValName WHERE {{
            {{ ?entity :hasName ?label . }}
            UNION {{ ?entity :hasCode ?label . }}

            ?entity a ?type .

            OPTIONAL {{ ?entity :description ?desc . }}

            OPTIONAL {{
                ?entity ?prop ?val .
                FILTER(?prop != :hasName && ?prop != rdf:type && ?prop != :description && ?prop != :hasCode)
                OPTIONAL {{ ?val :hasName ?valLabel . }}
                BIND(COALESCE(?valLabel, str(?val)) AS ?valname)
            }}

            OPTIONAL {{
                ?invVal ?invProp ?entity .
                FILTER(?invProp != rdf:type)
                OPTIONAL {{ ?invVal :hasName ?invLabel . }}
                BIND(COALESCE(?invLabel, str(?invVal)) AS ?invValName)
            }}

            FILTER ({_label_match_filter(keyword)})
        }} LIMIT 20
        """

        try:
            bindings = _run_query(query)
        except Exception:
            return []

        if bindings:
            break

    if not bindings:
        return []

    entity_info: Dict[str, Dict[str, Any]] = {}
    for row in bindings:
        label = row["label"]["value"]
        type_uri = row["type"]["value"].split("#")[-1]
        if type_uri == "FAQ" and not any(term in lowered for term in ["where", "download", "find", "access"]):
            continue

        if label not in entity_info:
            entity_info[label] = {"type": type_uri, "desc": row["desc"]["value"] if "desc" in row else None, "props": []}

        if "prop" in row:
            prop_name = row["prop"]["value"].split("#")[-1]
            val_text = row["valname"]["value"]
            prop_str = f"{_friendly_prop_name(prop_name)}: {val_text}"
            if prop_str not in entity_info[label]["props"]:
                entity_info[label]["props"].append(prop_str)

        if "invProp" in row:
            inv_prop_name = row["invProp"]["value"].split("#")[-1]
            inv_val_text = row["invValName"]["value"]
            inv_str = f"is {inv_prop_name} of: {inv_val_text}"
            if inv_prop_name in {"teaches", "has_faculty"}:
                inv_str = f"Taught by: {inv_val_text}"
            if inv_prop_name == "belongs_to":
                inv_str = f"Belongs to: {inv_val_text}"
            if inv_str not in entity_info[label]["props"]:
                entity_info[label]["props"].append(inv_str)

    facts: List[Dict[str, Any]] = []
    for label, info in entity_info.items():
        if info["desc"]:
            facts.append(_make_fact(label, info["desc"], 0.92))
        for prop in info["props"]:
            facts.append(_make_fact(label, prop, 0.88))

    return facts[:8]


def query_kg(question: str) -> str | None:
    facts = query_kg_facts(question)
    if not facts:
        return None
    lines = []
    for fact in facts:
        lines.append(f"{fact['entity']}: {fact['fact']}")
    return "\n".join(lines)
