#!/usr/bin/env python3
"""
Redis 后台启动脚本
隐秘启动Redis服务器，不显示终端窗口
"""
import os
import sys
import time
import subprocess
import psutil
from pathlib import Path


def print_banner():
    """打印启动横幅"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    🔴 Redis 服务启动器                         ║")
    print("║                                                              ║")
    print("║  📊 内存数据库服务                                             ║")
    print("║  🔄 后台隐秘启动                                               ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")


def check_redis_running():
    """检查Redis是否已经在运行"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] and 'redis-server' in proc.info['name'].lower():
                return proc.info['pid']
        return None
    except Exception:
        return None


def start_redis():
    """启动Redis服务器"""
    print("\n🔍 检查Redis状态...")

    # 检查是否已经运行
    existing_pid = check_redis_running()
    if existing_pid:
        print(f"✅ Redis已在运行 (PID: {existing_pid})")
        return True

    # 查找Redis可执行文件
    redis_paths = [
        "backend/Redis-x64-3.2.100/redis-server.exe",
        "Redis-x64-3.2.100/redis-server.exe",
        "redis-server.exe"
    ]

    redis_exe = None
    for path in redis_paths:
        if os.path.exists(path):
            redis_exe = os.path.abspath(path)
            break

    if not redis_exe:
        print("❌ 未找到Redis可执行文件")
        print("   请确保Redis已正确安装在以下位置之一:")
        for path in redis_paths:
            print(f"   - {path}")
        return False

    print(f"📁 找到Redis: {redis_exe}")

    try:
        # 后台启动Redis (隐藏窗口)
        print("🚀 启动Redis服务器...")

        # Windows下隐藏窗口启动
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            process = subprocess.Popen(
                [redis_exe],
                startupinfo=startupinfo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.path.dirname(redis_exe)
            )
        else:
            # Linux/Mac
            process = subprocess.Popen(
                [redis_exe],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.path.dirname(redis_exe)
            )

        # 等待启动
        print("⏳ 等待Redis启动...")
        time.sleep(2)

        # 验证启动
        redis_pid = check_redis_running()
        if redis_pid:
            print(f"✅ Redis启动成功 (PID: {redis_pid})")
            print("🔄 Redis正在后台运行...")
            return True
        else:
            print("❌ Redis启动失败")
            return False

    except Exception as e:
        print(f"❌ Redis启动异常: {e}")
        return False


def test_redis_connection():
    """测试Redis连接"""
    try:
        import redis
        print("\n🔍 测试Redis连接...")

        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis连接测试成功")
        return True

    except ImportError:
        print("⚠️  Redis Python客户端未安装，跳过连接测试")
        return True
    except Exception as e:
        print(f"❌ Redis连接测试失败: {e}")
        return False


def cleanup_redis_tasks():
    """清理Redis中的残留任务"""
    try:
        import redis
        print("\n🧹 清理Redis残留任务...")

        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()

        # 定义需要清理的队列和键
        cleanup_targets = [
            'celery',  # Celery默认队列
            'text_to_image',  # 文生图任务队列
            'celery-task-meta-*',  # 任务结果缓存
            'unacked',  # 未确认的任务
            'unacked_index',  # 未确认任务索引
            '_kombu.binding.*',  # Kombu绑定信息
        ]

        cleaned_count = 0

        # 清理队列
        for target in cleanup_targets:
            try:
                if '*' in target:
                    # 使用模式匹配删除
                    keys = r.keys(target)
                    if keys:
                        deleted = r.delete(*keys)
                        cleaned_count += deleted
                        print(f"   🗑️  删除 {len(keys)} 个匹配 '{target}' 的键")
                else:
                    # 检查键是否存在
                    if r.exists(target):
                        # 获取键的类型
                        key_type = r.type(target).decode()
                        if key_type == 'list':
                            queue_length = r.llen(target)
                            if queue_length > 0:
                                r.delete(target)
                                cleaned_count += 1
                                print(f"   🗑️  清理队列 '{target}': {queue_length} 个任务")
                        else:
                            # 直接删除非列表类型的键
                            r.delete(target)
                            cleaned_count += 1
                            print(f"   🗑️  删除键 '{target}' (类型: {key_type})")
            except Exception as e:
                print(f"   ⚠️  清理 '{target}' 时出错: {e}")

        # 清理过期的任务结果
        try:
            # 获取所有以celery-task-meta开头的键
            task_meta_keys = r.keys('celery-task-meta-*')
            if task_meta_keys:
                r.delete(*task_meta_keys)
                cleaned_count += len(task_meta_keys)
                print(f"   🗑️  清理任务结果缓存: {len(task_meta_keys)} 个")
        except Exception as e:
            print(f"   ⚠️  清理任务结果缓存时出错: {e}")

        if cleaned_count > 0:
            print(f"✅ Redis清理完成，共清理 {cleaned_count} 个项目")
        else:
            print("✅ Redis无需清理，没有发现残留任务")

        return True

    except ImportError:
        print("⚠️  Redis Python客户端未安装，跳过任务清理")
        return True
    except Exception as e:
        print(f"❌ Redis任务清理失败: {e}")
        return False


def main():
    """主函数"""
    print_banner()

    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    print(f"📁 工作目录: {os.getcwd()}")

    # 启动Redis
    if start_redis():
        # 测试连接
        if test_redis_connection():
            # 清理残留任务
            cleanup_redis_tasks()

        print("\n" + "=" * 60)
        print("🎉 Redis服务启动完成")
        print("=" * 60)
        print("📊 服务状态: 运行中 (后台)")
        print("🔗 连接地址: localhost:6379")
        print("💡 提示: Redis正在后台运行，无需保持此窗口")

        return True
    else:
        print("\n" + "=" * 60)
        print("❌ Redis服务启动失败")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = main()
    if not success:
        input("\n按回车键退出...")
        sys.exit(1)