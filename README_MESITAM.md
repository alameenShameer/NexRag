# MESITAM Institutional AI Assistant

This repository contains the MESITAM-focused NexRag deployment. It is a local hybrid assistant built around:

- a FastAPI backend,
- a React frontend in `frontend/`,
- a Fuseki-hosted knowledge graph,
- PDF retrieval using SentenceTransformers, FAISS, BM25, and reranking,
- answer generation through Ollama.

## Quick Start

### One-click startup

Run:

```powershell
start_mesitam_assistant.bat
```

That script will:

1. merge the KG source files,
2. start Fuseki on `/mesitam_kg`,
3. start the FastAPI backend on port `8000`,
4. start the frontend development server.

### Manual startup

```powershell
venv\Scripts\python.exe merge_kg.py
java -jar fuseki\apache-jena-fuseki-5.6.0\fuseki-server.jar --file=data/merged_kg.ttl /mesitam_kg
venv\Scripts\uvicorn.exe api:app --host 127.0.0.1 --port 8000
cd frontend
npm run dev
```

## Important Files

- `api.py`: backend API and chat orchestration
- `kg.py`: Fuseki querying and KG health checks
- `rag.py`: retrieval engine and vector store integration
- `llm.py`: Ollama prompt and model settings
- `router.py`: query intent routing
- `data/mesitam_data.ttl`: institutional knowledge graph source data
- `data/university_faq.ttl`: additional graph data
- `frontend/`: web UI

## Operational Notes

- The system is designed to prefer local model caches for offline-friendly startup.
- If the graph lacks a fact, the assistant should state that clearly instead of guessing.
- The frontend includes a knowledge graph editor for `.ttl` source updates and restart flows.

## Verification

```powershell
venv\Scripts\python.exe test_import.py
venv\Scripts\python.exe test_router.py
venv\Scripts\python.exe test_retrieval.py
venv\Scripts\python.exe test_kg.py
cd frontend
npm run build
```

## Troubleshooting

- `Connection refused` from KG calls usually means Fuseki is not running.
- Backend startup issues often mean Ollama or local embedding model files are unavailable.
- Frontend build issues inside restricted environments can come from sandboxed process spawning rather than app code.
