
import os
import time
from rag import get_rag_engine
rag_engine = get_rag_engine()
from router import get_intent
from llm import generate_answer

# Mock KG (since Fuseki might not be running/populated in this env)
def mock_query_kg(question):
    if "rag" in question.lower():
        return "RAG stands for Retrieval-Augmented Generation. It combines retrieval with generation."
    return None

print(">>> 🧪 STARTING SYSTEM INTEGRATION TEST <<<\n")

# 1. Setup Data
print("Step 1: Indexing Knowledge Base...")
test_content = """
NexRag is an advanced hybrid retrieval system designed for academic projects.
It uses SentenceTransformers for embedding and FAISS for vector search.
Uniquely, it reserves the GPU heavily for the LLM by offloading retrieval to CPU.
It includes a Router to classify intents like Definition vs General questions.
Cross-Encoders are used to rerank the top retrieved chunks for maximum precision.
"""
chunks = rag_engine.chunk_text(test_content, source="system_test_doc.pdf")
embeddings = rag_engine.encoder.encode([c["text"] for c in chunks], convert_to_numpy=True)
rag_engine.index.add(embeddings)
rag_engine.chunks_metadata.extend(chunks)
print(f"✅ Indexed {len(chunks)} chunks.")

# 2. Test Router & Hybrid Logic
query = "What is the unique feature of NexRag?"
print(f"\nStep 2: Processing Query: '{query}'")

intent = get_intent(query)
print(f"🧠 Intent Detected: {intent}")

# 3. Retrieval
print("🔍 Retrieving & Reranking...")
retrieved = rag_engine.retrieve(query, top_k=3)
print(f"✅ Retrieved {len(retrieved)} chunks.")
top_hit = retrieved[0]
print(f"   Top Result (Score {top_hit['score']:.4f}): {top_hit['text'][:100]}...")

# 4. Context Assembly
context = f"Context:\n{top_hit['text']}"

# 5. LLM Generation
print("\nStep 3: Generating Answer with LLM (Streaming)...")
full_response = ""
try:
    start_time = time.time()
    for chunk in generate_answer(query, context):
        print(chunk, end="", flush=True)
        full_response += chunk
    end_time = time.time()
    print(f"\n\n⏱️ Generation Time: {end_time - start_time:.2f}s")
    
    if len(full_response) > 10:
        print("✅ LLM Test Passed")
    else:
        print("❌ LLM output suspicious")
        
except Exception as e:
    print(f"\n❌ LLM Failed: {e}")
    print("Ensure Ollama is running safely.")

print("\n>>> 🏁 INTEGRATION TEST COMPLETE <<<")
