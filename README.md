# NexRag

NexRag is a local-first hybrid RAG assistant for MES Institute of Technology and Management. It combines:

- a knowledge graph served from Apache Jena Fuseki,
- document retrieval over uploaded PDFs using SentenceTransformers, FAISS, BM25, and a reranker,
- local answer generation through Ollama,
- a FastAPI backend and a Vite + React frontend.

The project no longer runs as the older Streamlit + TF-IDF app described in earlier drafts. The current system is API-backed and optimized for local deployment.

## Architecture

User query flow:

1. `router.py` classifies the query intent.
2. `kg.py` tries to answer entity-centric questions from Fuseki.
3. `rag.py` retrieves supporting document chunks from the vector store.
4. `llm.py` generates a grounded answer using Ollama.
5. `api.py` returns the answer, snippets, routing trace, and system status to the frontend.

Main code paths:

- `api.py`: FastAPI service and chat/upload/status endpoints
- `rag.py`: embedding, indexing, BM25, FAISS, reranking
- `kg.py`: Fuseki query logic and KG health check
- `llm.py`: local Ollama prompt and generation config
- `frontend/`: React app
- `data/`: PDFs, vector index, KG source files, merged graph
- `start_mesitam_assistant.bat`: local convenience launcher

## Requirements

- Python 3.10+
- Node.js 18+
- Java 17+
- Ollama installed locally

Recommended Ollama model:

```powershell
ollama pull llama3.2:3b
```

## Backend Setup

Create and activate the virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

The embedding and reranker models are expected to be available locally. The app prefers cached local model files for offline reliability.

## Running The App

### Option 1: one-click local startup

```powershell
start_mesitam_assistant.bat
```

This will:

- merge `.ttl` knowledge graph files into `data/merged_kg.ttl`,
- start Fuseki on `/mesitam_kg`,
- start the FastAPI backend on `http://127.0.0.1:8000`,
- start the frontend dev server from `frontend/`.

### Option 2: manual startup

Start Fuseki:

```powershell
venv\Scripts\python.exe merge_kg.py
java -jar fuseki\apache-jena-fuseki-5.6.0\fuseki-server.jar --file=data/merged_kg.ttl /mesitam_kg
```

Start the backend:

```powershell
venv\Scripts\uvicorn.exe api:app --host 127.0.0.1 --port 8000
```

Start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Frontend Build

For a production-style frontend build:

```powershell
cd frontend
npm run build
```

## Example Queries

- `Who is the HOD of Computer Science and Engineering?`
- `Who teaches Operating Systems?`
- `What are KTU exam rules?`
- `Explain the seminar guidelines.`
- `What is a project?`

## Notes

- The knowledge graph may answer only what is actually modeled in the `.ttl` files. If a faculty-to-course relationship is missing, the app should say it does not know rather than guess.
- The frontend includes a knowledge graph editor that can update source `.ttl` files and trigger a graph restart.
- Generated artifacts such as `frontend/build/`, `logs/`, and vector store files should not be mixed into feature commits unless intentionally updated.

## Verification

Useful local checks:

```powershell
venv\Scripts\python.exe test_import.py
venv\Scripts\python.exe test_router.py
venv\Scripts\python.exe test_retrieval.py
venv\Scripts\python.exe test_kg.py
cd frontend
npm run build
```

## License

This project is intended for educational and academic use.
