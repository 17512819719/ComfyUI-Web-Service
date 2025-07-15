"""
Celery任务定义
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from celery import Task
from ..core.base import TaskType, TaskRequest, TaskResult, TaskStatus, WorkflowExecutionError
from ..core.task_manager import get_task_type_manager
from ..core.config_manager import get_config_manager
from ..core.workflow_executor import get_workflow_executor

# 导入处理器以确保它们被注册（重要！）
from ..processors import text_to_image_processor

logger = logging.getLogger(__name__)

# 延迟导入celery_app以避免循环导入
def get_celery_app_instance():
    from .celery_app import get_celery_app
    return get_celery_app()

celery_app = get_celery_app_instance()


class BaseWorkflowTask(Task):
    """基础工作流任务类"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"任务 {task_id} 执行失败: {exc}")
        
        # 更新任务状态
        self.update_task_status(task_id, {
            'status': TaskStatus.FAILED.value,
            'error_message': str(exc),
            'progress': 0
        })
    
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的回调"""
        logger.info(f"任务 {task_id} 执行成功")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任务重试时的回调"""
        logger.warning(f"任务 {task_id} 重试: {exc}")
        
        # 更新任务状态
        self.update_task_status(task_id, {
            'status': TaskStatus.PROCESSING.value,
            'message': f'任务重试中: {exc}',
            'progress': 0
        })
    
    def update_task_status(self, task_id: str, status_data: Dict[str, Any]):
        """更新任务状态 - 优化版本，减少竞态条件"""
        try:
            # 映射自定义状态到Celery状态
            status = status_data.get('status', 'processing')
            celery_state_map = {
                'queued': 'PENDING',
                'processing': 'PROGRESS',
                'completed': 'SUCCESS',
                'failed': 'FAILURE',
                'cancelled': 'REVOKED'
            }

            celery_state = celery_state_map.get(status, 'PROGRESS')

            # 更新Celery任务状态
            self.update_state(
                state=celery_state,
                meta=status_data
            )

            # 使用数据库状态管理器
            from ..database.task_status_manager import get_database_task_status_manager

            status_manager = get_database_task_status_manager()

            # 查找任务ID，可能是原始task_id或celery_task_id
            target_task_id = None

            # 首先尝试直接匹配（task_id就是实际任务ID）
            if status_manager.get_task_status(task_id):
                target_task_id = task_id
            else:
                # 如果直接匹配失败，查找celery_task_id匹配的任务
                all_tasks = status_manager.list_tasks()
                for stored_task_id, task_info in all_tasks.items():
                    if task_info.get('celery_task_id') == task_id:
                        target_task_id = stored_task_id
                        break

            if target_task_id:
                # 更新状态管理器
                status_manager.update_task_status(target_task_id, status_data)
                logger.debug(f"任务状态已更新: {target_task_id} -> {status}")
            else:
                logger.warning(f"未找到任务ID进行状态更新: {task_id}")

        except Exception as e:
            logger.error(f"更新任务状态失败 [{task_id}]: {e}")

    def _process_comfyui_result(self, result_data: Dict, task_id: str) -> Dict:
        """处理ComfyUI返回的结果数据，提取文件路径"""
        import os  # 添加os导入
        try:
            from ..utils.path_utils import get_output_dir
            output_dir = get_output_dir()

            files = []

            # 从ComfyUI历史记录中提取输出文件
            if 'outputs' in result_data:
                for node_id, node_output in result_data['outputs'].items():
                    if 'images' in node_output:
                        for image_info in node_output['images']:
                            filename = image_info.get('filename')
                            subfolder = image_info.get('subfolder', '')
                            if filename:
                                # 构建完整文件路径
                                if subfolder:
                                    file_path = os.path.join(output_dir, subfolder, filename)
                                else:
                                    file_path = os.path.join(output_dir, filename)

                                # 检查文件是否存在
                                if os.path.exists(file_path):
                                    files.append(file_path)
                                    logger.info(f"找到输出文件: {file_path}")
                                else:
                                    logger.warning(f"输出文件不存在: {file_path}")

            # 不再复制文件，直接使用ComfyUI生成的文件路径
            # 只记录文件路径，不进行额外的文件操作
            logger.info(f"使用ComfyUI原始输出文件，不进行复制操作")

            # 返回处理后的结果
            processed_result = {
                'files': files,
                'original_result': result_data,
                'task_id': task_id
            }

            logger.info(f"ComfyUI结果处理完成，找到 {len(files)} 个文件")
            return processed_result

        except Exception as e:
            logger.error(f"处理ComfyUI结果失败: {e}")
            return {
                'files': [],
                'original_result': result_data,
                'task_id': task_id,
                'error': str(e)
            }


@celery_app.task(bind=True, base=BaseWorkflowTask, queue='text_to_image')
def execute_text_to_image_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行文生图任务"""
    # 修复：确保使用API层传递的task_id，而不是Celery任务ID
    task_id = request_data.get('task_id')
    if not task_id:
        raise Exception("任务ID缺失，无法执行任务")
    
    try:
        logger.info(f"开始执行文生图任务: {task_id}")
        
        # 更新任务状态为处理中
        self.update_task_status(task_id, {
            'status': TaskStatus.PROCESSING.value,
            'message': '正在处理文生图任务',
            'progress': 10
        })
        
        # 创建任务请求 - 优化：减少重复验证
        task_manager = get_task_type_manager()
        task_request = task_manager.create_task_request(request_data)
        task_request.task_type = TaskType.TEXT_TO_IMAGE

        # 跳过验证，因为API层已经验证过了
        logger.debug(f"跳过Celery层参数验证，API层已验证: {task_id}")
        
        # 获取配置和处理器
        config_manager = get_config_manager()
        processor = task_manager.get_processor(TaskType.TEXT_TO_IMAGE)
        
        if not processor:
            raise Exception("未找到文生图任务处理器")
        
        # 获取工作流配置
        workflow_name = task_request.workflow_name
        if not workflow_name:
            workflow_config = config_manager.get_default_workflow(TaskType.TEXT_TO_IMAGE)
            if workflow_config:
                workflow_name = workflow_config.name
        else:
            workflow_config = config_manager.get_workflow_config(workflow_name)

        if not workflow_config:
            raise Exception(f"未找到工作流配置: {workflow_name or 'default'}")

        if not workflow_name:
            raise Exception("工作流名称为空")
        
        # 更新进度
        self.update_task_status(task_id, {
            'status': TaskStatus.PROCESSING.value,
            'message': '正在处理参数',
            'progress': 30
        })
        
        # 处理参数 - 现在返回完整的工作流数据
        complete_workflow = processor.process_params(task_request, workflow_config)

        # 更新进度
        self.update_task_status(task_id, {
            'status': TaskStatus.PROCESSING.value,
            'message': '正在执行工作流',
            'progress': 50
        })

        # 执行工作流 - 简化版本
        import requests
        import time
        import os

        # 修复：从配置文件读取ComfyUI URL
        comfyui_config = config_manager.get_comfyui_config()
        comfyui_host = comfyui_config.get('host', '127.0.0.1')
        comfyui_port = comfyui_config.get('port', 8188)
        comfyui_url = f"http://{comfyui_host}:{comfyui_port}"

        logger.info(f"提交工作流到ComfyUI: {task_id}")

        # 提交工作流 - 增强错误处理
        try:
            logger.info(f"向ComfyUI提交工作流: {comfyui_url}/prompt")
            response = requests.post(f"{comfyui_url}/prompt", json={"prompt": complete_workflow}, timeout=30)

            if response.status_code != 200:
                error_detail = f"状态码: {response.status_code}, 响应: {response.text[:500]}"
                logger.error(f"ComfyUI API调用失败: {error_detail}")
                raise WorkflowExecutionError(f"ComfyUI API调用失败: {error_detail}")

            response_data = response.json()
            if "prompt_id" not in response_data:
                logger.error(f"ComfyUI响应格式异常: {response_data}")
                raise Exception("ComfyUI响应中缺少prompt_id")

            prompt_id = response_data["prompt_id"]
            logger.info(f"工作流已成功提交到ComfyUI，prompt_id: {prompt_id}")

        except requests.exceptions.Timeout:
            error_msg = f"ComfyUI连接超时 (URL: {comfyui_url})"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = f"无法连接到ComfyUI服务器 (URL: {comfyui_url})"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"ComfyUI请求失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

        # 更新进度
        self.update_task_status(task_id, {
            'status': TaskStatus.PROCESSING.value,
            'message': '工作流执行中',
            'progress': 70
        })

        # 等待完成
        max_wait = 300  # 5分钟
        start_time = time.time()
        result_data = None

        while time.time() - start_time < max_wait:
            try:
                history_response = requests.get(f"{comfyui_url}/history/{prompt_id}", timeout=10)
                if history_response.status_code == 200:
                    history = history_response.json()
                    if prompt_id in history:
                        # 任务完成
                        result_data = history[prompt_id]
                        logger.info(f"工作流执行完成: {prompt_id}")
                        break
            except requests.exceptions.RequestException as e:
                logger.warning(f"查询历史记录失败: {e}")

            time.sleep(3)
        else:
            raise Exception("任务超时，ComfyUI可能处理时间过长")

        if not result_data:
            raise Exception("未获取到执行结果")

        # 处理结果 - 完善文件路径提取逻辑
        processed_result = self._process_comfyui_result(result_data, task_id)

        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result_data=processed_result
        )

        # 检查执行结果
        if result.status == TaskStatus.COMPLETED:
            # 更新任务状态为完成
            self.update_task_status(task_id, {
                'status': TaskStatus.COMPLETED.value,
                'message': '文生图任务完成',
                'progress': 100,
                'result_data': result.result_data
            })

            logger.info(f"文生图任务完成: {task_id}")
            return {
                'status': 'completed',
                'result': result.result_data,
                'message': '文生图任务完成'
            }
        else:
            raise WorkflowExecutionError(result.error_message or "工作流执行失败")
            
    except Exception as e:
        logger.error(f"文生图任务执行失败 {task_id}: {e}")

        # 更新任务状态为失败
        self.update_task_status(task_id, {
            'status': TaskStatus.FAILED.value,
            'message': f'任务执行失败: {str(e)}',
            'error_message': str(e),
            'progress': 0
        })

        # 返回失败结果而不是抛出异常，避免 Celery Worker 崩溃
        return {
            'status': 'failed',
            'error': str(e),
            'message': f'任务执行失败: {str(e)}',
            'task_id': task_id
        }


@celery_app.task(bind=True, base=BaseWorkflowTask, queue='image_to_video')
def execute_image_to_video_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行图生视频任务"""
    task_id = request_data.get('task_id')
    if not task_id:
        raise Exception("任务ID缺失，无法执行任务")

    try:
        logger.info(f"开始执行图生视频任务: {task_id}")

        # 更新任务状态为处理中
        self.update_task_status(task_id, {
            'status': 'processing',
            'progress': 0,
            'message': '正在处理图生视频任务...'
        })

        # 获取工作流参数处理器
        from ..core.workflow_parameter_processor import get_workflow_parameter_processor
        processor = get_workflow_parameter_processor()

        # 获取工作流名称，默认使用配置的默认工作流
        workflow_name = request_data.get('workflow_name', 'Wan2.1 i2v')

        # 处理图片路径 - 将相对路径转换为绝对路径
        image_path = request_data.get('image', '')
        if image_path:
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(image_path):
                from ..api.routes import UPLOAD_DIR
                full_image_path = os.path.join(UPLOAD_DIR, image_path)
                if os.path.exists(full_image_path):
                    request_data['image'] = full_image_path
                    logger.info(f"图片路径转换: {image_path} -> {full_image_path}")
                else:
                    raise Exception(f"图片文件不存在: {full_image_path}")
            else:
                # 检查绝对路径是否存在
                if not os.path.exists(image_path):
                    raise Exception(f"图片文件不存在: {image_path}")

        # 处理工作流参数
        logger.info(f"处理工作流参数: {workflow_name}")
        processed_workflow = processor.process_workflow_request(workflow_name, request_data)

        if not processed_workflow:
            raise Exception(f"工作流 {workflow_name} 处理失败")

        # 更新进度
        self.update_task_status(task_id, {
            'status': 'processing',
            'progress': 20,
            'message': '工作流参数处理完成，正在提交到ComfyUI...'
        })

        # 获取ComfyUI客户端
        from ..core.comfyui_client import get_comfyui_client
        client = get_comfyui_client()

        # 提交工作流到ComfyUI
        logger.info(f"提交工作流到ComfyUI: {task_id}")
        prompt_id = client.queue_prompt(processed_workflow)

        if not prompt_id:
            raise Exception("提交工作流到ComfyUI失败")

        # 更新进度
        self.update_task_status(task_id, {
            'status': 'processing',
            'progress': 40,
            'message': f'工作流已提交到ComfyUI，提示ID: {prompt_id}'
        })

        # 等待任务完成
        logger.info(f"等待ComfyUI任务完成: {prompt_id}")
        result = client.wait_for_completion(prompt_id, timeout=300)  # 5分钟超时

        if not result or not result.get('success'):
            error_msg = result.get('error', '未知错误') if result else 'ComfyUI任务执行失败'
            raise Exception(f"ComfyUI任务执行失败: {error_msg}")

        # 更新进度
        self.update_task_status(task_id, {
            'status': 'processing',
            'progress': 80,
            'message': '视频生成完成，正在处理结果文件...'
        })

        # 处理结果文件
        output_files = result.get('files', [])
        if not output_files:
            raise Exception("未生成任何输出文件")

        logger.info(f"图生视频任务完成: {task_id}, 生成文件: {len(output_files)}")

        # 更新任务状态为完成
        self.update_task_status(task_id, {
            'status': 'completed',
            'progress': 100,
            'message': f'图生视频任务完成，生成了 {len(output_files)} 个文件',
            'result_data': {
                'files': output_files,
                'prompt': request_data.get('prompt', ''),
                'negative_prompt': request_data.get('negative_prompt', ''),
                'workflow_name': workflow_name,
                'image': request_data.get('image', ''),
                'batch_id': request_data.get('batch_id', ''),
                'created_at': request_data.get('created_at', ''),
                'updated_at': datetime.now().isoformat()
            }
        })

        return {
            'task_id': task_id,
            'status': 'completed',
            'files': output_files,
            'message': '图生视频任务执行成功'
        }

    except Exception as e:
        logger.error(f"图生视频任务执行失败 {task_id}: {e}")

        # 更新任务状态为失败
        self.update_task_status(task_id, {
            'status': 'failed',
            'progress': 0,
            'message': f'图生视频任务执行失败: {str(e)}',
            'error_message': str(e)
        })

        # 返回失败结果而不是抛出异常，避免 Celery Worker 崩溃
        return {
            'status': 'failed',
            'error': str(e),
            'message': f'任务执行失败: {str(e)}',
            'task_id': task_id
        }


@celery_app.task(bind=True, base=BaseWorkflowTask)
def execute_generic_workflow_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行通用工作流任务"""
    task_id = request_data.get('task_id', self.request.id)
    
    try:
        logger.info(f"开始执行通用工作流任务: {task_id}")
        
        # 识别任务类型
        task_manager = get_task_type_manager()
        task_type = task_manager.identify_task_type(request_data)
        
        # 根据任务类型调用相应的任务
        if task_type == TaskType.TEXT_TO_IMAGE:
            return execute_text_to_image_task.apply_async(args=[request_data]).get()
        elif task_type == TaskType.IMAGE_TO_VIDEO:
            return execute_image_to_video_task.apply_async(args=[request_data]).get()
        else:
            raise Exception(f"不支持的任务类型: {task_type.value}")
            
    except Exception as e:
        logger.error(f"通用工作流任务执行失败 {task_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


# 任务状态查询函数
def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务状态"""
    try:
        # 从数据库状态管理器获取
        from ..database.task_status_manager import get_database_task_status_manager

        status_manager = get_database_task_status_manager()

        # 首先尝试直接通过task_id获取
        task_info = status_manager.get_task_status(task_id)
        if task_info:
            return task_info

        # 如果没找到，尝试通过celery_task_id查找
        # 这里需要查询数据库中celery_task_id匹配的任务
        from ..database.dao.task_dao import GlobalTaskDAO
        global_task_dao = GlobalTaskDAO()
        task = global_task_dao.get_task_by_celery_id(task_id)
        if task:
            return status_manager._task_to_dict(task)

        # 如果本地存储中没有找到，尝试从Celery获取
        try:
            result = celery_app.AsyncResult(task_id)

            if result.state == 'PENDING':
                return {
                    'status': 'queued',
                    'message': '任务在队列中等待',
                    'progress': 0
                }
            elif result.state == 'PROGRESS':
                # 返回存储在meta中的详细状态信息
                if result.info and isinstance(result.info, dict):
                    return result.info
                else:
                    return {
                        'status': 'processing',
                        'message': '任务处理中',
                        'progress': 50
                    }
            elif result.state == 'SUCCESS':
                # 对于成功的任务，检查meta中是否有详细信息
                if result.info and isinstance(result.info, dict):
                    return result.info
                else:
                    return {
                        'status': 'completed',
                        'message': '任务完成',
                        'progress': 100,
                        'result': result.result
                    }
            elif result.state == 'FAILURE':
                return {
                    'status': 'failed',
                    'message': '任务失败',
                    'error_message': str(result.info),
                    'progress': 0
                }
            elif result.state == 'REVOKED':
                return {
                    'status': 'cancelled',
                    'message': '任务已取消',
                    'progress': 0
                }
            else:
                return {
                    'status': result.state.lower(),
                    'message': f'任务状态: {result.state}',
                    'progress': 0
                }
        except Exception as celery_error:
            logger.debug(f"从Celery获取任务状态失败: {celery_error}")
            return None

    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return None


# 任务取消函数
def cancel_task(task_id: str) -> bool:
    """取消任务"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"任务已取消: {task_id}")
        return True
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return False
