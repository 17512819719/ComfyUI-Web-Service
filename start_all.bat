@echo off
setlocal enabledelayedexpansion

title ComfyUI Service Launcher

echo.
echo ================================================================
echo                    ComfyUI Service Launcher
echo ================================================================
echo   Redis - Background startup
echo   Celery Worker - Separate terminal
echo   FastAPI - Main service (current terminal)
echo ================================================================
echo.

:: Check Python environment
echo [INFO] Checking Python environment...
if exist "backend\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=backend\.venv\Scripts\python.exe"
    echo [OK] Found virtual environment: backend\.venv
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [OK] Found virtual environment: .venv
) else (
    set "PYTHON_EXE=python"
    echo [WARN] Using system Python
)

:: Check scripts directory
if not exist "scripts" (
    echo [ERROR] Scripts directory not found
    echo [INFO] Please run this script from project root directory
    pause
    exit /b 1
)

:: Check required scripts
set "MISSING_SCRIPTS="
if not exist "scripts\start_redis.py" (
    set "MISSING_SCRIPTS=!MISSING_SCRIPTS! start_redis.py"
)
if not exist "scripts\start_celery.py" (
    set "MISSING_SCRIPTS=!MISSING_SCRIPTS! start_celery.py"
)
if not exist "scripts\start_fastapi.py" (
    set "MISSING_SCRIPTS=!MISSING_SCRIPTS! start_fastapi.py"
)

if not "!MISSING_SCRIPTS!"=="" (
    echo [ERROR] Missing startup scripts: !MISSING_SCRIPTS!
    pause
    exit /b 1
)

echo [OK] All startup scripts ready
echo.

@REM :: Step 0: Check Database Connection
@REM echo ================================================================
@REM echo Step 0: Check Database Connection
@REM echo ================================================================
@REM echo.

@REM echo [INFO] Testing database connections...
@REM %PYTHON_EXE% backend\test_database.py --check-only 2>nul
@REM if errorlevel 1 (
@REM     echo [WARN] Database connection test failed
@REM     echo [INFO] This might be the first run or database configuration issue
@REM     echo [INFO] The system will continue, but some features may not work properly
@REM     echo.
@REM     set /p "CONTINUE_DB=Continue without database? (y/n): "
@REM     if /i not "!CONTINUE_DB!"=="y" (
@REM         echo [INFO] Please check database configuration in backend\config.yaml
@REM         pause
@REM         exit /b 1
@REM     )
@REM ) else (
@REM     echo [OK] Database connections verified
@REM )

@REM echo.
@REM timeout /t 2 /nobreak >nul

:: Step 1: Start Redis (background)
echo ================================================================
echo Step 1: Start Redis service (background)
echo ================================================================
echo.

echo [INFO] Starting Redis...
%PYTHON_EXE% scripts\start_redis.py
if errorlevel 1 (
    echo.
    echo [ERROR] Redis startup failed
    echo [INFO] Checking if Redis is already running...

    :: Check if Redis is already running
    %PYTHON_EXE% -c "import redis; r=redis.Redis(); r.ping(); print('Redis is already running')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Redis is not running and failed to start
        echo [INFO] Please check Redis configuration or start Redis manually
        echo [INFO] You can also try running: redis-server
        pause
        exit /b 1
    ) else (
        echo [OK] Redis is already running
    )
) else (
    echo [OK] Redis startup completed
)

echo.
timeout /t 2 /nobreak >nul

:: Step 2: Start Celery Worker (new terminal)
echo ================================================================
echo Step 2: Start Celery Worker (new terminal)
echo ================================================================
echo.

echo [INFO] Starting Celery Worker...
start "Celery Worker - ComfyUI" cmd /k "%PYTHON_EXE% scripts\start_celery.py"

echo [OK] Celery Worker terminal opened
echo [INFO] Please check Celery terminal window to confirm startup

:: Wait for user confirmation
echo.
echo [WAIT] Waiting for Celery Worker startup...
echo        Please confirm you see "celery@xxx ready." message in Celery terminal
echo.
set /p "CELERY_READY=Is Celery Worker started successfully? (y/n): "
if /i not "!CELERY_READY!"=="y" (
    echo [ERROR] Celery Worker startup failed or not confirmed
    echo [INFO] Please check Celery terminal window for error messages
    pause
    exit /b 1
)

echo [OK] Celery Worker startup confirmed
timeout /t 1 /nobreak >nul

:: Step 3: Start FastAPI (current terminal)
echo.
echo ================================================================
echo Step 3: Start FastAPI main service (current terminal)
echo ================================================================
echo.

echo [INFO] Starting FastAPI server...
echo [INFO] FastAPI logs will be displayed in this terminal
echo [INFO] Press Ctrl+C to stop the server
echo.

:: Start FastAPI (blocking current terminal)
%PYTHON_EXE% scripts\start_fastapi.py

:: If FastAPI exits, show exit information
echo.
echo ================================================================
echo FastAPI service stopped
echo ================================================================
echo.

:: Ask whether to stop other services
set /p "STOP_ALL=Stop all related services? (y/n): "
if /i "!STOP_ALL!"=="y" (
    echo.
    echo [INFO] Stopping all services...
    %PYTHON_EXE% scripts\stop_services.py
    echo.
    echo [OK] All services stopped
) else (
    echo.
    echo [WARN] Other services are still running:
    echo        - Redis (background)
    echo        - Celery Worker (separate terminal)
    echo.
    echo [INFO] To stop all services, run:
    echo        python scripts\stop_services.py
)

echo.
echo ================================================================
echo Startup script execution completed
echo ================================================================
echo.
pause
