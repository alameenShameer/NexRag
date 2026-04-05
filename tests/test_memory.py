from _bootstrap import ensure_repo_root

ensure_repo_root()

import api


class FakeRagEngine:
    def __init__(self, results):
        self.results = results
        self.queries = []

    def retrieve(self, query, top_k=5, filter_category=None, min_score=0.0):
        self.queries.append(query)
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
    print("--- Running soft-failure and follow-up checks ---")

    weak_but_relevant_chunk = {
        "text": "NexRag is a hybrid retrieval-augmented generation system for grounded academic question answering.",
        "source": "Project Report Front.pdf",
        "title": "NexRAG Project Report",
        "page": 1,
        "score": 0.46,
        "vector_score": 0.28,
        "reranker_score": 0.32,
        "keyword_match_score": 0.78,
        "title_match_score": 0.9,
        "match_type": "exact_keyword",
        "forced_match": True,
    }

    fallback_rag = FakeRagEngine([weak_but_relevant_chunk])

    llm_called_for_fact = {"value": False}

    def refusing_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        llm_called_for_fact["value"] = True
        yield "I don't have enough information in the knowledge base"

    api.get_rag_engine_safe = lambda: fallback_rag
    api.query_kg = lambda question: []
    api.generate_answer = refusing_generator

    response = api.chat(api.ChatRequest(query="What is NexRAG?", history=[]))
    print("Soft-failure answer:", response["answer"])
    assert_true(response["status"] in {"complete", "limited"}, "Weak but relevant evidence should produce a grounded answer instead of refusal.")
    assert_true("nexrag" in response["answer"].lower(), "Extractive fallback should still answer from indexed evidence.")
    assert_true(len(response["sources"]) == 1, "The best supporting source should be returned.")
    assert_true(llm_called_for_fact["value"], "Grounded fact answers should now use the LLM before fallback is considered.")

    follow_up_rag = FakeRagEngine(
        [
            {
                "text": "NexRag uses both knowledge graph facts and document retrieval for grounded answers.",
                "source": "NexRAG Project Report",
                "title": "NexRAG Project Report",
                "page": 2,
                "score": 0.71,
                "vector_score": 0.62,
                "reranker_score": 0.74,
                "keyword_match_score": 0.55,
                "match_type": "keyword",
            }
        ]
    )

    def grounded_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        yield "NexRag combines knowledge graph facts with document retrieval to keep answers grounded."

    api.get_rag_engine_safe = lambda: follow_up_rag
    api.generate_answer = grounded_generator

    follow_up = api.chat(
        api.ChatRequest(
            query="How does it work?",
            history=[
                {"role": "user", "content": "What is NexRAG?"},
                {"role": "assistant", "content": "Earlier assistant text should not matter."},
            ],
        )
    )

    retrieval_query = follow_up_rag.queries[-1].lower()
    print("Follow-up retrieval query:", retrieval_query)
    assert_true("what is nexrag" in retrieval_query, "Follow-up retrieval should carry forward the prior user subject.")
    assert_true("how does it work" in retrieval_query, "Follow-up retrieval should include the current question.")
    assert_true(follow_up["status"] in {"complete", "limited"}, "Follow-up with evidence should not refuse.")

    def drifting_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        yield "NexRag uses document retrieval, knowledge graph facts, and web search."

    api.generate_answer = drifting_generator

    grounded_fallback = api.chat(
        api.ChatRequest(
            query="How does it work?",
            history=[{"role": "user", "content": "What is NexRAG?"}],
        )
    )

    print("Grounding fallback answer:", grounded_fallback["answer"])
    assert_true("web search" not in grounded_fallback["answer"].lower(), "Unsupported generated terms should be discarded.")
    assert_true("document retrieval" in grounded_fallback["answer"].lower(), "Fallback should preserve supported extracted evidence.")

    print("Soft-failure and follow-up checks passed.")
finally:
    restore_originals()
