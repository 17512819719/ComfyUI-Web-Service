#!/usr/bin/env python3
"""
服务停止脚本
优雅关闭所有相关服务
"""
import os
import sys
import psutil
from pathlib import Path

def find_process_by_name(name):
    """查找指定名称的进程"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if name.lower() in ' '.join(proc.info['cmdline'] or []).lower():
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes

def stop_redis():
    """停止Redis服务"""
    print("[INFO] Stopping Redis...")
    redis_processes = find_process_by_name('redis-server')
    
    if not redis_processes:
        print("[INFO] Redis is not running")
        return True
    
    for proc in redis_processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"[OK] Redis process {proc.pid} stopped")
        except psutil.TimeoutExpired:
            proc.kill()
            print(f"[WARN] Redis process {proc.pid} killed")
        except Exception as e:
            print(f"[ERROR] Failed to stop Redis process {proc.pid}: {e}")
            return False
    
    return True

def stop_celery():
    """停止Celery Worker"""
    print("[INFO] Stopping Celery Worker...")
    celery_processes = find_process_by_name('celery')
    
    if not celery_processes:
        print("[INFO] Celery Worker is not running")
        return True
    
    for proc in celery_processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"[OK] Celery process {proc.pid} stopped")
        except psutil.TimeoutExpired:
            proc.kill()
            print(f"[WARN] Celery process {proc.pid} killed")
        except Exception as e:
            print(f"[ERROR] Failed to stop Celery process {proc.pid}: {e}")
            return False
    
    return True

def stop_fastapi():
    """停止FastAPI服务"""
    print("[INFO] Stopping FastAPI...")
    uvicorn_processes = find_process_by_name('uvicorn')
    
    if not uvicorn_processes:
        print("[INFO] FastAPI is not running")
        return True
    
    for proc in uvicorn_processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"[OK] FastAPI process {proc.pid} stopped")
        except psutil.TimeoutExpired:
            proc.kill()
            print(f"[WARN] FastAPI process {proc.pid} killed")
        except Exception as e:
            print(f"[ERROR] Failed to stop FastAPI process {proc.pid}: {e}")
            return False
    
    return True

def stop_node_services():
    """停止所有Node.js服务（前端服务）"""
    print("[INFO] Stopping Node.js services...")
    node_processes = find_process_by_name('node')
    vite_processes = [p for p in node_processes if 'vite' in ' '.join(p.info['cmdline'] or []).lower()]
    
    if not vite_processes:
        print("[INFO] No frontend services are running")
        return True
    
    for proc in vite_processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"[OK] Frontend process {proc.pid} stopped")
        except psutil.TimeoutExpired:
            proc.kill()
            print(f"[WARN] Frontend process {proc.pid} killed")
        except Exception as e:
            print(f"[ERROR] Failed to stop frontend process {proc.pid}: {e}")
            return False
    
    return True

def main():
    """停止所有服务"""
    success = True
    
    # 停止FastAPI
    if not stop_fastapi():
        success = False
    
    # 停止Celery Worker
    if not stop_celery():
        success = False
    
    # 停止Redis
    if not stop_redis():
        success = False
    
    # 停止前端服务
    if not stop_node_services():
        success = False
    
    if success:
        print("\n[OK] All services stopped successfully")
    else:
        print("\n[WARN] Some services may still be running")
        print("[INFO] Please check running processes manually")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
