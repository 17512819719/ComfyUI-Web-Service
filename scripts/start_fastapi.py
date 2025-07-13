#!/usr/bin/env python3
"""
FastAPI 主服务启动脚本
在主终端显示详细日志
"""
import os
import sys
import yaml
import time
import subprocess
import psutil
import requests
from pathlib import Path

def print_banner():
    """打印启动横幅"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    🚀 FastAPI 主服务启动器                  ║")
    print("║                                                              ║")
    print("║  🌐 Web API 服务器                                          ║")
    print("║  📊 实时请求日志                                             ║")
    print("║  🔗 ComfyUI 分布式服务                                       ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")

def check_environment():
    """检查运行环境"""
    print("\n🔍 检查运行环境...")
    
    # 检查工作目录
    current_dir = Path.cwd()
    if current_dir.name != "backend":
        backend_dir = current_dir / "backend"
        if backend_dir.exists():
            os.chdir(backend_dir)
            print(f"📁 切换到backend目录: {backend_dir}")
        else:
            print("❌ 未找到backend目录")
            return False
    
    # 检查配置文件
    config_file = Path("config.yaml")
    if not config_file.exists():
        print("❌ 未找到config.yaml配置文件")
        return False
    
    # 检查主应用文件
    main_file = Path("app/main_v2.py")
    if not main_file.exists():
        print("❌ 未找到主应用文件 app/main_v2.py")
        return False
    
    # 检查虚拟环境
    venv_python = Path("../.venv/Scripts/python.exe")
    if venv_python.exists():
        print("✅ 找到虚拟环境")
        return str(venv_python.absolute())
    else:
        print("⚠️  未找到虚拟环境，使用系统Python")
        return sys.executable

def check_dependencies():
    """检查依赖服务"""
    print("\n🔍 检查依赖服务...")
    
    # 检查Redis
    redis_running = False
    try:
        import redis
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        redis_config = config.get('redis', {})
        r = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0)
        )
        r.ping()
        print("✅ Redis: 连接正常")
        redis_running = True
    except Exception as e:
        print(f"❌ Redis: 连接失败 ({e})")
    
    # 检查Celery Worker
    celery_running = False
    try:
        from app.queue.celery_app import get_celery_app
        celery_app = get_celery_app()
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        if active_workers:
            worker_count = len(active_workers)
            print(f"✅ Celery: {worker_count} 个Worker运行中")
            celery_running = True
        else:
            print("⚠️  Celery: 未发现活跃Worker")
    except Exception as e:
        print(f"⚠️  Celery: 检查失败 ({e})")
    
    # 检查ComfyUI
    comfyui_running = False
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        comfyui_config = config.get('comfyui', {})
        host = comfyui_config.get('host', '127.0.0.1')
        port = comfyui_config.get('port', 8188)
        
        response = requests.get(f"http://{host}:{port}/system_stats", timeout=3)
        if response.status_code == 200:
            print(f"✅ ComfyUI: 服务正常 ({host}:{port})")
            comfyui_running = True
        else:
            print(f"⚠️  ComfyUI: 响应异常 ({response.status_code})")
    except Exception as e:
        print(f"⚠️  ComfyUI: 连接失败 ({e})")
    
    return {
        'redis': redis_running,
        'celery': celery_running,
        'comfyui': comfyui_running
    }

def load_server_config():
    """加载服务器配置"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        server_config = config.get('server', {})
        return {
            'host': server_config.get('host', '0.0.0.0'),
            'port': server_config.get('port', 8000),
            'reload': server_config.get('reload', True),
            'workers': server_config.get('workers', 1)
        }
    except Exception as e:
        print(f"⚠️  配置加载失败，使用默认配置: {e}")
        return {
            'host': '0.0.0.0',
            'port': 8000,
            'reload': True,
            'workers': 1
        }

def start_fastapi_server(python_exe, server_config):
    """启动FastAPI服务器"""
    print("\n🚀 启动FastAPI服务器...")
    print("="*60)
    print("🎯 服务器配置:")
    print(f"   🌐 监听地址: {server_config['host']}:{server_config['port']}")
    print(f"   🔄 热重载: {'启用' if server_config['reload'] else '禁用'}")
    print(f"   👥 工作进程: {server_config['workers']}")
    print("="*60)

    # 确保在backend目录中运行
    current_dir = os.getcwd()
    print(f"📁 当前工作目录: {current_dir}")

    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONPATH'] = current_dir

    # 构建启动命令
    cmd = [
        python_exe, "-m", "uvicorn",
        "app.main_v2:app",
        "--host", server_config['host'],
        "--port", str(server_config['port']),
        "--log-level", "info"
    ]

    if server_config['reload']:
        cmd.append("--reload")

    if server_config['workers'] > 1:
        cmd.extend(["--workers", str(server_config['workers'])])

    print(f"🔧 启动命令: {' '.join(cmd)}")
    print(f"🔧 PYTHONPATH: {env.get('PYTHONPATH', 'Not set')}")
    print("\n" + "="*60)
    print("🎯 FastAPI 服务器启动中...")
    print("="*60)
    print("💡 提示: 按 Ctrl+C 停止服务器")
    print("🌐 访问地址:")
    print(f"   - 主页: http://{server_config['host']}:{server_config['port']}")
    print(f"   - API文档: http://{server_config['host']}:{server_config['port']}/docs")
    print(f"   - 客户端: http://{server_config['host']}:{server_config['port']}/client")
    print("📊 以下是实时日志输出:")
    print("-"*60)
    
    try:
        # 启动FastAPI服务器
        process = subprocess.Popen(
            cmd,
            cwd=current_dir,
            env=env
        )
        
        # 等待进程结束
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号...")
        print("🔄 正在优雅关闭FastAPI服务器...")
        try:
            process.terminate()
            process.wait(timeout=10)
            print("✅ FastAPI服务器已停止")
        except subprocess.TimeoutExpired:
            print("⚠️  强制终止FastAPI服务器")
            process.kill()
    except Exception as e:
        print(f"\n❌ FastAPI服务器启动失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print_banner()
    
    # 检查环境
    python_exe = check_environment()
    if not python_exe:
        return False
    
    # 检查依赖服务
    deps = check_dependencies()
    
    # 显示服务状态摘要
    print("\n📊 服务状态摘要:")
    print("-"*30)
    print(f"🔴 Redis:   {'✅ 运行中' if deps['redis'] else '❌ 未运行'}")
    print(f"🔄 Celery:  {'✅ 运行中' if deps['celery'] else '⚠️  未运行'}")
    print(f"🎨 ComfyUI: {'✅ 运行中' if deps['comfyui'] else '⚠️  未运行'}")
    
    if not deps['redis']:
        print("\n⚠️  警告: Redis未运行，某些功能可能不可用")
    if not deps['celery']:
        print("⚠️  警告: Celery Worker未运行，任务处理将不可用")
    if not deps['comfyui']:
        print("⚠️  警告: ComfyUI未运行，图像生成将不可用")
    
    # 加载服务器配置
    server_config = load_server_config()
    
    print("\n✅ 环境检查完成，准备启动FastAPI服务器")
    
    # 启动服务器
    return start_fastapi_server(python_exe, server_config)

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("\n按回车键退出...")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 启动脚本异常: {e}")
        input("\n按回车键退出...")
        sys.exit(1)
