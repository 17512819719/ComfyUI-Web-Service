#!/usr/bin/env python3
"""
服务状态检查脚本
快速检查所有服务的运行状态
"""
import os
import sys
import yaml
import psutil
import requests
from pathlib import Path

def print_banner():
    """打印状态横幅"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    📊 服务状态检查器                        ║")
    print("║                                                              ║")
    print("║  🔍 快速检查所有服务状态                                     ║")
    print("║  📈 实时监控面板                                             ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")

def check_redis():
    """检查Redis状态"""
    try:
        import redis
        
        # 切换到backend目录读取配置
        current_dir = Path.cwd()
        if current_dir.name != "backend":
            backend_dir = current_dir / "backend"
            if backend_dir.exists():
                os.chdir(backend_dir)
        
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        redis_config = config.get('redis', {})
        r = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password')
        )
        
        r.ping()
        
        # 获取队列信息
        queue_info = {
            'celery': r.llen('celery'),
            'text_to_image': r.llen('text_to_image')
        }
        
        return {
            'status': 'running',
            'host': redis_config.get('host', 'localhost'),
            'port': redis_config.get('port', 6379),
            'queues': queue_info
        }
        
    except ImportError:
        return {'status': 'module_missing', 'error': 'Redis模块未安装'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def check_celery():
    """检查Celery状态"""
    try:
        # 切换到backend目录
        current_dir = Path.cwd()
        if current_dir.name != "backend":
            backend_dir = current_dir / "backend"
            if backend_dir.exists():
                os.chdir(backend_dir)
        
        from app.queue.celery_app import get_celery_app
        
        celery_app = get_celery_app()
        inspect = celery_app.control.inspect()
        
        # 检查活跃worker
        active_workers = inspect.active()
        registered_tasks = inspect.registered()
        
        if active_workers:
            worker_info = {}
            for worker, tasks in active_workers.items():
                worker_info[worker] = {
                    'active_tasks': len(tasks),
                    'registered_tasks': len(registered_tasks.get(worker, []))
                }
            
            return {
                'status': 'running',
                'workers': worker_info,
                'worker_count': len(active_workers)
            }
        else:
            return {'status': 'no_workers', 'error': '未发现活跃Worker'}
            
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def check_fastapi():
    """检查FastAPI状态"""
    try:
        # 切换到backend目录读取配置
        current_dir = Path.cwd()
        if current_dir.name != "backend":
            backend_dir = current_dir / "backend"
            if backend_dir.exists():
                os.chdir(backend_dir)
        
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        server_config = config.get('server', {})
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 8000)
        
        # 尝试连接健康检查端点
        test_url = f"http://localhost:{port}/health" if host == '0.0.0.0' else f"http://{host}:{port}/health"
        
        response = requests.get(test_url, timeout=3)
        if response.status_code == 200:
            return {
                'status': 'running',
                'host': host,
                'port': port,
                'url': test_url
            }
        else:
            return {
                'status': 'error',
                'error': f'HTTP {response.status_code}'
            }
            
    except requests.exceptions.ConnectionError:
        return {'status': 'not_running', 'error': '连接被拒绝'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def check_comfyui():
    """检查ComfyUI状态"""
    try:
        # 切换到backend目录读取配置
        current_dir = Path.cwd()
        if current_dir.name != "backend":
            backend_dir = current_dir / "backend"
            if backend_dir.exists():
                os.chdir(backend_dir)
        
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        comfyui_config = config.get('comfyui', {})
        host = comfyui_config.get('host', '127.0.0.1')
        port = comfyui_config.get('port', 8188)
        
        response = requests.get(f"http://{host}:{port}/system_stats", timeout=3)
        if response.status_code == 200:
            return {
                'status': 'running',
                'host': host,
                'port': port
            }
        else:
            return {
                'status': 'error',
                'error': f'HTTP {response.status_code}'
            }
            
    except requests.exceptions.ConnectionError:
        return {'status': 'not_running', 'error': '连接被拒绝'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def get_process_count():
    """获取相关进程数量"""
    patterns = ['redis-server', 'celery', 'uvicorn', 'python.*main_v2']
    count = 0
    
    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            proc_name = proc.info['name'] or ''
            cmdline = ' '.join(proc.info['cmdline'] or [])
            
            for pattern in patterns:
                if pattern.lower() in proc_name.lower() or pattern.lower() in cmdline.lower():
                    count += 1
                    break
    except Exception:
        pass
    
    return count

def print_status_table(services):
    """打印状态表格"""
    print("\n📊 服务状态总览:")
    print("="*70)
    
    status_icons = {
        'running': '✅',
        'not_running': '❌',
        'no_workers': '⚠️ ',
        'error': '❌',
        'module_missing': '⚠️ '
    }
    
    for service_name, info in services.items():
        status = info.get('status', 'unknown')
        icon = status_icons.get(status, '❓')
        
        print(f"{icon} {service_name:12} ", end="")
        
        if status == 'running':
            if service_name == 'Redis':
                print(f"运行中 ({info['host']}:{info['port']})")
                for queue, count in info['queues'].items():
                    print(f"{'':16} 队列 {queue}: {count} 个任务")
            elif service_name == 'Celery':
                print(f"运行中 ({info['worker_count']} 个Worker)")
                for worker, worker_info in info['workers'].items():
                    print(f"{'':16} {worker}: {worker_info['active_tasks']} 活跃任务")
            elif service_name == 'FastAPI':
                print(f"运行中 ({info['host']}:{info['port']})")
            elif service_name == 'ComfyUI':
                print(f"运行中 ({info['host']}:{info['port']})")
        else:
            error_msg = info.get('error', status)
            print(f"异常: {error_msg}")

def main():
    """主函数"""
    print_banner()
    
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"\n📁 项目目录: {os.getcwd()}")
    
    # 检查所有服务
    print("\n🔍 正在检查服务状态...")
    
    services = {
        'Redis': check_redis(),
        'Celery': check_celery(),
        'FastAPI': check_fastapi(),
        'ComfyUI': check_comfyui()
    }
    
    # 显示状态表格
    print_status_table(services)
    
    # 统计信息
    running_count = sum(1 for info in services.values() if info.get('status') == 'running')
    total_processes = get_process_count()
    
    print(f"\n📈 统计信息:")
    print(f"   🟢 运行中服务: {running_count}/4")
    print(f"   🔄 相关进程数: {total_processes}")
    
    # 整体状态
    if running_count == 4:
        print(f"\n🎉 所有服务运行正常！")
    elif running_count >= 2:
        print(f"\n⚠️  部分服务运行中，请检查异常服务")
    else:
        print(f"\n❌ 大部分服务未运行，请启动服务")

if __name__ == "__main__":
    try:
        main()
        input("\n按回车键退出...")
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断")
    except Exception as e:
        print(f"\n❌ 检查脚本异常: {e}")
        input("\n按回车键退出...")
        sys.exit(1)
