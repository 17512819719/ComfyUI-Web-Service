"""
工作流参数处理器 - 新的参数映射和注入系统
实现精确的参数位置映射和注入机制
"""
import copy
import json
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class DataTypeConverter:
    """数据类型转换器"""
    
    @staticmethod
    def convert_value(value: Any, target_type: str) -> Any:
        """根据配置的数据类型转换值"""
        try:
            if target_type == "int":
                return int(value)
            elif target_type == "float":
                return float(value)
            elif target_type == "string":
                return str(value)
            elif target_type == "bool":
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            else:
                return value
        except (ValueError, TypeError) as e:
            logger.error(f"数据类型转换失败: {value} -> {target_type}, 错误: {e}")
            raise ValueError(f"无法将 '{value}' 转换为 {target_type} 类型")


class ParameterMapper:
    """参数映射处理器"""
    
    def __init__(self, workflow_config: Dict):
        self.parameter_mapping = workflow_config.get('parameter_mapping', {})
        self.allowed_params = workflow_config.get('allowed_frontend_params', [])
        self.workflow_name = workflow_config.get('name', 'Unknown')
    
    def validate_frontend_params(self, frontend_params: Dict) -> bool:
        """验证前端参数是否在允许范围内"""
        errors = []

        # 统一的系统内部参数白名单，不需要验证
        system_params = {
            'task_id', 'user_id', 'task_type', 'workflow_name', 'priority',
            'steps', 'cfg_scale', 'sampler', 'scheduler', 'seed',
            # 添加更多系统参数
            'celery_task_id', 'created_at', 'updated_at', 'estimated_time',
            'batch_id', 'checkpoint', 'model_name',  # 添加model_name到系统参数
            # 分布式文件服务相关参数
            'image_download_info', 'file_download_info', '_downloaded_files',
            'image_file_id', 'upload_file_id',  # 文件ID相关参数
            'image_relative_path'  # 文件相对路径参数
        }

        # 调试日志：显示接收到的所有参数
        logger.info(f"收到前端参数 [{self.workflow_name}]: {list(frontend_params.keys())}")
        logger.info(f"允许的参数列表: {self.allowed_params}")

        for param_name in frontend_params.keys():
            # 跳过系统内部参数
            if param_name in system_params:
                logger.debug(f"跳过系统参数: {param_name}")
                continue

            if param_name not in self.allowed_params:
                logger.warning(f"发现不允许的参数: {param_name} = {frontend_params[param_name]}")
                errors.append(f"不允许的参数: {param_name}")

        if errors:
            raise ValueError(f"参数验证失败 [{self.workflow_name}]: {'; '.join(errors)}")

        logger.info(f"前端参数验证通过 [{self.workflow_name}]: {list(frontend_params.keys())}")
        return True
    
    def merge_parameters(self, frontend_params: Dict) -> Dict:
        """合并参数：前端 > 配置文件默认值
        
        Args:
            frontend_params: 前端提交的参数
            
        Returns:
            合并后的最终参数字典
        """
        final_params = {}
        
        # 遍历所有配置的参数映射
        for param_name, mapping_config in self.parameter_mapping.items():
            # 优先级：前端参数 > 配置文件默认值
            if param_name in frontend_params and frontend_params[param_name] is not None:
                # 使用前端提供的值
                raw_value = frontend_params[param_name]
                # 进行数据类型转换
                converted_value = DataTypeConverter.convert_value(
                    raw_value, mapping_config.get('data_type', 'string')
                )
                final_params[param_name] = converted_value
                logger.debug(f"使用前端参数 [{param_name}]: {raw_value} -> {converted_value}")
            else:
                # 使用配置文件的默认值
                default_value = mapping_config.get('default_value')
                if default_value is not None:
                    final_params[param_name] = default_value
                    logger.debug(f"使用默认参数 [{param_name}]: {default_value}")
        
        # 处理特殊参数
        final_params = self._process_special_parameters(final_params)

        logger.info(f"参数合并完成 [{self.workflow_name}]: {len(final_params)} 个参数")
        return final_params

    def _process_special_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理特殊参数，如随机种子生成"""
        result = params.copy()

        # 处理随机种子
        if 'seed' in result and result['seed'] == -1:
            import random
            result['seed'] = random.randint(0, 2147483647)
            logger.info(f"生成随机种子: {result['seed']}")

        return result


class WorkflowInjector:
    """工作流参数注入器"""
    
    def inject_parameters(self, workflow_data: Dict, parameters: Dict, 
                         parameter_mapping: Dict) -> Dict:
        """精确注入参数到指定位置
        
        Args:
            workflow_data: 原始工作流数据
            parameters: 要注入的参数
            parameter_mapping: 参数映射配置
            
        Returns:
            注入参数后的工作流数据
        """
        # 深拷贝工作流，避免修改原始数据
        modified_workflow = copy.deepcopy(workflow_data)
        
        injection_count = 0
        
        for param_name, param_value in parameters.items():
            if param_name not in parameter_mapping:
                logger.warning(f"参数 {param_name} 没有映射配置，跳过注入")
                continue
                
            mapping = parameter_mapping[param_name]
            node_id = mapping['node_id']
            input_name = mapping['input_name']
            
            # 检测工作流格式并注入
            if self._inject_to_workflow(modified_workflow, node_id, input_name, param_value):
                injection_count += 1
                logger.debug(f"成功注入参数 [{param_name}] = {param_value} 到节点 {node_id}.{input_name}")
            else:
                logger.error(f"注入参数失败 [{param_name}] 到节点 {node_id}.{input_name}")
        
        logger.info(f"参数注入完成: {injection_count}/{len(parameters)} 个参数成功注入")
        return modified_workflow
    
    def _inject_to_workflow(self, workflow: Dict, node_id: str, 
                           input_name: str, value: Any) -> bool:
        """注入参数到工作流节点
        
        Args:
            workflow: 工作流数据
            node_id: 节点ID
            input_name: 输入字段名
            value: 要注入的值
            
        Returns:
            是否注入成功
        """
        # 检测工作流格式
        if 'nodes' in workflow:
            # 新格式：nodes数组
            return self._inject_new_format(workflow, node_id, input_name, value)
        else:
            # 旧格式：节点字典
            return self._inject_old_format(workflow, node_id, input_name, value)
    
    def _inject_new_format(self, workflow: Dict, node_id: str, 
                          input_name: str, value: Any) -> bool:
        """注入到新格式工作流（nodes数组）"""
        for node in workflow.get('nodes', []):
            if str(node.get('id')) == node_id:
                return self._inject_to_node_inputs(node, input_name, value)
        
        logger.error(f"在新格式工作流中未找到节点: {node_id}")
        return False
    
    def _inject_old_format(self, workflow: Dict, node_id: str, 
                          input_name: str, value: Any) -> bool:
        """注入到旧格式工作流（节点字典）"""
        if node_id in workflow:
            node = workflow[node_id]
            return self._inject_to_node_inputs(node, input_name, value)
        
        logger.error(f"在旧格式工作流中未找到节点: {node_id}")
        return False
    
    def _inject_to_node_inputs(self, node: Dict, input_name: str, value: Any) -> bool:
        """注入值到节点的inputs字段"""
        if 'inputs' not in node:
            node['inputs'] = {}
        
        node['inputs'][input_name] = value
        return True


class WorkflowParameterProcessor:
    """工作流参数处理器 - 主要处理类"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.workflow_cache = {}  # 工作流文件缓存
    
    def process_workflow_request(self, workflow_name: str, 
                               frontend_params: Dict) -> Dict:
        """处理工作流请求
        
        Args:
            workflow_name: 工作流名称
            frontend_params: 前端提交的参数
            
        Returns:
            处理后的完整工作流数据
        """
        logger.info(f"开始处理工作流请求: {workflow_name}")
        
        try:
            # 1. 获取工作流配置（使用新的原始配置方法）
            workflow_config = self.config_manager.get_workflow_config_raw(workflow_name)
            if not workflow_config:
                raise ValueError(f"未找到工作流配置: {workflow_name}")
            
            # 2. 验证前端参数
            mapper = ParameterMapper(workflow_config)
            mapper.validate_frontend_params(frontend_params)
            
            # 3. 加载原始工作流文件
            workflow_data = self._load_workflow_file(workflow_config['workflow_file'])
            
            # 4. 合并参数（前端 > 配置默认值）
            final_params = mapper.merge_parameters(frontend_params)
            
            # 5. 精确注入参数
            injector = WorkflowInjector()
            modified_workflow = injector.inject_parameters(
                workflow_data, 
                final_params, 
                workflow_config['parameter_mapping']
            )
            
            logger.info(f"工作流请求处理完成: {workflow_name}")
            return modified_workflow
            
        except Exception as e:
            logger.error(f"工作流请求处理失败 [{workflow_name}]: {e}")
            raise
    
    def _load_workflow_file(self, workflow_file_path: str) -> Dict:
        """加载工作流文件（带缓存）"""
        # 修复：正确处理相对路径
        import os

        # 规范化路径
        full_path = os.path.normpath(workflow_file_path)

        # 检查缓存（使用规范化后的路径作为缓存键）
        if full_path in self.workflow_cache:
            logger.debug(f"从缓存加载工作流文件: {full_path}")
            return self.workflow_cache[full_path]

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)

            # 缓存工作流数据（使用规范化后的路径作为缓存键）
            self.workflow_cache[full_path] = workflow_data
            logger.info(f"工作流文件加载成功: {full_path}")
            return workflow_data

        except FileNotFoundError:
            raise FileNotFoundError(f"工作流文件不存在: {full_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"工作流文件格式错误: {workflow_file_path}, 错误: {e}")

    def clear_cache(self):
        """清除工作流缓存"""
        self.workflow_cache.clear()
        logger.info("工作流缓存已清除")
    
    def clear_cache(self):
        """清空工作流缓存"""
        self.workflow_cache.clear()
        logger.info("工作流缓存已清空")


# 全局实例
_workflow_parameter_processor = None


def get_workflow_parameter_processor(config_manager=None, force_recreate=False):
    """获取工作流参数处理器实例"""
    global _workflow_parameter_processor

    if _workflow_parameter_processor is None or force_recreate:
        if config_manager is None:
            from .config_manager import get_config_manager
            config_manager = get_config_manager()

        _workflow_parameter_processor = WorkflowParameterProcessor(config_manager)
        logger.info("工作流参数处理器实例已创建/重新创建")

    return _workflow_parameter_processor
