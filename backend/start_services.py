#!/usr/bin/env python3
"""
ComfyUI Web Service 启动脚本
用于启动Redis、Celery Worker和FastAPI服务，检测ComfyUI服务状态
"""

import http
import subprocess
import sys
import os
import time
import signal
import threading
import requests
import yaml
from pathlib import Path

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def load_config():
    """加载配置文件"""
    try:
        with open(os.path.join(os.path.dirname(__file__), 'config.yaml'), 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"警告: 无法加载配置文件 config.yaml: {e}")
        return {}

def check_redis():
    """检查Redis是否运行"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        return True
    except:
        return False

def check_comfyui():
    """检查ComfyUI是否运行"""
    config = load_config()
    port = config.get('comfyui', {}).get('port', 8188)
    
    # 尝试多个可能的ComfyUI API端点
    endpoints = [
        "/system_stats",  # 系统状态
        "/history",       # 历史记录
        "/object_info",   # 对象信息
        "/",             # 根路径
        "/api/object_info"  # API对象信息
    ]
    
    # 创建session，禁用代理
    session = requests.Session()
    session.trust_env = False  # 禁用环境变量中的代理设置
    
    for endpoint in endpoints:
        try:
            url = f"http://localhost:{port}{endpoint}"
            print(f"尝试连接: {url}")
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ 成功连接到ComfyUI端点: {endpoint}")
                return True
            else:
                print(f"端点 {endpoint} 返回状态码: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"连接失败: {endpoint} - 无法连接到服务器")
        except requests.exceptions.Timeout:
            print(f"连接超时: {endpoint} - 请求超时")
        except Exception as e:
            print(f"连接错误: {endpoint} - {str(e)}")
    
    return False

def find_redis_executable():
    """查找Redis可执行文件"""
    # 检查项目目录下的Redis
    redis_paths = [
        os.path.join(os.path.dirname(__file__), "Redis-x64-3.2.100", "redis-server.exe"),
        os.path.join(os.path.dirname(__file__), "redis-server.exe"),
        os.path.join(os.path.dirname(__file__), "redis-server")
    ]
    
    for path in redis_paths:
        if os.path.exists(path):
            return path
    
    return None

def start_redis():
    """启动Redis服务"""
    print("正在启动Redis服务...")
    
    # 查找Redis可执行文件
    redis_executable = find_redis_executable()
    if not redis_executable:
        print("✗ 未找到Redis可执行文件")
        print("请确保Redis已安装，或者将Redis文件夹放在项目根目录下")
        return None
    
    print(f"找到Redis可执行文件: {redis_executable}")
    
    try:
        # 启动Redis服务器
        redis_cwd = os.path.dirname(redis_executable)
        if not redis_cwd:
            redis_cwd = os.getcwd()  # 如果 dirname 返回空字符串，使用当前工作目录
        
        redis_process = subprocess.Popen(
            [redis_executable],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=redis_cwd
        )
        
        # 等待Redis启动
        print("等待Redis服务启动...")
        for i in range(15):  # 增加等待时间到15秒
            if check_redis():
                print("✓ Redis服务启动成功")
                return redis_process
            time.sleep(1)
            print(f"等待中... ({i+1}/15)")
        
        # 如果Redis没有启动成功，检查进程状态
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

def check_comfyui_service():
    """检测ComfyUI服务状态"""
    print("正在检测ComfyUI服务状态...")
    
    config = load_config()
    comfyui_config = config.get('comfyui', {})
    port = comfyui_config.get('port', 8188)
    
    print(f"检测端口: {port}")
    print(f"检测地址: http://localhost:{port}")
    
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
        print(f"   当前配置的输出目录: {comfyui_config.get('output_dir', '未设置')}")
        return False

def start_celery_worker():
    """启动Celery Worker"""
    print("正在启动Celery Worker...")

    # 启动前清空队列
    try:
        print("清空Celery队列...")
        subprocess.run([
            sys.executable, "-m", "celery", "-A", "app.tasks", "purge", "-f"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✓ Celery队列已清空")
    except Exception as e:
        print(f"清空Celery队列失败: {e}")

    try:
        # 启动Celery Worker（现在在根目录）
        worker_process = subprocess.Popen([
            sys.executable, "-m", "celery", "-A", "app.tasks", "worker",
            "--loglevel=info", "--pool=solo", "--concurrency=1"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 等待一下确保worker启动
        time.sleep(3)
        
        # 检查worker是否启动成功
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
    print("正在启动FastAPI服务...")
    try:
        # 启动FastAPI（禁用reload模式以避免文件监控问题）
        api_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", "8000"
            # 移除 --reload 参数以避免文件监控导致的服务重启
        ])
        
        # 等待一下确保服务启动
        time.sleep(3)
        
        # 检查服务是否启动成功
        if api_process.poll() is None:
            print("✓ FastAPI服务启动成功")
            return api_process
        else:
            print("✗ FastAPI服务启动失败")
            return None
    except Exception as e:
        print(f"✗ 启动FastAPI失败: {e}")
        return None

def main():
    """主函数"""
    print("=== ComfyUI Web Service 启动脚本 ===")
    print()
    
    # 检查当前目录
    # if not os.path.exists("main.py"):
    #     print("错误: 请在项目根目录下运行此脚本")
    #     sys.exit(1)
    
    processes = []
    
    try:
        # 1. 启动Redis
        redis_process = start_redis()
        if redis_process:
            processes.append(("Redis", redis_process))
        else:
            print("\nRedis启动失败，请尝试以下解决方案:")
            print("1. 确保Redis文件夹在项目根目录下")
            print("2. 手动启动Redis: Redis-x64-3.2.100\\redis-server.exe")
            print("3. 或者安装Redis到系统PATH中")
            print("\n是否继续启动其他服务? (y/n): ", end="")
            choice = input().lower()
            if choice != 'y':
                return
        
        # 2. 检测ComfyUI服务状态
        if not check_comfyui_service():
            print("\nComfyUI服务未运行，请先启动ComfyUI服务后再运行此脚本")
            print("启动顺序建议:")
            print("1. 先启动ComfyUI服务")
            print("2. 再运行此脚本启动其他服务")
            return
        
        # 3. 启动Celery Worker
        worker_process = start_celery_worker()
        if worker_process:
            processes.append(("Celery Worker", worker_process))
        else:
            print("Celery Worker启动失败，请检查依赖")
            return
        
        # 4. 启动FastAPI
        api_process = start_fastapi()
        if api_process:
            processes.append(("FastAPI", api_process))
        else:
            print("FastAPI启动失败")
            return
        
        config = load_config()
        comfyui_config = config.get('comfyui', {})
        port = comfyui_config.get('port', 8188)
        
        print()
        print("=== 所有服务启动成功 ===")
        print("FastAPI服务地址: http://localhost:8000")
        print("API文档地址: http://localhost:8000/docs")
        print(f"ComfyUI服务地址: http://localhost:{port}")
        print()
        print("按 Ctrl+C 停止所有服务")
        
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
                # 尝试优雅停止
                process.terminate()
                print(f"等待 {name} 停止...")
                
                # 等待进程结束
                try:
                    process.wait(timeout=10)
                    print(f"✓ {name} 已停止")
                except subprocess.TimeoutExpired:
                    # 强制杀死进程
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