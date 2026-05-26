@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "PYTHON=%BACKEND%\venv\Scripts\python.exe"

echo [Dushman AI] Preparing backend...
if not exist "%PYTHON%" (
  echo [Dushman AI] Creating backend virtual environment...
  python -m venv "%BACKEND%\venv"
)

call "%PYTHON%" -m pip install -r "%BACKEND%\requirements.txt"

echo [Dushman AI] Verifying Supabase connection...
call "%PYTHON%" "%BACKEND%\verify_supabase.py"

echo [Dushman AI] Starting frontend...
if not exist "%FRONTEND%\node_modules" (
  echo [Dushman AI] Installing frontend dependencies...
  pushd "%FRONTEND%"
  call npm install
  popd
)

start "Dushman AI Frontend" cmd /k "cd /d ""%FRONTEND%"" && npm run dev"

echo [Dushman AI] Starting backend in this window (keep it open)...
cd /d "%BACKEND%"
call "%PYTHON%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
