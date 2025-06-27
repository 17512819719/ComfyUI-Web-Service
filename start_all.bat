@echo off
chcp 65001 >nul
echo ========================================
echo ComfyUI Web Service 一键启动脚本
echo ========================================
echo.

REM 自动切换到项目根目录（即包含 backend 目录的目录）
setlocal enabledelayedexpansion
set CURDIR=%cd%
:findroot
if exist "backend\app\main.py" goto rootfound
cd ..
if "%cd%"=="%CURDIR%" (
    echo 错误: 未找到 backend\app\main.py，请确认目录结构！
    pause
    exit /b 1
)
goto findroot
:rootfound

echo 正在启动所有服务...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 启动后端服务（包含数据库迁移、Redis、Celery、FastAPI）
echo 启动后端服务...

cd backend
python start_services.py

REM 等待后端服务启动
echo 等待后端服务启动...
timeout /t 8 /nobreak >nul

pause >nul 