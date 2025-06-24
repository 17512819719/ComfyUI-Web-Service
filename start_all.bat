@echo off
chcp 65001 >nul
echo ========================================
echo ComfyUI Web Service 一键启动脚本
echo ========================================
echo.

echo 正在启动所有服务...
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

REM 启动后端服务
echo 启动后端服务...
python start_services.py

REM 等待后端服务启动
echo 等待后端服务启动...
timeout /t 5 /nobreak >nul

echo.
echo 所有服务启动完成！
echo.
echo 服务地址:
echo - 前端界面: http://www.HaoSComfyUI.com
echo - 本地访问: http://localhost
echo - FastAPI服务: http://localhost:8000
echo - API文档: http://localhost:8000/docs
echo - ComfyUI服务: http://localhost:8188
echo.
echo 局域网访问:
echo - 其他电脑可以通过 http://[本机IP] 访问
echo.
echo 按任意键退出...
pause >nul 