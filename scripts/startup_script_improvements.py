import yaml
import requests
from pathlib import Path


def validate_distributed_config():
    """验证分布式配置"""
    print("\n🔧 验证分布式配置...")
    print("=" * 50)

    try:
        # 检查是否为分布式模式
        with open('backend/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        distributed_config = config.get('distributed', {})
        is_distributed = distributed_config.get('enabled', False)

        if not is_distributed:
            print("✅ 单机模式，跳过分布式配置验证")
            return True

        print("🌐 分布式模式，开始验证配置...")

        # 验证分布式配置结构
        nodes_config = config.get('nodes', {})
        if not nodes_config:
            print("❌ 缺少nodes配置节")
            return False

        discovery_mode = nodes_config.get('discovery_mode', 'static')
        print(f"📡 发现模式: {discovery_mode}")

        static_nodes = nodes_config.get('static_nodes', [])
        if discovery_mode in ['static', 'hybrid'] and not static_nodes:
            print("❌ 静态发现模式下必须配置static_nodes")
            return False

        print(f"📊 配置的静态节点数: {len(static_nodes)}")

        # 验证节点配置
        node_ids = set()
        for i, node in enumerate(static_nodes):
            node_id = node.get('node_id')
            if not node_id:
                print(f"❌ 节点{i+1}: 缺少node_id")
                return False

            if node_id in node_ids:
                print(f"❌ 节点ID重复: {node_id}")
                return False
            node_ids.add(node_id)

            host = node.get('host')
            port = node.get('port')
            if not host or not port:
                print(f"❌ 节点{node_id}: 缺少host或port")
                return False

            print(f"  ✅ {node_id}: {host}:{port}")

        print("✅ 分布式配置验证通过")
        return True

    except Exception as e:
        print(f"❌ 分布式配置验证失败: {e}")
        return False


def check_dependencies():
    """检查依赖服务"""
    print("\n🔍 检查依赖服务...")
    print("=" * 50)

    # 检查Redis
    redis_running = False
    try:
        import redis
        with open('backend/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        redis_config = config.get('redis', {})
        r = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0)
        )
        r.ping()
        print("✅ Redis: 连接正常")
        redis_running = True
    except Exception as e:
        print(f"❌ Redis: 连接失败 ({e})")
    
    # 检查Celery Worker
    celery_running = False
    try:
        from app.queue.celery_app import get_celery_app
        celery_app = get_celery_app()
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        if active_workers:
            worker_count = len(active_workers)
            print(f"✅ Celery: {worker_count} 个Worker运行中")
            celery_running = True
        else:
            print("⚠️  Celery: 未发现活跃Worker")
    except Exception as e:
        print(f"⚠️  Celery: 检查失败 ({e})")
    
    # 检查ComfyUI - 支持分布式模式
    comfyui_running = False
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 检查是否为分布式模式
        distributed_config = config.get('distributed', {})
        is_distributed = distributed_config.get('enabled', False)

        if is_distributed:
            # 分布式模式：检查所有节点
            nodes_config = config.get('nodes', {})
            static_nodes = nodes_config.get('static_nodes', [])

            if not static_nodes:
                print("⚠️  ComfyUI: 分布式模式但没有配置节点")
            else:
                print(f"🌐 ComfyUI: 分布式模式 ({len(static_nodes)} 个节点)")
                healthy_count = 0

                for node in static_nodes:
                    node_id = node.get('node_id', 'unknown')
                    host = node.get('host', '127.0.0.1')
                    port = node.get('port', 8188)

                    try:
                        response = requests.get(f"http://{host}:{port}/system_stats", timeout=3)
                        if response.status_code == 200:
                            print(f"  ✅ {node_id}: 服务正常 ({host}:{port})")
                            healthy_count += 1
                        else:
                            print(f"  ⚠️  {node_id}: 响应异常 ({response.status_code}) - {host}:{port}")
                    except Exception as e:
                        print(f"  ❌ {node_id}: 连接失败 - {host}:{port} ({str(e)[:30]})")

                if healthy_count > 0:
                    print(f"✅ ComfyUI: {healthy_count}/{len(static_nodes)} 个节点可用")
                    comfyui_running = True

                    # 显示节点状态汇总
                    print("   📊 节点状态汇总:")
                    for node in static_nodes:
                        node_id = node.get('node_id', 'unknown')
                        host = node.get('host', 'unknown')
                        port = node.get('port', 'unknown')
                        capabilities = node.get('capabilities', [])

                        # 检查这个节点是否健康（简单检查）
                        try:
                            response = requests.get(f"http://{host}:{port}/system_stats", timeout=2)
                            status = "🟢 在线" if response.status_code == 200 else "🟡 异常"
                        except:
                            status = "🔴 离线"

                        print(f"     {status} {node_id} ({host}:{port}) - {', '.join(capabilities)}")
                else:
                    print("❌ ComfyUI: 所有分布式节点都不可用")
        else:
            # 单机模式：检查配置文件中的ComfyUI实例
            comfyui_config = config.get('comfyui', {})
            host = comfyui_config.get('host', '127.0.0.1')
            port = comfyui_config.get('port', 8188)

            response = requests.get(f"http://{host}:{port}/system_stats", timeout=3)
            if response.status_code == 200:
                print(f"✅ ComfyUI: 服务正常 ({host}:{port}) [单机模式]")
                comfyui_running = True
            else:
                print(f"⚠️  ComfyUI: 响应异常 ({response.status_code}) [单机模式]")

    except Exception as e:
        print(f"⚠️  ComfyUI: 检查失败 ({str(e)[:50]})")

