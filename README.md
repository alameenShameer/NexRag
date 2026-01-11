🦅 NexRag – Hybrid RAG Assistant (KG + PDF + LLM)

NexRag is a Hybrid Retrieval-Augmented Generation (RAG) system that intelligently answers questions using:

📘 Knowledge Graph (SPARQL + Fuseki) for definition-type questions

📄 PDF document retrieval (TF-IDF + cosine similarity) for descriptive queries

🤖 Local LLM (Ollama) for grounded answer generation

The system is designed to be offline-friendly, privacy-preserving, and demo-ready.

✨ Key Features

🔀 Hybrid Routing

Definitions → Knowledge Graph

Other queries → PDF-based RAG

Automatic fallback if KG has no answer

📄 PDF Upload & Indexing

Upload academic PDFs

Automatic chunking and indexing

🧠 Classical RAG Retriever

TF-IDF vectorization

Cosine similarity

Top-k filtering + thresholding

🤖 Local LLM Inference

Uses Ollama (no cloud, no API keys)

Supports CPU-only mode (stable)

🔐 Privacy-Safe

No data leaves your machine

🏗️ Project Structure
NexRag/
│
├── app.py            # Streamlit UI & main flow
├── rag.py            # PDF RAG logic (TF-IDF + similarity)
├── kg.py             # Knowledge Graph (SPARQL queries)
├── llm.py            # LLM interaction via Ollama
├── router.py         # Query routing logic
│
├── data/
│   ├── pdfs/         # Uploaded PDFs
│   └── university_faq.ttl  # Knowledge Graph data
│
├── requirements.txt
├── README.md
└── venv/

🔁 System Architecture (High Level)
User Question
     ↓
Query Router
     ↓
 ┌───────────────┬──────────────────┐
 │ Definition?   │ Other Queries    │
 │               │                  │
 │ Knowledge     │ PDF Retrieval    │
 │ Graph (KG)    │ (TF-IDF + Cosine)│
 │               │                  │
 └───────┬───────┴─────────┬────────┘
         ↓                 ↓
     Answer from KG   Context from PDF
                          ↓
                   LLM (Ollama)
                          ↓
                    Final Answer

⚙️ Requirements

Python 3.9+

Ollama installed

Apache Jena Fuseki

📦 Installation & Setup
1️⃣ Clone the Repository
git clone <your-repo-url>
cd NexRag

2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Install & Pull LLM (Ollama)

Install Ollama from:
👉 https://ollama.com

Then pull the model:

ollama pull mistral:7b-instruct-q4_K_M
# or faster alternative
ollama pull phi3:mini

5️⃣ Setup Knowledge Graph (Fuseki)

Start Fuseki:

fuseki-server


Open browser:

http://localhost:3030


Create dataset:

Dataset name: university_faq
Type: Persistent (TDB2)


Upload:

data/university_faq.ttl

6️⃣ Run the Application
streamlit run app.py

🧪 Example Queries
Question	Answer Source
what is a seminar	Knowledge Graph
define seminar	Knowledge Graph
what are the guidelines	PDF (RAG)
explain seminar evaluation	PDF (RAG)
🧠 Why Hybrid RAG?

Knowledge Graphs are accurate for definitions

PDFs are rich for explanations

LLMs provide natural language answers

Hybrid approach ensures robustness & correctness

🧑‍🏫 Viva / Seminar Explanation (Use This)

“The system first attempts structured retrieval using a Knowledge Graph for definition-type queries. If no answer is found, it falls back to document-based retrieval using TF-IDF and cosine similarity, followed by LLM-based answer generation.”

🚀 Future Improvements

🔹 Replace TF-IDF with embeddings (FAISS / Sentence Transformers)

🔹 Multi-PDF indexing

🔹 Confidence score for answers

🔹 Source citation highlighting

🔹 Cloud LLM support (ChatGPT / Gemini)

👨‍🎓 Who Is This For?

Computer Science students

Final-year projects

RAG beginners

Knowledge Graph learners

Offline / privacy-focused AI demos

📜 License

This project is intended for educational and academic use.

⭐ If this helped you

Feel free to ⭐ the repository and share it with your friends 😊