@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

echo [Dushman AI] Starting backend...
if not exist "%BACKEND%\venv\Scripts\python.exe" (
  echo [Dushman AI] Creating backend virtual environment...
  python -m venv "%BACKEND%\venv"
)

call "%BACKEND%\venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt"

start "Dushman AI Backend" cmd /k "cd /d ""%BACKEND%"" && ""%BACKEND%\venv\Scripts\python.exe"" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [Dushman AI] Starting frontend...
if not exist "%FRONTEND%\node_modules" (
  echo [Dushman AI] Installing frontend dependencies...
  pushd "%FRONTEND%"
  call npm install
  popd
)

start "Dushman AI Frontend" cmd /k "cd /d ""%FRONTEND%"" && npm run dev"

echo [Dushman AI] Done. Backend: http://localhost:8000/docs  Frontend: http://localhost:3000
