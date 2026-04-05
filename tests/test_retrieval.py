from _bootstrap import ensure_repo_root

ensure_repo_root()

from rag import get_rag_engine
from kg import query_kg_facts
from services.chat import build_chat_payload, build_extractive_fallback


rag_engine = get_rag_engine()

print("Testing embedding model load...")
print(f"Encoder ready: {rag_engine.encoder is not None}")

test_text = """
NexRag is a hybrid retrieval-augmented generation system.
It uses both knowledge graphs and vector databases.
The goal is to reduce hallucination and improve accuracy.
"""

chunks = rag_engine.chunk_text(test_text, source="virtual_test.txt")
print(f"Created {len(chunks)} chunks from sample text.")
assert len(chunks) > 0, "Chunking returned no chunks."

diagnostics = rag_engine.retrieve_with_fallbacks("What is the goal of NexRag?", top_k=2)
results = diagnostics["results"]
print(f"Retrieved {len(results)} result(s) from the current vector store.")
assert isinstance(results, list), "Retrieval did not return a list."
assert "passes" in diagnostics and "retrieval_version" in diagnostics, "Soft-failure retrieval diagnostics were not returned."

compound_diagnostics = rag_engine.retrieve_with_fallbacks("what is neuro nest", top_k=2)
compound_results = compound_diagnostics["results"]
print("Compound-name retrieval results:", len(compound_results))
assert compound_results, "Compound-name queries should retrieve compact document terms such as NeuroNest."
assert any("neuronest" in result["text"].lower() for result in compound_results), "Expected a NeuroNest chunk for the spaced compound query."

for result in results[:2]:
    print(f" - [{result['score']:.4f}] {result['source']}: {result['text'][:90]}")

hod_payload = build_chat_payload(
    "Who is the HOD of Computer Science & Engineering?",
    [],
    rag_engine,
    kg_query_fn=query_kg_facts,
)
hod_titles = [item["title"] for item in hod_payload["vector_results"][:3]]
print("HOD retrieval titles:", hod_titles)
assert hod_payload["kg_facts"], "Expected KG facts for the HOD query."
assert all("(Artificial Intelligence)" not in title for title in hod_titles), "AI department evidence leaked into the plain CSE HOD query."
assert "Vineetha" in hod_payload["kg_facts"][0]["entity"], "Expected the KG HOD answer to resolve to Dr. Vineetha G. R."

nayana_payload = build_chat_payload(
    "Who is Nayana?",
    [],
    rag_engine,
    kg_query_fn=query_kg_facts,
)
print("Nayana payload status:", nayana_payload["status"], "direct answer:", nayana_payload["direct_answer"])
assert nayana_payload["status"] != "refused", "Uploaded PDFs with richer person context should answer person queries."
assert nayana_payload["direct_answer"] is not None, "Uploaded person queries should produce a grounded direct answer when sufficient details are present."
assert "Nayana" in nayana_payload["direct_answer"], "The uploaded-person answer should mention Nayana."
assert "NEURONEST" in nayana_payload["direct_answer"], "The uploaded-person answer should preserve the grounded project title when present."
assert "repog-20.pdf" in [item["title"] for item in nayana_payload["sources"]], "The supporting uploaded PDF should be surfaced in sources."

neuronest_payload = build_chat_payload(
    "can you explain neuronest",
    [],
    rag_engine,
    kg_query_fn=query_kg_facts,
)
neuronest_fallback = build_extractive_fallback(neuronest_payload, answer_mode="detailed")
print(
    "NeuroNest explanation:",
    neuronest_payload["status"],
    "vector_results=",
    len(neuronest_payload["vector_results"]),
    "filtered_evidence=",
    len(neuronest_payload["filtered_evidence"]),
)
assert neuronest_payload["status"] != "refused", "NeuroNest explanation queries should have enough grounded evidence."
assert len(neuronest_payload["vector_results"]) >= 6, "Explanation queries should retain more than five retrieved chunks when strong evidence exists."
assert len(neuronest_payload["filtered_evidence"]) >= 3, "Explanation queries should keep multiple evidence sentences."
assert len(neuronest_payload["sources"]) >= 2, "Explanation queries should surface multiple supporting source excerpts."
assert "NeuroNest" in neuronest_fallback, "The explanation fallback should stay grounded on the queried entity."

print("Retrieval checks completed.")
