from _bootstrap import ensure_repo_root

ensure_repo_root()

from kg import query_kg_facts
from services.chat import build_chat_payload, build_extractive_fallback, question_type_for, resolve_department_focus


class FakeRagEngine:
    def __init__(self, results):
        self.results = results

    def retrieve_with_fallbacks(self, query, top_k=5, filter_category=None):
        return {
            "query": query,
            "expanded_queries": [query],
            "passes": [{"name": "fake", "candidates": len(self.results), "top_score": self.results[0]["score"] if self.results else 0.0}],
            "results": [dict(item) for item in self.results[:top_k]],
            "retrieval_version": "test-double",
            "has_evidence": bool(self.results),
        }


print("--- Running department alias matching checks ---")

for query in ["who is the hod of ec", "who is the hod of ece"]:
    facts = query_kg_facts(query)
    print(query, "->", facts[0]["entity"] if facts else "no fact")
    assert facts, f"Expected a KG fact for {query!r}"
    assert "Azad" in facts[0]["entity"], f"Expected ECE HOD resolution for {query!r}"
    assert "Electronics" in facts[0]["fact"], f"Expected ECE department in fact for {query!r}"

focus = resolve_department_focus("who is the hod of ec")
print("Resolved focus:", focus["name"] if focus else None)
assert focus is not None, "Expected department focus to resolve for EC alias."
assert "Electronics & Communication Engineering" in focus["name"], "EC alias should resolve to ECE."

fake_results = [
    {
        "text": "Prof. Anoob D. T. is the Head of Department for Dept. of Civil Engineering.",
        "source": "MESITAM HODs",
        "title": "MESITAM HODs",
        "page": None,
        "score": 0.88,
        "vector_score": 0.55,
        "reranker_score": 0.51,
        "keyword_match_score": 0.86,
        "match_type": "exact_keyword",
        "forced_match": True,
    },
    {
        "text": "Prof. Azad A. is the Head of Department for Dept. of Electronics & Communication Engineering.",
        "source": "MESITAM HODs",
        "title": "MESITAM HODs",
        "page": None,
        "score": 0.84,
        "vector_score": 0.62,
        "reranker_score": 0.66,
        "keyword_match_score": 0.72,
        "match_type": "keyword",
        "forced_match": True,
    },
]

payload = build_chat_payload("who is the hod of ece", [], FakeRagEngine(fake_results), kg_query_fn=lambda _: [])
titles = [item["title"] for item in payload["vector_results"]]
texts = [item["text"] for item in payload["vector_results"]]
print("Filtered titles:", titles)
assert payload["vector_results"], "Expected filtered vector results for ECE query."
assert all("Civil Engineering" not in text for text in texts), "Civil evidence should be filtered out for ECE."
assert "Azad" in payload["vector_results"][0]["text"], "ECE evidence should rank first after department filtering."

shorthand_results = [
    {
        "text": "Vice Principal M.Tech(HeatPowerEngineering- Thermal Engineering) Ph.d ( Mechanical Engineering) M.E(Mechanical Engineering.) 2",
        "source": "Mandatory Disclosure",
        "title": "Mandatory Disclosure",
        "page": None,
        "score": 0.87,
        "vector_score": 0.74,
        "reranker_score": 0.7,
        "keyword_match_score": 0.81,
        "match_type": "keyword",
        "forced_match": True,
    }
]

shorthand_query = "hod of mechanical"
print("Shorthand query type:", question_type_for(shorthand_query))
assert question_type_for(shorthand_query) == "fact", "Shorthand role queries should be treated as fact lookups."
assert question_type_for("what is hod") == "definition", "Pure acronym-definition queries should stay in definition mode."

shorthand_payload = build_chat_payload(shorthand_query, [], FakeRagEngine(shorthand_results), kg_query_fn=query_kg_facts)
print("Shorthand direct answer:", shorthand_payload["direct_answer"])
assert shorthand_payload["direct_answer"] is not None, "Shorthand role queries should still produce a direct answer."
assert "Shanavas" in shorthand_payload["direct_answer"], "Mechanical HOD shorthand queries should resolve to Dr. Shanavas S."
assert "Vice Principal" not in build_extractive_fallback(shorthand_payload), "Shorthand HOD queries must not fall back to noisy disclosure fragments."

print("Department alias matching checks passed.")
