from _bootstrap import ensure_repo_root

ensure_repo_root()

import api


class FakeRagEngine:
    def __init__(self, results):
        self.results = results

    def retrieve(self, query, top_k=5, filter_category=None, min_score=0.0):
        return [dict(item) for item in self.results[:top_k]]


ORIGINAL_GET_RAG_ENGINE_SAFE = api.get_rag_engine_safe
ORIGINAL_QUERY_KG = api.query_kg
ORIGINAL_GENERATE_ANSWER = api.generate_answer


def restore_originals():
    api.get_rag_engine_safe = ORIGINAL_GET_RAG_ENGINE_SAFE
    api.query_kg = ORIGINAL_QUERY_KG
    api.generate_answer = ORIGINAL_GENERATE_ANSWER


def assert_true(condition, message):
    assert condition, message


try:
    print("--- Running grounded fact-mode checks ---")

    llm_called = {"value": False}

    def grounded_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        llm_called["value"] = True
        yield "The principal of MESITAM is Dr. Shafi K. A."

    principal_chunk = {
        "text": "Key Personnel Dr. Shafi K. A. Principal Prof. Rafi A Vice Principal.",
        "source": "MESITAM About",
        "title": "MESITAM About",
        "page": None,
        "score": 0.93,
        "vector_score": 0.88,
        "reranker_score": 0.9,
        "keyword_match_score": 0.86,
        "match_type": "keyword",
    }

    api.get_rag_engine_safe = lambda: FakeRagEngine([principal_chunk])
    api.query_kg = lambda question: []
    api.generate_answer = grounded_generator

    response = api.chat(api.ChatRequest(query="Who is the principal of MESITAM?", history=[]))
    print("Principal response:", response["answer"])
    assert_true(response["status"] in {"complete", "limited"}, "Grounded fact answers should not refuse.")
    assert_true(response["answer"] == "The principal of MESITAM is Dr. Shafi K. A.", "Principal queries should return a clean grounded answer.")
    assert_true("menu" not in response["answer"].lower(), "Fact answers must not include site boilerplate.")
    assert_true(llm_called["value"], "Grounded fact answers should use the LLM for final phrasing.")

    print("Grounded fact-mode checks passed.")
finally:
    restore_originals()
