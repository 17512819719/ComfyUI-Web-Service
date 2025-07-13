"""
任务类型管理器
负责识别和管理不同类型的生成任务
"""
from typing import Dict, List, Optional, Type, Any
import logging
from .base import (
    TaskType, TaskRequest, TaskResult, BaseTaskProcessor,
    TaskProcessingError, ConfigurationError
)

logger = logging.getLogger(__name__)


class TaskTypeManager:
    """任务类型管理器"""
    
    def __init__(self):
        self._processors: Dict[TaskType, BaseTaskProcessor] = {}
        self._task_type_configs: Dict[TaskType, Dict[str, Any]] = {}
        
    def register_processor(self, processor: BaseTaskProcessor):
        """注册任务处理器"""
        task_type = processor.get_supported_task_type()
        self._processors[task_type] = processor
        logger.info(f"注册任务处理器: {task_type.value}")
    
    def unregister_processor(self, task_type: TaskType):
        """注销任务处理器"""
        if task_type in self._processors:
            del self._processors[task_type]
            logger.info(f"注销任务处理器: {task_type.value}")
    
    def get_processor(self, task_type: TaskType) -> Optional[BaseTaskProcessor]:
        """获取任务处理器"""
        return self._processors.get(task_type)
    
    def identify_task_type(self, request_data: Dict[str, Any]) -> TaskType:
        """识别任务类型"""
        # 根据请求参数自动识别任务类型
        
        # 检查是否包含图像文件（图生视频）
        if any(key in request_data for key in ['image_path', 'source_image', 'input_image']):
            return TaskType.IMAGE_TO_VIDEO
        
        # 检查是否包含视频相关参数
        if any(key in request_data for key in ['duration', 'fps', 'motion_strength']):
            return TaskType.IMAGE_TO_VIDEO
        
        # 检查工作流名称
        workflow_name = request_data.get('workflow_template', '').lower()
        if 'video' in workflow_name or '视频' in workflow_name:
            return TaskType.IMAGE_TO_VIDEO
        
        # 默认为文生图
        return TaskType.TEXT_TO_IMAGE
    
    def create_task_request(self, request_data: Dict[str, Any]) -> TaskRequest:
        """创建任务请求对象"""
        task_type = self.identify_task_type(request_data)
        
        return TaskRequest(
            task_id=request_data.get('task_id', ''),
            task_type=task_type,
            user_id=request_data.get('user_id', ''),
            parameters=request_data,
            workflow_name=request_data.get('workflow_name'),
            priority=request_data.get('priority', 1)
        )
    
    def validate_task_request(self, request: TaskRequest) -> bool:
        """验证任务请求"""
        processor = self.get_processor(request.task_type)
        if not processor:
            raise TaskProcessingError(f"不支持的任务类型: {request.task_type.value}")
        
        return processor.validate_params(request.parameters)
    
    def get_supported_task_types(self) -> List[TaskType]:
        """获取支持的任务类型列表"""
        return list(self._processors.keys())
    
    def is_task_type_supported(self, task_type: TaskType) -> bool:
        """检查是否支持指定的任务类型"""
        return task_type in self._processors
    
    def get_task_type_info(self, task_type: TaskType) -> Dict[str, Any]:
        """获取任务类型信息"""
        if task_type not in self._processors:
            raise TaskProcessingError(f"不支持的任务类型: {task_type.value}")
        
        return {
            'task_type': task_type.value,
            'processor': self._processors[task_type].__class__.__name__,
            'supported': True
        }
    
    def set_task_type_config(self, task_type: TaskType, config: Dict[str, Any]):
        """设置任务类型配置"""
        self._task_type_configs[task_type] = config
    
    def get_task_type_config(self, task_type: TaskType) -> Dict[str, Any]:
        """获取任务类型配置"""
        return self._task_type_configs.get(task_type, {})


# 全局任务类型管理器实例
task_type_manager = TaskTypeManager()


def get_task_type_manager() -> TaskTypeManager:
    """获取任务类型管理器实例"""
    return task_type_manager


# 任务类型识别辅助函数
def identify_task_type_from_params(params: Dict[str, Any]) -> TaskType:
    """从参数中识别任务类型的辅助函数"""
    return task_type_manager.identify_task_type(params)


def create_task_request_from_params(params: Dict[str, Any]) -> TaskRequest:
    """从参数创建任务请求的辅助函数"""
    return task_type_manager.create_task_request(params)


# 装饰器：自动注册任务处理器
def register_task_processor(task_type: TaskType):
    """装饰器：自动注册任务处理器"""
    def decorator(cls: Type[BaseTaskProcessor]):
        # 创建实例并注册
        processor = cls()
        task_type_manager.register_processor(processor)
        return cls
    return decorator
