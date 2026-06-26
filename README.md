# NexRag

NexRag is a local-first academic assistant for MES Institute of Technology and Management that combines an official-source knowledge graph, hybrid retrieval, and a local LLM. The current app uses:

- a FastAPI backend in `api.py`
- modular backend services in `services/`
- a Vite + React frontend in `frontend/`
- Apache Jena Fuseki for the knowledge graph
- FAISS + BM25 + reranking for document retrieval
- Ollama for local answer generation
- an ingestion worker that scrapes official MESITAM pages and downloads

## How It Works

1. `tools/ingestion/run_worker.py` fetches official MESITAM pages and PDFs into the generated knowledge base.
2. `services/ingestion.py` builds `data/knowledge_base.json`, `data/mesitam_official.ttl`, and `data/official_documents.json`.
3. `kg.py` answers entity-style questions from the generated RDF graph, with Fuseki support and a local fallback.
4. `rag.py` retrieves grounded evidence from the official document corpus plus any user uploads in `data/uploads/`.
5. `llm.py` generates the final answer with strict grounding and concise/detailed answer modes.
6. `api.py` exposes readiness, chat, structured knowledge, ingestion, and evaluation endpoints to the frontend.

## Requirements

- Python 3.10+
- Node.js 18+
- Java 17+
- Ollama installed locally

Recommended model:

```powershell
ollama pull llama3.2:3b
```

## Setup

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

## Run NexRag

### One-click startup

```powershell
start_NexRag.bat
```

This launcher will:

- build or refresh the active RDF graph in `data/merged_kg.ttl`
- start Fuseki on `/mesitam_kg`
- start the FastAPI backend on `http://127.0.0.1:8000`
- start the frontend on `http://127.0.0.1:5173`

### Manual startup

Build or refresh the official knowledge base:

```powershell
venv\Scripts\python.exe tools\ingestion\run_worker.py --force
```

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
npm run dev
```

## Project Layout

- `frontend/`: active web UI
- `services/`: chat, readiness, ingestion, knowledge-base, and evaluation services
- `data/`: generated official knowledge artifacts, manifests, and vector artifacts
- `data/uploads/`: user-uploaded PDFs
- `tests/`: verification scripts
- `tools/`: maintenance, ingestion, and evaluation scripts
- `local/`: ignored local-only references and scratch files

## Useful Checks

```powershell
venv\Scripts\python.exe tests\test_import.py
venv\Scripts\python.exe tests\test_router.py
venv\Scripts\python.exe tests\test_retrieval.py
venv\Scripts\python.exe tests\test_kg.py
venv\Scripts\python.exe tests\test_readiness_and_modes.py
cd frontend
npm run build
```

Optional health check:

```powershell
venv\Scripts\python.exe tools\maintenance\check_health.py
```

## Notes

- The default Knowledge Base view is structured for users; graph inspection and Turtle editing are kept behind Developer Mode.
- Chat answers are restricted to retrieved MESITAM knowledge. Out-of-domain questions should return: `I don't have enough information in the knowledge base`.
- The startup UI uses `/api/readiness` so the app can clearly show `loading`, `ready`, or `error`.
- Generated runtime files such as raw scrape snapshots, logs, and local scratch data are intentionally ignored.

## License

This project is intended for academic and educational use.
