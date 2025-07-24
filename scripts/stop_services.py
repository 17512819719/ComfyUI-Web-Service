#!/usr/bin/env python3
"""
增强版服务停止脚本
优雅关闭所有相关服务，防止多实例冲突
"""
import os
import sys
import time
import signal
import psutil
import socket
from pathlib import Path
from typing import List, Dict, Optional

class ServiceStopper:
    """增强版服务停止器"""

    def __init__(self):
        self.stopped_services = []
        self.failed_services = []

    def print_status(self, message: str, status: str = "INFO"):
        """打印状态信息"""
        icons = {
            "INFO": "🔍",
            "OK": "✅",
            "WARN": "⚠️",
            "ERROR": "❌",
            "KILL": "🔫",
            "CLEAN": "🧹"
        }
        icon = icons.get(status, "ℹ️")
        print(f"{icon} [{status}] {message}")

    def find_processes_by_name(self, name: str) -> List[psutil.Process]:
        """查找指定名称的进程"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if name.lower() in cmdline.lower():
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return processes

    def find_processes_by_port(self, port: int) -> List[psutil.Process]:
        """查找占用指定端口的进程"""
        processes = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                try:
                    proc = psutil.Process(conn.pid)
                    processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return processes

    def is_port_free(self, port: int) -> bool:
        """检查端口是否空闲"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False

    def stop_process_gracefully(self, proc: psutil.Process, service_name: str, timeout: int = 10) -> bool:
        """优雅停止进程"""
        try:
            self.print_status(f"Stopping {service_name} (PID: {proc.pid})")

            # 首先尝试优雅停止
            proc.terminate()

            # 等待进程结束
            try:
                proc.wait(timeout=timeout)
                self.print_status(f"{service_name} stopped gracefully", "OK")
                return True
            except psutil.TimeoutExpired:
                # 超时后强制杀死
                self.print_status(f"{service_name} timeout, force killing...", "WARN")
                proc.kill()
                proc.wait(timeout=5)
                self.print_status(f"{service_name} force killed", "KILL")
                return True

        except psutil.NoSuchProcess:
            self.print_status(f"{service_name} already stopped", "OK")
            return True
        except Exception as e:
            self.print_status(f"Failed to stop {service_name}: {e}", "ERROR")
            return False

    def stop_redis(self) -> bool:
        """停止Redis服务"""
        self.print_status("Stopping Redis services...")
        redis_processes = self.find_processes_by_name('redis-server')

        if not redis_processes:
            self.print_status("Redis is not running", "OK")
            return True

        success = True
        for proc in redis_processes:
            if not self.stop_process_gracefully(proc, "Redis"):
                success = False

        if success:
            self.stopped_services.append("Redis")
        else:
            self.failed_services.append("Redis")

        return success

    def stop_celery(self) -> bool:
        """停止Celery Worker"""
        self.print_status("Stopping Celery Worker...")
        celery_processes = self.find_processes_by_name('celery')

        if not celery_processes:
            self.print_status("Celery Worker is not running", "OK")
            return True

        success = True
        for proc in celery_processes:
            if not self.stop_process_gracefully(proc, "Celery Worker"):
                success = False

        if success:
            self.stopped_services.append("Celery")
        else:
            self.failed_services.append("Celery")

        return success

    def stop_fastapi(self) -> bool:
        """停止FastAPI服务 - 增强版，防止多实例问题"""
        self.print_status("Stopping FastAPI services...")

        # 查找所有uvicorn进程
        uvicorn_processes = self.find_processes_by_name('uvicorn')

        # 查找所有占用8000端口的进程
        port_processes = self.find_processes_by_port(8000)

        # 查找所有包含main_v2的Python进程
        main_processes = self.find_processes_by_name('main_v2')

        # 合并所有相关进程，去重
        all_processes = []
        seen_pids = set()

        for proc_list in [uvicorn_processes, port_processes, main_processes]:
            for proc in proc_list:
                if proc.pid not in seen_pids:
                    all_processes.append(proc)
                    seen_pids.add(proc.pid)

        if not all_processes:
            self.print_status("No FastAPI processes found", "OK")
            return True

        self.print_status(f"Found {len(all_processes)} FastAPI-related processes")

        success = True
        for proc in all_processes:
            try:
                cmdline = ' '.join(proc.cmdline())
                self.print_status(f"Stopping process: {cmdline[:80]}...")
                if not self.stop_process_gracefully(proc, f"FastAPI (PID: {proc.pid})"):
                    success = False
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 验证端口8000是否已释放
        time.sleep(1)  # 等待一秒让端口释放
        if self.is_port_free(8000):
            self.print_status("Port 8000 is now free", "OK")
        else:
            self.print_status("Port 8000 is still in use", "WARN")
            # 强制杀死占用8000端口的进程
            remaining_processes = self.find_processes_by_port(8000)
            for proc in remaining_processes:
                self.print_status(f"Force killing process on port 8000: PID {proc.pid}", "KILL")
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        if success:
            self.stopped_services.append("FastAPI")
        else:
            self.failed_services.append("FastAPI")

        return success

    def stop_node_services(self) -> bool:
        """停止所有Node.js服务（前端服务）"""
        self.print_status("Stopping Node.js services...")
        node_processes = self.find_processes_by_name('node')
        vite_processes = [p for p in node_processes if 'vite' in ' '.join(p.cmdline()).lower()]

        if not vite_processes:
            self.print_status("No frontend services are running", "OK")
            return True

        success = True
        for proc in vite_processes:
            if not self.stop_process_gracefully(proc, "Frontend Service"):
                success = False

        if success:
            self.stopped_services.append("Frontend")
        else:
            self.failed_services.append("Frontend")

        return success

    def cleanup_python_processes(self) -> bool:
        """清理所有相关的Python进程"""
        self.print_status("Performing comprehensive Python process cleanup...", "CLEAN")

        # 查找所有可能相关的Python进程
        python_keywords = [
            'uvicorn', 'celery', 'main_v2', 'comfyui', 'fastapi',
            'app.main_v2', 'backend', 'worker'
        ]

        cleaned_processes = []
        for keyword in python_keywords:
            processes = self.find_processes_by_name(keyword)
            for proc in processes:
                try:
                    if proc.pid not in [p.pid for p in cleaned_processes]:
                        cleaned_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if not cleaned_processes:
            self.print_status("No additional Python processes to clean", "OK")
            return True

        self.print_status(f"Found {len(cleaned_processes)} additional processes to clean")

        success = True
        for proc in cleaned_processes:
            try:
                cmdline = ' '.join(proc.cmdline())
                if any(keyword in cmdline.lower() for keyword in python_keywords):
                    self.print_status(f"Cleaning process: {cmdline[:60]}...", "CLEAN")
                    if not self.stop_process_gracefully(proc, f"Python Process (PID: {proc.pid})", timeout=5):
                        success = False
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return success

    def verify_cleanup(self) -> bool:
        """验证清理结果"""
        self.print_status("Verifying cleanup results...")

        issues = []

        # 检查端口8000
        if not self.is_port_free(8000):
            issues.append("Port 8000 is still in use")

        # 检查是否还有相关进程
        remaining_processes = []
        for keyword in ['uvicorn', 'celery', 'main_v2']:
            processes = self.find_processes_by_name(keyword)
            remaining_processes.extend(processes)

        if remaining_processes:
            issues.append(f"{len(remaining_processes)} related processes still running")

        if issues:
            for issue in issues:
                self.print_status(issue, "WARN")
            return False
        else:
            self.print_status("All services successfully stopped", "OK")
            return True

def main():
    """增强版主函数 - 停止所有服务"""
    print("🚀 Starting enhanced service shutdown process...")
    print("=" * 60)

    stopper = ServiceStopper()
    overall_success = True

    # 第一阶段：优雅停止主要服务
    stopper.print_status("Phase 1: Graceful service shutdown", "INFO")

    services = [
        ("FastAPI", stopper.stop_fastapi),
        ("Celery", stopper.stop_celery),
        ("Redis", stopper.stop_redis),
        ("Frontend", stopper.stop_node_services)
    ]

    for service_name, stop_func in services:
        try:
            if not stop_func():
                overall_success = False
        except Exception as e:
            stopper.print_status(f"Error stopping {service_name}: {e}", "ERROR")
            overall_success = False

    # 第二阶段：清理残留进程
    stopper.print_status("Phase 2: Cleanup remaining processes", "INFO")
    if not stopper.cleanup_python_processes():
        overall_success = False

    # 第三阶段：验证清理结果
    stopper.print_status("Phase 3: Verification", "INFO")
    verification_success = stopper.verify_cleanup()

    # 输出最终报告
    print("\n" + "=" * 60)
    print("📊 SHUTDOWN REPORT")
    print("=" * 60)

    if stopper.stopped_services:
        stopper.print_status(f"Successfully stopped: {', '.join(stopper.stopped_services)}", "OK")

    if stopper.failed_services:
        stopper.print_status(f"Failed to stop: {', '.join(stopper.failed_services)}", "ERROR")

    if overall_success and verification_success:
        stopper.print_status("All services stopped successfully! 🎉", "OK")
        stopper.print_status("System is ready for restart", "INFO")
        return 0
    else:
        stopper.print_status("Some issues occurred during shutdown", "WARN")
        stopper.print_status("Manual intervention may be required", "WARN")
        return 1

if __name__ == '__main__':
    sys.exit(main())
