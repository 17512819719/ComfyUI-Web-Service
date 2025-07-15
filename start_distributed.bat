@echo off
chcp 65001 >nul
title ComfyUI 分布式服务启动器

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    ComfyUI 分布式服务启动器                    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: 设置颜色
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "RESET=[0m"

:: 检查Python环境
echo %BLUE%[1/6] 检查Python环境...%RESET%
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Python未安装或未添加到PATH%RESET%
    pause
    exit /b 1
)
echo %GREEN%✅ Python环境正常%RESET%

:: 检查虚拟环境
echo.
echo %BLUE%[2/6] 检查虚拟环境...%RESET%
if not exist "backend\venv\Scripts\activate.bat" (
    echo %YELLOW%⚠️  虚拟环境不存在，正在创建...%RESET%
    cd backend
    python -m venv venv
    if errorlevel 1 (
        echo %RED%❌ 创建虚拟环境失败%RESET%
        pause
        exit /b 1
    )
    cd ..
)
echo %GREEN%✅ 虚拟环境就绪%RESET%

:: 激活虚拟环境并安装依赖
echo.
echo %BLUE%[3/6] 安装依赖包...%RESET%
cd backend
call venv\Scripts\activate.bat
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️  依赖安装可能有问题，继续启动...%RESET%
) else (
    echo %GREEN%✅ 依赖包安装完成%RESET%
)

:: 清理任务队列
echo.
echo %BLUE%[4/6] 清理任务队列...%RESET%
python -c "
import sys
sys.path.append('.')
try:
    from scripts.cleanup_tasks import cleanup_all_tasks
    cleanup_all_tasks()
    print('✅ 任务队列清理完成')
except Exception as e:
    print(f'⚠️  清理任务队列时出错: {e}')
"

:: 检查分布式配置
echo.
echo %BLUE%[5/6] 检查分布式配置...%RESET%
python -c "
import sys
sys.path.append('.')
try:
    from app.core.config_manager import get_config_manager
    config_manager = get_config_manager()
    if config_manager.is_distributed_mode():
        static_nodes = config_manager.get_static_nodes_config()
        print(f'✅ 分布式模式已启用，配置了 {len(static_nodes)} 个节点')
        for node in static_nodes:
            print(f'   - {node[\"node_id\"]}: {node[\"host\"]}:{node[\"port\"]}')
    else:
        print('ℹ️  当前为单机模式')
except Exception as e:
    print(f'❌ 配置检查失败: {e}')
"

:: 测试分布式功能
echo.
echo %BLUE%[6/6] 测试分布式功能...%RESET%
python test_distributed.py
if errorlevel 1 (
    echo %YELLOW%⚠️  分布式测试有问题，但继续启动服务...%RESET%
) else (
    echo %GREEN%✅ 分布式功能测试通过%RESET%
)

echo.
echo %GREEN%🚀 准备启动分布式服务...%RESET%
echo.

:: 启动Redis
echo %BLUE%启动Redis服务...%RESET%
start "Redis Server" /min cmd /c "Redis-x64-3.2.100\redis-server.exe Redis-x64-3.2.100\redis.windows.conf"
timeout /t 3 /nobreak >nul

:: 启动Celery Worker
echo %BLUE%启动Celery Worker...%RESET%
start "Celery Worker" cmd /c "call venv\Scripts\activate.bat && python -m celery -A app.queue.celery_app worker --loglevel=info --pool=solo"
timeout /t 3 /nobreak >nul

:: 启动FastAPI主服务
echo %BLUE%启动FastAPI主服务...%RESET%
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                        服务信息                              ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║ 主服务地址: http://localhost:8000                            ║
echo ║ API文档:   http://localhost:8000/docs                       ║
echo ║ 管理界面:   http://localhost:8000/admin                      ║
echo ║ 客户端:    http://localhost:8000/client                     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo %GREEN%按 Ctrl+C 停止服务%RESET%
echo.

python -m uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --reload

echo.
echo %YELLOW%服务已停止%RESET%
pause
