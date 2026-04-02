import os
import shutil
import pickle
import numpy as np
import pdfplumber
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
import re
import math


# Configuration
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
VECTOR_DB_PATH = "data/vector_store.index"
CHUNKS_METADATA_PATH = "data/chunks_metadata.pkl"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

class RAGEngine:
    def __init__(self):
        # Load Embedding Model
        print("Loading embedding model...")
        self.encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        # Load Reranker
        print("Loading reranker...")
        self.reranker = CrossEncoder(RERANK_MODEL_NAME)
        
        # Initialize Vector Store
        self.index = None
        self.chunks_metadata = [] # Stores actual text and metadata corresponding to Faiss indices
        
        # Load existing index if available
        self._load_index()

    def _preprocess(self, text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return text

    def _rebuild_bm25(self):
        if not self.chunks_metadata:
            self.bm25 = None
            return
        tokenized_docs = [self._preprocess(c["text"]).split() for c in self.chunks_metadata]
        self.bm25 = BM25Okapi(tokenized_docs)

    def _load_index(self):
        if os.path.exists(VECTOR_DB_PATH) and os.path.exists(CHUNKS_METADATA_PATH):
            print("Loading vector store from disk...")
            self.index = faiss.read_index(VECTOR_DB_PATH)
            with open(CHUNKS_METADATA_PATH, "rb") as f:
                self.chunks_metadata = pickle.load(f)
            self._rebuild_bm25()
        else:
            print("No existing vector store found. Initializing new one.")
            # Dimension for all-MiniLM-L6-v2 is 384
            self.index = faiss.IndexFlatL2(384)
            self.chunks_metadata = []
            self.bm25 = None

    def _save_index(self):
        os.makedirs("data", exist_ok=True)
        faiss.write_index(self.index, VECTOR_DB_PATH)
        with open(CHUNKS_METADATA_PATH, "wb") as f:
            pickle.dump(self.chunks_metadata, f)

    def extract_text(self, pdf_path):
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def chunk_text(self, text, source="unknown"):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = splitter.split_text(text)
        return [{"text": c, "source": source} for c in chunks]

    def index_pdf(self, pdf_path, category="General"):
        # 1. Extract
        print(f"Extracting text from {pdf_path} (Category: {category})...")
        text = self.extract_text(pdf_path)
        
        # 2. Chunk
        print("Chunking text...")
        source = os.path.basename(pdf_path)
        new_chunks = self.chunk_text(text, source=source)
        
        if not new_chunks:
            return 0
            
        # Add metadata to chunks
        for chunk in new_chunks:
            chunk["category"] = category

        # 3. Embed
        print("Generating embeddings...")
        texts = [c["text"] for c in new_chunks]
        embeddings = self.encoder.encode(texts, convert_to_numpy=True)
        
        # 4. Add to Index
        print("Adding to vector store...")
        if self.index is None:
             self.index = faiss.IndexFlatL2(384)
             
        self.index.add(embeddings)
        self.chunks_metadata.extend(new_chunks)
        self._rebuild_bm25()
        
        # 5. Persist
        self._save_index()
        print(f"Indexed {len(new_chunks)} chunks.")
        return len(new_chunks)

    def retrieve(self, query, top_k=5, filter_category=None):
        if self.index is None or self.index.ntotal == 0:
            return []
        
        # 1. Embed Query
        query_vec = self.encoder.encode([query], convert_to_numpy=True)
        
        # 2. Search (Fetch detailed candidates)
        # Fetch more candidates to allow for filtering
        initial_k = top_k * 5
        distances, indices = self.index.search(query_vec, initial_k)
        
        candidates = {} # text -> item
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.chunks_metadata):
                item = self.chunks_metadata[idx]
                
                # Apply Filter
                if filter_category and item.get("category", "General") != filter_category:
                    continue
                    
                candidates[item["text"]] = item
                
        # 2b. Search BM25
        if self.bm25 is not None:
            tokenized_query = self._preprocess(query).split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            bm25_indices = np.argsort(bm25_scores)[::-1][:initial_k]
            for idx in bm25_indices:
                score = bm25_scores[idx]
                if score > 0:
                    item = self.chunks_metadata[idx]
                    if filter_category and item.get("category", "General") != filter_category:
                        continue
                    if item["text"] not in candidates:
                        candidates[item["text"]] = item
        
        candidate_list = list(candidates.values())
        if not candidate_list:
            return []
            
        # 3. Rerank
        pairs = [[query, c["text"]] for c in candidate_list]
        scores = self.reranker.predict(pairs)
        
        # 4. Sort and Format (Apply Sigmoid for 0-1 probability)
        results = []
        for i, raw_score in enumerate(scores):
            # Sigmoid normalization to convert CrossEncoder logit to percentage properly
            normalized_score = 1 / (1 + math.exp(-raw_score))

            results.append({
                "text": candidate_list[i]["text"],
                "source": candidate_list[i]["source"],
                "category": candidate_list[i].get("category", "General"),
                "score": float(normalized_score)
            })
            
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# Helper function for lazy initialization
def get_rag_engine():
    return RAGEngine()

# Globals for script compatibility
_global_engine = None
def _get_global_engine():
    global _global_engine
    if _global_engine is None:
        _global_engine = RAGEngine()
    return _global_engine

def index_pdf(pdf_path, category="General"):
    return _get_global_engine().index_pdf(pdf_path, category)

def retrieve(query, top_k=5, filter_category=None):
    return _get_global_engine().retrieve(query, top_k, filter_category)
