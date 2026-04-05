from _bootstrap import ensure_repo_root

ensure_repo_root()

from services.pipeline_v2.fusion import weighted_rrf


def assert_true(condition, message):
    assert condition, message


print("--- Running pipeline v2 RRF checks ---")

channels = {
    "vector": [
        {"chunk_id": "a", "title": "Doc A", "text": "Alpha", "page": 1, "source": "Doc A", "source_type": "official", "source_url": None, "category": "General", "match_type": "vector", "vector_score": 0.91},
        {"chunk_id": "b", "title": "Doc B", "text": "Beta", "page": 2, "source": "Doc B", "source_type": "official", "source_url": None, "category": "General", "match_type": "vector", "vector_score": 0.88},
    ],
    "bm25": [
        {"chunk_id": "b", "title": "Doc B", "text": "Beta", "page": 2, "source": "Doc B", "source_type": "official", "source_url": None, "category": "General", "match_type": "keyword", "bm25_score": 0.95},
        {"chunk_id": "a", "title": "Doc A", "text": "Alpha", "page": 1, "source": "Doc A", "source_type": "official", "source_url": None, "category": "General", "match_type": "keyword", "bm25_score": 0.76},
    ],
    "lexical": [
        {"chunk_id": "a", "title": "Doc A", "text": "Alpha", "page": 1, "source": "Doc A", "source_type": "official", "source_url": None, "category": "General", "match_type": "exact_keyword", "keyword_match_score": 1.0},
    ],
}

fused = weighted_rrf(channels)
print("Fused titles:", [item["title"] for item in fused])

assert_true(fused[0]["title"] == "Doc A", "Lexical support plus vector rank should lift Doc A to the top under weighted RRF.")
assert_true("vector" in fused[0]["channel_ranks"], "RRF results should preserve vector channel ranks.")
assert_true("bm25" in fused[0]["channel_ranks"], "RRF results should preserve bm25 channel ranks.")
assert_true("lexical" in fused[0]["channel_ranks"], "RRF results should preserve lexical channel ranks.")

print("Pipeline v2 RRF checks passed.")
