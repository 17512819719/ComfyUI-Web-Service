"""
Celery应用配置
"""
from celery import Celery
from ..core.config_manager import get_config_manager

# 获取配置
config_manager = get_config_manager()
task_queue_config = config_manager.get_task_queue_config()
redis_config = config_manager.get_redis_config()

# 构建Redis URL
redis_host = redis_config.get('host', 'localhost')
redis_port = redis_config.get('port', 6379)
redis_db = redis_config.get('db', 0)
redis_password = redis_config.get('password')

if redis_password:
    broker_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    result_backend = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
else:
    broker_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
    result_backend = f"redis://{redis_host}:{redis_port}/{redis_db}"

# 创建Celery应用
celery_app = Celery('comfyui_workflow_manager')

# 如果Redis不可用，使用内存后端
try:
    import redis
    r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, password=redis_password)
    r.ping()
    # Redis可用，使用Redis作为broker和backend
    final_broker_url = task_queue_config.get('broker_url', broker_url)
    final_result_backend = task_queue_config.get('result_backend', result_backend)
except:
    # Redis不可用，使用内存后端
    final_broker_url = 'memory://'
    final_result_backend = 'cache+memory://'
    

# 配置Celery
celery_app.conf.update(
    broker_url=final_broker_url,
    result_backend='cache+memory://',  # 使用内存后端，避免Redis序列化问题
    task_serializer=task_queue_config.get('task_serializer', 'json'),
    result_serializer=task_queue_config.get('result_serializer', 'json'),
    accept_content=task_queue_config.get('accept_content', ['json']),
    timezone=task_queue_config.get('timezone', 'UTC'),
    enable_utc=task_queue_config.get('enable_utc', True),
    task_routes=task_queue_config.get('task_routes', {}),
    worker_prefetch_multiplier=task_queue_config.get('worker_prefetch_multiplier', 1),
    task_acks_late=False,  # 禁用延迟确认，避免未确认任务恢复
    task_reject_on_worker_lost=True,  # Worker丢失时拒绝任务
    worker_max_tasks_per_child=task_queue_config.get('worker_max_tasks_per_child', 100),

    # 任务结果过期时间
    result_expires=3600,  # 1小时

    # 任务超时设置
    task_soft_time_limit=1800,  # 30分钟软超时
    task_time_limit=2400,       # 40分钟硬超时

    # 任务重试设置
    task_default_retry_delay=60,    # 重试延迟60秒
    task_max_retries=3,             # 最大重试3次

    # 任务优先级
    task_inherit_parent_priority=True,
    task_default_priority=5,

    # 监控设置
    worker_send_task_events=True,
    task_send_sent_event=True,

    # 内存后端特殊配置
    task_always_eager=final_broker_url == 'memory://',  # 如果使用内存后端，立即执行任务
    task_eager_propagates=True,
)

# 自动发现任务
celery_app.autodiscover_tasks(['app.queue'])


# Worker启动时的信号处理
from celery.signals import worker_ready, worker_shutdown

@worker_ready.connect
def init_worker(sender, **kwargs):
    """Worker启动完成时初始化数据库连接"""
    try:
        # 初始化配置管理器
        from ..core.config_manager import get_config_manager
        config_manager = get_config_manager()

        # 重新加载配置文件（确保最新配置）
        config_manager.reload_config()
        print("✅ Celery Worker: 配置文件已加载")

        # 初始化数据库连接
        from ..database.connection import initialize_database
        mysql_config = config_manager.get_mysql_config()

        if not mysql_config:
            print("❌ Celery Worker: MySQL配置为空")
            return

        # 检查配置结构
        print(f"🔍 Celery Worker: MySQL配置结构: {list(mysql_config.keys())}")

        # 确保包含所有必需的数据库配置
        required_dbs = ['client', 'admin', 'shared']
        for db_name in required_dbs:
            if db_name not in mysql_config:
                print(f"❌ Celery Worker: 缺少数据库配置: {db_name}")
                return

        # 构建正确的配置格式
        database_config = {'mysql': mysql_config}
        initialize_database(database_config)
        print("✅ Celery Worker: 数据库连接已初始化")

        # 初始化数据库任务状态管理器
        from ..database.task_status_manager import get_database_task_status_manager
        task_manager = get_database_task_status_manager()
        print("✅ Celery Worker: 数据库任务状态管理器已初始化")

        # 测试数据库连接
        task_manager = get_database_task_status_manager()
        if task_manager:
            print("✅ Celery Worker: 数据库连接测试成功")
        else:
            print("⚠️ Celery Worker: 数据库连接测试失败")

    except Exception as e:
        import traceback
        print(f"❌ Celery Worker: 数据库初始化失败: {e}")
        print(f"详细错误: {traceback.format_exc()}")


@worker_shutdown.connect
def cleanup_worker(sender, **kwargs):
    """Worker关闭时清理资源"""
    try:
        print("🔄 Celery Worker: 正在清理数据库连接...")
        # 这里可以添加数据库连接清理逻辑
    except Exception as e:
        print(f"⚠️ Celery Worker: 清理资源失败: {e}")


def get_celery_app():
    """获取Celery应用实例"""
    return celery_app
