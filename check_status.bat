@echo off

title ComfyUI Service Status Checker

echo.
echo ================================================================
echo                    ComfyUI Service Status Checker
echo ================================================================
echo.

:: Check Python environment
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [INFO] Using virtual environment Python
) else (
    set "PYTHON_EXE=python"
    echo [INFO] Using system Python
)

echo.

:: Run status check
%PYTHON_EXE% scripts\check_status.py
