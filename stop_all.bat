@echo off
chcp 65001 >nul
echo ========================================
echo ComfyUI Web Service 一键停止脚本
echo ========================================
echo.

echo 正在停止所有服务...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查是否在正确的目录
if not exist "main.py" (
    echo 错误: 请在项目根目录下运行此脚本
    pause
    exit /b 1
)

REM 停止前清空Redis队列，避免Celery遗留任务
if exist "Redis-x64-3.2.100\redis-cli.exe" (
    echo 正在清空Redis队列...
    Redis-x64-3.2.100\redis-cli.exe -n 0 FLUSHDB
    echo Redis队列已清空。
) else (
    echo 未找到redis-cli.exe，跳过Redis清理。
)

REM 停止后端服务
echo 停止后端服务...
python stop_services.py

echo.
echo 所有服务停止完成！
echo.
echo 按任意键退出...
pause >nul 