from _bootstrap import ensure_repo_root

ensure_repo_root()

from services.chat import build_chat_payload


class FakeRagEngine:
    def __init__(self, results):
        self.results = results

    def retrieve(self, query, top_k=5, filter_category=None, min_score=0.0):
        return [dict(item) for item in self.results[:top_k]]


def assert_true(condition, message):
    assert condition, message


print("--- Running uploaded person fact checks ---")

rich_person_chunks = [
    {
        "text": "NEURONEST: A SMART HEALTH CARE\nMONITORING SYSTEM\nPROJECT REPORT\nsubmitted by\nNAYANA S P\nMEK22CS036\nDepartment of Computer Science and Engineering\nMES Institute of Technology and Management\nApril 2026",
        "source": "repog-20.pdf",
        "title": "repog-20.pdf",
        "page": 1,
        "score": 0.91,
        "vector_score": 0.88,
        "reranker_score": 0.92,
        "keyword_match_score": 0.95,
        "match_type": "exact_keyword",
        "source_type": "upload",
    },
    {
        "text": 'Certified that this report entitled "NEURONEST: A SMART HEALTH CARE\nMONITORING SYSTEM" is the report of project presented by NAYANA SP (MEK22CS036) during the year 2025-2026.',
        "source": "repog-20.pdf",
        "title": "repog-20.pdf",
        "page": 2,
        "score": 0.93,
        "vector_score": 0.9,
        "reranker_score": 0.94,
        "keyword_match_score": 0.96,
        "match_type": "exact_keyword",
        "source_type": "upload",
    },
]

rich_payload = build_chat_payload(
    "Who is Nayana?",
    [],
    FakeRagEngine(rich_person_chunks),
    kg_query_fn=lambda question: [],
)
print("Rich uploaded-person payload:", rich_payload["status"], rich_payload["direct_answer"])
assert_true(rich_payload["status"] != "refused", "Richer uploaded-person context should not be refused.")
assert_true(rich_payload["direct_answer"] is not None, "Richer uploaded-person context should produce a direct answer.")
assert_true("Nayana" in rich_payload["direct_answer"], "The uploaded-person direct answer should mention the focus name.")
assert_true(
    "NEURONEST: A SMART HEALTH CARE MONITORING SYSTEM" in rich_payload["direct_answer"],
    "The uploaded-person direct answer should preserve the full grounded project title.",
)

minimal_author_chunks = [
    {
        "text": "PROJECT REPORT submitted by NAYANA S P MEK22CS036 NEHIYAN NOUSHAD MEK22CS038",
        "source": "author-list.pdf",
        "title": "author-list.pdf",
        "page": 1,
        "score": 0.9,
        "vector_score": 0.88,
        "reranker_score": 0.91,
        "keyword_match_score": 0.95,
        "match_type": "exact_keyword",
        "source_type": "upload",
    }
]

minimal_payload = build_chat_payload(
    "Who is Nayana?",
    [],
    FakeRagEngine(minimal_author_chunks),
    kg_query_fn=lambda question: [],
)
print("Minimal uploaded-person payload:", minimal_payload["status"], minimal_payload["direct_answer"])
assert_true(minimal_payload["status"] == "refused", "Bare author-list mentions should still be refused.")
assert_true(minimal_payload["direct_answer"] is None, "Bare author-list mentions should not create a direct answer.")

print("Uploaded person fact checks passed.")
