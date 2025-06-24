#!/usr/bin/env python3
"""
ComfyUI Web Service 停止脚本
用于停止Redis、Celery Worker和FastAPI服务
"""

import subprocess
import sys
import os
import time
import signal
import psutil
import requests
import yaml
from pathlib import Path

def load_config():
    """加载配置文件"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"警告: 无法加载配置文件 config.yaml: {e}")
        return {}

def find_process_by_name(name_patterns):
    """根据进程名模式查找进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # 检查进程名
            if any(pattern.lower() in proc.info['name'].lower() for pattern in name_patterns):
                processes.append(proc)
                continue
            
            # 检查命令行
            if proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline']).lower()
                if any(pattern.lower() in cmdline for pattern in name_patterns):
                    processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes

def find_process_by_port(port):
    """根据端口号查找进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            connections = proc.info['connections']
            for conn in connections:
                if conn.laddr.port == port:
                    processes.append(proc)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes

def stop_process(process, name, timeout=10):
    """停止单个进程"""
    try:
        print(f"正在停止 {name} (PID: {process.pid})...")
        
        # 尝试优雅停止
        process.terminate()
        
        # 等待进程结束
        try:
            process.wait(timeout=timeout)
            print(f"✓ {name} 已停止")
            return True
        except psutil.TimeoutExpired:
            # 强制杀死进程
            print(f"强制停止 {name}...")
            process.kill()
            process.wait(timeout=5)
            print(f"✓ {name} 已强制停止")
            return True
            
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"停止 {name} 时出错: {e}")
        return False

def stop_redis():
    """停止Redis服务"""
    print("=== 停止Redis服务 ===")
    
    # 查找Redis进程
    redis_processes = find_process_by_name(['redis-server', 'redis'])
    
    if not redis_processes:
        print("未找到运行中的Redis进程")
        return True
    
    success = True
    for proc in redis_processes:
        if not stop_process(proc, "Redis"):
            success = False
    
    return success

def stop_celery_worker():
    """停止Celery Worker"""
    print("\n=== 停止Celery Worker ===")
    
    # 只匹配命令行中包含 'celery' 且包含 'worker' 的进程
    celery_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ''
            if 'celery' in cmdline and 'worker' in cmdline:
                celery_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    if not celery_processes:
        print("未找到运行中的Celery Worker进程")
        return True
    
    success = True
    for proc in celery_processes:
        if not stop_process(proc, "Celery Worker"):
            success = False
    
    return success

def stop_fastapi():
    """停止FastAPI服务"""
    print("\n=== 停止FastAPI服务 ===")
    
    # 查找使用8000端口的进程
    fastapi_processes = find_process_by_port(8000)
    
    if not fastapi_processes:
        print("未找到运行在端口8000的FastAPI进程")
        return True
    
    success = True
    for proc in fastapi_processes:
        if not stop_process(proc, "FastAPI"):
            success = False
    
    return success

def stop_uvicorn():
    """停止Uvicorn进程"""
    print("\n=== 停止Uvicorn进程 ===")
    
    # 查找Uvicorn进程
    uvicorn_processes = find_process_by_name(['uvicorn'])
    
    if not uvicorn_processes:
        print("未找到运行中的Uvicorn进程")
        return True
    
    success = True
    for proc in uvicorn_processes:
        if not stop_process(proc, "Uvicorn"):
            success = False
    
    return success

def check_services_status():
    """检查服务状态"""
    print("=== 检查服务状态 ===")
    
    # 检查Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✗ Redis 仍在运行")
    except:
        print("✓ Redis 已停止")
    
    # 检查ComfyUI（仅显示状态，不停止）
    config = load_config()
    comfyui_config = config.get('comfyui', {})
    port = comfyui_config.get('port', 8188)
    try:
        response = requests.get(f"http://localhost:{port}/system_stats", timeout=3)
        if response.status_code == 200:
            print(f"✓ ComfyUI 仍在运行 (端口 {port}) - 请手动停止")
        else:
            print(f"✓ ComfyUI 已停止 (端口 {port})")
    except:
        print(f"✓ ComfyUI 已停止 (端口 {port})")
    
    # 检查端口8000
    fastapi_processes = find_process_by_port(8000)
    if fastapi_processes:
        print("✗ FastAPI 仍在运行")
    else:
        print("✓ FastAPI 已停止")
    
    # 检查Celery Worker
    celery_processes = find_process_by_name(['celery', 'worker'])
    if celery_processes:
        print("✗ Celery Worker 仍在运行")
    else:
        print("✓ Celery Worker 已停止")

def main():
    """主函数"""
    print("=== ComfyUI Web Service 停止脚本 ===")
    print()
    
    # 检查是否以管理员权限运行（Windows）
    if os.name == 'nt':
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        
        if not is_admin:
            print("注意: 建议以管理员权限运行此脚本以确保能够停止所有进程")
            print()
    
    try:
        # 停止各个服务
        redis_ok = stop_redis()
        celery_ok = stop_celery_worker()
        fastapi_ok = stop_fastapi()
        uvicorn_ok = stop_uvicorn()
        
        print("\n" + "="*50)
        print("停止结果:")
        print(f"Redis: {'✓' if redis_ok else '✗'}")
        print(f"Celery Worker: {'✓' if celery_ok else '✗'}")
        print(f"FastAPI: {'✓' if fastapi_ok else '✗'}")
        print(f"Uvicorn: {'✓' if uvicorn_ok else '✗'}")
        print("ComfyUI: 需要手动停止")
        
        # 等待一下再检查状态
        print("\n等待进程完全停止...")
        time.sleep(2)
        
        # 检查最终状态
        check_services_status()
        
        print("\n=== 停止完成 ===")
        print("注意: ComfyUI服务需要手动停止")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"停止服务时出错: {e}")

if __name__ == "__main__":
    main() 