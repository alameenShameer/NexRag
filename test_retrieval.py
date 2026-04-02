
import os
import shutil
from rag import index_pdf, retrieve

# Setup dummy PDF for testing
TEST_PDF_PATH = "data/pdfs/test_doc.pdf"
os.makedirs("data/pdfs", exist_ok=True)

# Create a simple PDF if not exists (using reportlab or just mocking pdfplumber behavior? 
# mocking is hard without lib, let's assume user has a PDF or I can just test retrieval if index exists.
# Actually, I can't easily create a PDF without reportlab. 
# I will try to use a mock or just check if rag.py's internal components work with text.)

# Let's test the RAGEngine components directly with raw text to avoid PDF dependency issues in this script
from rag import get_rag_engine
rag_engine = get_rag_engine()

print(">>> Testing Embedding Model Load...")
# Force load
encoder = rag_engine.encoder
print(f"Model loaded: {encoder}")

print("\n>>> Testing Indexing with Raw Text...")
test_text = """
NexRag is a hybrid retrieval-augmented generation system.
It uses both Knowledge Graphs and Vector Databases.
The goal is to reduce hallucination and improve accuracy.
This project is for a final year university submission.
"""

chunks = rag_engine.chunk_text(test_text, source="virtual_test.txt")
print(f"Created {len(chunks)} chunks.")

print("Generating embeddings and adding to FAISS...")
embeddings = rag_engine.encoder.encode([c["text"] for c in chunks], convert_to_numpy=True)
rag_engine.index.add(embeddings)
rag_engine.chunks_metadata.extend(chunks)
print(f"Index size: {rag_engine.index.ntotal}")

print("\n>>> Testing Retrieval...")
query = "What is the goal of NexRag?"
results = rag_engine.retrieve(query, top_k=2)

print(f"Query: {query}")
for r in results:
    print(f" - [Score {r['score']:.4f}] {r['text']}")

assert len(results) > 0, "Retrieval failed to find results."
print("\nVerification Successful.")
