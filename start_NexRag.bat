@echo off
TITLE NexRag
COLOR 0A

echo ========================================================
echo   STARTING NEXRAG
echo ========================================================
echo.

echo [1/3] Merging knowledge graph files and starting Fuseki...
venv\Scripts\python.exe merge_kg.py
start "Fuseki Server" java -jar fuseki\apache-jena-fuseki-5.6.0\fuseki-server.jar --file=data/merged_kg.ttl /mesitam_kg

timeout /t 5 /nobreak >nul

echo [2/3] Starting FastAPI backend...
start "FastAPI Backend" cmd /c "venv\Scripts\activate && uvicorn api:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [3/3] Launching NexRag interface...
echo.
echo    - Product: NexRag
echo    - Runtime: Local hybrid KG + vector retrieval
echo.
cd frontend
npm run dev
