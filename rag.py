import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

vectorizer = TfidfVectorizer(stop_words="english")
documents_store = []

def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

def chunk_text(text, chunk_size=750, overlap=100):
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start+chunk_size])
        start += chunk_size - overlap
    return chunks

def index_pdf(pdf_path):
    text = extract_text(pdf_path)
    chunks = chunk_text(text)
    embeddings = vectorizer.fit_transform(chunks).toarray()

    documents_store.clear()
    for c, e in zip(chunks, embeddings):
        documents_store.append({"content": c, "embedding": e})

def retrieve(query, top_k=5, threshold=0.05):
    if not documents_store:
        return []

    q_vec = vectorizer.transform([query]).toarray()
    scored = []

    for doc in documents_store:
        sim = cosine_similarity(q_vec, [doc["embedding"]])[0][0]
        if sim >= threshold:
            scored.append((sim, doc["content"]))

    scored.sort(reverse=True)
    return [c for _, c in scored[:top_k]]
