@echo off
setlocal enabledelayedexpansion

title ComfyUI Service Stopper

echo.
echo ================================================================
echo                        ComfyUI Service Stopper
echo ================================================================
echo   Gracefully shutdown all services
echo   Clean up system resources
echo ================================================================
echo.

:: Check Python environment
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [OK] Using virtual environment Python
) else (
    set "PYTHON_EXE=python"
    echo [WARN] Using system Python
)

:: Check stop script
if not exist "scripts\stop_services.py" (
    echo [ERROR] Stop script not found: scripts\stop_services.py
    pause
    exit /b 1
)

echo.
echo [INFO] Stopping all ComfyUI related services...
echo.

:: Run stop script
%PYTHON_EXE% scripts\stop_services.py

echo.
echo ================================================================
echo Stop script execution completed
echo ================================================================
echo.
pause
