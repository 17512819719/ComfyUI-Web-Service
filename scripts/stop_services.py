#!/usr/bin/env python3
"""
服务停止脚本
优雅关闭所有相关服务
"""
import os
import sys
import time
import psutil
import signal
from pathlib import Path

def print_banner():
    """打印停止横幅"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    🛑 服务停止器                            ║")
    print("║                                                              ║")
    print("║  🔄 优雅关闭所有服务                                         ║")
    print("║  🧹 清理系统资源                                             ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")

def find_processes_by_name(name_patterns):
    """根据进程名模式查找进程"""
    processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name']:
                proc_name = proc.info['name'].lower()
                cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                
                for pattern in name_patterns:
                    if pattern.lower() in proc_name or pattern.lower() in cmdline:
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                        })
                        break
    except Exception as e:
        print(f"⚠️  查找进程时出错: {e}")
    
    return processes

def stop_process(pid, name, timeout=10):
    """停止指定进程"""
    try:
        proc = psutil.Process(pid)
        print(f"🔄 正在停止 {name} (PID: {pid})...")
        
        # 尝试优雅关闭
        proc.terminate()
        
        # 等待进程结束
        try:
            proc.wait(timeout=timeout)
            print(f"✅ {name} 已优雅停止")
            return True
        except psutil.TimeoutExpired:
            print(f"⚠️  {name} 未在 {timeout} 秒内停止，强制终止...")
            proc.kill()
            proc.wait(timeout=5)
            print(f"✅ {name} 已强制停止")
            return True
            
    except psutil.NoSuchProcess:
        print(f"✅ {name} 进程已不存在")
        return True
    except Exception as e:
        print(f"❌ 停止 {name} 失败: {e}")
        return False

def stop_redis():
    """停止Redis服务"""
    print("\n🔴 停止Redis服务...")
    redis_processes = find_processes_by_name(['redis-server'])
    
    if not redis_processes:
        print("✅ 未发现Redis进程")
        return True
    
    success = True
    for proc in redis_processes:
        if not stop_process(proc['pid'], f"Redis ({proc['name']})", timeout=5):
            success = False
    
    return success

def stop_celery():
    """停止Celery Worker"""
    print("\n🔄 停止Celery Worker...")
    celery_processes = find_processes_by_name(['celery', 'python.*celery'])
    
    if not celery_processes:
        print("✅ 未发现Celery进程")
        return True
    
    success = True
    for proc in celery_processes:
        if not stop_process(proc['pid'], f"Celery ({proc['name']})", timeout=15):
            success = False
    
    return success

def stop_fastapi():
    """停止FastAPI服务"""
    print("\n🚀 停止FastAPI服务...")
    fastapi_processes = find_processes_by_name(['uvicorn', 'python.*uvicorn', 'main_v2'])
    
    if not fastapi_processes:
        print("✅ 未发现FastAPI进程")
        return True
    
    success = True
    for proc in fastapi_processes:
        if not stop_process(proc['pid'], f"FastAPI ({proc['name']})", timeout=10):
            success = False
    
    return success

def cleanup_temp_files():
    """清理临时文件"""
    print("\n🧹 清理临时文件...")
    
    cleanup_patterns = [
        "*.pyc",
        "__pycache__",
        "*.log",
        "celerybeat-schedule*",
        "*.pid"
    ]
    
    cleaned_count = 0
    try:
        # 切换到项目根目录
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        
        for pattern in cleanup_patterns:
            for file_path in project_root.rglob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        cleaned_count += 1
                    elif file_path.is_dir() and pattern == "__pycache__":
                        import shutil
                        shutil.rmtree(file_path)
                        cleaned_count += 1
                except Exception as e:
                    print(f"⚠️  清理 {file_path} 失败: {e}")
        
        if cleaned_count > 0:
            print(f"✅ 清理了 {cleaned_count} 个临时文件/目录")
        else:
            print("✅ 无需清理临时文件")
            
    except Exception as e:
        print(f"⚠️  清理过程出错: {e}")

def check_remaining_processes():
    """检查剩余的相关进程"""
    print("\n🔍 检查剩余进程...")
    
    all_patterns = ['redis-server', 'celery', 'uvicorn', 'main_v2']
    remaining = find_processes_by_name(all_patterns)
    
    if remaining:
        print("⚠️  发现剩余进程:")
        for proc in remaining:
            print(f"   - PID {proc['pid']}: {proc['name']}")
            print(f"     命令: {proc['cmdline']}")
        return False
    else:
        print("✅ 所有相关进程已停止")
        return True

def main():
    """主函数"""
    print_banner()
    
    print("\n🔍 开始停止所有服务...")
    
    # 停止服务的顺序很重要
    services = [
        ("FastAPI", stop_fastapi),
        ("Celery", stop_celery),
        ("Redis", stop_redis)
    ]
    
    success_count = 0
    for service_name, stop_func in services:
        try:
            if stop_func():
                success_count += 1
            time.sleep(1)  # 给进程一点时间完全停止
        except Exception as e:
            print(f"❌ 停止 {service_name} 时出错: {e}")
    
    # 清理临时文件
    cleanup_temp_files()
    
    # 检查剩余进程
    all_clean = check_remaining_processes()
    
    # 显示结果
    print("\n" + "="*60)
    print("📊 停止结果摘要:")
    print("="*60)
    print(f"✅ 成功停止: {success_count}/{len(services)} 个服务")
    
    if all_clean:
        print("🎉 所有服务已完全停止")
        print("💡 系统资源已释放")
    else:
        print("⚠️  部分进程可能仍在运行")
        print("💡 建议手动检查任务管理器")
    
    return all_clean

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n{'✅ 停止完成' if success else '⚠️  停止完成（有警告）'}")
        input("\n按回车键退出...")
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断停止过程")
    except Exception as e:
        print(f"\n❌ 停止脚本异常: {e}")
        input("\n按回车键退出...")
        sys.exit(1)
