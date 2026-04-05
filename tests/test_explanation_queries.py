from _bootstrap import ensure_repo_root

ensure_repo_root()

from services.chat import (
    build_chat_payload,
    build_extractive_fallback,
    grounding_query_terms,
    question_focus_phrase,
)
from services.pipeline_v2.query_understanding import build_query_plan


class FakeRagEngine:
    def __init__(self, results):
        self.results = results
        self.chunks_metadata = [dict(item) for item in results]
        self.last_top_k = None

    def retrieve_with_fallbacks(self, query, top_k=5, filter_category=None):
        self.last_top_k = top_k
        return {
            "query": query,
            "expanded_queries": [query],
            "passes": [],
            "results": [dict(item) for item in self.results[:top_k]],
            "retrieval_version": "fake-retrieve",
            "has_evidence": bool(self.results),
        }


def assert_true(condition, message):
    assert condition, message


print("--- Running explanation-query checks ---")

focus = question_focus_phrase("can you explain neuronest")
print("Focus phrase:", focus)
assert_true(focus == "neuronest", "Polite explanation prompts should focus on the topic phrase.")

ground_terms = grounding_query_terms("can you explain neuronest")
print("Grounding terms:", ground_terms)
assert_true(ground_terms == ["neuronest"], "Grounding terms should remove polite wrapper tokens for explanation queries.")

query_plan = build_query_plan("can you explain neuronest", [])
print("Rewritten query:", query_plan.rewritten_query, "expanded:", query_plan.expanded_queries)
assert_true(query_plan.rewritten_query == "neuronest", "Pipeline query planning should normalize polite explanation prompts.")
assert_true("neuronest" in [item.lower() for item in query_plan.expanded_queries], "Expanded queries should include the topic keyword.")

neuronest_chunks = [
    {
        "text": "ABSTRACT NeuroNest is an IoT-integrated multi-module healthcare and patient assistance ecosystem designed to support remote patient monitoring, clinical workflow management, and assistance for patients with limited mobility through a unified hardware and software platform.",
        "source": "repog-20.pdf",
        "title": "repog-20.pdf",
        "page": 5,
        "score": 0.95,
        "vector_score": 0.93,
        "reranker_score": 0.94,
        "keyword_match_score": 0.95,
        "match_type": "exact_keyword",
        "source_type": "upload",
    },
    {
        "text": "The proposed system, NeuroNest, is an IoT-integrated healthcare and patient assistance platform designed to provide real-time physiological monitoring and efficient healthcare management. The system combines hardware components such as biomedical sensors and microcontrollers with a full-stack web application to create a centralized and intelligent healthcare ecosystem.",
        "source": "repog-20.pdf",
        "title": "repog-20.pdf",
        "page": 22,
        "score": 0.92,
        "vector_score": 0.9,
        "reranker_score": 0.93,
        "keyword_match_score": 0.94,
        "match_type": "vector",
        "source_type": "upload",
    },
    {
        "text": "In addition to health monitoring, NeuroNest provides features such as online appointment booking, digital prescriptions, medical record management, and real-time communication between patients and doctors through chat or video consultation.",
        "source": "repog-20.pdf",
        "title": "repog-20.pdf",
        "page": 23,
        "score": 0.9,
        "vector_score": 0.88,
        "reranker_score": 0.91,
        "keyword_match_score": 0.92,
        "match_type": "vector",
        "source_type": "upload",
    },
    {
        "text": "NeuroNest bridges the gap between patients and healthcare providers by combining IoT and web-based healthcare into a single platform. The system improves safety, reduces workload, enhances accessibility, and provides a scalable healthcare solution.",
        "source": "repog-20.pdf",
        "title": "repog-20.pdf",
        "page": 13,
        "score": 0.88,
        "vector_score": 0.86,
        "reranker_score": 0.89,
        "keyword_match_score": 0.9,
        "match_type": "vector",
        "source_type": "upload",
    },
    {
        "text": "The NeuroNest system supports three main types of users: patients, doctors, and administrators. Patients can monitor their real-time health data, doctors can review data and provide consultations, and administrators manage platform operations.",
        "source": "repog-20.pdf",
        "title": "repog-20.pdf",
        "page": 24,
        "score": 0.86,
        "vector_score": 0.84,
        "reranker_score": 0.87,
        "keyword_match_score": 0.88,
        "match_type": "vector",
        "source_type": "upload",
    },
    {
        "text": "Overall, the NeuroNest system provides a comprehensive, cost-effective, and scalable solution for modern healthcare challenges. It enhances patient care, improves accessibility to healthcare services, and contributes to the advancement of digital healthcare systems.",
        "source": "repog-20.pdf",
        "title": "repog-20.pdf",
        "page": 45,
        "score": 0.85,
        "vector_score": 0.83,
        "reranker_score": 0.86,
        "keyword_match_score": 0.87,
        "match_type": "vector",
        "source_type": "upload",
    },
]

fake_rag = FakeRagEngine(neuronest_chunks)
payload = build_chat_payload(
    "can you explain neuronest",
    [],
    fake_rag,
    kg_query_fn=lambda question: [],
)
fallback_answer = build_extractive_fallback(payload, answer_mode="detailed")
print("Explanation payload:", payload["status"], "vector_results=", len(payload["vector_results"]), "filtered_evidence=", len(payload["filtered_evidence"]))
print("Fallback answer:", fallback_answer)
print("Sources:", [(item["title"], item.get("page")) for item in payload["sources"]])

assert_true(payload["status"] != "refused", "Explanation queries with strong uploaded evidence should not be refused.")
assert_true(len(payload["vector_results"]) >= 6, "Explanation queries should retain a broader retrieval set.")
assert_true(len(payload["filtered_evidence"]) >= 4, "Explanation queries should keep multiple evidence sentences.")
assert_true(len(payload["sources"]) >= 2, "Explanation queries should surface more than one supporting source excerpt.")
assert_true("remote patient monitoring" in fallback_answer.lower(), "The explanation fallback should include the core system overview.")
assert_true("online appointment booking" in fallback_answer.lower(), "The explanation fallback should include a concrete feature from the report.")

print("Explanation-query checks passed.")
