@echo off
setlocal enabledelayedexpansion

title ComfyUI Task Cleaner

echo.
echo ================================================================
echo                        ComfyUI Task Cleaner
echo ================================================================
echo   Clean up all residual tasks and cache
echo   Reset queue status
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

:: Check cleanup script
if not exist "scripts\cleanup_tasks.py" (
    echo [ERROR] Cleanup script not found: scripts\cleanup_tasks.py
    pause
    exit /b 1
)

echo.
echo [INFO] Starting task cleanup...
echo.

:: Run cleanup script
%PYTHON_EXE% scripts\cleanup_tasks.py

echo.
echo ================================================================
echo Task cleanup completed
echo ================================================================
echo.
pause
