@echo off
setlocal enabledelayedexpansion

:: ── Configuration ──────────────────────────────────────────────────────────
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "VENV_PY=%BACKEND%\venv\Scripts\python.exe"
set "LAUNCHER_BACKEND=%TEMP%\dushman_backend.bat"
set "LAUNCHER_FRONTEND=%TEMP%\dushman_frontend.bat"

:: Detect if Docker is available
set "DOCKER_AVAILABLE=no"
where docker >nul 2>&1 && set "DOCKER_AVAILABLE=yes"

echo ======================================================
echo       Dushman AI - One-Click Launcher
echo ======================================================
echo.

:: ── 1. Prerequisites ───────────────────────────────────────────────────────
echo [1/9] Checking prerequisites...

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found! Install Python 3.10+ from python.org
    pause
    exit /b 1
)
:: Parse minor version from "Python 3.12.0" —^ tokens=2 delims=. gives "12"
for /f "tokens=2 delims=." %%a in ('python --version 2^>^&1') do set "PY_MINOR=%%a"
if %PY_MINOR% lss 10 (
    echo [ERROR] Python 3.10+ required. Found:
    python --version
    echo Upgrade Python and try again.
    pause
    exit /b 1
)
echo [OK] Python %PY_MINOR%.x detected

where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js not found! Install Node.js 20+ from nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js detected

:: ── 2. Environment File ────────────────────────────────────────────────────
echo.
echo [2/9] Configuring backend environment...

if not exist "%BACKEND%\.env" (
    if exist "%BACKEND%\.env.example" (
        copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
        echo [OK] Created backend\.env from template

        :: Prompt to edit the .env file with the user's values
        echo.
        echo  ===== IMPORTANT: Edit your .env file =====
        echo  The file backend\.env has been created from the template.
        echo  You MUST update these settings before continuing:
        echo.
        echo    DATABASE_URL  - Your PostgreSQL connection string
        echo    JWT_SECRET    - Any string 64+ characters
        echo    NVIDIA_API_KEY or GEMINI_API_KEY  - Your LLM provider key
        echo.
        echo  Press any key to open the file in Notepad now...
        pause >nul

        start notepad "%BACKEND%\.env"
        echo  Press any key AFTER you've saved your changes...
        pause >nul

        :: Restart the batch file so new .env values take effect
        echo [OK] .env saved — restarting setup...
        echo.
        echo.
        echo Restarting setup from step 3...
        goto :continue_setup
    ) else (
        echo [ERROR] No .env.example found! Create backend\.env manually.
        pause
        exit /b 1
    )
) else (
    echo [OK] backend\.env found
)

echo      .env file is ready. Continuing...

:continue_setup
:: ── 3. Python Virtual Environment ──────────────────────────────────────────
echo.
echo [3/9] Setting up Python virtual environment...
if not exist "%VENV_PY%" (
    echo     Creating virtual environment...
    python -m venv "%BACKEND%\venv"
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)

:: ── 4. Install Backend Dependencies ────────────────────────────────────────
echo.
echo [4/9] Installing backend dependencies...
call "%VENV_PY%" -m pip install -q -r "%BACKEND%\requirements.txt"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install backend dependencies
    pause
    exit /b 1
)
echo [OK] Backend dependencies installed

:: ── 5. Install Frontend Dependencies ───────────────────────────────────────
echo.
echo [5/9] Installing frontend dependencies...
if not exist "%FRONTEND%\node_modules" (
    echo     Running npm install...
    pushd "%FRONTEND%"
    call npm install
    popd
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to install frontend dependencies
        pause
        exit /b 1
    )
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies exist
)

:: ── 6. Initialize Database ─────────────────────────────────────────────────
echo.
echo [6/9] Initializing database tables...
echo      Connect to PostgreSQL and create tables...
pushd "%BACKEND%"
call "%VENV_PY%" -m app.db.init_db
popd
if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Database init failed!
    echo     Possible causes:
    echo     1. PostgreSQL is not running
    echo     2. DATABASE_URL in .env is incorrect
    echo.
    if /i "%DOCKER_AVAILABLE%"=="yes" (
        echo     Docker is available. Start PostgreSQL with:
        echo       docker compose up postgres -d
        echo.
        echo     Then re-run this launcher.
    )
    pause
    exit /b 1
)
echo [OK] Database tables initialized

:: ── 7. Seed Database ───────────────────────────────────────────────────────
echo.
echo [7/9] Seeding database with sample data...
set "PYTHONIOENCODING=utf-8"
pushd "%BACKEND%"
call "%VENV_PY%" seed.py
popd
if %ERRORLEVEL% neq 0 (
    echo [!] Seeding failed (non-fatal, continuing...)
) else (
    echo [OK] Database seeded
)

:: ── 8. Start Services ──────────────────────────────────────────────────────
echo.
echo [8/9] Starting services...

:: Kill old processes on ports 8000 and 3000
echo     Cleaning ports...
%SystemRoot%\System32\timeout.exe /t 1 /nobreak >nul

:: Create launcher scripts — avoids quoting issues with paths containing spaces
> "%LAUNCHER_BACKEND%" (
    echo @echo off
    echo title Dushman AI Backend - http://localhost:8000
    echo cd /d "%BACKEND%"
    echo "%VENV_PY%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    echo echo.
    echo echo Backend has stopped. Close this window.
    echo pause
)

> "%LAUNCHER_FRONTEND%" (
    echo @echo off
    echo title Dushman AI Frontend - http://localhost:3000
    echo cd /d "%FRONTEND%"
    echo npm run dev
    echo echo.
    echo echo Frontend has stopped. Close this window.
    echo pause
)

:: Start backend
echo     Starting backend on http://localhost:8000 ...
start "Dushman AI Backend" "%LAUNCHER_BACKEND%"

:: Brief pause so backend can bind
%SystemRoot%\System32\timeout.exe /t 3 /nobreak >nul

:: Start frontend
echo     Starting frontend on http://localhost:3000 ...
start "Dushman AI Frontend" "%LAUNCHER_FRONTEND%"

:: ── 9. Open Browser ────────────────────────────────────────────────────────
echo.
echo [9/9] Opening browser...
%SystemRoot%\System32\timeout.exe /t 5 /nobreak >nul
start http://localhost:3000

:: ── Done ───────────────────────────────────────────────────────────────────
echo.
echo ======================================================
echo     .  Dushman AI is now running!
echo ======================================================
echo.
echo   Frontend:  http://localhost:3000  ^(new window^)
echo   Backend:   http://localhost:8000   ^(new window^)
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Close the service windows to stop the application.
echo   Press any key to close this window.
echo.
pause >nul
endlocal
