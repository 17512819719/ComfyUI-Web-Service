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
    print("=" * 60)
    print("                 Celery Worker 清理器                  ")
    print("=" * 60)
    print("  异步任务处理器")
    print("  实时日志监控")
    print("  队列任务执行")
    print("=" * 60)


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

        # 定义需要清理的队列和模式
        queue_patterns = [
            'text_to_image',
            'image_to_video',
            'celery',
            '*text_to_image*',
            '*image_to_video*',
            '*celery*',
            'kombu.pidbox.*',
            'celeryev.*'
        ]
        cleaned_count = 0

        # 清理所有匹配的队列
        for pattern in queue_patterns:
            try:
                if '*' in pattern:
                    # 模式匹配
                    matching_keys = r.keys(pattern)
                    for key in matching_keys:
                        try:
                            key_name = key.decode() if isinstance(key, bytes) else key
                            key_type = r.type(key).decode()
                            if key_type == 'list':
                                queue_length = r.llen(key)
                                if queue_length > 0:
                                    r.delete(key)
                                    cleaned_count += queue_length
                                    print(f"   🗑️  清理队列 '{key_name}': {queue_length} 个任务")
                            else:
                                r.delete(key)
                                cleaned_count += 1
                                print(f"   🗑️  删除键 '{key_name}' (类型: {key_type})")
                        except Exception as e:
                            print(f"   ⚠️  清理键 '{key}' 时出错: {e}")
                else:
                    # 精确匹配
                    if r.exists(pattern):
                        key_type = r.type(pattern).decode()
                        if key_type == 'list':
                            queue_length = r.llen(pattern)
                            if queue_length > 0:
                                r.delete(pattern)
                                cleaned_count += queue_length
                                print(f"   🗑️  清理队列 '{pattern}': {queue_length} 个任务")
                        else:
                            r.delete(pattern)
                            cleaned_count += 1
                            print(f"   🗑️  删除键 '{pattern}' (类型: {key_type})")
            except Exception as e:
                print(f"   ⚠️  清理模式 '{pattern}' 时出错: {e}")

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

        # 清理未确认任务 - 增强版
        try:
            # 清理所有可能的未确认任务模式
            unacked_patterns = [
                'unacked*',
                '*unacked*',
                'celery.unacked*',
                '*unacknowledged*'
            ]

            for pattern in unacked_patterns:
                try:
                    unacked_keys = r.keys(pattern)
                    if unacked_keys:
                        r.delete(*unacked_keys)
                        print(f"   🗑️  清理未确认任务 '{pattern}': {len(unacked_keys)} 个键")
                        cleaned_count += len(unacked_keys)
                except Exception as e:
                    print(f"   ⚠️  清理未确认任务模式 '{pattern}' 时出错: {e}")
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

        # 强制清理所有Celery相关数据 - 彻底清理
        try:
            # 获取所有键
            all_keys = r.keys('*')
            celery_related_keys = []

            # 过滤出所有Celery相关的键
            for key in all_keys:
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                if any(pattern in key_str.lower() for pattern in [
                    'celery', 'kombu', 'task', 'worker', 'queue',
                    'unacked', 'meta', 'result', 'pidbox', 'heartbeat'
                ]):
                    celery_related_keys.append(key)

            if celery_related_keys:
                r.delete(*celery_related_keys)
                print(f"   🗑️  强制清理所有Celery相关数据: {len(celery_related_keys)} 个键")
                cleaned_count += len(celery_related_keys)

            # 额外清理特定问题任务
            problem_task_id = '62a4c4da-1e6d-4666-9c5e-6d349026c2b0'
            problem_patterns = [
                f'*{problem_task_id}*',
                'celery-task-meta-*',
                '*text_to_image*',
                '*image_to_video*',
                '*execute_text_to_image*',
                '*execute_image_to_video*'
            ]

            for pattern in problem_patterns:
                try:
                    keys = r.keys(pattern)
                    if keys:
                        r.delete(*keys)
                        print(f"   🗑️  清理问题任务模式 '{pattern}': {len(keys)} 个")
                        cleaned_count += len(keys)
                except Exception as e:
                    print(f"   ⚠️  清理问题任务 '{pattern}' 时出错: {e}")
        except Exception as e:
            print(f"   ⚠️  强制清理Celery数据时出错: {e}")

        # 清理所有可能的Worker状态
        try:
            worker_patterns = ['celery@*', '*worker*', '*heartbeat*']
            for pattern in worker_patterns:
                try:
                    keys = r.keys(pattern)
                    if keys:
                        r.delete(*keys)
                        print(f"   🗑️  清理Worker状态 '{pattern}': {len(keys)} 个")
                        cleaned_count += len(keys)
                except Exception as e:
                    print(f"   ⚠️  清理Worker状态 '{pattern}' 时出错: {e}")
        except Exception as e:
            print(f"   ⚠️  清理Worker状态时出错: {e}")

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
        from app.queue.tasks import execute_text_to_image_task, execute_image_to_video_task

        celery_app = get_celery_app()
        print(f"✅ Celery应用: {celery_app.main}")
        print(f"✅ 任务模块导入成功")

        # 检查任务注册
        registered_tasks = list(celery_app.tasks.keys())
        text_tasks = [task for task in registered_tasks if 'text_to_image' in task]
        video_tasks = [task for task in registered_tasks if 'image_to_video' in task]
        print(f"📋 已注册任务: {len(registered_tasks)} 个")
        print(f"🎨 文生图任务: {text_tasks}")
        print(f"🎬 图生视频任务: {video_tasks}")

        return True

    except Exception as e:
        print(f"❌ Celery模块检查失败: {e}")
        print(f"💡 当前工作目录: {os.getcwd()}")
        print(f"💡 Python路径: {sys.path[:3]}...")
        return False

def main():
    """主函数"""
    print_banner()

    # 检查环境
    python_exe = check_environment()
    if not python_exe:
        return False

    # 检查Redis
    if not check_redis_connection():
        print("\n⚠️  Redis不可用，将使用内存模式运行")
        print("💡 内存模式下任务状态不会持久化")

    # 清理残留任务（仅在Redis可用时）
    if check_redis_connection():
        cleanup_celery_tasks()
    else:
        print("\n🧹 跳过任务清理（Redis不可用）")

    # 检查Celery
    if not check_celery_imports():
        return False

    print("\n✅ 所有检查通过，准备启动Celery Worker")


if __name__ == "__main__":
    try:
        success = main()
    except Exception as e:
        print(f"\n❌ 启动脚本异常: {e}")
        input("\n按回车键退出...")
        sys.exit(1)