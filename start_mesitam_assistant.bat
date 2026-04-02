@echo off
TITLE MESITAM Institutional AI Assistant
COLOR 0A

echo ========================================================
echo   STARTING MESITAM INSTITUTIONAL AI ASSISTANT
echo ========================================================
echo.

:: 1. Start Fuseki Server (Background)
echo [1/3] Merging Knowledge Graph Files and Starting Server (Fuseki)...
venv\Scripts\python.exe merge_kg.py
start "Fuseki Server" java -jar fuseki\apache-jena-fuseki-5.6.0\fuseki-server.jar --file=data/merged_kg.ttl /mesitam_kg

:: Wait for Fuseki to initialize
timeout /t 5 /nobreak >nul

:: 2. Start FastAPI Backend (Background)
echo [2/3] Starting FastAPI Backend...
start "FastAPI Backend" cmd /c "venv\Scripts\activate && uvicorn api:app --host 127.0.0.1 --port 8000"

:: Wait for API to initialize
timeout /t 3 /nobreak >nul

:: 3. Start Vite App
echo [3/3] Launching AI Assistant Interface...
echo.
echo    - Role: Institutional AI
echo    - Device: RTX 3050 Optimized
echo.
cd frontend
npm run dev
