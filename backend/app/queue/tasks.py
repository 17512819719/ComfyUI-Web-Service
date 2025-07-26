"""
Celery任务定义
"""
import asyncio
import logging
import os
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

    def _select_comfyui_node_for_task(self, task_id: str, task_type: str) -> tuple[str, str]:
        """为任务选择ComfyUI节点 - 支持分布式模式

        Returns:
            tuple: (comfyui_url, node_id)
        """
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()

            # 检查是否为分布式模式
            if config_manager.is_distributed_mode():
                # 分布式模式：使用节点管理器选择最佳节点
                try:
                    from ..core.node_manager import get_node_manager
                    from ..core.load_balancer import get_load_balancer
                    from ..core.base import TaskType

                    # 定义异步函数执行器
                    import asyncio
                    import concurrent.futures

                    def run_async_in_thread(coro):
                        """在新线程中运行异步函数"""
                        def run_in_thread():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(coro)
                            finally:
                                new_loop.close()

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_in_thread)
                            return future.result()

                    # 获取节点管理器和负载均衡器
                    node_manager = get_node_manager()
                    load_balancer = get_load_balancer()

                    # 确保节点管理器已启动
                    if not node_manager._running:
                        logger.warning("节点管理器未启动，尝试启动...")
                        try:
                            run_async_in_thread(node_manager.start())
                        except Exception as start_error:
                            logger.error(f"启动节点管理器失败: {start_error}")
                            raise Exception("节点管理器启动失败")

                    # 转换任务类型
                    task_type_enum = TaskType.TEXT_TO_IMAGE if task_type == 'text_to_image' else TaskType.IMAGE_TO_VIDEO

                    # 获取可用节点
                    available_nodes = run_async_in_thread(node_manager.get_available_nodes(task_type_enum))

                    logger.info(f"可用节点: {available_nodes}")

                    if not available_nodes:
                        logger.warning("分布式模式：没有可用的ComfyUI节点，降级到单机模式")
                        raise Exception("没有可用节点")

                    # 使用负载均衡器选择节点
                    selected_node = load_balancer.select_node(available_nodes, task_type_enum)

                    if not selected_node:
                        logger.warning("分布式模式：负载均衡器无法选择节点，降级到单机模式")
                        raise Exception("负载均衡器选择失败")

                    # 分配任务到节点
                    run_async_in_thread(node_manager.assign_task_to_node(selected_node.node_id, task_id))

                    logger.info(f"分布式模式：任务 {task_id} 分配到节点 {selected_node.node_id} ({selected_node.url})")
                    return selected_node.url, selected_node.node_id

                except Exception as e:
                    logger.error(f"分布式节点选择失败: {e}")
                    # 降级到单机模式
                    pass

            # 单机模式或分布式降级：使用配置文件中的ComfyUI配置
            comfyui_config = config_manager.get_comfyui_config()
            comfyui_host = comfyui_config.get('host', '127.0.0.1')
            comfyui_port = comfyui_config.get('port', 8188)
            comfyui_url = f"http://{comfyui_host}:{comfyui_port}"

            logger.info(f"单机模式：使用配置文件ComfyUI实例 {comfyui_url}")
            return comfyui_url, "default"

        except Exception as e:
            logger.error(f"选择ComfyUI节点失败: {e}")
            # 最终降级到默认配置
            return "http://127.0.0.1:8188", "default"

    def _prepare_distributed_task_files(self, request_data: Dict[str, Any], selected_node_id: str) -> Dict[str, Any]:
        """为分布式任务准备文件下载信息"""
        if selected_node_id == "default":
            # 单机模式，无需处理文件下载
            return request_data

        try:
            # 检查是否为图生视频任务且包含图片
            if request_data.get('task_type') == 'image_to_video' and request_data.get('image'):
                logger.info(f"[TASK_FILE_PREP] 为图生视频任务准备文件下载: {request_data.get('task_id')}")

                # 使用文件场景适配器准备下载信息
                from ..services.file_scenario_adapter import get_file_scenario_adapter
                adapter = get_file_scenario_adapter()

                # 异步调用适配器
                import asyncio
                import concurrent.futures

                def run_async_in_thread(coro):
                    """在新线程中运行异步函数"""
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(coro)
                        finally:
                            new_loop.close()

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        return future.result()

                # 准备文件下载信息
                updated_request_data = run_async_in_thread(
                    adapter.handle_image_upload_to_node(request_data, selected_node_id)
                )

                logger.info(f"[TASK_FILE_PREP] 文件下载信息准备完成: {request_data.get('task_id')}")
                return updated_request_data

            return request_data

        except Exception as e:
            logger.error(f"[TASK_FILE_PREP] 准备分布式任务文件失败: {e}")
            import traceback
            logger.error(f"[TASK_FILE_PREP] 错误堆栈: {traceback.format_exc()}")
            # 对于图生视频任务，文件下载信息准备失败应该中止任务
            if request_data.get('task_type') == 'image_to_video':
                raise Exception(f"图生视频任务文件准备失败: {str(e)}")
            # 其他任务类型返回原始数据
            return request_data

    def _cleanup_node_assignment(self, task_id: str, node_id: str):
        """清理节点任务分配"""
        if node_id == "default":
            return  # 单机模式，无需清理

        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()

            if config_manager.is_distributed_mode():
                from ..core.node_manager import get_node_manager
                node_manager = get_node_manager()

                import asyncio
                asyncio.run(node_manager.remove_task_from_node(node_id, task_id))
                logger.debug(f"已清理节点任务分配: {task_id} <- {node_id}")
        except Exception as e:
            logger.warning(f"清理节点任务分配失败: {e}")

    def _process_comfyui_result(self, result_data: Dict, task_id: str, node_id: str = "default") -> Dict:
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
                                # 在分布式模式下，构建特殊的文件路径标识
                                if node_id != "default":
                                    # 分布式模式：使用相对路径，代理服务会处理
                                    if subfolder:
                                        # 保持ComfyUI原始的路径分隔符格式
                                        # ComfyUI在Windows上通常使用反斜杠
                                        if '\\' in subfolder:
                                            file_path = f"{subfolder}\\{filename}"
                                        else:
                                            file_path = f"{subfolder}/{filename}"
                                    else:
                                        file_path = filename
                                    files.append(file_path)
                                    logger.info(f"分布式模式文件路径: {file_path} (节点: {node_id})")
                                else:
                                    # 单机模式：使用完整本地路径
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

    def _extract_generation_params(self, request_data: Dict[str, Any], workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """从请求数据和工作流数据中提取生成参数"""
        params = {}

        # 从请求数据中提取基础参数
        param_mapping = {
            'model_name': 'checkpoint',  # checkpoint映射到model_name
            'width': 'width',
            'height': 'height',
            'steps': 'steps',
            'cfg_scale': 'cfg_scale',
            'sampler': 'sampler',
            'scheduler': 'scheduler',
            'seed': 'seed',
            'batch_size': 'batch_size'
        }

        for db_field, request_field in param_mapping.items():
            if request_field in request_data:
                params[db_field] = request_data[request_field]

        # 从工作流数据中提取参数（如果请求数据中没有）
        if workflow_data and isinstance(workflow_data, dict):
            # 尝试从工作流节点中提取参数
            try:
                # 检查新格式工作流（nodes数组）
                if 'nodes' in workflow_data:
                    for node in workflow_data.get('nodes', []):
                        if isinstance(node, dict) and 'inputs' in node:
                            inputs = node['inputs']
                            # 提取常见参数
                            if 'ckpt_name' in inputs and 'model_name' not in params:
                                params['model_name'] = inputs['ckpt_name']
                            if 'width' in inputs and 'width' not in params:
                                params['width'] = inputs['width']
                            if 'height' in inputs and 'height' not in params:
                                params['height'] = inputs['height']
                            if 'steps' in inputs and 'steps' not in params:
                                params['steps'] = inputs['steps']
                            if 'cfg' in inputs and 'cfg_scale' not in params:
                                params['cfg_scale'] = inputs['cfg']
                            if 'sampler_name' in inputs and 'sampler' not in params:
                                params['sampler'] = inputs['sampler_name']
                            if 'scheduler' in inputs and 'scheduler' not in params:
                                params['scheduler'] = inputs['scheduler']
                            if 'seed' in inputs and 'seed' not in params:
                                params['seed'] = inputs['seed']
                            if 'batch_size' in inputs and 'batch_size' not in params:
                                params['batch_size'] = inputs['batch_size']

                # 检查旧格式工作流（节点字典）
                else:
                    for node_id, node_data in workflow_data.items():
                        if isinstance(node_data, dict) and 'inputs' in node_data:
                            inputs = node_data['inputs']
                            # 同样的参数提取逻辑
                            if 'ckpt_name' in inputs and 'model_name' not in params:
                                params['model_name'] = inputs['ckpt_name']
                            # ... 其他参数提取逻辑类似

            except Exception as e:
                logger.warning(f"从工作流数据中提取参数失败: {e}")

        # 设置默认值
        params.setdefault('batch_size', 1)

        logger.debug(f"提取的生成参数: {params}")
        return params

    def _execute_text_to_image_logic(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行文生图核心逻辑"""
        task_id = request_data.get('task_id')
        if not task_id:
            logger.error("任务ID缺失，无法执行任务")
            return {
                'status': 'failed',
                'error': '任务ID缺失，无法执行任务',
                'message': '任务ID缺失，无法执行任务'
            }

        try:
            logger.info(f"开始执行文生图任务: {task_id}")

            # 更新任务状态为处理中
            self.update_task_status(task_id, {
                'status': 'processing',
                'progress': 0,
                'message': '正在处理文生图任务...'
            })

            # 获取工作流参数处理器
            from ..core.workflow_parameter_processor import get_workflow_parameter_processor
            processor = get_workflow_parameter_processor()

            # 获取工作流名称，默认使用配置的默认工作流
            workflow_name = request_data.get('workflow_name', 'sd_basic')

            # 更新进度
            self.update_task_status(task_id, {
                'status': 'processing',
                'progress': 10,
                'message': '正在处理工作流参数...'
            })

            # 处理工作流参数
            logger.info(f"处理工作流参数: {workflow_name}")
            complete_workflow = processor.process_workflow_request(workflow_name, request_data)

            if not complete_workflow:
                raise Exception(f"工作流 {workflow_name} 处理失败")

            # 更新进度
            self.update_task_status(task_id, {
                'status': 'processing',
                'progress': 20,
                'message': '工作流参数处理完成，正在提交到ComfyUI...'
            })

            # 选择ComfyUI节点 - 支持分布式模式
            comfyui_url, selected_node_id = self._select_comfyui_node_for_task(task_id, 'text_to_image')

            # 执行工作流
            import requests
            import time

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

            except requests.exceptions.ConnectionError as e:
                error_msg = f"无法连接到ComfyUI服务器 (URL: {comfyui_url})"
                logger.error(error_msg)
                raise Exception(error_msg)
            except requests.exceptions.Timeout as e:
                error_msg = f"ComfyUI请求超时 (URL: {comfyui_url})"
                logger.error(error_msg)
                raise Exception(error_msg)
            except Exception as e:
                logger.error(f"提交工作流失败: {e}")
                raise

            # 更新进度
            self.update_task_status(task_id, {
                'status': 'processing',
                'progress': 30,
                'message': f'工作流已提交，正在等待ComfyUI处理... (ID: {prompt_id})'
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
            processed_result = self._process_comfyui_result(result_data, task_id, selected_node_id)

            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result_data=processed_result
            )

            if result.status == TaskStatus.COMPLETED:
                # 从工作流中提取实际使用的参数（如果有的话）
                workflow_extracted_params = self._extract_generation_params(request_data, complete_workflow)

                # 更新任务状态为完成
                update_data = {
                    'status': TaskStatus.COMPLETED.value,
                    'progress': 100,
                    'message': '文生图任务完成',
                    'result_data': result.result_data,
                    'completed_at': datetime.now(),
                    'updated_at': datetime.now().isoformat()
                }

                # 只添加从工作流中实际提取到的参数（避免覆盖已存储的参数）
                if workflow_extracted_params:
                    # 只更新那些从工作流中成功提取到且与原始参数不同的参数
                    for key, value in workflow_extracted_params.items():
                        if value is not None and key not in ['batch_id', 'created_at']:  # 排除非核心参数
                            update_data[key] = value

                self.update_task_status(task_id, update_data)

                # 清理节点任务分配
                self._cleanup_node_assignment(task_id, selected_node_id)

                logger.info(f"文生图任务完成: {task_id}")
                return {
                    'status': 'completed',
                    'result': result.result_data,
                    'message': '文生图任务完成'
                }
            else:
                error_msg = result.error_message or "工作流执行失败"
                logger.error(f"文生图任务执行失败 {task_id}: {error_msg}")

                # 更新任务状态为失败
                self.update_task_status(task_id, {
                    'status': TaskStatus.FAILED.value,
                    'message': f'任务执行失败: {error_msg}',
                    'error_message': error_msg,
                    'progress': 0
                })

                # 清理节点任务分配
                self._cleanup_node_assignment(task_id, selected_node_id)

                # 返回失败结果而不是抛出异常
                return {
                    'status': 'failed',
                    'error': error_msg,
                    'message': f'任务执行失败: {error_msg}',
                    'task_id': task_id
                }

        except Exception as e:
            logger.error(f"文生图任务执行失败 {task_id}: {e}")

            # 清理节点任务分配（如果已选择节点）
            try:
                if 'selected_node_id' in locals():
                    self._cleanup_node_assignment(task_id, selected_node_id)
            except:
                pass

            # 更新任务状态为失败
            logger.info(f"[TASK_FAILED] 任务 {task_id} 执行失败，更新状态...")

            # 获取当前任务状态以检查参数是否完整
            current_status = self.get_task_status(task_id)
            if current_status:
                logger.info(f"[TASK_FAILED] 任务 {task_id} 当前状态中的参数:")
                critical_params = ['model_name', 'width', 'height', 'seed', 'steps', 'cfg_scale']
                for param in critical_params:
                    value = current_status.get(param)
                    logger.info(f"  - {param}: {value} ({'✓' if value is not None else '✗'})")

            self.update_task_status(task_id, {
                'status': TaskStatus.FAILED.value,
                'message': f'任务执行失败: {str(e)}',
                'error_message': str(e),
                'progress': 0,
                'completed_at': datetime.now(),
                'updated_at': datetime.now().isoformat()
            })

            logger.info(f"[TASK_FAILED] 任务 {task_id} 失败状态更新完成")

            # 返回失败结果而不是抛出异常，避免 Celery Worker 崩溃
            return {
                'status': 'failed',
                'error': str(e),
                'message': f'任务执行失败: {str(e)}',
                'task_id': task_id,
                'error_type': type(e).__name__,  # 添加异常类型信息
                'exc_type': type(e).__name__,    # Celery需要的异常类型字段
                'exc_message': str(e)            # Celery需要的异常消息字段
            }

    def _execute_image_to_video_logic(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行图生视频核心逻辑"""
        task_id = request_data.get('task_id')
        if not task_id:
            logger.error("任务ID缺失，无法执行任务")
            return {
                'status': 'failed',
                'error': '任务ID缺失，无法执行任务',
                'message': '任务ID缺失，无法执行任务'
            }

        try:
            logger.info(f"开始执行图生视频任务: {task_id}")

            # 更新任务状态为处理中
            self.update_task_status(task_id, {
                'status': 'processing',
                'progress': 0,
                'message': '正在处理图生视频任务...'
            })

            # 准备远程文件下载指令（如果需要）
            file_downloads = []
            if 'image_download_info' in request_data:
                download_info = request_data['image_download_info']
                logger.info(f"[TASK] 检测到图片下载信息，准备远程下载指令: {task_id}")
                logger.info(f"[TASK] 下载URL: {download_info.get('download_url')}")
                logger.info(f"[TASK] 本地路径: {download_info.get('local_path')}")

                # 构建文件下载指令
                file_download = {
                    'download_url': download_info.get('download_url'),
                    'local_path': download_info.get('local_path'),
                    'filename': download_info.get('filename'),
                    'file_size': download_info.get('file_size', 0),
                    'target_field': '54.inputs.image'  # LoadImage节点的image输入
                }
                file_downloads.append(file_download)

                # 更新工作流中的图片路径为下载后的本地路径
                request_data['image'] = download_info.get('local_path')

                logger.info(f"[TASK] 远程下载指令准备完成: {task_id}")
                logger.info(f"[TASK] 图片路径设置为: {request_data.get('image')}")
            else:
                logger.info(f"[TASK] 任务不包含文件下载信息，直接执行: {task_id}")
                logger.info(f"[TASK] 当前图片路径: {request_data.get('image', 'N/A')}")

            # 获取工作流参数处理器
            from ..core.workflow_parameter_processor import get_workflow_parameter_processor
            processor = get_workflow_parameter_processor()

            # 获取工作流名称
            workflow_name = request_data.get('workflow_name', 'svd_basic')

            # 更新进度
            self.update_task_status(task_id, {
                'status': 'processing',
                'progress': 10,
                'message': '正在处理工作流参数...'
            })

            # 处理工作流参数
            logger.info(f"处理工作流参数: {workflow_name}")
            complete_workflow = processor.process_workflow_request(workflow_name, request_data)

            if not complete_workflow:
                raise Exception(f"工作流 {workflow_name} 处理失败")

            # 更新进度
            self.update_task_status(task_id, {
                'status': 'processing',
                'progress': 20,
                'message': '工作流参数处理完成，正在提交到ComfyUI...'
            })

            # 选择ComfyUI节点 - 支持分布式模式
            comfyui_url, selected_node_id = self._select_comfyui_node_for_task(task_id, 'image_to_video')

            # 为分布式任务准备文件下载信息
            logger.info(f"[TASK] 准备分布式任务文件，节点: {selected_node_id}")
            try:
                request_data = self._prepare_distributed_task_files(request_data, selected_node_id)
                logger.info(f"[TASK] 分布式任务文件准备完成")
            except Exception as e:
                logger.error(f"[TASK] 分布式任务文件准备失败: {e}")
                raise

            # 执行工作流
            import requests
            import time

            logger.info(f"提交工作流到ComfyUI: {task_id}")

            # 提交工作流
            try:
                logger.info(f"向ComfyUI提交工作流: {comfyui_url}/prompt")

                # 构建提交数据，包含文件下载指令
                prompt_data = {
                    "prompt": complete_workflow,
                    "client_id": task_id
                }

                # 如果有文件下载指令，添加到请求中
                if file_downloads:
                    prompt_data["file_downloads"] = file_downloads
                    logger.info(f"[TASK] 添加文件下载指令到工作流: {len(file_downloads)} 个文件")
                    for i, download in enumerate(file_downloads):
                        logger.info(f"[TASK] 下载指令 {i+1}: {download['download_url']} -> {download['local_path']}")

                response = requests.post(f"{comfyui_url}/prompt", json=prompt_data, timeout=30)

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

            except requests.exceptions.ConnectionError as e:
                error_msg = f"无法连接到ComfyUI服务器 (URL: {comfyui_url})"
                logger.error(error_msg)
                raise Exception(error_msg)
            except requests.exceptions.Timeout as e:
                error_msg = f"ComfyUI请求超时 (URL: {comfyui_url})"
                logger.error(error_msg)
                raise Exception(error_msg)
            except Exception as e:
                logger.error(f"提交工作流失败: {e}")
                raise

            # 更新进度
            self.update_task_status(task_id, {
                'status': 'processing',
                'progress': 30,
                'message': f'工作流已提交，正在等待ComfyUI处理... (ID: {prompt_id})'
            })

            # 等待完成
            max_wait = 600  # 10分钟（视频生成需要更长时间）
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

                time.sleep(5)  # 视频生成检查间隔更长
            else:
                raise Exception("任务超时，ComfyUI可能处理时间过长")

            if not result_data:
                raise Exception("未获取到执行结果")

            # 处理结果文件 - 使用统一的文件处理逻辑
            processed_result = self._process_comfyui_result(result_data, task_id, selected_node_id)
            output_files = processed_result.get('files', [])

            if not output_files:
                raise Exception("未生成任何输出文件")

            # 更新任务状态为完成
            self.update_task_status(task_id, {
                'status': 'completed',
                'progress': 100,
                'message': '图生视频任务执行成功',
                'completed_at': datetime.now(),
                'updated_at': datetime.now().isoformat(),
                'result_data': {
                    'files': output_files,
                    'prompt_id': prompt_id
                }
            })

            # 清理节点任务分配
            self._cleanup_node_assignment(task_id, selected_node_id)

            return {
                'task_id': task_id,
                'status': 'completed',
                'files': output_files,
                'message': '图生视频任务执行成功'
            }

        except Exception as e:
            logger.error(f"图生视频任务执行失败 {task_id}: {e}")

            # 清理节点任务分配（如果已选择节点）
            try:
                if 'selected_node_id' in locals():
                    self._cleanup_node_assignment(task_id, selected_node_id)
            except:
                pass

            # 更新任务状态为失败
            self.update_task_status(task_id, {
                'status': 'failed',
                'progress': 0,
                'message': f'图生视频任务执行失败: {str(e)}',
                'error_message': str(e),
                'completed_at': datetime.now(),
                'updated_at': datetime.now().isoformat()
            })

            # 返回失败结果而不是抛出异常，避免 Celery Worker 崩溃
            return {
                'status': 'failed',
                'error': str(e),
                'message': f'任务执行失败: {str(e)}',
                'task_id': task_id,
                'error_type': type(e).__name__,  # 添加异常类型信息
                'exc_type': type(e).__name__,    # Celery需要的异常类型字段
                'exc_message': str(e)            # Celery需要的异常消息字段
            }


@celery_app.task(bind=True, base=BaseWorkflowTask, queue='text_to_image')
def execute_text_to_image_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行文生图任务"""
    # 修复：确保使用API层传递的task_id，而不是Celery任务ID
    task_id = request_data.get('task_id')
    if not task_id:
        logger.error("任务ID缺失，无法执行任务")
        return {
            'status': 'failed',
            'error': '任务ID缺失，无法执行任务',
            'message': '任务ID缺失，无法执行任务'
        }

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

        # 执行工作流 - 支持分布式模式
        import requests
        import time
        import os

        # 选择ComfyUI节点 - 支持分布式模式
        comfyui_url, selected_node_id = self._select_comfyui_node_for_task(task_id, 'text_to_image')

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
        processed_result = self._process_comfyui_result(result_data, task_id, selected_node_id)

        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result_data=processed_result
        )

        # 检查执行结果
        if result.status == TaskStatus.COMPLETED:
            # 从工作流中提取实际使用的参数（如果有的话）
            workflow_extracted_params = self._extract_generation_params(request_data, complete_workflow)

            # 更新任务状态为完成
            update_data = {
                'status': TaskStatus.COMPLETED.value,
                'message': '文生图任务完成',
                'progress': 100,
                'result_data': result.result_data,
                'completed_at': datetime.now(),
                'updated_at': datetime.now().isoformat()
            }

            # 只添加从工作流中实际提取到的参数（避免覆盖已存储的参数）
            if workflow_extracted_params:
                # 只更新那些从工作流中成功提取到且与原始参数不同的参数
                for key, value in workflow_extracted_params.items():
                    if value is not None and key not in ['batch_id', 'created_at']:  # 排除非核心参数
                        update_data[key] = value

            self.update_task_status(task_id, update_data)

            # 清理节点任务分配
            self._cleanup_node_assignment(task_id, selected_node_id)

            logger.info(f"文生图任务完成: {task_id}")
            return {
                'status': 'completed',
                'result': result.result_data,
                'message': '文生图任务完成'
            }
        else:
            error_msg = result.error_message or "工作流执行失败"
            logger.error(f"文生图任务执行失败 {task_id}: {error_msg}")

            # 更新任务状态为失败
            self.update_task_status(task_id, {
                'status': TaskStatus.FAILED.value,
                'message': f'任务执行失败: {error_msg}',
                'error_message': error_msg,
                'progress': 0
            })

            # 清理节点任务分配
            self._cleanup_node_assignment(task_id, selected_node_id)

            # 返回失败结果而不是抛出异常
            return {
                'status': 'failed',
                'error': error_msg,
                'message': f'任务执行失败: {error_msg}',
                'task_id': task_id
            }
            
    except Exception as e:
        logger.error(f"文生图任务执行失败 {task_id}: {e}")

        # 清理节点任务分配（如果已选择节点）
        try:
            if 'selected_node_id' in locals():
                self._cleanup_node_assignment(task_id, selected_node_id)
        except:
            pass

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
            'task_id': task_id,
            'error_type': type(e).__name__,  # 添加异常类型信息
            'exc_type': type(e).__name__,    # Celery需要的异常类型字段
            'exc_message': str(e)            # Celery需要的异常消息字段
        }


@celery_app.task(bind=True, base=BaseWorkflowTask, queue='image_to_video')
def execute_image_to_video_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行图生视频任务 - 兼容性包装器"""
    # 直接调用核心逻辑，避免任务套任务
    return self._execute_image_to_video_logic(request_data)


@celery_app.task(bind=True, base=BaseWorkflowTask, queue='text_to_image')
def execute_text_to_image_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行文生图任务 - 兼容性包装器"""
    # 直接调用核心逻辑，避免任务套任务
    return self._execute_text_to_image_logic(request_data)


@celery_app.task(bind=True, base=BaseWorkflowTask)
def execute_generic_workflow_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行通用工作流任务 - 分布式优化版本"""
    task_id = request_data.get('task_id', self.request.id)

    try:
        logger.info(f"开始执行通用工作流任务: {task_id}")

        # 识别任务类型
        task_manager = get_task_type_manager()
        task_type = task_manager.identify_task_type(request_data)

        # 直接执行对应的业务逻辑，而不是调用其他任务
        if task_type == TaskType.TEXT_TO_IMAGE:
            return self._execute_text_to_image_logic(request_data)
        elif task_type == TaskType.IMAGE_TO_VIDEO:
            return self._execute_image_to_video_logic(request_data)
        else:
            raise Exception(f"不支持的任务类型: {task_type.value}")

    except Exception as e:
        logger.error(f"通用工作流任务执行失败 {task_id}: {e}")

        # 更新任务状态为失败
        self.update_task_status(task_id, {
            'status': TaskStatus.FAILED.value,
            'message': f'任务执行失败: {str(e)}',
            'error_message': str(e),
            'progress': 0
        })

        # 返回失败结果而不是重试
        return {
            'status': 'failed',
            'error': str(e),
            'message': f'任务执行失败: {str(e)}',
            'task_id': task_id
        }


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
