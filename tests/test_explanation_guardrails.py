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
    print("--- Running explanation guardrail checks ---")

    llm_called = {"value": False}

    def grounded_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        llm_called["value"] = True
        yield "The Career Guidance & Placement Cell gives training in soft skill, aptitude group discussion, and interview preparation, and frequently arranges motivation classes to expose students to the industry."

    api.get_rag_engine_safe = lambda: FakeRagEngine([])
    api.generate_answer = grounded_generator
    api.query_kg = lambda question: [
        {
            "entity": "Career Guidance & Placement Cell",
            "fact": (
                "Career Guidance & Placement Cell MESITAM The winner is not one who never fails but one who never quits "
                "Career Guidance & Placement Cell [CGPC] of MES Institute of Technology and Management, Chathannoor "
                "having the aim of helping our young professionals by giving intensive training to incur the capacity to come out "
                "with fine colors in the respective fields of study. It is the duty of CGPC to give training for our students in "
                "the areas of soft skill, aptitude group discussion and prepare the students to face the interviews. "
                "CGPC frequently arrange motivation classes for our students, thereby we mould our students to get exposed "
                "to the industry, which will help our students to obtain great heights with attractive perks."
            ),
            "score": 0.92,
        },
        {
            "entity": "Career Guidance & Placement Cell",
            "fact": "Source URL: https://www.mesitam.ac.in/placement.php",
            "score": 0.88,
        },
    ]

    placement = api.chat(api.ChatRequest(query="Explain the placement process", history=[]))
    print("Placement response:", placement["answer"])
    assert_true(placement["type"] == "explanation", "Placement query should remain an explanation response.")
    assert_true(placement["status"] in {"complete", "limited"}, "Grounded placement guidance should not refuse.")
    assert_true("source url" not in placement["answer"].lower(), "KG metadata should never leak into the answer text.")
    assert_true("soft skill" in placement["answer"].lower() or "interviews" in placement["answer"].lower(), "Placement answer should extract the substantive process summary.")
    assert_true(llm_called["value"], "Grounded explanations should use the LLM for final phrasing.")
    assert_true(len(placement["sources"]) == 1, "Placement explanation should expose the structured supporting source.")

    llm_called["value"] = False
    api.get_rag_engine_safe = lambda: FakeRagEngine(
        [
            {
                "text": "Students are not permitted to change the PE and OE/ILE courses chosen in a semester after completing the exam registration on the KTU Portal.",
                "source": "B.Tech Regulation 2024",
                "title": "B.Tech Regulation 2024",
                "page": 48,
                "score": 0.72,
                "vector_score": 0.66,
                "reranker_score": 0.73,
                "keyword_match_score": 0.81,
                "match_type": "exact_keyword",
            },
            {
                "text": "To facilitate the smooth transfer of KTU credits to foreign universities, the curriculum shall include provisions for self-study hours and ECTS calculations.",
                "source": "B.Tech Regulation 2024",
                "title": "B.Tech Regulation 2024",
                "page": 72,
                "score": 0.7,
                "vector_score": 0.61,
                "reranker_score": 0.69,
                "keyword_match_score": 0.78,
                "match_type": "exact_keyword",
            },
        ]
    )
    api.query_kg = lambda question: []

    weak_explanation = api.chat(api.ChatRequest(query="Explain the KTU exam rules", history=[]))
    print("Weak explanation response:", weak_explanation["answer"])
    assert_true(weak_explanation["status"] == "refused", "Incoherent explanation evidence should refuse instead of stitching unrelated rules together.")
    assert_true("don't have enough information" in weak_explanation["answer"].lower(), "Refusal text should stay strict for weak explanation grounding.")
    assert_true(not llm_called["value"], "The LLM should not run when explanation evidence is incoherent.")

    llm_called["value"] = False

    def neuronest_generator(question, context, history=None, stream=False, answer_mode=None, response_type=None):
        llm_called["value"] = True
        yield "NeuroNest is an IoT-integrated healthcare and patient assistance platform that provides real-time physiological monitoring and efficient healthcare management."

    api.get_rag_engine_safe = lambda: FakeRagEngine(
        [
            {
                "text": "RESULTS AND DISCUSSION The performance and functionality of the NeuroNest system are evaluated in this chapter through various system tests and observations.",
                "source": "repog-20.pdf",
                "title": "repog-20.pdf",
                "page": 31,
                "score": 0.92,
                "vector_score": 0.82,
                "reranker_score": 0.91,
                "keyword_match_score": 0.88,
                "match_type": "exact_keyword",
            },
            {
                "text": "NeuroNest is an IoT-integrated healthcare and patient assistance platform designed to provide real-time physiological monitoring and efficient healthcare management.",
                "source": "repog-20.pdf",
                "title": "repog-20.pdf",
                "page": 22,
                "score": 0.88,
                "vector_score": 0.79,
                "reranker_score": 0.86,
                "keyword_match_score": 0.84,
                "match_type": "exact_keyword",
            },
            {
                "text": "DECLARATION We hereby declare that this project report entitled NEURONEST is the bonafide work carried out by us.",
                "source": "repog-20.pdf",
                "title": "repog-20.pdf",
                "page": 3,
                "score": 0.85,
                "vector_score": 0.76,
                "reranker_score": 0.82,
                "keyword_match_score": 0.83,
                "match_type": "exact_keyword",
            },
        ]
    )
    api.generate_answer = neuronest_generator

    neuronest_explanation = api.chat(api.ChatRequest(query="Explain NeuroNest", history=[]))
    print("NeuroNest explanation response:", neuronest_explanation["answer"])
    assert_true(neuronest_explanation["status"] in {"complete", "limited"}, "Entity explanations with strong overview evidence should not refuse.")
    assert_true(neuronest_explanation["sources"][0]["page"] == 22, "Overview-style evidence should outrank results/discussion boilerplate.")
    assert_true("results and discussion" not in neuronest_explanation["sources"][0]["excerpt"].lower(), "Results/discussion blurbs should not be the lead explanation source.")
    assert_true(llm_called["value"], "Strong explanation grounding should still use the generator.")

    print("Explanation guardrail checks passed.")
finally:
    restore_originals()
