#!/usr/bin/env python3
"""
Celery Worker 启动脚本
在单独终端显示详细日志
"""
import os
import sys
import yaml
import time
import subprocess
import psutil
from pathlib import Path

def print_banner():
    """打印启动横幅"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    🔄 Celery Worker 启动器                  ║")
    print("║                                                              ║")
    print("║  ⚡ 异步任务处理器                                           ║")
    print("║  📊 实时日志监控                                             ║")
    print("║  🎯 队列任务执行                                             ║")
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
    
    # 检查虚拟环境
    venv_python = Path("../.venv/Scripts/python.exe")
    if venv_python.exists():
        print("✅ 找到虚拟环境")
        return str(venv_python.absolute())
    else:
        print("⚠️  未找到虚拟环境，使用系统Python")
        return sys.executable

def check_redis_connection():
    """检查Redis连接"""
    print("\n🔍 检查Redis连接...")
    try:
        import redis

        # 读取配置
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
        print("✅ Redis连接正常")
        return True

    except ImportError:
        print("❌ Redis模块未安装")
        return False
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        print("💡 请确保Redis服务已启动")
        return False

def cleanup_celery_tasks():
    """清理Celery残留任务"""
    print("\n🧹 清理Celery残留任务...")
    try:
        import redis

        # 读取配置
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        redis_config = config.get('redis', {})
        r = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password')
        )

        # 定义需要清理的队列
        queues_to_clean = ['text_to_image', 'celery']
        cleaned_count = 0

        for queue_name in queues_to_clean:
            try:
                if r.exists(queue_name):
                    key_type = r.type(queue_name).decode()
                    if key_type == 'list':
                        queue_length = r.llen(queue_name)
                        if queue_length > 0:
                            r.delete(queue_name)
                            cleaned_count += queue_length
                            print(f"   🗑️  清理队列 '{queue_name}': {queue_length} 个任务")
                    else:
                        r.delete(queue_name)
                        cleaned_count += 1
                        print(f"   🗑️  删除键 '{queue_name}' (类型: {key_type})")
            except Exception as e:
                print(f"   ⚠️  清理队列 '{queue_name}' 时出错: {e}")

        # 清理活跃任务集合
        try:
            if r.exists('celery.active'):
                key_type = r.type('celery.active').decode()
                if key_type == 'set':
                    active_tasks = r.smembers('celery.active')
                    if active_tasks:
                        r.delete('celery.active')
                        print(f"   🗑️  清理活跃任务集合: {len(active_tasks)} 个任务")
                        cleaned_count += len(active_tasks)
                else:
                    r.delete('celery.active')
                    print(f"   🗑️  删除活跃任务键 (类型: {key_type})")
                    cleaned_count += 1
        except Exception as e:
            print(f"   ⚠️  清理活跃任务时出错: {e}")

        # 清理未确认任务
        try:
            unacked_keys = r.keys('unacked*')
            if unacked_keys:
                r.delete(*unacked_keys)
                print(f"   🗑️  清理未确认任务: {len(unacked_keys)} 个键")
                cleaned_count += len(unacked_keys)
        except Exception as e:
            print(f"   ⚠️  清理未确认任务时出错: {e}")

        # 清理任务结果缓存
        try:
            task_meta_keys = r.keys('celery-task-meta-*')
            if task_meta_keys:
                r.delete(*task_meta_keys)
                print(f"   🗑️  清理任务结果缓存: {len(task_meta_keys)} 个")
                cleaned_count += len(task_meta_keys)
        except Exception as e:
            print(f"   ⚠️  清理任务结果缓存时出错: {e}")

        # 清理Kombu相关键
        try:
            kombu_keys = r.keys('_kombu.binding.*')
            if kombu_keys:
                r.delete(*kombu_keys)
                print(f"   🗑️  清理Kombu绑定: {len(kombu_keys)} 个")
                cleaned_count += len(kombu_keys)
        except Exception as e:
            print(f"   ⚠️  清理Kombu绑定时出错: {e}")

        if cleaned_count > 0:
            print(f"✅ Celery任务清理完成，共清理 {cleaned_count} 个项目")
        else:
            print("✅ Celery无需清理，没有发现残留任务")

        return True

    except Exception as e:
        print(f"❌ Celery任务清理失败: {e}")
        return False

def check_celery_imports():
    """检查Celery模块导入"""
    print("\n🔍 检查Celery模块...")
    try:
        # 添加当前目录到Python路径
        import sys
        current_dir = os.getcwd()
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            print(f"📁 添加Python路径: {current_dir}")

        from app.queue.celery_app import get_celery_app
        from app.queue.tasks import execute_text_to_image_task

        celery_app = get_celery_app()
        print(f"✅ Celery应用: {celery_app.main}")
        print(f"✅ 任务模块导入成功")

        # 检查任务注册
        registered_tasks = list(celery_app.tasks.keys())
        text_tasks = [task for task in registered_tasks if 'text_to_image' in task]
        print(f"📋 已注册任务: {len(registered_tasks)} 个")
        print(f"🎨 文生图任务: {text_tasks}")

        return True

    except Exception as e:
        print(f"❌ Celery模块检查失败: {e}")
        print(f"💡 当前工作目录: {os.getcwd()}")
        print(f"💡 Python路径: {sys.path[:3]}...")
        return False

def start_celery_worker(python_exe):
    """启动Celery Worker"""
    print("\n🚀 启动Celery Worker...")
    print("="*60)
    print("🎯 Worker配置:")
    print("   📊 日志级别: INFO")
    print("   🏊 进程池: solo (Windows兼容)")
    print("   📮 监听队列: text_to_image, celery")
    print("   🔄 并发数: 1")
    print("="*60)

    # 确保在backend目录中运行
    current_dir = os.getcwd()
    print(f"📁 当前工作目录: {current_dir}")

    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONPATH'] = current_dir

    # 构建启动命令
    cmd = [
        python_exe, "-m", "celery",
        "-A", "app.queue.celery_app",
        "worker",
        "--loglevel=info",
        "--pool=solo",
        "--queues=text_to_image,celery",
        "--concurrency=1"
    ]

    print(f"🔧 启动命令: {' '.join(cmd)}")
    print(f"🔧 PYTHONPATH: {env.get('PYTHONPATH', 'Not set')}")
    print("\n" + "="*60)
    print("🎯 Celery Worker 启动中...")
    print("="*60)
    print("💡 提示: 按 Ctrl+C 停止Worker")
    print("📊 以下是实时日志输出:")
    print("-"*60)
    
    try:
        # 启动Celery Worker
        process = subprocess.Popen(
            cmd,
            cwd=current_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 实时显示日志
        for line in iter(process.stdout.readline, ''):
            print(line.rstrip())
            
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号...")
        print("🔄 正在优雅关闭Celery Worker...")
        try:
            process.terminate()
            process.wait(timeout=10)
            print("✅ Celery Worker已停止")
        except subprocess.TimeoutExpired:
            print("⚠️  强制终止Celery Worker")
            process.kill()
    except Exception as e:
        print(f"\n❌ Celery Worker启动失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print_banner()
    
    # 检查环境
    python_exe = check_environment()
    if not python_exe:
        return False
    
    # 检查Redis
    if not check_redis_connection():
        print("\n💡 请先启动Redis服务")
        return False

    # 清理残留任务
    cleanup_celery_tasks()

    # 检查Celery
    if not check_celery_imports():
        return False

    print("\n✅ 所有检查通过，准备启动Celery Worker")
    
    # 启动Worker
    return start_celery_worker(python_exe)

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
