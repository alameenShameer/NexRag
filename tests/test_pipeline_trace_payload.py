from _bootstrap import ensure_repo_root

ensure_repo_root()

import api


class FakeRagEngine:
    def __init__(self, results):
        self.results = results

    def retrieve(self, query, top_k=5, filter_category=None, min_score=0.0):
        return [dict(item) for item in self.results]


ORIGINAL_GET_RAG_ENGINE_SAFE = api.get_rag_engine_safe


def assert_true(condition, message):
    assert condition, message


try:
    print("--- Running pipeline trace payload checks ---")

    api.get_rag_engine_safe = lambda: FakeRagEngine(
        [
            {
                "text": "NeuroNest is an IoT-integrated healthcare and patient assistance platform designed to provide real-time physiological monitoring and efficient healthcare management.",
                "source": "repog-20.pdf",
                "title": "repog-20.pdf",
                "page": 22,
                "score": 0.96,
                "vector_score": 0.91,
                "reranker_score": 0.94,
                "keyword_match_score": 0.78,
                "match_type": "definition_scan",
                "source_type": "upload",
                "source_url": None,
            }
        ]
    )

    response = api.chat(api.ChatRequest(query="What is NeuroNest?", history=[]))
    print("Response keys:", sorted(response.keys()))
    assert_true(bool(response.get("trace_id")), "Chat responses should expose a trace id.")
    assert_true(isinstance(response.get("query_plan"), dict), "Chat responses should include a serialized query plan.")
    assert_true(isinstance(response.get("retrieval_trace"), dict), "Chat responses should include retrieval trace diagnostics.")
    assert_true("graph_view" in response, "Chat responses should include an answer-scoped graph view payload.")
    assert_true("source_groups" in response, "Chat responses should expose grouped evidence for the UI.")

    graph_debug = api.graph_query(api.GraphQueryRequest(query="What is NeuroNest?", history=[]))
    print("Graph debug keys:", sorted(graph_debug.keys()))
    assert_true("query_plan" in graph_debug and "graph_view" in graph_debug, "Graph debug endpoint should expose the query plan and graph view.")
    assert_true("kg_queries" in graph_debug, "Graph debug endpoint should expose generated KG/SPARQL trace data.")

    print("Pipeline trace payload checks passed.")
finally:
    api.get_rag_engine_safe = ORIGINAL_GET_RAG_ENGINE_SAFE
