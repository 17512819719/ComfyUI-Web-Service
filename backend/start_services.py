#!/usr/bin/env python3
import subprocess
import sys
import os
import time
import signal
import threading
import requests
import yaml
from pathlib import Path

# 设置工作目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def load_config():
    """加载配置文件"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"警告: 无法加载配置文件 config.yaml: {e}")
        return {}

def auto_migrate_database():
    """自动迁移数据库表结构"""
    print("\n[数据库] 正在自动迁移/更新表结构...")
    try:
        from app.admin_api.models import Base
        from app.admin_api.utils import engine
        Base.metadata.create_all(bind=engine)
        print("✓ 数据库表结构已自动同步")
        return True
    except Exception as e:
        print(f"✗ 数据库自动迁移失败: {e}")
        return False

def check_redis():
    """检查Redis是否运行"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        return True
    except:
        return False

def find_redis_executable():
    """查找Redis可执行文件"""
    redis_paths = [
        os.path.join("Redis-x64-3.2.100", "redis-server.exe"),
        "redis-server.exe",
        "redis-server"
    ]
    
    for path in redis_paths:
        if os.path.exists(path):
            return path
    return None

def start_redis():
    """启动Redis服务"""
    print("\n[Redis] 正在启动Redis服务...")
    
    if check_redis():
        print("✓ Redis服务已在运行")
        return None
    
    redis_executable = find_redis_executable()
    if not redis_executable:
        print("✗ 未找到Redis可执行文件")
        print("请确保Redis已安装，或者将Redis文件夹放在backend目录下")
        return None
    
    print(f"找到Redis可执行文件: {redis_executable}")
    
    try:
        redis_cwd = os.path.dirname(redis_executable) or os.getcwd()
        redis_process = subprocess.Popen(
            [redis_executable],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=redis_cwd
        )
        
        print("等待Redis服务启动...")
        for i in range(15):
            if check_redis():
                print("✓ Redis服务启动成功")
                return redis_process
            time.sleep(1)
            print(f"等待中... ({i+1}/15)")
        
        if redis_process.poll() is not None:
            stdout, stderr = redis_process.communicate()
            print(f"✗ Redis启动失败")
            print(f"stdout: {stdout.decode()}")
            print(f"stderr: {stderr.decode()}")
        else:
            print("✗ Redis服务启动超时")
        
        return None
    except Exception as e:
        print(f"✗ 启动Redis失败: {e}")
        return None

def check_comfyui():
    """检查ComfyUI是否运行"""
    config = load_config()
    port = config.get('comfyui', {}).get('port', 8188)
    
    endpoints = ["/system_stats", "/history", "/object_info", "/", "/api/object_info"]
    session = requests.Session()
    session.trust_env = False
    
    for endpoint in endpoints:
        try:
            url = f"http://localhost:{port}{endpoint}"
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            continue
    return False

def check_comfyui_service():
    """检测ComfyUI服务状态"""
    print("\n[ComfyUI] 正在检测ComfyUI服务状态...")
    
    config = load_config()
    port = config.get('comfyui', {}).get('port', 8188)
    
    if check_comfyui():
        print(f"✓ ComfyUI服务正在运行 (端口 {port})")
        return True
    else:
        print(f"✗ ComfyUI服务未运行 (端口 {port})")
        print("\n故障排除建议:")
        print("1. 确认ComfyUI是否已启动")
        print("2. 检查ComfyUI是否在正确的端口上运行")
        print("3. 检查防火墙设置")
        print("4. 尝试手动访问: http://localhost:8188")
        print("\n启动ComfyUI的方法:")
        print("方法1 - 命令行启动:")
        print("   1. 进入ComfyUI安装目录")
        print("   2. 运行: python main.py --listen 0.0.0.0 --port 8188")
        print("方法2 - 使用ComfyUI启动脚本:")
        print("   1. 双击ComfyUI目录中的 run_nvidia.bat 或 run_cpu.bat")
        print("   2. 或者运行: python main.py")
        print("\n配置检查:")
        print(f"   当前配置的端口: {port}")
        return False

def start_celery_worker():
    """启动Celery Worker"""
    print("\n[Celery] 正在启动Celery Worker...")

    try:
        # 清空队列
        print("清空Celery队列...")
        subprocess.run([
            sys.executable, "-m", "celery", "-A", "app.tasks", "purge", "-f"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✓ Celery队列已清空")
    except Exception as e:
        print(f"清空Celery队列失败: {e}")

    try:
        worker_process = subprocess.Popen([
            sys.executable, "-m", "celery", "-A", "app.tasks", "worker",
            "--loglevel=info", "--pool=solo", "--concurrency=1"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(3)
        
        if worker_process.poll() is None:
            print("✓ Celery Worker启动成功")
            return worker_process
        else:
            print("✗ Celery Worker启动失败")
            return None
    except Exception as e:
        print(f"✗ 启动Celery Worker失败: {e}")
        return None

def start_fastapi():
    """启动FastAPI服务"""
    print("\n[FastAPI] 正在启动FastAPI服务...")
    try:
        api_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", "8000"
        ])
        
        time.sleep(3)
        
        if api_process.poll() is None:
            print("✓ FastAPI服务启动成功")
            return api_process
        else:
            print("✗ FastAPI服务启动失败")
            return None
    except Exception as e:
        print(f"✗ 启动FastAPI失败: {e}")
        return None

def check_fastapi():
    """检查FastAPI是否运行"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_frontend():
    """启动前端Vite开发服务器"""
    print("\n[前端] 正在启动前端管理后台 (Vite)...")
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'admin'))
    if not os.path.exists(frontend_dir):
        print(f"✗ 未找到前端目录: {frontend_dir}")
        return None
    try:
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )
        time.sleep(3)
        print("✓ 前端管理后台已启动 (http://localhost:5173)")
        return process
    except Exception as e:
        print(f"✗ 启动前端失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 50)
    print("ComfyUI Web Service 完整启动脚本")
    print("=" * 50)
    
    processes = []
    
    try:
        # 1. 数据库迁移
        if not auto_migrate_database():
            print("数据库迁移失败，是否继续启动其他服务? (y/n): ", end="")
            choice = input().lower()
            if choice != 'y':
                return
        
        # 2. 启动Redis
        redis_process = start_redis()
        if redis_process:
            processes.append(("Redis", redis_process))
        
        # 3. 检测ComfyUI服务状态
        if not check_comfyui_service():
            print("\nComfyUI服务未运行，请先启动ComfyUI服务后再运行此脚本")
            print("启动顺序建议:")
            print("1. 先启动ComfyUI服务")
            print("2. 再运行此脚本启动其他服务")
            return
        
        # 4. 启动Celery Worker
        worker_process = start_celery_worker()
        if worker_process:
            processes.append(("Celery Worker", worker_process))
        else:
            print("Celery Worker启动失败，请检查依赖")
            return
        
        # 5. 启动FastAPI
        api_process = start_fastapi()
        if api_process:
            processes.append(("FastAPI", api_process))
        else:
            print("FastAPI启动失败")
            return
        
        # 6. 启动前端
        frontend_process = start_frontend()
        if frontend_process:
            processes.append(("前端Vite", frontend_process))
        else:
            print("前端启动失败，请检查Node.js和依赖")
        
        # 等待FastAPI完全启动
        print("\n等待FastAPI服务完全启动...")
        for i in range(10):
            if check_fastapi():
                break
            time.sleep(1)
        
        config = load_config()
        comfyui_port = config.get('comfyui', {}).get('port', 8188)
        
        print("\n" + "=" * 50)
        print("🎉 所有服务启动成功！")
        print("=" * 50)
        print("服务地址:")
        print(f"  • FastAPI服务: http://localhost:8000")
        print(f"  • API文档: http://localhost:8000/docs")
        print(f"  • 管理后台页面: http://localhost:5173")
        print(f"  • ComfyUI服务: http://localhost:{comfyui_port}")
        print()
        print()
        print("按 Ctrl+C 停止所有服务")
        print("=" * 50)
        
        # 等待用户中断
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在停止所有服务...")
    
    except Exception as e:
        print(f"启动过程中出错: {e}")
    
    finally:
        # 停止所有进程
        print("\n正在停止所有服务...")
        for name, process in processes:
            print(f"正在停止 {name}...")
            try:
                process.terminate()
                print(f"等待 {name} 停止...")
                
                try:
                    process.wait(timeout=10)
                    print(f"✓ {name} 已停止")
                except subprocess.TimeoutExpired:
                    print(f"强制停止 {name}...")
                    process.kill()
                    process.wait(timeout=5)
                    print(f"✓ {name} 已强制停止")
                    
            except Exception as e:
                print(f"停止 {name} 时出错: {e}")
                try:
                    process.kill()
                except:
                    pass
        
        print("所有服务已停止")

if __name__ == "__main__":
    main() 