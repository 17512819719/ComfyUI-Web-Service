"""
工作流执行器
统一的工作流执行接口
"""
import os
import json
import asyncio
import aiohttp
import websockets
from typing import Dict, List, Any, Optional, Callable
import logging
from pathlib import Path
from .base import (
    TaskType, TaskResult, TaskStatus, WorkflowConfig,
    BaseWorkflowExecutor, WorkflowExecutionError, ComfyUINode
)
from .config_manager import get_config_manager

logger = logging.getLogger(__name__)


class ComfyUIWorkflowExecutor(BaseWorkflowExecutor):
    """ComfyUI工作流执行器 - 支持分布式节点"""

    def __init__(self):
        self.config_manager = get_config_manager()

        # 基础配置
        self.timeout = 300  # 默认超时时间

        # 分布式模式支持
        self.is_distributed = self.config_manager.is_distributed_mode()
        self.node_manager = None
        self.load_balancer = None

        # 单机模式兼容配置（仅在非分布式模式下使用）
        self.single_mode_config = None

        if self.is_distributed:
            # 分布式模式：初始化分布式组件
            self._init_distributed_components()
        else:
            # 单机模式：初始化单机配置
            self._init_single_mode_config()

    def _init_single_mode_config(self):
        """初始化单机模式配置"""
        try:
            comfyui_config = self.config_manager.get_comfyui_config()
            self.single_mode_config = {
                'host': comfyui_config.get('host', '127.0.0.1'),
                'port': comfyui_config.get('port', 8188),
                'timeout': comfyui_config.get('timeout', 300),
            }

            # 构建URL
            host = self.single_mode_config['host']
            port = self.single_mode_config['port']
            self.single_mode_config['base_url'] = f"http://{host}:{port}"
            self.single_mode_config['ws_url'] = f"ws://{host}:{port}/ws"

            # 更新超时时间
            self.timeout = self.single_mode_config['timeout']

            logger.info(f"单机模式已配置: {self.single_mode_config['base_url']}")
        except Exception as e:
            logger.error(f"初始化单机模式配置失败: {e}")
            # 使用默认配置
            self.single_mode_config = {
                'host': '127.0.0.1',
                'port': 8188,
                'timeout': 300,
                'base_url': 'http://127.0.0.1:8188',
                'ws_url': 'ws://127.0.0.1:8188/ws'
            }

    def _init_distributed_components(self):
        """初始化分布式组件"""
        try:
            from .node_manager import get_node_manager
            from .load_balancer import get_load_balancer

            self.node_manager = get_node_manager()
            self.load_balancer = get_load_balancer()
            logger.info("分布式模式已启用")
        except Exception as e:
            logger.error(f"初始化分布式组件失败: {e}")
            self.is_distributed = False
            # 降级到单机模式
            logger.warning("降级到单机模式")
            self._init_single_mode_config()

    def get_execution_url(self, task_type: str = None, task_id: str = None) -> tuple[str, str]:
        """获取执行URL - 支持分布式和单机模式

        Returns:
            tuple: (base_url, node_id)
        """
        if self.is_distributed and self.node_manager and self.load_balancer:
            try:
                # 分布式模式：使用负载均衡器选择节点
                from .base import TaskType

                # 转换任务类型
                if task_type == 'text_to_image':
                    task_type_enum = TaskType.TEXT_TO_IMAGE
                elif task_type == 'image_to_video':
                    task_type_enum = TaskType.IMAGE_TO_VIDEO
                else:
                    task_type_enum = TaskType.TEXT_TO_IMAGE  # 默认

                # 获取可用节点
                import asyncio
                available_nodes = asyncio.run(self.node_manager.get_available_nodes(task_type_enum))

                if available_nodes:
                    # 选择最佳节点
                    selected_node = self.load_balancer.select_node(available_nodes, task_type_enum)
                    if selected_node:
                        if task_id:
                            # 分配任务到节点
                            asyncio.run(self.node_manager.assign_task_to_node(selected_node.node_id, task_id))

                        logger.debug(f"分布式模式选择节点: {selected_node.node_id} ({selected_node.url})")
                        return selected_node.url, selected_node.node_id

                # 没有可用节点，降级到单机模式
                logger.warning("没有可用的分布式节点，降级到单机模式")

            except Exception as e:
                logger.error(f"分布式节点选择失败: {e}")

        # 单机模式或分布式降级
        if self.single_mode_config:
            base_url = self.single_mode_config['base_url']
            logger.debug(f"单机模式URL: {base_url}")
            return base_url, "default"
        else:
            # 最终降级
            default_url = "http://127.0.0.1:8188"
            logger.warning(f"使用默认URL: {default_url}")
            return default_url, "default"

    def cleanup_task_assignment(self, task_id: str, node_id: str):
        """清理任务分配"""
        if self.is_distributed and self.node_manager and node_id != "default":
            try:
                import asyncio
                asyncio.run(self.node_manager.remove_task_from_node(node_id, task_id))
                logger.debug(f"已清理任务分配: {task_id} <- {node_id}")
            except Exception as e:
                logger.warning(f"清理任务分配失败: {e}")


    async def execute(self, workflow_config: WorkflowConfig, workflow_data: Dict[str, Any]) -> TaskResult:
        """执行工作流

        Args:
            workflow_config: 工作流配置（用于获取元信息）
            workflow_data: 完整的工作流数据（已注入参数）
        """
        try:
            # 检查输入数据类型
            if isinstance(workflow_data, dict) and ('nodes' in workflow_data or any(key.isdigit() for key in workflow_data.keys())):
                # 这是完整的工作流数据，直接使用
                modified_workflow = workflow_data
                task_id = workflow_data.get('task_id', '')
            else:
                # 这是旧格式的参数数据，使用旧的处理方式
                logger.warning("使用旧格式的参数处理方式")
                workflow_file_data = await self._load_workflow_file(workflow_config.workflow_file)
                modified_workflow = await self._inject_parameters(workflow_file_data, workflow_data)
                task_id = workflow_data.get('task_id', '')

            # 选择执行节点
            selected_node = await self._select_execution_node(workflow_config.task_type, task_id)
            if not selected_node:
                raise WorkflowExecutionError("没有可用的ComfyUI节点")

            # 提交工作流到选定的节点
            prompt_id = await self._submit_workflow_to_node(modified_workflow, selected_node)

            # 监控执行进度
            result = await self._monitor_execution_on_node(prompt_id, task_id, selected_node)

            return result

        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            return TaskResult(
                task_id=parameters.get('task_id', ''),
                status=TaskStatus.FAILED,
                error_message=str(e)
            )

    async def _select_execution_node(self, task_type: TaskType, task_id: str) -> Optional[ComfyUINode]:
        """选择执行节点"""
        if not self.is_distributed:
            # 单机模式，返回默认节点
            from datetime import datetime
            if self.single_mode_config:
                host = self.single_mode_config['host']
                port = self.single_mode_config['port']
            else:
                host = '127.0.0.1'
                port = 8188

            return ComfyUINode(
                node_id="default",
                host=host,
                port=port,
                status=NodeStatus.ONLINE,
                last_heartbeat=datetime.now()
            )

        # 分布式模式，使用负载均衡器选择节点
        if not self.node_manager or not self.load_balancer:
            raise WorkflowExecutionError("分布式组件未初始化")

        # 获取可用节点
        available_nodes = await self.node_manager.get_available_nodes(task_type)
        if not available_nodes:
            raise WorkflowExecutionError("没有可用的ComfyUI节点")

        # 使用负载均衡器选择最佳节点
        selected_node = self.load_balancer.select_node(available_nodes, task_type)
        if not selected_node:
            raise WorkflowExecutionError("负载均衡器无法选择节点")

        # 分配任务到节点
        await self.node_manager.assign_task_to_node(selected_node.node_id, task_id)

        logger.info(f"任务 {task_id} 分配到节点 {selected_node.node_id}")
        return selected_node

    async def _submit_workflow_to_node(self, workflow_data: Dict[str, Any], node: ComfyUINode) -> str:
        """提交工作流到指定节点"""
        if self.is_distributed:
            # 使用节点的URL
            base_url = node.url
        else:
            # 使用单机模式URL
            base_url = self.single_mode_config['base_url'] if self.single_mode_config else "http://127.0.0.1:8188"

        return await self._submit_workflow_with_url(workflow_data, base_url)

    async def _monitor_execution_on_node(self, prompt_id: str, task_id: str, node: ComfyUINode) -> TaskResult:
        """在指定节点上监控执行"""
        try:
            if self.is_distributed:
                # 使用节点的URL
                base_url = node.url
                ws_url = f"ws://{node.host}:{node.port}/ws"
            else:
                # 使用单机模式URL
                if self.single_mode_config:
                    base_url = self.single_mode_config['base_url']
                    ws_url = self.single_mode_config['ws_url']
                else:
                    base_url = "http://127.0.0.1:8188"
                    ws_url = "ws://127.0.0.1:8188/ws"

            result = await self._monitor_execution_with_url(prompt_id, task_id, base_url, ws_url)

            # 任务完成后从节点移除
            if self.is_distributed and self.node_manager:
                await self.node_manager.remove_task_from_node(node.node_id, task_id)

            return result

        except Exception as e:
            # 任务失败时也要从节点移除
            if self.is_distributed and self.node_manager:
                await self.node_manager.remove_task_from_node(node.node_id, task_id)
            raise e

    async def _load_workflow_file(self, workflow_file: str) -> Dict[str, Any]:
        """加载工作流文件"""
        # 直接使用配置文件中的路径，不再添加额外前缀
        workflow_path = os.path.normpath(workflow_file)

        if not os.path.exists(workflow_path):
            raise WorkflowExecutionError(f"工作流文件不存在: {workflow_path}")

        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            logger.debug(f"加载工作流文件: {workflow_path}")
            return workflow_data
        except json.JSONDecodeError as e:
            raise WorkflowExecutionError(f"工作流文件格式错误: {e}")
        except Exception as e:
            raise WorkflowExecutionError(f"加载工作流文件失败: {e}")
    
    async def _inject_parameters(self, workflow_data: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        注入参数到工作流 - 按照用户设计：1:1复制模板并替换用户指定的参数
        只修改用户指定的参数，保留所有默认值以维持预期的图像输出质量
        """
        import copy

        # 深拷贝工作流数据，确保不修改原始模板
        modified_workflow = copy.deepcopy(workflow_data)

        logger.info(f"开始参数注入，用户参数: {list(parameters.keys())}")

        # 只处理用户明确指定的参数，不添加或修改其他参数
        user_params = {k: v for k, v in parameters.items() if v is not None and k != 'task_id'}

        # 处理ComfyUI工作流格式
        if 'nodes' in modified_workflow:
            # 新格式：包含nodes数组
            logger.info("检测到新格式工作流（包含nodes数组）")
            nodes = modified_workflow['nodes']
            for node in nodes:
                if isinstance(node, dict):
                    self._inject_node_parameters_new_format(node, user_params)
        else:
            # 旧格式：节点ID作为键的字典
            logger.info("检测到旧格式工作流（节点字典）")
            for node_id, node_data in modified_workflow.items():
                if isinstance(node_data, dict) and ('inputs' in node_data or 'class_type' in node_data):
                    self._inject_node_parameters_old_format(node_data, user_params, node_id)

        logger.info(f"参数注入完成，处理了 {len(user_params)} 个用户参数")
        return modified_workflow

    def _inject_node_parameters_new_format(self, node: Dict[str, Any], user_params: Dict[str, Any]):
        """为新格式节点注入参数（包含widgets_values和inputs）"""
        node_type = node.get('type', '')
        node_id = node.get('id', 'unknown')
        widgets_values = node.get('widgets_values', [])

        logger.debug(f"处理节点 {node_id} (类型: {node_type})")

        # 1. 处理widgets_values中的占位符
        if widgets_values:
            for i, value in enumerate(widgets_values):
                if isinstance(value, str):
                    # 替换{{placeholder}}格式的占位符
                    original_value = value
                    for param_name, param_value in user_params.items():
                        placeholder = f"{{{{{param_name}}}}}"
                        if placeholder in value:
                            widgets_values[i] = value.replace(placeholder, str(param_value))
                            logger.info(f"节点 {node_id}: 替换占位符 {placeholder} -> {param_value}")

                    # 如果值被修改了，记录日志
                    if widgets_values[i] != original_value:
                        logger.debug(f"节点 {node_id}: widgets_values[{i}] = {widgets_values[i]}")

        # 2. 处理没有占位符的工作流 - 直接修改widgets_values
        if node_type == 'CLIPTextEncode' and widgets_values:
            # 文本编码节点 - 根据现有内容判断是正面还是负面提示词
            current_text = widgets_values[0] if len(widgets_values) > 0 else ""

            # 如果当前文本为空或很短，可能是负面提示词节点
            if len(current_text.strip()) == 0 and 'negative_prompt' in user_params:
                widgets_values[0] = user_params['negative_prompt']
                logger.info(f"节点 {node_id}: 设置负面提示词 = {user_params['negative_prompt'][:50]}...")
            elif len(current_text.strip()) > 0 and 'prompt' in user_params:
                # 有内容的文本节点，替换为正面提示词
                widgets_values[0] = user_params['prompt']
                logger.info(f"节点 {node_id}: 设置正面提示词 = {user_params['prompt'][:50]}...")

        elif node_type in ['KSampler', 'KSamplerAdvanced'] and widgets_values:
            # 采样器节点 - widgets_values通常是: [add_noise, seed, control, steps, cfg, sampler, scheduler, ...]
            if len(widgets_values) >= 10:  # KSamplerAdvanced
                if 'seed' in user_params and isinstance(widgets_values[1], int):
                    widgets_values[1] = user_params['seed']
                    logger.info(f"节点 {node_id}: 设置种子 = {user_params['seed']}")
                if 'steps' in user_params and isinstance(widgets_values[3], int):
                    widgets_values[3] = user_params['steps']
                    logger.info(f"节点 {node_id}: 设置步数 = {user_params['steps']}")
                if 'cfg_scale' in user_params and isinstance(widgets_values[4], (int, float)):
                    widgets_values[4] = user_params['cfg_scale']
                    logger.info(f"节点 {node_id}: 设置CFG = {user_params['cfg_scale']}")
                if 'sampler_name' in user_params and isinstance(widgets_values[5], str):
                    widgets_values[5] = user_params['sampler_name']
                    logger.info(f"节点 {node_id}: 设置采样器 = {user_params['sampler_name']}")
                if 'scheduler' in user_params and isinstance(widgets_values[6], str):
                    widgets_values[6] = user_params['scheduler']
                    logger.info(f"节点 {node_id}: 设置调度器 = {user_params['scheduler']}")

        elif node_type == 'EmptyLatentImage' and widgets_values:
            # 空潜在图像节点 - widgets_values通常是: [width, height, batch_size]
            if len(widgets_values) >= 3:
                if 'width' in user_params and isinstance(widgets_values[0], int):
                    widgets_values[0] = user_params['width']
                    logger.info(f"节点 {node_id}: 设置宽度 = {user_params['width']}")
                if 'height' in user_params and isinstance(widgets_values[1], int):
                    widgets_values[1] = user_params['height']
                    logger.info(f"节点 {node_id}: 设置高度 = {user_params['height']}")
                if 'batch_size' in user_params and isinstance(widgets_values[2], int):
                    widgets_values[2] = user_params['batch_size']
                    logger.info(f"节点 {node_id}: 设置批量大小 = {user_params['batch_size']}")

        elif node_type == 'CheckpointLoaderSimple' and widgets_values:
            # 检查点加载器 - widgets_values通常是: [ckpt_name]
            if len(widgets_values) >= 1 and 'checkpoint' in user_params:
                widgets_values[0] = user_params['checkpoint']
                logger.info(f"节点 {node_id}: 设置检查点 = {user_params['checkpoint']}")

        # 3. 处理inputs中的参数（作为后备方案）
        inputs = node.get('inputs', [])
        if inputs and isinstance(inputs, list):
            for input_item in inputs:
                if isinstance(input_item, dict) and 'name' in input_item:
                    input_name = input_item['name']

                    # 根据节点类型和输入名称进行参数映射
                    if node_type in ['KSampler', 'KSamplerAdvanced']:
                        if input_name == 'steps' and 'steps' in user_params:
                            input_item['value'] = user_params['steps']
                            logger.debug(f"节点 {node_id}: inputs设置采样步数 = {user_params['steps']}")
                        elif input_name == 'cfg' and 'cfg_scale' in user_params:
                            input_item['value'] = user_params['cfg_scale']
                            logger.debug(f"节点 {node_id}: inputs设置CFG = {user_params['cfg_scale']}")
                        elif input_name == 'sampler_name' and 'sampler_name' in user_params:
                            input_item['value'] = user_params['sampler_name']
                            logger.debug(f"节点 {node_id}: inputs设置采样器 = {user_params['sampler_name']}")
                        elif input_name == 'scheduler' and 'scheduler' in user_params:
                            input_item['value'] = user_params['scheduler']
                            logger.debug(f"节点 {node_id}: inputs设置调度器 = {user_params['scheduler']}")
                        elif input_name == 'noise_seed' and 'seed' in user_params:
                            input_item['value'] = user_params['seed']
                            logger.debug(f"节点 {node_id}: inputs设置种子 = {user_params['seed']}")

                    elif node_type == 'EmptyLatentImage':
                        if input_name == 'width' and 'width' in user_params:
                            input_item['value'] = user_params['width']
                            logger.debug(f"节点 {node_id}: inputs设置宽度 = {user_params['width']}")
                        elif input_name == 'height' and 'height' in user_params:
                            input_item['value'] = user_params['height']
                            logger.debug(f"节点 {node_id}: inputs设置高度 = {user_params['height']}")
                        elif input_name == 'batch_size' and 'batch_size' in user_params:
                            input_item['value'] = user_params['batch_size']
                            logger.debug(f"节点 {node_id}: inputs设置批量大小 = {user_params['batch_size']}")

                    elif node_type == 'CheckpointLoaderSimple':
                        if input_name == 'ckpt_name' and 'checkpoint' in user_params:
                            input_item['value'] = user_params['checkpoint']
                            logger.debug(f"节点 {node_id}: inputs设置检查点 = {user_params['checkpoint']}")

                    elif node_type == 'CLIPTextEncode':
                        if input_name == 'text':
                            # 对于文本输入，需要更智能的判断
                            if 'prompt' in user_params and not input_item.get('value'):
                                input_item['value'] = user_params['prompt']
                                logger.debug(f"节点 {node_id}: inputs设置提示词")
                            elif 'negative_prompt' in user_params and not input_item.get('value'):
                                input_item['value'] = user_params['negative_prompt']
                                logger.debug(f"节点 {node_id}: inputs设置负面提示词")

    def _inject_node_parameters_old_format(self, node_data: Dict[str, Any], user_params: Dict[str, Any], node_id: str):
        """为旧格式节点注入参数（直接inputs字典）"""
        inputs = node_data.get('inputs', {})
        class_type = node_data.get('class_type', '')

        logger.debug(f"处理旧格式节点 {node_id} (类型: {class_type})")

        # 处理占位符替换
        for input_name, input_value in inputs.items():
            if isinstance(input_value, str) and '{{' in input_value and '}}' in input_value:
                # 替换占位符
                original_value = input_value
                for param_name, param_value in user_params.items():
                    placeholder = f"{{{{{param_name}}}}}"
                    if placeholder in input_value:
                        inputs[input_name] = input_value.replace(placeholder, str(param_value))
                        logger.info(f"节点 {node_id}: 替换占位符 {placeholder} -> {param_value}")
                        break

        # 根据节点类型和用户参数进行精确匹配
        if class_type == 'CLIPTextEncode':
            # 文本编码节点 - 处理提示词
            if 'prompt' in user_params and 'text' in inputs:
                if '{{prompt}}' in str(inputs['text']):
                    inputs['text'] = inputs['text'].replace('{{prompt}}', user_params['prompt'])
                    logger.info(f"节点 {node_id}: 设置正面提示词")
            if 'negative_prompt' in user_params and 'text' in inputs:
                if '{{negative_prompt}}' in str(inputs['text']):
                    inputs['text'] = inputs['text'].replace('{{negative_prompt}}', user_params['negative_prompt'])
                    logger.info(f"节点 {node_id}: 设置负面提示词")

        elif class_type == 'KSampler':
            # 采样器节点
            if 'steps' in user_params:
                if 'steps' in inputs and ('{{steps}}' in str(inputs['steps']) or inputs['steps'] == '{{steps}}'):
                    inputs['steps'] = user_params['steps']
                    logger.info(f"节点 {node_id}: 设置采样步数 = {user_params['steps']}")
            if 'cfg_scale' in user_params:
                if 'cfg' in inputs and ('{{cfg_scale}}' in str(inputs['cfg']) or inputs['cfg'] == '{{cfg_scale}}'):
                    inputs['cfg'] = user_params['cfg_scale']
                    logger.info(f"节点 {node_id}: 设置CFG = {user_params['cfg_scale']}")
            if 'sampler_name' in user_params:
                if 'sampler_name' in inputs and ('{{sampler_name}}' in str(inputs['sampler_name']) or inputs['sampler_name'] == '{{sampler_name}}'):
                    inputs['sampler_name'] = user_params['sampler_name']
                    logger.info(f"节点 {node_id}: 设置采样器 = {user_params['sampler_name']}")
            if 'scheduler' in user_params:
                if 'scheduler' in inputs and ('{{scheduler}}' in str(inputs['scheduler']) or inputs['scheduler'] == '{{scheduler}}'):
                    inputs['scheduler'] = user_params['scheduler']
                    logger.info(f"节点 {node_id}: 设置调度器 = {user_params['scheduler']}")
            if 'seed' in user_params:
                if 'seed' in inputs and ('{{seed}}' in str(inputs['seed']) or inputs['seed'] == '{{seed}}'):
                    inputs['seed'] = user_params['seed']
                    logger.info(f"节点 {node_id}: 设置种子 = {user_params['seed']}")

        elif class_type == 'EmptyLatentImage':
            # 空潜在图像节点 - 处理尺寸
            if 'width' in user_params:
                if 'width' in inputs and ('{{width}}' in str(inputs['width']) or inputs['width'] == '{{width}}'):
                    inputs['width'] = user_params['width']
                    logger.info(f"节点 {node_id}: 设置宽度 = {user_params['width']}")
            if 'height' in user_params:
                if 'height' in inputs and ('{{height}}' in str(inputs['height']) or inputs['height'] == '{{height}}'):
                    inputs['height'] = user_params['height']
                    logger.info(f"节点 {node_id}: 设置高度 = {user_params['height']}")
            if 'batch_size' in user_params:
                if 'batch_size' in inputs and ('{{batch_size}}' in str(inputs['batch_size']) or inputs['batch_size'] == '{{batch_size}}'):
                    inputs['batch_size'] = user_params['batch_size']
                    logger.info(f"节点 {node_id}: 设置批量大小 = {user_params['batch_size']}")

        elif class_type == 'CheckpointLoaderSimple':
            # 检查点加载器
            if 'checkpoint' in user_params:
                if 'ckpt_name' in inputs and ('{{checkpoint}}' in str(inputs['ckpt_name']) or inputs['ckpt_name'] == '{{checkpoint}}'):
                    inputs['ckpt_name'] = user_params['checkpoint']
                    logger.info(f"节点 {node_id}: 设置检查点 = {user_params['checkpoint']}")
    
    def _inject_common_parameters(self, inputs: Dict[str, Any], parameters: Dict[str, Any]):
        """注入通用参数"""
        # 文本提示词
        if 'text' in inputs and 'prompt' in parameters:
            inputs['text'] = parameters['prompt']
        
        # 负面提示词
        if 'text' in inputs and 'negative_prompt' in parameters and 'negative' in str(inputs).lower():
            inputs['text'] = parameters['negative_prompt']
        
        # 尺寸参数
        if 'width' in inputs and 'width' in parameters:
            inputs['width'] = parameters['width']
        if 'height' in inputs and 'height' in parameters:
            inputs['height'] = parameters['height']
        
        # 采样参数
        if 'steps' in inputs and 'steps' in parameters:
            inputs['steps'] = parameters['steps']
        if 'cfg' in inputs and 'cfg_scale' in parameters:
            inputs['cfg'] = parameters['cfg_scale']
        if 'sampler_name' in inputs and 'sampler' in parameters:
            inputs['sampler_name'] = parameters['sampler']
        if 'scheduler' in inputs and 'scheduler' in parameters:
            inputs['scheduler'] = parameters['scheduler']
        
        # 种子
        if 'seed' in inputs and 'seed' in parameters:
            inputs['seed'] = parameters['seed']
        
        # 批量大小
        if 'batch_size' in inputs and 'batch_size' in parameters:
            inputs['batch_size'] = parameters['batch_size']
    
    def _inject_node_specific_parameters(self, inputs: Dict[str, Any], parameters: Dict[str, Any], class_type: str):
        """注入节点特定参数"""
        # 检查点加载器
        if 'CheckpointLoader' in class_type and 'checkpoint' in parameters:
            inputs['ckpt_name'] = parameters['checkpoint']
        
        # VAE加载器
        if 'VAELoader' in class_type and 'vae' in parameters:
            inputs['vae_name'] = parameters['vae']
        
        # 图像加载器（图生视频）
        if 'LoadImage' in class_type:
            # 检查多种可能的图像参数名
            image_path = None
            for param_name in ['image', 'image_path', 'input_image']:
                if param_name in parameters:
                    image_path = parameters[param_name]
                    logger.info(f"[WORKFLOW_EXECUTOR] 找到图像参数: {param_name} = {image_path}")
                    break

            if image_path:
                # 对于分布式模式，只使用文件名
                filename = os.path.basename(image_path)
                inputs['image'] = filename
                logger.info(f"[WORKFLOW_EXECUTOR] LoadImage节点使用文件名: {filename}")
            else:
                logger.warning(f"[WORKFLOW_EXECUTOR] LoadImage节点未找到图像参数")
        
        # 视频参数
        if 'video' in class_type.lower():
            if 'fps' in parameters:
                inputs['fps'] = parameters['fps']
            if 'duration' in parameters:
                inputs['duration'] = parameters['duration']
            if 'motion_strength' in parameters:
                inputs['motion_strength'] = parameters['motion_strength']
    
    async def _submit_workflow_with_url(self, workflow_data: Dict[str, Any], base_url: str) -> str:
        """提交工作流到指定URL的ComfyUI"""
        # 转换工作流格式为ComfyUI期望的格式
        comfyui_workflow = self._convert_to_comfyui_format(workflow_data)

        prompt_data = {"prompt": comfyui_workflow}

        logger.debug(f"提交工作流到 {base_url}: {json.dumps(prompt_data, indent=2, ensure_ascii=False)[:500]}...")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{base_url}/prompt",
                    json=prompt_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        prompt_id = result.get('prompt_id')
                        if prompt_id:
                            logger.info(f"工作流提交成功: {prompt_id} (节点: {base_url})")
                            return prompt_id
                        else:
                            raise WorkflowExecutionError("提交工作流失败：未获取到prompt_id")
                    else:
                        error_text = await response.text()
                        logger.error(f"ComfyUI错误响应: {error_text}")
                        raise WorkflowExecutionError(f"提交工作流失败: {response.status} - {error_text}")

            except asyncio.TimeoutError:
                raise WorkflowExecutionError("提交工作流超时")
            except Exception as e:
                raise WorkflowExecutionError(f"提交工作流失败: {e}")

    async def _submit_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """提交工作流到ComfyUI（兼容性方法）"""
        base_url = self.single_mode_config['base_url'] if self.single_mode_config else "http://127.0.0.1:8188"
        return await self._submit_workflow_with_url(workflow_data, base_url)

    def _convert_to_comfyui_format(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """将工作流转换为ComfyUI期望的格式"""
        if 'nodes' in workflow_data:
            # 新格式转换为旧格式
            logger.info("转换新格式工作流为ComfyUI格式")
            comfyui_format = {}

            # 需要过滤的节点类型（注释、UI元素等）
            skip_node_types = {'Note', 'Reroute', 'PrimitiveNode'}

            for node in workflow_data['nodes']:
                node_type = node.get('type', '')
                node_id = str(node['id'])

                # 跳过注释和UI节点
                if node_type in skip_node_types:
                    logger.debug(f"跳过节点 {node_id} (类型: {node_type})")
                    continue

                # 构建ComfyUI节点格式
                comfyui_node = {
                    "class_type": node_type,
                    "inputs": {}
                }

                # 处理inputs
                if 'inputs' in node:
                    for input_item in node['inputs']:
                        if isinstance(input_item, dict) and 'name' in input_item:
                            input_name = input_item['name']
                            if 'link' in input_item:
                                # 这是一个连接，需要找到源节点
                                link_id = input_item['link']
                                source_info = self._find_link_source(workflow_data, link_id)
                                if source_info:
                                    # 确保源节点不是被跳过的节点
                                    source_node = self._find_node_by_id(workflow_data, source_info['node_id'])
                                    if source_node and source_node.get('type') not in skip_node_types:
                                        comfyui_node['inputs'][input_name] = [str(source_info['node_id']), source_info['output_index']]
                            elif 'value' in input_item:
                                # 这是一个直接值
                                comfyui_node['inputs'][input_name] = input_item['value']

                # 处理widgets_values
                if 'widgets_values' in node and node['widgets_values']:
                    # 根据节点类型映射widgets_values到inputs
                    self._map_widgets_to_inputs(comfyui_node, node['widgets_values'], node_type)

                comfyui_format[node_id] = comfyui_node

            logger.info(f"转换完成，生成 {len(comfyui_format)} 个节点")
            return comfyui_format
        else:
            # 已经是旧格式
            logger.info("工作流已经是ComfyUI格式")
            return workflow_data

    def _find_node_by_id(self, workflow_data: Dict[str, Any], node_id: int) -> Dict[str, Any]:
        """根据ID查找节点"""
        for node in workflow_data.get('nodes', []):
            if node.get('id') == node_id:
                return node
        return None

    def _find_link_source(self, workflow_data: Dict[str, Any], link_id: int) -> Dict[str, Any]:
        """查找连接的源节点"""
        # 在新格式中查找连接信息
        if 'links' in workflow_data:
            for link in workflow_data['links']:
                if link[0] == link_id:
                    return {
                        'node_id': link[1],  # 源节点ID
                        'output_index': link[2]  # 输出索引
                    }

        # 如果没有找到，尝试从节点输出中推断
        for node in workflow_data.get('nodes', []):
            if 'outputs' in node:
                for output in node['outputs']:
                    if 'links' in output and link_id in output['links']:
                        return {
                            'node_id': node['id'],
                            'output_index': output.get('slot_index', 0)
                        }

        return None

    def _map_widgets_to_inputs(self, comfyui_node: Dict[str, Any], widgets_values: list, node_type: str):
        """将widgets_values映射到ComfyUI inputs"""
        if not widgets_values:
            return

        # 根据节点类型进行映射
        if node_type == "CLIPTextEncode":
            if len(widgets_values) > 0:
                comfyui_node['inputs']['text'] = widgets_values[0]

        elif node_type == "KSampler":
            # KSampler的widgets_values顺序通常是: [seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise]
            if len(widgets_values) >= 7:
                comfyui_node['inputs']['seed'] = int(widgets_values[0]) if str(widgets_values[0]).isdigit() else 42
                comfyui_node['inputs']['steps'] = int(widgets_values[2]) if isinstance(widgets_values[2], (int, str)) else 20
                comfyui_node['inputs']['cfg'] = float(widgets_values[3]) if isinstance(widgets_values[3], (int, float, str)) else 7.0
                comfyui_node['inputs']['sampler_name'] = str(widgets_values[4])
                comfyui_node['inputs']['scheduler'] = str(widgets_values[5])
                comfyui_node['inputs']['denoise'] = float(widgets_values[6]) if len(widgets_values) > 6 else 1.0

        elif node_type == "EmptyLatentImage":
            # EmptyLatentImage的widgets_values通常是: [width, height, batch_size]
            if len(widgets_values) >= 3:
                comfyui_node['inputs']['width'] = int(widgets_values[0])
                comfyui_node['inputs']['height'] = int(widgets_values[1])
                comfyui_node['inputs']['batch_size'] = int(widgets_values[2])

        elif node_type == "CheckpointLoaderSimple":
            if len(widgets_values) > 0:
                comfyui_node['inputs']['ckpt_name'] = str(widgets_values[0])

        # 对于其他节点类型，尝试通用映射
        else:
            logger.debug(f"节点类型 {node_type} 使用通用widgets映射")
    
    async def _monitor_execution_with_url(self, prompt_id: str, task_id: str, base_url: str, ws_url: str) -> TaskResult:
        """监控工作流执行（指定URL）"""
        try:
            async with websockets.connect(f"{ws_url}?clientId={task_id}") as websocket:
                start_time = asyncio.get_event_loop().time()

                while True:
                    # 检查超时
                    if asyncio.get_event_loop().time() - start_time > self.timeout:
                        raise WorkflowExecutionError("工作流执行超时")

                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)

                        # 处理消息编码问题
                        if isinstance(message, bytes):
                            try:
                                message = message.decode('utf-8')
                            except UnicodeDecodeError:
                                logger.debug("跳过无法解码的WebSocket消息")
                                continue

                        data = json.loads(message)

                        # 处理不同类型的消息
                        if data['type'] == 'executing':
                            node_id = data['data']['node']
                            if node_id is None:
                                # 执行完成
                                result_files = await self._get_result_files_with_url(prompt_id, base_url)
                                return TaskResult(
                                    task_id=task_id,
                                    status=TaskStatus.COMPLETED,
                                    progress=100.0,
                                    message="工作流执行完成",
                                    result_data={"files": result_files}
                                )

                        elif data['type'] == 'progress':
                            # 更新进度
                            progress_data = data['data']
                            progress = (progress_data['value'] / progress_data['max']) * 100
                            logger.debug(f"执行进度: {progress:.1f}%")

                        elif data['type'] == 'execution_error':
                            # 执行错误
                            error_data = data['data']
                            raise WorkflowExecutionError(f"工作流执行错误: {error_data}")

                    except asyncio.TimeoutError:
                        # WebSocket接收超时，继续等待
                        continue
                    except json.JSONDecodeError as e:
                        # 忽略无效的JSON消息
                        logger.debug(f"跳过无效的JSON消息: {e}")
                        continue
                    except UnicodeDecodeError as e:
                        # 忽略编码错误的消息
                        logger.debug(f"跳过编码错误的消息: {e}")
                        continue

        except Exception as e:
            logger.error(f"监控工作流执行失败: {e}")
            raise WorkflowExecutionError(f"监控工作流执行失败: {e}")

    async def _monitor_execution(self, prompt_id: str, task_id: str) -> TaskResult:
        """监控工作流执行（兼容性方法）"""
        if self.single_mode_config:
            base_url = self.single_mode_config['base_url']
            ws_url = self.single_mode_config['ws_url']
        else:
            base_url = "http://127.0.0.1:8188"
            ws_url = "ws://127.0.0.1:8188/ws"
        return await self._monitor_execution_with_url(prompt_id, task_id, base_url, ws_url)
    
    async def _get_result_files_with_url(self, prompt_id: str, base_url: str) -> List[str]:
        """获取结果文件（指定URL）"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{base_url}/history/{prompt_id}") as response:
                    if response.status == 200:
                        history = await response.json()

                        if prompt_id in history:
                            outputs = history[prompt_id].get('outputs', {})
                            result_files = []

                            for node_id, node_output in outputs.items():
                                if 'images' in node_output:
                                    for image_info in node_output['images']:
                                        filename = image_info['filename']
                                        subfolder = image_info.get('subfolder', '')

                                        # 构建完整路径
                                        from ..utils.path_utils import get_output_dir
                                        output_dir = get_output_dir()

                                        if subfolder:
                                            file_path = os.path.join(output_dir, subfolder, filename)
                                        else:
                                            file_path = os.path.join(output_dir, filename)

                                        result_files.append(file_path)

                            return result_files
                        else:
                            raise WorkflowExecutionError(f"未找到prompt_id {prompt_id} 的历史记录")
                    else:
                        raise WorkflowExecutionError(f"获取历史记录失败: {response.status}")

            except Exception as e:
                raise WorkflowExecutionError(f"获取结果文件失败: {e}")

    async def _get_result_files(self, prompt_id: str) -> List[str]:
        """获取结果文件（兼容性方法）"""
        base_url = self.single_mode_config['base_url'] if self.single_mode_config else "http://127.0.0.1:8188"
        return await self._get_result_files_with_url(prompt_id, base_url)
    
    def get_supported_task_types(self) -> List[TaskType]:
        """获取支持的任务类型"""
        return [TaskType.TEXT_TO_IMAGE, TaskType.IMAGE_TO_VIDEO]


# 全局工作流执行器实例
workflow_executor = ComfyUIWorkflowExecutor()


def get_workflow_executor() -> ComfyUIWorkflowExecutor:
    """获取工作流执行器实例"""
    return workflow_executor
