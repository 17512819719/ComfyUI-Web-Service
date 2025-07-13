"""
多模态内容生成工作流管理系统 - 主应用
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

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
        get_config_manager()
        print("📋 配置管理器已加载")

        # 2. 初始化任务类型管理器
        from .core.task_manager import get_task_type_manager
        get_task_type_manager()

        # 3. 注册任务处理器（通过导入模块自动注册）
        from .processors import text_to_image_processor
        print("🔧 任务处理器已注册")

        # 4. 初始化工作流执行器
        from .core.workflow_executor import get_workflow_executor
        get_workflow_executor()
        print("⚙️  工作流执行器已初始化")

        # 5. 检查系统依赖
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

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
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
    """用户登录（向后兼容）"""
    if username == "z" and password == "z":  # 示例，实际应查数据库
        token = create_access_token({"sub": username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="认证失败")

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
