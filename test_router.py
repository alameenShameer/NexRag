from router import get_intent

test_cases = [
    ("What is Artificial Intelligence?", "DEFINITION"),
    ("Define Machine Learning.", "DEFINITION"),
    ("Meaning of RAG.", "DEFINITION"),
    ("Difference between RAM and ROM", "COMPARISON"),
    ("Compare Python vs Java", "COMPARISON"),
    ("How does the system work?", "GENERAL"),
    ("Why is the sky blue?", "GENERAL"),
]

print("Running Router Tests...")
for query, expected in test_cases:
    result = get_intent(query)
    print(f"Query: '{query}' -> Got: {result} (Expected: {expected})")
    assert result == expected, f"Failed for '{query}'"

print("\nAll Router Tests Passed.")
