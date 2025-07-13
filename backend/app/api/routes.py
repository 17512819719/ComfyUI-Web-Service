"""
API路由定义
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Form, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse

# 设置日志
logger = logging.getLogger(__name__)

from .schemas import (
    TextToImageRequest, TaskResponse, TaskSubmissionResponse,
    WorkflowInfo, WorkflowListResponse, SystemConfigResponse, HealthCheckResponse,
    ErrorResponse, TaskTypeEnum, TaskStatusEnum
)
from ..auth import verify_token
from ..core.task_manager import get_task_type_manager
from ..core.config_manager import get_config_manager
from ..core.base import TaskType
# 延迟导入任务模块以避免循环导入
# from ..queue.tasks import execute_text_to_image_task, get_task_status
from ..core.workflow_parameter_processor import get_workflow_parameter_processor

# 创建路由器
router = APIRouter()
security = HTTPBearer()

# 文件存储目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'outputs')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 任务状态存储（临时，生产环境应使用数据库）
task_status_store: Dict[str, Dict] = {}


@router.post("/api/v2/tasks/text-to-image", response_model=TaskSubmissionResponse)
async def submit_text_to_image_task(
    request: TextToImageRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """提交文生图任务"""
    user = verify_token(credentials.credentials)
    task_id = str(uuid.uuid4())
    
    try:
        # 构建请求数据
        request_data = request.dict()
        request_data.update({
            'task_id': task_id,
            'user_id': user['sub'],
            'task_type': TaskType.TEXT_TO_IMAGE.value
        })
        
        # 获取任务处理器进行参数验证
        task_manager = get_task_type_manager()
        task_request = task_manager.create_task_request(request_data)
        task_manager.validate_task_request(task_request)
        
        # 估算处理时间
        processor = task_manager.get_processor(TaskType.TEXT_TO_IMAGE)
        estimated_time = processor.estimate_processing_time(request_data) if processor else 60
        
        # 初始化任务状态
        task_status_store[task_id] = {
            'status': TaskStatusEnum.QUEUED.value,
            'progress': 0,
            'message': '文生图任务已提交到队列',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'estimated_time': estimated_time
        }
        
        # 提交到任务队列 - 增强错误处理
        try:
            from ..queue.tasks import execute_text_to_image_task
            logger.info(f"准备提交任务到Celery队列: {task_id}")

            # 确保request_data包含必要字段
            if 'task_id' not in request_data:
                raise ValueError("request_data缺少task_id字段")

            celery_task = execute_text_to_image_task.delay(request_data)
            task_status_store[task_id]['celery_task_id'] = celery_task.id
            logger.info(f"任务已成功提交到Celery队列: {task_id} -> {celery_task.id}")

        except ImportError as e:
            error_msg = f"Celery任务模块导入失败: {str(e)}"
            logger.error(error_msg)
            task_status_store[task_id].update({
                'status': TaskStatusEnum.FAILED.value,
                'error_message': error_msg,
                'updated_at': datetime.now().isoformat()
            })
            raise HTTPException(status_code=500, detail=error_msg)
        except Exception as e:
            error_msg = f"任务队列提交失败: {str(e)}"
            logger.error(f"{error_msg} (task_id: {task_id})")
            # 更新任务状态为失败
            task_status_store[task_id].update({
                'status': TaskStatusEnum.FAILED.value,
                'error_message': error_msg,
                'updated_at': datetime.now().isoformat()
            })
            raise HTTPException(status_code=500, detail=error_msg)
        
        return TaskSubmissionResponse(
            task_id=task_id,
            status=TaskStatusEnum.QUEUED,
            message="文生图任务已提交到队列",
            estimated_time=estimated_time
        )
        
    except Exception as e:
        # 更新任务状态为失败
        if task_id in task_status_store:
            task_status_store[task_id].update({
                'status': TaskStatusEnum.FAILED.value,
                'error_message': str(e),
                'updated_at': datetime.now().isoformat()
            })
        
        raise HTTPException(status_code=500, detail=f"任务提交失败: {str(e)}")


@router.post("/api/generate/image", response_model=TaskSubmissionResponse)
async def generate_image_form(
    prompt: str = Form(..., description="正面提示词"),
    negative_prompt: str = Form("", description="负面提示词"),
    width: int = Form(512, description="图像宽度"),
    height: int = Form(512, description="图像高度"),
    batch_size: int = Form(1, description="批量大小"),
    seed: int = Form(-1, description="随机种子"),
    checkpoint: Optional[str] = Form(None, description="模型检查点"),
    workflow_name: str = Form("sd_basic", description="工作流名称"),
    steps: int = Form(20, description="采样步数"),
    cfg_scale: float = Form(7.0, description="CFG引导强度"),
    sampler: str = Form("euler", description="采样器"),
    scheduler: str = Form("normal", description="调度器"),
    priority: int = Form(1, description="任务优先级"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """提交文生图任务（表单数据）"""
    user = verify_token(credentials.credentials)
    task_id = str(uuid.uuid4())

    try:
        # 构建请求数据
        request_data = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'width': width,
            'height': height,
            'batch_size': batch_size,
            'seed': seed,
            'checkpoint': checkpoint,
            'workflow_name': workflow_name,
            'steps': steps,
            'cfg_scale': cfg_scale,
            'sampler': sampler,
            'scheduler': scheduler,
            'priority': priority,
            'task_id': task_id,
            'user_id': user['sub'],
            'task_type': TaskType.TEXT_TO_IMAGE.value
        }

        # 使用工作流参数处理器验证和处理参数
        processor = get_workflow_parameter_processor()
        try:
            # 验证工作流参数
            processed_workflow = processor.process_workflow_request(workflow_name, request_data)
            if not processed_workflow:
                raise ValueError("工作流处理返回空结果")
            print(f"✓ 工作流 {workflow_name} 参数处理成功，节点数: {len(processed_workflow)}")
        except Exception as e:
            logger.error(f"工作流参数处理失败 [{workflow_name}]: {e}")
            raise HTTPException(status_code=400, detail=f"工作流参数处理失败: {str(e)}")

        # 验证请求参数
        try:
            text_to_image_request = TextToImageRequest(**{
                k: v for k, v in request_data.items()
                if k not in ['task_id', 'user_id', 'task_type']
            })
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"参数验证失败: {str(e)}")

        # 获取任务处理器进行进一步验证
        task_manager = get_task_type_manager()
        task_request = task_manager.create_task_request(request_data)
        task_manager.validate_task_request(task_request)

        # 估算处理时间
        task_processor = task_manager.get_processor(TaskType.TEXT_TO_IMAGE)
        estimated_time = task_processor.estimate_processing_time(request_data) if task_processor else 60

        # 根据工作流类型调整预估时间
        if workflow_name == 'sdxl_basic':
            estimated_time = int(estimated_time * 1.5)  # SDXL通常需要更长时间

        # 初始化任务状态
        task_status_store[task_id] = {
            'status': TaskStatusEnum.QUEUED.value,
            'progress': 0,
            'message': f'文生图任务已提交到队列 (工作流: {workflow_name})',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'estimated_time': estimated_time,
            'workflow_name': workflow_name,
            'prompt': prompt[:100] + '...' if len(prompt) > 100 else prompt
        }

        # 提交到任务队列
        try:
            from ..queue.tasks import execute_text_to_image_task
            celery_task = execute_text_to_image_task.delay(request_data)
            task_status_store[task_id]['celery_task_id'] = celery_task.id
            logger.info(f"任务已提交到Celery队列: {task_id} -> {celery_task.id}")
        except Exception as e:
            logger.error(f"提交任务到Celery失败: {e}")
            # 更新任务状态为失败
            task_status_store[task_id].update({
                'status': TaskStatusEnum.FAILED.value,
                'error_message': f'任务队列连接失败: {str(e)}',
                'updated_at': datetime.now().isoformat()
            })
            raise HTTPException(status_code=500, detail=f"任务队列连接失败: {str(e)}")

        return TaskSubmissionResponse(
            task_id=task_id,
            status=TaskStatusEnum.QUEUED,
            message=f"文生图任务已提交到队列 (工作流: {workflow_name})",
            estimated_time=estimated_time
        )

    except HTTPException:
        raise
    except Exception as e:
        # 更新任务状态为失败
        if task_id in task_status_store:
            task_status_store[task_id].update({
                'status': TaskStatusEnum.FAILED.value,
                'error_message': str(e),
                'updated_at': datetime.now().isoformat()
            })

        raise HTTPException(status_code=500, detail=f"任务提交失败: {str(e)}")



@router.get("/api/v2/tasks/{task_id}/status", response_model=TaskResponse)
async def get_task_status_v2(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取任务状态"""
    verify_token(credentials.credentials)
    
    # 从本地存储获取基础信息
    if task_id not in task_status_store:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = task_status_store[task_id]
    
    # 尝试从Celery获取最新状态
    if 'celery_task_id' in task_info:
        try:
            from ..queue.tasks import get_task_status
            celery_status = get_task_status(task_info['celery_task_id'])
            if celery_status:
                # 更新状态信息
                task_info.update(celery_status)
                task_info['updated_at'] = datetime.now().isoformat()
        except Exception as e:
            # 如果获取Celery状态失败，使用本地状态
            pass
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatusEnum(task_info.get('status', 'queued')),
        message=task_info.get('message', ''),
        progress=task_info.get('progress', 0),
        result_data=task_info.get('result_data'),
        error_message=task_info.get('error_message'),
        created_at=task_info.get('created_at'),
        updated_at=task_info.get('updated_at'),
        estimated_time=task_info.get('estimated_time')
    )


# 删除重复的工作流列表路由，保留下面更完整的版本


@router.get("/api/v2/config", response_model=SystemConfigResponse)
async def get_system_config_v2(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取系统配置信息"""
    verify_token(credentials.credentials)
    
    config_manager = get_config_manager()
    
    # 获取任务类型配置
    task_types_config = {}
    for task_type in TaskType:
        task_config = config_manager.get_task_type_config(task_type)
        if task_config.get('enabled', False):
            task_types_config[task_type.value] = {
                'enabled': task_config.get('enabled', False),
                'max_concurrent_tasks': task_config.get('max_concurrent_tasks', 1),
                'priority': task_config.get('priority', 1),
                'workflows': list(task_config.get('workflows', {}).keys())
            }
    
    # 获取系统配置
    system_config = config_manager.get_system_config()
    
    return SystemConfigResponse(
        task_types=task_types_config,
        supported_formats={
            'image': system_config.get('allowed_image_formats', ['jpg', 'jpeg', 'png', 'webp']),
            'video': system_config.get('allowed_video_formats', ['mp4', 'avi', 'mov'])
        },
        limits={
            'max_file_size': system_config.get('max_file_size', 50),
            'task_retention_time': system_config.get('task_retention_time', 86400),
            'cleanup_interval': system_config.get('cleanup_interval', 3600)
        },
        presets={
            'resolution': {
                'square_512': {'width': 512, 'height': 512},
                'square_768': {'width': 768, 'height': 768},
                'portrait_512': {'width': 512, 'height': 768},
                'landscape_512': {'width': 768, 'height': 512}
            },
            'quality': {
                'draft': {'steps': 10, 'cfg_scale': 5.0},
                'normal': {'steps': 20, 'cfg_scale': 7.0},
                'high': {'steps': 30, 'cfg_scale': 8.0}
            },
            'motion': {
                'subtle': 0.3,
                'moderate': 0.6,
                'strong': 0.9
            }
        }
    )


@router.get("/api/v2/health", response_model=HealthCheckResponse)
async def health_check_v2():
    """健康检查"""
    from ..queue.celery_app import get_celery_app

    celery_app = get_celery_app()
    services = {}

    # 检查Celery状态
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        services['celery'] = 'healthy' if stats else 'unhealthy'
    except Exception:
        services['celery'] = 'unhealthy'

    # 检查Redis状态
    try:
        import redis
        config_manager = get_config_manager()
        redis_config = config_manager.get_redis_config()
        r = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password')
        )
        r.ping()
        services['redis'] = 'healthy'
    except Exception:
        services['redis'] = 'unhealthy'

    # 检查ComfyUI状态
    try:
        import aiohttp
        config_manager = get_config_manager()
        comfyui_config = config_manager.get_comfyui_config()
        host = comfyui_config.get('host', '127.0.0.1')
        port = comfyui_config.get('port', 8188)

        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{host}:{port}/system_stats", timeout=5) as response:
                services['comfyui'] = 'healthy' if response.status == 200 else 'unhealthy'
    except Exception:
        services['comfyui'] = 'unhealthy'

    # 计算队列信息
    queue_info = {}
    try:
        active_tasks = len([t for t in task_status_store.values()
                          if t.get('status') in ['queued', 'processing']])
        queue_info = {
            'active_tasks': active_tasks,
            'total_tasks': len(task_status_store)
        }
    except Exception:
        queue_info = {'active_tasks': 0, 'total_tasks': 0}

    overall_status = 'healthy' if all(status == 'healthy' for status in services.values()) else 'degraded'

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        services=services,
        queue_info=queue_info
    )


@router.delete("/api/v2/tasks/{task_id}")
async def cancel_task_v2(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """取消任务"""
    verify_token(credentials.credentials)

    if task_id not in task_status_store:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_info = task_status_store[task_id]

    # 如果任务已完成或失败，不能取消
    if task_info.get('status') in ['completed', 'failed']:
        raise HTTPException(status_code=400, detail="任务已完成或失败，无法取消")

    try:
        # 取消Celery任务
        if 'celery_task_id' in task_info:
            from ..queue.tasks import cancel_task
            cancel_task(task_info['celery_task_id'])

        # 更新任务状态
        task_info.update({
            'status': TaskStatusEnum.CANCELLED.value,
            'message': '任务已取消',
            'updated_at': datetime.now().isoformat()
        })

        return {'message': '任务已取消', 'task_id': task_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.get("/api/v2/tasks/{task_id}/download")
async def download_task_result_v2(
    task_id: str,
    index: Optional[int] = Query(None, description="批量结果索引"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """下载任务结果"""
    verify_token(credentials.credentials)

    if task_id not in task_status_store:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_info = task_status_store[task_id]

    if task_info.get('status') != TaskStatusEnum.COMPLETED.value:
        raise HTTPException(status_code=400, detail="任务尚未完成")

    result_data = task_info.get('result_data', {})
    files = result_data.get('files', [])

    if not files:
        raise HTTPException(status_code=404, detail="未找到结果文件")

    # 处理批量结果
    if isinstance(files, list):
        if index is None:
            if len(files) == 1:
                file_path = files[0]
            else:
                raise HTTPException(status_code=400, detail="请指定要下载的文件索引")
        else:
            if index < 0 or index >= len(files):
                raise HTTPException(status_code=404, detail="文件索引超出范围")
            file_path = files[index]
    else:
        file_path = files

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    filename = os.path.basename(file_path)
    return FileResponse(file_path, filename=filename)


@router.get("/api/v2/tasks")
async def list_tasks_v2(
    status: Optional[TaskStatusEnum] = Query(None, description="按状态过滤"),
    task_type: Optional[TaskTypeEnum] = Query(None, description="按任务类型过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取任务列表"""
    user = verify_token(credentials.credentials)

    # 过滤任务
    filtered_tasks = []
    for task_id, task_info in task_status_store.items():
        # 只返回当前用户的任务（可选）
        # if task_info.get('user_id') != user['sub']:
        #     continue

        # 按状态过滤
        if status and task_info.get('status') != status.value:
            continue

        # 按任务类型过滤
        if task_type and task_info.get('task_type') != task_type.value:
            continue

        task_response = TaskResponse(
            task_id=task_id,
            status=TaskStatusEnum(task_info.get('status', 'queued')),
            message=task_info.get('message', ''),
            progress=task_info.get('progress', 0),
            result_data=task_info.get('result_data'),
            error_message=task_info.get('error_message'),
            created_at=task_info.get('created_at'),
            updated_at=task_info.get('updated_at'),
            estimated_time=task_info.get('estimated_time')
        )
        filtered_tasks.append(task_response)

    # 按创建时间排序（最新的在前）
    filtered_tasks.sort(key=lambda x: x.created_at or '', reverse=True)

    # 分页
    total = len(filtered_tasks)
    tasks = filtered_tasks[offset:offset + limit]

    return {
        'tasks': tasks,
        'total': total,
        'limit': limit,
        'offset': offset
    }


@router.get("/api/v2/workflows", response_model=WorkflowListResponse)
async def get_workflows(
    task_type: Optional[TaskTypeEnum] = Query(None, description="任务类型过滤"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取可用工作流列表"""
    user = verify_token(credentials.credentials)

    try:
        config_manager = get_config_manager()
        workflows_by_type = {}

        # 获取所有工作流配置
        all_workflows = config_manager.get_all_workflow_configs()

        for workflow_name, workflow_config in all_workflows.items():
            # 确定工作流的任务类型
            if 'text_to_image' in workflow_name or workflow_name in ['sd_basic', 'sdxl_basic']:
                workflow_task_type = TaskTypeEnum.TEXT_TO_IMAGE

            else:
                continue  # 跳过未知类型的工作流

            # 如果指定了任务类型过滤，则只返回匹配的工作流
            if task_type and workflow_task_type != task_type:
                continue

            # 构建工作流信息
            workflow_info = WorkflowInfo(
                name=workflow_name,
                version=workflow_config.get('version', '1.0'),
                description=workflow_config.get('description', ''),
                task_type=workflow_task_type,
                default_params=workflow_config.get('parameter_mapping', {}),
                param_rules=workflow_config.get('allowed_frontend_params', [])
            )

            # 按任务类型分组
            task_type_key = workflow_task_type.value
            if task_type_key not in workflows_by_type:
                workflows_by_type[task_type_key] = []
            workflows_by_type[task_type_key].append(workflow_info)

        total_count = sum(len(workflows) for workflows in workflows_by_type.values())

        return WorkflowListResponse(
            workflows=workflows_by_type,
            total_count=total_count
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流列表失败: {str(e)}")


@router.get("/api/v2/workflows/{workflow_name}")
async def get_workflow_details(
    workflow_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取特定工作流的详细信息"""
    user = verify_token(credentials.credentials)

    try:
        config_manager = get_config_manager()
        workflow_config = config_manager.get_workflow_config_raw(workflow_name)

        if not workflow_config:
            raise HTTPException(status_code=404, detail=f"工作流 '{workflow_name}' 不存在")

        return {
            'name': workflow_name,
            'config': workflow_config,
            'parameter_mapping': workflow_config.get('parameter_mapping', {}),
            'allowed_params': workflow_config.get('allowed_frontend_params', []),
            'description': workflow_config.get('description', ''),
            'version': workflow_config.get('version', '1.0')
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作流详情失败: {str(e)}")


@router.post("/api/v2/workflows/{workflow_name}/validate")
async def validate_workflow_parameters(
    workflow_name: str,
    parameters: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """验证工作流参数"""
    user = verify_token(credentials.credentials)

    try:
        config_manager = get_config_manager()
        processor = get_workflow_parameter_processor()

        # 检查工作流是否存在
        workflow_config = config_manager.get_workflow_config_raw(workflow_name)
        if not workflow_config:
            raise HTTPException(status_code=404, detail=f"工作流 '{workflow_name}' 不存在")

        # 验证参数
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'processed_params': {}
        }

        try:
            # 使用工作流处理器验证参数
            processed_workflow = processor.process_workflow_request(workflow_name, parameters)
            validation_result['processed_params'] = parameters
            validation_result['workflow_nodes'] = len(processed_workflow)

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(str(e))

        # 检查必需参数
        allowed_params = workflow_config.get('allowed_frontend_params', [])
        parameter_mapping = workflow_config.get('parameter_mapping', {})

        for param_name, param_config in parameter_mapping.items():
            if param_name in allowed_params and param_name not in parameters:
                # 检查是否有默认值
                if 'default_value' not in param_config:
                    validation_result['warnings'].append(f"参数 '{param_name}' 未提供，将使用工作流默认值")

        # 检查不支持的参数
        for param_name in parameters:
            if param_name not in allowed_params:
                validation_result['warnings'].append(f"参数 '{param_name}' 不在允许的参数列表中，将被忽略")

        return validation_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"参数验证失败: {str(e)}")


@router.get("/api/v2/system/config", response_model=SystemConfigResponse)
async def get_system_config(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取系统配置信息"""
    user = verify_token(credentials.credentials)

    try:
        config_manager = get_config_manager()

        # 获取任务类型配置
        task_types = {
            'text_to_image': {
                'name': '文生图',
                'description': '根据文本提示生成图像',
                'supported_workflows': ['sd_basic', 'sdxl_basic'],
                'default_workflow': 'sd_basic'
            }
        }

        # 支持的文件格式
        supported_formats = {
            'image': ['jpg', 'jpeg', 'png', 'webp', 'bmp']
        }

        # 系统限制
        limits = {
            'max_image_size': 2048,
            'min_image_size': 64,
            'max_batch_size': 8,
            'max_file_size_mb': 50
        }

        # 预设配置
        presets = {
            'resolutions': {
                'sd': ['512x512', '768x768', '512x768', '768x512'],
                'sdxl': ['1024x1024', '832x1216', '1216x832', '1344x768']
            },
            'quality': {
                'fast': {'steps': 20, 'cfg_scale': 7.0},
                'balanced': {'steps': 30, 'cfg_scale': 8.0},
                'high': {'steps': 50, 'cfg_scale': 9.0}
            }
        }

        return SystemConfigResponse(
            task_types=task_types,
            supported_formats=supported_formats,
            limits=limits,
            presets=presets
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统配置失败: {str(e)}")


# 前端兼容性API端点
@router.get("/api/config/defaults")
async def get_config_defaults():
    """获取前端默认配置（兼容性端点）"""
    return {
        "default_width": 1024,
        "default_height": 1024,
        "width_options": [512, 768, 832, 1024, 1216, 1344],
        "height_options": [512, 768, 832, 1024, 1216, 1480],
        "default_duration": 5,
        "default_fps": 8,
        "default_motion_strength": 0.8,
        "fps_options": [8, 12, 16, 24],
        "duration_min": 1,
        "duration_max": 10,
        "motion_min": 0.1,
        "motion_max": 1.0,
        "motion_step": 0.1,
        "video_width_options": [512, 832, 1024],
        "video_height_options": [512, 768, 1024],
        "video_default_width": 512,
        "video_default_height": 768
    }


@router.get("/api/tasks/status/{task_id}")
async def get_task_status_legacy(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取任务状态（兼容性端点）"""
    verify_token(credentials.credentials)

    if task_id not in task_status_store:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_info = task_status_store[task_id]

    # 尝试从Celery获取最新状态
    if 'celery_task_id' in task_info:
        try:
            from ..queue.tasks import get_task_status
            celery_status = get_task_status(task_info['celery_task_id'])
            if celery_status:
                task_info.update(celery_status)
                task_info['updated_at'] = datetime.now().isoformat()
        except Exception as e:
            logger.warning(f"获取Celery状态失败: {e}")

    # 转换为前端期望的格式
    status_mapping = {
        'queued': 'queued',
        'processing': 'processing',
        'completed': 'completed',
        'failed': 'failed',
        'cancelled': 'cancelled'
    }

    result = {
        'id': task_id,
        'status': status_mapping.get(task_info.get('status', 'queued'), 'queued'),
        'progress': task_info.get('progress', 0),
        'message': task_info.get('message', ''),
        'created_at': task_info.get('created_at'),
        'updated_at': task_info.get('updated_at')
    }

    # 如果任务完成，添加结果信息
    if task_info.get('status') == 'completed':
        result_data = task_info.get('result_data', {})
        files = result_data.get('files', [])

        if files:
            if isinstance(files, list):
                # 多个文件，生成URL列表
                result['resultUrls'] = [f"/api/download/{task_id}?index={i}" for i in range(len(files))]
                result['resultUrl'] = result['resultUrls'][0] if result['resultUrls'] else None
            else:
                # 单个文件
                result['resultUrl'] = f"/api/download/{task_id}"
                result['resultUrls'] = [result['resultUrl']]

    return result


@router.get("/api/download/{task_id}")
async def download_task_result_legacy(
    task_id: str,
    index: Optional[int] = Query(None, description="文件索引"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """下载任务结果（兼容性端点）"""
    verify_token(credentials.credentials)

    if task_id not in task_status_store:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_info = task_status_store[task_id]

    if task_info.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="任务尚未完成")

    result_data = task_info.get('result_data', {})
    files = result_data.get('files', [])

    if not files:
        raise HTTPException(status_code=404, detail="未找到结果文件")

    # 处理文件选择
    if isinstance(files, list):
        if index is None:
            if len(files) == 1:
                file_path = files[0]
            else:
                raise HTTPException(status_code=400, detail="请指定要下载的文件索引")
        else:
            if index < 0 or index >= len(files):
                raise HTTPException(status_code=404, detail="文件索引超出范围")
            file_path = files[index]
    else:
        file_path = files

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    filename = os.path.basename(file_path)
    return FileResponse(file_path, filename=filename)
