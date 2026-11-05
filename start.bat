@echo off
REM Start the KAFA UPKK Learning Assistant: double-click this file.
REM Two windows open (backend and frontend); close them to stop the system.
cd /d "%~dp0"

REM models are already downloaded: do not check the internet for updates
set HF_HUB_OFFLINE=1

echo Starting backend (http://localhost:8000) ...
start "KAFA backend" cmd /k ".venv\Scripts\uvicorn backend.app.main:app --port 8000"

echo Starting frontend (http://localhost:5173) ...
start "KAFA frontend" cmd /k "cd frontend && npm run dev -- --port 5173"

echo Waiting for the models to load, then opening the app ...
timeout /t 25 /nobreak >nul
start "" http://localhost:5173
