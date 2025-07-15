"""
多模态内容生成工作流管理系统 - 主应用
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

# 配置日志 - 简化格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 设置第三方库日志级别为WARNING，减少噪音
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
logging.getLogger('kombu').setLevel(logging.WARNING)
logging.getLogger('celery').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("\n" + "="*60)
    print("🚀 ComfyUI Web Service 启动中...")
    print("="*60)

    try:
        # 初始化核心组件
        await initialize_system()

        # 初始化所有服务（避免动态导入导致的表冲突）
        try:
            from .services.file_service import get_file_service
            from .services.config_service import get_config_service
            from .services.log_service import get_log_service
            from .services.performance_service import get_performance_service

            # 预初始化服务
            get_file_service()
            get_config_service()
            get_log_service()
            get_performance_service()

            print("🔧 所有服务已预初始化")
        except Exception as e:
            print(f"⚠️  服务预初始化失败: {e}")

        print("✅ 系统启动完成，服务已就绪！")
        print("="*60 + "\n")

        yield

    finally:
        # 关闭时执行
        print("\n" + "="*60)
        print("🛑 正在关闭系统...")
        await cleanup_system()
        print("✅ 系统已安全关闭")
        print("="*60 + "\n")


async def initialize_system():
    """初始化系统组件"""
    try:
        # 1. 加载配置
        from .core.config_manager import get_config_manager
        config_manager = get_config_manager()
        print("📋 配置管理器已加载")

        # 2. 初始化数据库连接
        from .database.connection import initialize_database
        config = config_manager.get_config()
        initialize_database(config)
        print("🗄️  数据库连接已初始化")

        # 3. 测试数据库连接
        from .database.connection import get_database_manager
        db_manager = get_database_manager()
        test_results = db_manager.test_connections()
        for db_name, success in test_results.items():
            status = "✅" if success else "❌"
            print(f"   {status} {db_name} 数据库连接测试")

        # 4. 初始化任务类型管理器
        from .core.task_manager import get_task_type_manager
        get_task_type_manager()

        # 5. 注册任务处理器（通过导入模块自动注册）
        from .processors import text_to_image_processor
        print("🔧 任务处理器已注册")

        # 6. 初始化工作流执行器
        from .core.workflow_executor import get_workflow_executor
        get_workflow_executor()
        print("⚙️  工作流执行器已初始化")

        # 5. 初始化分布式组件（如果启用）
        config_manager = get_config_manager()
        if config_manager.is_distributed_mode():
            from .core.node_manager import get_node_manager
            from .core.load_balancer import get_load_balancer

            # 启动节点管理器
            node_manager = get_node_manager()
            await node_manager.start()
            print("🌐 节点管理器已启动")

            # 初始化负载均衡器
            get_load_balancer()
            print("⚖️  负载均衡器已初始化")

            print("🚀 分布式模式已启用")
        else:
            print("🖥️  单机模式运行")

        # 6. 检查系统依赖
        await check_system_dependencies()

    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        raise


async def check_system_dependencies():
    """检查系统依赖"""
    from .core.config_manager import get_config_manager

    config_manager = get_config_manager()

    # 检查Redis连接
    try:
        import redis
        redis_config = config_manager.get_redis_config()
        r = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password')
        )
        r.ping()
        print("🔴 Redis: 已连接")
    except Exception:
        print("🟡 Redis: 不可用 (使用内存模式)")

    # 检查ComfyUI连接
    try:
        import aiohttp
        comfyui_config = config_manager.get_comfyui_config()
        host = comfyui_config.get('host', '127.0.0.1')
        port = comfyui_config.get('port', 8188)

        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{host}:{port}/system_stats", timeout=5) as response:
                if response.status == 200:
                    print(f"🎨 ComfyUI: 已连接 ({host}:{port})")
                else:
                    print(f"🟡 ComfyUI: 响应异常 ({response.status})")
    except Exception:
        print("❌ ComfyUI: 连接失败 (请检查ComfyUI是否运行)")


async def cleanup_system():
    """清理系统资源"""
    try:
        # 停止分布式组件
        try:
            from .core.config_manager import get_config_manager
            config_manager = get_config_manager()

            if config_manager.is_distributed_mode():
                from .core.node_manager import get_node_manager
                node_manager = get_node_manager()
                await node_manager.stop()
                print("🌐 节点管理器已停止")
        except Exception as e:
            print(f"⚠️  停止分布式组件时出错: {e}")

        # 清理任务状态
        from .api.routes import task_status_store
        task_count = len(task_status_store)
        task_status_store.clear()
        if task_count > 0:
            print(f"🧹 清理任务状态: {task_count} 个任务")

        # 清理Celery任务队列
        try:
            from .queue.celery_app import get_celery_app
            celery_app = get_celery_app()

            # 尝试清理活跃任务
            try:
                inspect = celery_app.control.inspect()
                active_tasks = inspect.active()
                if active_tasks:
                    for worker, tasks in active_tasks.items():
                        for task in tasks:
                            celery_app.control.revoke(task['id'], terminate=True)
                            logger.info(f"清理活跃任务: {task['id']}")

                # 清理队列中的任务
                reserved_tasks = inspect.reserved()
                if reserved_tasks:
                    for worker, tasks in reserved_tasks.items():
                        for task in tasks:
                            celery_app.control.revoke(task['id'], terminate=True)
                            logger.info(f"清理队列任务: {task['id']}")

                logger.info("Celery任务队列清理完成")
            except Exception as e:
                logger.info(f"Celery队列清理跳过 (可能使用内存后端): {e}")

        except Exception as e:
            logger.warning(f"Celery队列清理失败: {e}")

    except Exception as e:
        logger.error(f"系统清理失败: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="多模态内容生成工作流管理系统",
    description="支持文生图、图生视频等多种AI内容生成任务的统一管理平台",
    version="2.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
import os
client_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Client')
if os.path.exists(client_dir):
    app.mount("/Client", StaticFiles(directory=client_dir), name="client")
    logger.info(f"静态文件服务已挂载: /Client -> {client_dir}")
else:
    logger.warning(f"客户端目录不存在: {client_dir}")

# 挂载outputs目录用于图片访问
outputs_dir = os.path.join(os.path.dirname(__file__), '..', 'outputs')
if os.path.exists(outputs_dir):
    app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")
    logger.info(f"输出文件服务已挂载: /outputs -> {outputs_dir}")
else:
    logger.warning(f"输出目录不存在: {outputs_dir}")

# 挂载ComfyUI的output目录（如果存在）
comfyui_output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ComfyUI', 'output')
if os.path.exists(comfyui_output_dir):
    app.mount("/comfyui-output", StaticFiles(directory=comfyui_output_dir), name="comfyui_output")
    logger.info(f"ComfyUI输出文件服务已挂载: /comfyui-output -> {comfyui_output_dir}")
else:
    logger.warning(f"ComfyUI输出目录不存在: {comfyui_output_dir}")

# 导入新的异常处理模块
try:
    from .core.exceptions import ServiceError, ErrorCode
    ENHANCED_ERROR_HANDLING = True
except ImportError:
    ENHANCED_ERROR_HANDLING = False
    logger.warning("增强错误处理模块未找到，使用基础错误处理")

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)

    # 如果启用了增强错误处理
    if ENHANCED_ERROR_HANDLING and isinstance(exc, ServiceError):
        return JSONResponse(
            status_code=500,
            content={
                "error": exc.error_code.value,
                "message": exc.message,
                "details": exc.details
            }
        )

    # 默认错误处理
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "服务器内部错误",
            "details": str(exc) if app.debug else None
        }
    )

# 注册路由
try:
    from .api.routes import router as api_router
    app.include_router(api_router)
except ImportError as e:
    logger.error(f"导入API路由失败: {e}")
    # 创建一个空的路由器作为备用
    from fastapi import APIRouter
    api_router = APIRouter()
    app.include_router(api_router)

# 保持向后兼容的旧版API
from .auth import create_access_token, verify_token
from fastapi import Form, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """客户端用户登录"""
    try:
        from .services.client_auth_service import get_client_auth_service
        auth_service = get_client_auth_service()

        # 验证用户凭据
        user = auth_service.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 创建访问令牌
        token_data = {
            "sub": user["username"],
            "client_id": user["client_id"],
            "user_type": "client"
        }
        token = auth_service.create_access_token(token_data)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user_info": {
                "username": user["username"],
                "nickname": user["nickname"],
                "client_id": user["client_id"],
                "quota_limit": user["quota_limit"],
                "quota_used": user["quota_used"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {e}")
        raise HTTPException(status_code=500, detail="登录服务异常")



@app.get("/api/auth/profile")
async def get_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取用户配置信息"""
    try:
        from .services.client_auth_service import get_client_auth_service
        auth_service = get_client_auth_service()

        # 验证令牌
        payload = auth_service.verify_token(credentials.credentials)
        username = payload.get("sub")

        # 获取用户信息
        user = auth_service.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        # 获取配额信息
        quota_info = auth_service.check_quota(username)

        return {
            "username": user["username"],
            "nickname": user["nickname"],
            "client_id": user["client_id"],
            "is_active": user["is_active"],
            "last_access_at": user["last_access_at"].isoformat() if user["last_access_at"] else None,
            "quota": quota_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(status_code=500, detail="服务异常")


@app.post("/api/admin/migrate-client-db")
async def migrate_client_database():
    """迁移客户端数据库（管理员功能）"""
    try:
        from sqlalchemy import text
        from .database.connection import get_database_manager

        db_manager = get_database_manager()

        with db_manager.get_session('client') as session:
            # 检查表结构
            result = session.execute(text("DESCRIBE client_users"))
            columns = result.fetchall()

            # 检查是否有username字段
            has_username = any(col[0] == 'username' for col in columns)
            has_password_hash = any(col[0] == 'password_hash' for col in columns)

            changes = []

            if not has_username or not has_password_hash:
                if not has_username:
                    session.execute(text("ALTER TABLE client_users ADD COLUMN username VARCHAR(50) UNIQUE COMMENT '用户名' AFTER client_id"))
                    changes.append("添加 username 字段")

                if not has_password_hash:
                    session.execute(text("ALTER TABLE client_users ADD COLUMN password_hash VARCHAR(255) COMMENT '密码哈希' AFTER username"))
                    changes.append("添加 password_hash 字段")

                # 添加索引
                try:
                    session.execute(text("ALTER TABLE client_users ADD INDEX idx_username (username)"))
                    changes.append("添加 username 索引")
                except:
                    pass  # 索引可能已存在

                session.commit()

                return {
                    "message": "数据库迁移完成",
                    "changes": changes
                }
            else:
                return {
                    "message": "数据库已是最新版本",
                    "changes": []
                }

    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库迁移失败: {str(e)}")


@app.post("/api/admin/init-test-users")
async def init_test_users():
    """初始化测试用户（管理员功能）"""
    try:
        from sqlalchemy import text
        from .database.connection import get_database_manager
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        db_manager = get_database_manager()

        # 测试用户数据
        test_users = [
            {
                "client_id": "test-client-z",
                "username": "z",
                "password": "z",
                "nickname": "测试用户",
                "quota_limit": 100
            },
            {
                "client_id": "demo-client-001",
                "username": "demo",
                "password": "demo123",
                "nickname": "演示用户",
                "quota_limit": 50
            },
            {
                "client_id": "admin-client-001",
                "username": "admin",
                "password": "admin123",
                "nickname": "管理员用户",
                "quota_limit": 1000
            }
        ]

        created_users = []

        with db_manager.get_session('client') as session:
            for user_data in test_users:
                # 检查用户是否已存在（按用户名或client_id）
                existing = session.execute(text(
                    "SELECT username FROM client_users WHERE username = :username OR client_id = :client_id"
                ), {
                    "username": user_data["username"],
                    "client_id": user_data["client_id"]
                }).fetchone()

                if existing:
                    logger.info(f"用户 {user_data['username']} 已存在，跳过创建")
                    continue

                # 生成密码哈希
                password_hash = pwd_context.hash(user_data["password"])

                # 插入用户
                session.execute(text("""
                    INSERT INTO client_users (client_id, username, password_hash, nickname, quota_limit, is_active)
                    VALUES (:client_id, :username, :password_hash, :nickname, :quota_limit, TRUE)
                """), {
                    "client_id": user_data["client_id"],
                    "username": user_data["username"],
                    "password_hash": password_hash,
                    "nickname": user_data["nickname"],
                    "quota_limit": user_data["quota_limit"]
                })

                created_users.append(user_data["username"])
                logger.info(f"创建用户: {user_data['username']}")

            session.commit()

        return {
            "message": "测试用户初始化完成",
            "created_users": created_users,
            "total_users": len(test_users)
        }

    except Exception as e:
        logger.error(f"初始化测试用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")


@app.post("/api/admin/sync-config")
async def sync_config_to_database():
    """同步配置文件到数据库（管理员功能）"""
    try:
        from .services.config_service import get_config_service
        config_service = get_config_service()

        success = config_service.sync_config_to_database()
        if success:
            return {"message": "配置同步到数据库成功"}
        else:
            raise HTTPException(status_code=500, detail="配置同步失败")

    except Exception as e:
        logger.error(f"配置同步失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置同步失败: {str(e)}")


@app.get("/api/admin/config")
async def get_all_configs(category: str = None):
    """获取所有系统配置（管理员功能）"""
    try:
        from .services.config_service import get_config_service
        config_service = get_config_service()

        configs = config_service.get_all_configs(category)
        return {"configs": configs}

    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@app.get("/api/admin/config/{config_key}")
async def get_config(config_key: str):
    """获取指定配置项（管理员功能）"""
    try:
        from .services.config_service import get_config_service
        config_service = get_config_service()

        config_value = config_service.get_config(config_key)
        return {"config_key": config_key, "config_value": config_value}

    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@app.put("/api/admin/config/{config_key}")
async def update_config(config_key: str, config_data: dict):
    """更新配置项（管理员功能）"""
    try:
        from .services.config_service import get_config_service
        config_service = get_config_service()

        config_value = config_data.get('config_value')
        description = config_data.get('description')

        success = config_service.set_config(config_key, config_value, description, 'admin_api')
        if success:
            return {"message": f"配置 {config_key} 更新成功"}
        else:
            raise HTTPException(status_code=500, detail="配置更新失败")

    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@app.get("/api/admin/logs/access")
async def get_access_logs(
    client_id: str = None,
    limit: int = 100,
    offset: int = 0
):
    """获取访问日志（管理员功能）"""
    try:
        from .services.log_service import get_log_service
        log_service = get_log_service()

        logs = log_service.get_client_access_logs(client_id, limit, offset)
        return {"logs": logs, "total": len(logs)}

    except Exception as e:
        logger.error(f"获取访问日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取访问日志失败: {str(e)}")


@app.get("/api/admin/logs/system")
async def get_system_logs(
    event_type: str = None,
    level: str = None,
    limit: int = 100,
    offset: int = 0
):
    """获取系统日志（管理员功能）"""
    try:
        from .services.log_service import get_log_service
        log_service = get_log_service()

        logs = log_service.get_system_logs(event_type, level, limit, offset)
        return {"logs": logs, "total": len(logs)}

    except Exception as e:
        logger.error(f"获取系统日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统日志失败: {str(e)}")


@app.get("/api/admin/logs/statistics")
async def get_access_statistics(client_id: str = None):
    """获取访问统计（管理员功能）"""
    try:
        from .services.log_service import get_log_service
        log_service = get_log_service()

        stats = log_service.get_access_statistics(client_id)
        return {"statistics": stats}

    except Exception as e:
        logger.error(f"获取访问统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取访问统计失败: {str(e)}")


@app.get("/api/admin/performance/current")
async def get_current_performance():
    """获取当前系统性能（管理员功能）"""
    try:
        from .services.performance_service import get_performance_service
        performance_service = get_performance_service()

        metrics = performance_service.collect_system_metrics()
        return {"metrics": metrics}

    except Exception as e:
        logger.error(f"获取当前性能失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取当前性能失败: {str(e)}")


@app.get("/api/admin/performance/history")
async def get_performance_history(
    metric_type: str = None,
    metric_name: str = None,
    hours: int = 24,
    limit: int = 100
):
    """获取性能历史数据（管理员功能）"""
    try:
        from .services.performance_service import get_performance_service
        from datetime import datetime, timedelta

        performance_service = get_performance_service()

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        metrics = performance_service.get_performance_metrics(
            metric_type=metric_type,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        return {"metrics": metrics, "total": len(metrics)}

    except Exception as e:
        logger.error(f"获取性能历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能历史失败: {str(e)}")


@app.get("/api/admin/performance/summary")
async def get_performance_summary(hours: int = 24):
    """获取性能摘要（管理员功能）"""
    try:
        from .services.performance_service import get_performance_service
        performance_service = get_performance_service()

        summary = performance_service.get_performance_summary(hours)
        return {"summary": summary}

    except Exception as e:
        logger.error(f"获取性能摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能摘要失败: {str(e)}")


@app.post("/api/admin/performance/collect")
async def collect_performance_metrics():
    """手动收集性能指标（管理员功能）"""
    try:
        from .services.performance_service import get_performance_service
        performance_service = get_performance_service()

        success = performance_service.record_system_metrics()
        if success:
            return {"message": "性能指标收集成功"}
        else:
            raise HTTPException(status_code=500, detail="性能指标收集失败")

    except Exception as e:
        logger.error(f"收集性能指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"收集性能指标失败: {str(e)}")

# 兼容旧版接口
@app.post("/api/generate/image")
async def generate_image_legacy(
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: int = Form(512),
    height: int = Form(512),
    workflow_template: str = Form(None),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """文生图接口（向后兼容）"""
    from .api.schemas import TextToImageRequest
    from .api.routes import submit_text_to_image_task
    
    # 转换为新版请求格式
    request = TextToImageRequest(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        workflow_name=workflow_template
    )
    
    return await submit_text_to_image_task(request, credentials)



@app.get("/api/task/status/{task_id}")
async def get_task_status_legacy(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """查询任务状态（向后兼容）"""
    from .api.routes import get_task_status_v2
    
    response = await get_task_status_v2(task_id, credentials)
    
    # 转换为旧版格式
    return {
        "task_id": response.task_id,
        "status": response.status.value,
        "progress": response.progress,
        "message": response.message,
        "result_url": response.result_data.get('files') if response.result_data else None,
        "error_message": response.error_message,
        "created_at": response.created_at,
        "updated_at": response.updated_at
    }

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "多模态内容生成工作流管理系统",
        "version": "2.0.0",
        "description": "支持文生图、图生视频等多种AI内容生成任务的统一管理平台",
        "api_docs": "/docs",
        "health_check": "/api/v2/health"
    }

# 导入必要的依赖已在文件开头完成

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
