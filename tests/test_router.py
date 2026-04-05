from _bootstrap import ensure_repo_root

ensure_repo_root()

from router import get_intent


test_cases = [
    ("What is Artificial Intelligence?", "DEFINITION"),
    ("Define Machine Learning.", "DEFINITION"),
    ("Meaning of RAG.", "DEFINITION"),
    ("Explain NeuroNest.", "GENERAL"),
    ("Difference between RAM and ROM", "COMPARISON"),
    ("Compare Python vs Java", "COMPARISON"),
    ("How does the system work?", "GENERAL"),
    ("Why is the sky blue?", "GENERAL"),
]


print("Running router checks...")
for query, expected in test_cases:
    result = get_intent(query)
    print(f"Query: {query!r} -> {result} (expected {expected})")
    assert result == expected, f"Router mismatch for {query!r}"

print("All router checks passed.")
