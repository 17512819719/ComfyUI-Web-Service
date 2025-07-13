"""
Celery任务定义
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from celery import Task
from ..core.base import TaskType, TaskRequest, TaskResult, TaskStatus
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

            # 优化：使用线程安全的方式更新本地任务状态存储
            from ..api.routes import task_status_store
            import threading

            # 使用锁确保原子性更新
            if not hasattr(self, '_status_lock'):
                self._status_lock = threading.Lock()

            with self._status_lock:
                if task_id in task_status_store:
                    # 合并状态数据，保留重要字段
                    current_status = task_status_store[task_id].copy()
                    current_status.update(status_data)
                    current_status['updated_at'] = datetime.now().isoformat()
                    task_status_store[task_id] = current_status

                    logger.debug(f"任务状态已更新: {task_id} -> {status}")

        except Exception as e:
            logger.error(f"更新任务状态失败 [{task_id}]: {e}")

    def _process_comfyui_result(self, result_data: Dict, task_id: str) -> Dict:
        """处理ComfyUI返回的结果数据，提取文件路径"""
        import os  # 添加os导入
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()
            comfyui_config = config_manager.get_comfyui_config()
            output_dir = comfyui_config.get('output_dir', 'E:\\ComfyUI\\ComfyUI\\output')

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
                raise Exception(f"ComfyUI API调用失败: {error_detail}")

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
            raise Exception(result.error_message or "工作流执行失败")
            
    except Exception as e:
        logger.error(f"文生图任务执行失败 {task_id}: {e}")
        
        # 更新任务状态为失败
        self.update_task_status(task_id, {
            'status': TaskStatus.FAILED.value,
            'message': f'任务执行失败: {str(e)}',
            'error_message': str(e),
            'progress': 0
        })
        
        # 不重试，直接失败
        return {
            'status': 'failed',
            'error': str(e),
            'message': f'任务执行失败: {str(e)}'
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
        else:
            raise Exception(f"不支持的任务类型: {task_type.value}")
            
    except Exception as e:
        logger.error(f"通用工作流任务执行失败 {task_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


# 任务状态查询函数
def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务状态"""
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
