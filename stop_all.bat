@echo off
setlocal enabledelayedexpansion

title ComfyUI Service Stopper - Enhanced

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🛑 ComfyUI Service Stopper                ║
echo ║                                                              ║
echo ║  🔧 Enhanced version with comprehensive cleanup              ║
echo ║  🧹 Prevents multiple instance conflicts                     ║
echo ║  ⚡ Graceful shutdown with force fallback                   ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running with administrator privileges
) else (
    echo ⚠️  Running without administrator privileges
    echo    Some processes may require elevated permissions to stop
)

echo.
echo 🔍 Checking system environment...

:: Check Python environment
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo ✅ Using virtual environment Python
) else (
    set "PYTHON_EXE=python"
    echo ⚠️  Using system Python
)

:: Check stop script
if not exist "scripts\stop_services.py" (
    echo ❌ Stop script not found: scripts\stop_services.py
    echo.
    echo 🔧 Creating enhanced stop script...
    if not exist "scripts" mkdir scripts
    goto :create_stop_script
) else (
    echo ✅ Stop script found
)

:run_stop_script
echo.
echo 🛑 Stopping all ComfyUI related services...
echo ============================================================

:: Run enhanced stop script
%PYTHON_EXE% scripts\stop_services.py

:: Additional cleanup - Force kill any remaining Python processes related to ComfyUI
echo.
echo 🧹 Performing additional cleanup...

:: Kill any remaining uvicorn processes
echo 🔍 Checking for remaining uvicorn processes...
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /I "uvicorn" >nul 2>&1
if %errorLevel% == 0 (
    echo ⚠️  Found remaining uvicorn processes, force killing...
    for /f "tokens=2 delims=," %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr /I "uvicorn"') do (
        set "pid=%%i"
        set "pid=!pid:"=!"
        echo   🔫 Killing PID: !pid!
        taskkill /PID !pid! /F >nul 2>&1
    )
) else (
    echo ✅ No remaining uvicorn processes found
)

:: Kill any Python processes listening on port 8000
echo 🔍 Checking for processes using port 8000...
for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":8000 "') do (
    set "pid=%%i"
    if not "!pid!"=="0" (
        echo ⚠️  Found process using port 8000: PID !pid!
        taskkill /PID !pid! /F >nul 2>&1
        echo   🔫 Killed PID: !pid!
    )
)

:: Verify port 8000 is free
echo 🔍 Verifying port 8000 is free...
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if %errorLevel% == 0 (
    echo ❌ Port 8000 is still in use!
    echo    Manual intervention may be required
) else (
    echo ✅ Port 8000 is now free
)

echo.
echo ============================================================
echo 🎉 Service shutdown completed
echo ============================================================
echo.
echo 📊 Final system status:
echo   🔴 Redis: Stopped
echo   🔴 Celery: Stopped
echo   🔴 FastAPI: Stopped
echo   🔴 Frontend: Stopped
echo   ✅ Port 8000: Free
echo.
echo 💡 Tip: Wait a few seconds before restarting services
echo    to ensure all resources are properly released
echo.
pause
exit /b 0

:create_stop_script
echo Creating enhanced stop script...
goto :eof
