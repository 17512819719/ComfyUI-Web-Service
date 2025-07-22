@echo off
setlocal enabledelayedexpansion

:: Check Python environment
if exist "backend\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=backend\.venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:: Check Node.js environment
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    exit /b 1
)

:: Check scripts directory and required scripts
if not exist "scripts" (
    echo [ERROR] Scripts directory not found
    exit /b 1
)

set "MISSING_SCRIPTS="
if not exist "scripts\start_redis.py" set "MISSING_SCRIPTS=!MISSING_SCRIPTS! start_redis.py"
if not exist "scripts\start_celery.py" set "MISSING_SCRIPTS=!MISSING_SCRIPTS! start_celery.py"
if not exist "scripts\start_fastapi.py" set "MISSING_SCRIPTS=!MISSING_SCRIPTS! start_fastapi.py"
if not exist "scripts\start_client.py" set "MISSING_SCRIPTS=!MISSING_SCRIPTS! start_client.py"
if not exist "scripts\start_admin.py" set "MISSING_SCRIPTS=!MISSING_SCRIPTS! start_admin.py"

if not "!MISSING_SCRIPTS!"=="" (
    echo [ERROR] Missing startup scripts: !MISSING_SCRIPTS!
    exit /b 1
)

:: Start Redis (background)
echo [INFO] 正在启动 Redis...
%PYTHON_EXE% scripts\start_redis.py
if errorlevel 1 (
    echo [INFO] 检查 Redis 是否已在运行...
    %PYTHON_EXE% -c "import redis; r=redis.Redis(); r.ping()" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Redis 启动失败且未在运行
        echo [INFO] 尝试直接启动 Redis 服务器...
        start /min "Redis Server" backend\Redis-x64-3.2.100\redis-server.exe backend\Redis-x64-3.2.100\redis.windows.conf
        timeout /t 2 /nobreak >nul
        %PYTHON_EXE% -c "import redis; r=redis.Redis(); r.ping()" >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Redis 服务器启动失败
            echo [INFO] 请检查 Redis 配置或手动启动 Redis
            exit /b 1
        ) else (
            echo [OK] Redis 服务器已成功启动
        )
    ) else (
        echo [OK] Redis 已在运行
    )
) else (
    echo [OK] Redis 启动成功
)

:: Wait for Redis to fully start
timeout /t 2 /nobreak >nul

:: Start Celery Worker (minimized window)
echo [INFO] 正在启动 Celery Worker...
start /min "Celery Worker - ComfyUI" cmd /c "%PYTHON_EXE% scripts\start_celery.py"

:: Wait for Celery to initialize
timeout /t 3 /nobreak >nul

:: Start Client Frontend (minimized window)
echo [INFO] 正在启动客户端前端...
start /min "Client Frontend - ComfyUI" cmd /c "%PYTHON_EXE% scripts\start_client.py"

:: Start Admin Frontend (minimized window)
echo [INFO] 正在启动管理后台...
@REM start /min "Admin Frontend - ComfyUI" cmd /c "%PYTHON_EXE% scripts\start_admin.py"

:: Wait for frontends to initialize
timeout /t 2 /nobreak >nul

:: Start FastAPI (minimized window)
echo [INFO] 正在启动 FastAPI 服务...
start /min "FastAPI - ComfyUI" cmd /c "%PYTHON_EXE% scripts\start_fastapi.py"

echo [INFO] 所有服务已在最小化窗口中启动。
echo [INFO] 要停止所有服务，请运行: python scripts\stop_services.py 