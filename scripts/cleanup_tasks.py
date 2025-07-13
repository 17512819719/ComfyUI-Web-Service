#!/usr/bin/env python3
"""
任务清理脚本
清理Redis中的所有残留任务和缓存
"""
import os
import sys
import yaml
import time
from pathlib import Path

def print_banner():
    """打印清理横幅"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    🧹 任务清理器                            ║")
    print("║                                                              ║")
    print("║  🗑️  清理Redis残留任务                                       ║")
    print("║  🔄 重置队列状态                                             ║")
    print("║  💾 清理缓存数据                                             ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════════╝")

def load_redis_config():
    """加载Redis配置"""
    try:
        # 切换到backend目录
        current_dir = Path.cwd()
        if current_dir.name != "backend":
            backend_dir = current_dir / "backend"
            if backend_dir.exists():
                os.chdir(backend_dir)
        
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        redis_config = config.get('redis', {})
        return {
            'host': redis_config.get('host', 'localhost'),
            'port': redis_config.get('port', 6379),
            'db': redis_config.get('db', 0),
            'password': redis_config.get('password')
        }
    except Exception as e:
        print(f"❌ 加载Redis配置失败: {e}")
        return None

def connect_redis(config):
    """连接Redis"""
    try:
        import redis
        
        r = redis.Redis(
            host=config['host'],
            port=config['port'],
            db=config['db'],
            password=config['password']
        )
        
        r.ping()
        print(f"✅ 连接Redis成功: {config['host']}:{config['port']}")
        return r
        
    except ImportError:
        print("❌ Redis模块未安装")
        return None
    except Exception as e:
        print(f"❌ 连接Redis失败: {e}")
        return None

def cleanup_all_tasks(redis_client):
    """清理所有任务相关数据"""
    print("\n🧹 开始全面清理...")
    
    cleanup_items = [
        # 队列清理
        {
            'name': 'Celery队列',
            'keys': ['celery', 'text_to_image'],
            'type': 'list'
        },
        # 活跃任务
        {
            'name': '活跃任务集合',
            'keys': ['celery.active'],
            'type': 'set'
        },
        # 未确认任务
        {
            'name': '未确认任务',
            'keys': ['unacked*'],
            'type': 'pattern'
        },
        # 任务结果缓存
        {
            'name': '任务结果缓存',
            'keys': ['celery-task-meta-*'],
            'type': 'pattern'
        },
        # Kombu绑定
        {
            'name': 'Kombu绑定',
            'keys': ['_kombu.binding.*'],
            'type': 'pattern'
        },
        # 其他Celery相关键
        {
            'name': 'Celery状态',
            'keys': ['celery.stats', 'celery.heartbeat.*', 'celery.worker.*'],
            'type': 'pattern'
        }
    ]
    
    total_cleaned = 0
    
    for item in cleanup_items:
        print(f"\n🔍 清理 {item['name']}...")
        item_cleaned = 0
        
        for key_pattern in item['keys']:
            try:
                if item['type'] == 'pattern':
                    # 模式匹配删除
                    keys = redis_client.keys(key_pattern)
                    if keys:
                        deleted = redis_client.delete(*keys)
                        item_cleaned += deleted
                        print(f"   🗑️  删除 {len(keys)} 个匹配 '{key_pattern}' 的键")
                elif item['type'] == 'list':
                    # 列表队列清理
                    queue_length = redis_client.llen(key_pattern)
                    if queue_length > 0:
                        redis_client.delete(key_pattern)
                        item_cleaned += 1
                        print(f"   🗑️  清理列表 '{key_pattern}': {queue_length} 个项目")
                elif item['type'] == 'set':
                    # 集合清理
                    set_size = redis_client.scard(key_pattern)
                    if set_size > 0:
                        redis_client.delete(key_pattern)
                        item_cleaned += 1
                        print(f"   🗑️  清理集合 '{key_pattern}': {set_size} 个项目")
                else:
                    # 直接删除
                    if redis_client.exists(key_pattern):
                        redis_client.delete(key_pattern)
                        item_cleaned += 1
                        print(f"   🗑️  删除键 '{key_pattern}'")
                        
            except Exception as e:
                print(f"   ⚠️  清理 '{key_pattern}' 时出错: {e}")
        
        if item_cleaned == 0:
            print(f"   ✅ {item['name']} 无需清理")
        
        total_cleaned += item_cleaned
    
    return total_cleaned

def show_redis_info(redis_client):
    """显示Redis信息"""
    print("\n📊 Redis状态信息:")
    print("-" * 40)
    
    try:
        info = redis_client.info()
        print(f"   📈 已用内存: {info.get('used_memory_human', 'N/A')}")
        print(f"   🔗 连接数: {info.get('connected_clients', 'N/A')}")
        print(f"   📊 数据库键数: {redis_client.dbsize()}")
        
        # 检查剩余的相关键
        remaining_keys = []
        patterns = ['celery*', 'text_to_image*', '_kombu*', 'unacked*']
        for pattern in patterns:
            keys = redis_client.keys(pattern)
            remaining_keys.extend(keys)
        
        if remaining_keys:
            print(f"   ⚠️  剩余相关键: {len(remaining_keys)} 个")
            for key in remaining_keys[:5]:  # 只显示前5个
                print(f"      - {key.decode() if isinstance(key, bytes) else key}")
            if len(remaining_keys) > 5:
                print(f"      ... 还有 {len(remaining_keys) - 5} 个")
        else:
            print("   ✅ 无剩余相关键")
            
    except Exception as e:
        print(f"   ❌ 获取Redis信息失败: {e}")

def main():
    """主函数"""
    print_banner()
    
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"\n📁 项目目录: {os.getcwd()}")
    
    # 加载配置
    redis_config = load_redis_config()
    if not redis_config:
        return False
    
    # 连接Redis
    redis_client = connect_redis(redis_config)
    if not redis_client:
        return False
    
    # 显示清理前状态
    show_redis_info(redis_client)
    
    # 确认清理
    print("\n⚠️  警告: 此操作将清理所有Celery相关的任务和缓存数据")
    confirm = input("是否继续清理? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ 用户取消清理操作")
        return False
    
    # 执行清理
    cleaned_count = cleanup_all_tasks(redis_client)
    
    # 显示清理后状态
    print("\n" + "="*60)
    print("📊 清理结果:")
    print("="*60)
    print(f"🗑️  总共清理: {cleaned_count} 个项目")
    
    show_redis_info(redis_client)
    
    print("\n🎉 任务清理完成!")
    print("💡 现在可以重新启动Celery Worker")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("\n按回车键退出...")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断清理过程")
    except Exception as e:
        print(f"\n❌ 清理脚本异常: {e}")
        input("\n按回车键退出...")
        sys.exit(1)
