@echo off
setlocal enabledelayedexpansion
title ComfyUI Distributed Service Launcher

echo.
echo ================================================================
echo                ComfyUI Distributed Service Launcher
echo ================================================================
echo.

:: Check Python environment
echo [1/7] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not installed or not in PATH
    pause
    exit /b 1
)
echo [OK] Python environment ready

:: Check virtual environment
echo.
echo [2/7] Checking virtual environment...
if not exist ".venv\Scripts\activate.bat" (
    echo [WARN] Virtual environment not found, creating...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)
echo [OK] Virtual environment ready

:: Activate virtual environment and install dependencies
echo.
echo [3/7] Installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo [WARN] Dependencies installation may have issues, continuing...
) else (
    echo [OK] Dependencies installed
)

:: Clean task queue
echo.
echo [4/6] Cleaning task queue...
python scripts\cleanup_tasks.py >nul 2>&1
if errorlevel 1 (
    echo [WARN] Task queue cleanup failed
) else (
    echo [OK] Task queue cleaned
)

:: Validate distributed configuration
echo.
echo [5/7] Validating distributed configuration...
python scripts\validate_distributed_config.py
if errorlevel 1 (
    echo [WARN] Distributed configuration validation failed
    set /p "CONTINUE=Continue startup? (y/n): "
    if /i not "!CONTINUE!"=="y" (
        echo [INFO] Startup cancelled
        pause
        exit /b 1
    )
) else (
    echo [OK] Distributed configuration validated
)

echo.
echo [INFO] Starting distributed services...
echo.

:: Start All Service
echo [6/7] Testing distributed functionality...


:: Start Redis in background
echo [INFO] Starting Redis Worker...
start "Redis Server" cmd /k "cd backend && Redis-x64-3.2.100\redis-server.exe Redis-x64-3.2.100\redis.windows.conf" >nul 2>&1
timeout /t 3 /nobreak >nul
echo [OK] Redis startup attempted
echo.

:: Start Celery Worker
echo [INFO] Starting Celery Worker...
start "Celery Worker - ComfyUI Distributed" cmd /k "call .venv\Scripts\activate.bat && echo [INFO] Starting Celery Worker... && cd backend && python -m celery -A app.queue.celery_app worker --loglevel=info --pool=solo"
echo [OK] Celery Worker started in new window
timeout /t 3 /nobreak >nul
echo.

:: Start Client Service
echo [INFO] Starting Client Service
start "Client Service- ComfyUI Distributed" cmd /k "echo [INFO] Starting Client Service... && cd frontend\client && npm run dev"
echo [OK] Client Service started in new window
timeout /t 3 /nobreak >nul
echo.

:: Start Admin Service
echo [INFO] Starting Admin Service
start "Admin Service- ComfyUI Distributed" cmd /k "echo [INFO] Starting Admin Service... && cd frontend\admin && npm run dev"
echo [OK] Admin Service started in new window
timeout /t 3 /nobreak >nul


:: Test distributed functionality
echo.
echo [7/7] Testing distributed functionality...
python test\test_all_fixes.py
if errorlevel 1 (
    echo [WARN] Distributed test failed, but continuing startup...
) else (
    echo [OK] Distributed functionality test passed
)



:: Start FastAPI main service
echo [INFO] Starting FastAPI main service...
echo.
echo ================================================================
echo                        Service Information
echo ================================================================
echo  Main Service: http://localhost:8000
echo  API Docs:     http://localhost:8000/docs
echo  Admin Panel:  http://localhost:5173/
echo  Client:       http://localhost:5174/
echo ================================================================
echo.
echo [INFO] Press Ctrl+C to stop service
echo.

call .venv/Scripts/activate && python -m uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --reload

echo.
echo [INFO] Service stopped
pause
