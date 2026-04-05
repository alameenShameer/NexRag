from _bootstrap import ensure_repo_root

ensure_repo_root()

import api


class FakeRagEngine:
    def __init__(self, results):
        self.results = results

    def retrieve(self, query, top_k=5, filter_category=None, min_score=0.0):
        return [dict(item) for item in self.results]


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
    print("--- Running readiness and answer-mode checks ---")

    llm_called = {"value": False}

    def should_not_run_llm(*args, **kwargs):
        llm_called["value"] = True
        yield "This should not be generated."

    api.get_rag_engine_safe = lambda: FakeRagEngine([])
    api.query_kg = lambda question: []
    api.generate_answer = should_not_run_llm

    out_of_domain = api.chat(api.ChatRequest(query="What is sugar?", history=[]))
    print("Out-of-domain response:", out_of_domain["answer"])
    assert_true(out_of_domain["status"] == "refused", "Out-of-domain general knowledge should refuse when no evidence exists.")
    assert_true("don't have enough information" in out_of_domain["answer"].lower(), "Refusal text should stay strict.")
    assert_true(not llm_called["value"], "LLM should not run for evidence-free refusals.")

    captured = {"mode": None, "response_type": None}

    def answer_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        captured["mode"] = answer_mode
        captured["response_type"] = response_type
        yield "The minimum attendance requirement is 75% for examinations."

    api.get_rag_engine_safe = lambda: FakeRagEngine(
        [
            {
                "text": "The official B.Tech regulation mentions a minimum attendance requirement of 75% for examinations.",
                "source": "B.Tech Regulation 2024",
                "title": "B.Tech Regulation 2024",
                "page": 1,
                "score": 0.91,
                "vector_score": 0.88,
                "reranker_score": 0.92,
                "keyword_match_score": 0.64,
                "match_type": "keyword",
            }
        ]
    )
    api.query_kg = lambda question: []
    api.generate_answer = answer_generator

    response = api.chat(api.ChatRequest(query="Explain the minimum attendance requirement.", history=[], answer_mode="detailed"))
    print("Answer-mode response:", response["answer"])
    assert_true(captured["response_type"] == "explanation", "Explanation queries should drive the answer type passed to generation.")
    assert_true(response["status"] in {"complete", "limited"}, "Grounded answers should not refuse.")
    assert_true(response["type"] == "explanation", "Responses should expose the detected answer type.")
    assert_true(len(response["sources"]) > 0, "Grounded answer should expose sources in the new schema.")

    readiness = api.get_readiness()
    print("Readiness keys:", sorted(readiness.keys()))
    assert_true("state" in readiness and "index_version" in readiness, "Readiness endpoint should expose state and index version.")
    assert_true("checks" in readiness and "documents_indexed" in readiness, "Readiness endpoint should expose checklist data.")

    print("Readiness and answer-mode checks passed.")
finally:
    restore_originals()
