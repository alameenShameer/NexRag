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
    print("--- Running uploaded-definition fact checks ---")

    llm_called = {"value": False}

    def grounded_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        llm_called["value"] = True
        lowered = question.lower()
        if "neuronest" in lowered or "neuro nest" in lowered:
            yield "NeuroNest is an IoT-integrated healthcare and patient assistance platform designed to provide real-time physiological monitoring and efficient healthcare management."
        else:
            yield "The RAG architecture is inherently dynamic."

    neuronest_chunks = [
        {
            "text": "Overall, the NeuroNest system provides a comprehensive, cost-effective, and scalable solution for modern healthcare challenges. In addition to real-time monitoring and communication features, the NeuroNest",
            "source": "repog-20.pdf",
            "title": "repog-20.pdf",
            "page": 30,
            "score": 0.99,
            "vector_score": 0.97,
            "reranker_score": 0.99,
            "keyword_match_score": 0.94,
            "match_type": "exact_keyword",
            "source_type": "upload",
        },
        {
            "text": "DECLARATION We hereby declare that this project report entitled “NEURONEST: A SMART HEALTH CARE MONITORING SYSTEM” is the bonafide work carried out by us.",
            "source": "repog-20.pdf",
            "title": "repog-20.pdf",
            "page": 3,
            "score": 0.99,
            "vector_score": 0.96,
            "reranker_score": 0.99,
            "keyword_match_score": 0.94,
            "match_type": "exact_keyword",
            "source_type": "upload",
        },
        {
            "text": "PROPOSED SYSTEM 3.1SYSTEMOVERVIEW The proposed system, NeuroNest, is an IoT-integrated healthcare and patient assistance platform designed to provide real-time physiological monitoring and efficient healthcare management.",
            "source": "repog-20.pdf",
            "title": "repog-20.pdf",
            "page": 22,
            "score": 0.99,
            "vector_score": 0.97,
            "reranker_score": 0.99,
            "keyword_match_score": 0.94,
            "match_type": "exact_keyword",
            "source_type": "upload",
        },
    ]

    api.get_rag_engine_safe = lambda: FakeRagEngine(neuronest_chunks)
    api.query_kg = lambda question: []
    api.generate_answer = grounded_generator

    neuronest = api.chat(api.ChatRequest(query="what is neuronest", history=[], answer_mode="detailed"))
    print("Neuronest response:", neuronest["answer"])
    assert_true(
        neuronest["answer"] == "NeuroNest is an IoT-integrated healthcare and patient assistance platform designed to provide real-time physiological monitoring and efficient healthcare management.",
        "Uploaded-PDF fact questions should prefer the explicit definition sentence over chunk-edge fragments.",
    )
    assert_true(llm_called["value"], "Definition-style grounded answers should use the LLM for final phrasing.")
    assert_true(neuronest["sources"][0]["page"] == 22, "The best definition source should be surfaced first.")
    assert_true(
        all("declare" not in source.get("excerpt", "").lower() for source in neuronest["sources"]),
        "Declaration boilerplate should not be promoted as supporting evidence.",
    )

    capitalized_neuronest = api.chat(api.ChatRequest(query="What is NeuroNest?", history=[]))
    print("Capitalized NeuroNest response:", capitalized_neuronest["answer"])
    assert_true(
        capitalized_neuronest["answer"] == neuronest["answer"],
        "Definition extraction should stay stable across query casing.",
    )

    spaced_neuronest = api.chat(api.ChatRequest(query="what is neuro nest", history=[]))
    print("Spaced NeuroNest response:", spaced_neuronest["answer"])
    assert_true(
        spaced_neuronest["answer"] == neuronest["answer"],
        "Definition retrieval should stay stable when compound names are typed with spaces.",
    )

    rag_chunks = [
        {
            "text": "University policies, course catalogues, or event schedules. The RAG architecture is",
            "source": "Phase 1 Content.pdf",
            "title": "Phase 1 Content.pdf",
            "page": 11,
            "score": 0.99,
            "vector_score": 0.97,
            "reranker_score": 0.99,
            "keyword_match_score": 0.94,
            "match_type": "exact_keyword",
            "source_type": "upload",
        },
        {
            "text": "The RAG architecture is inherently dynamic. When new information becomes available, we simply update the vector database.",
            "source": "Phase 1 Content.pdf",
            "title": "Phase 1 Content.pdf",
            "page": 12,
            "score": 0.98,
            "vector_score": 0.96,
            "reranker_score": 0.98,
            "keyword_match_score": 0.93,
            "match_type": "exact_keyword",
            "source_type": "upload",
        },
    ]

    api.get_rag_engine_safe = lambda: FakeRagEngine(rag_chunks)

    rag_answer = api.chat(api.ChatRequest(query="what is the rag architecture", history=[], answer_mode="detailed"))
    print("RAG architecture response:", rag_answer["answer"])
    assert_true(
        rag_answer["answer"] == "The RAG architecture is inherently dynamic.",
        "Incomplete chunk-edge fragments should not be returned as final fact answers.",
    )

    print("Uploaded-definition fact checks passed.")
finally:
    restore_originals()
