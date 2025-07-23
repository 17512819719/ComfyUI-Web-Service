@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title ComfyUI 简化启动器

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    ComfyUI 简化启动器                        ║
echo ║                   (推荐使用此脚本)                           ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: 设置颜色
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "RESET=[0m"

:: 检查Python环境
echo %BLUE%[1/4] 检查环境...%RESET%
if not exist "backend\venv\Scripts\python.exe" (
    echo %RED%❌ 虚拟环境不存在，请先运行 setup.bat%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ 环境检查通过%RESET%

:: 进入backend目录并激活虚拟环境
cd backend
call .\venv\Scripts\activate.bat

:: 清理任务队列
echo.
echo %BLUE%[2/4] 清理任务队列...%RESET%
python -c "
try:
    from scripts.cleanup_tasks import cleanup_all_tasks
    cleanup_all_tasks()
    print('✅ 任务队列清理完成')
except Exception as e:
    print(f'⚠️  清理任务队列时出错: {e}')
"

:: 检查配置
echo.
echo %BLUE%[3/4] 检查配置...%RESET%
cd ..
python scripts\start_fastapi.py --check-only
if errorlevel 1 (
    echo %RED%❌ 配置检查失败%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ 配置检查通过%RESET%

:: 启动服务
echo.
echo %BLUE%[4/4] 启动服务...%RESET%
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                        服务信息                              ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║ 主服务地址: http://localhost:8001                            ║
echo ║ API文档:   http://localhost:8001/docs                       ║
echo ║ 管理界面:   http://localhost:8001/admin                      ║
echo ║ 客户端:    http://localhost:8001/client                     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo %GREEN%按 Ctrl+C 停止服务%RESET%
echo.

cd backend
python scripts\start_fastapi.py

echo.
echo %YELLOW%服务已停止%RESET%
pause
