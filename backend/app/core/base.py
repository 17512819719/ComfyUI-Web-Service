"""
基础抽象类和接口定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import uuid
from datetime import datetime


class TaskType(Enum):
    """任务类型枚举"""
    TEXT_TO_IMAGE = "text_to_image"
    # 预留其他任务类型
    TEXT_TO_AUDIO = "text_to_audio"
    IMAGE_TO_3D = "image_to_3d"


class TaskStatus(Enum):
    """任务状态枚举"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ParameterMergeStrategy(Enum):
    """参数合并策略"""
    FRONTEND_PRIORITY = "frontend_priority"    # 前端参数优先
    CONFIG_PRIORITY = "config_priority"        # 配置参数优先
    SMART_MERGE = "smart_merge"               # 智能合并
    CONDITIONAL = "conditional"               # 条件合并


@dataclass
class TaskRequest:
    """统一的任务请求数据结构"""
    task_id: str
    task_type: TaskType
    user_id: str
    parameters: Dict[str, Any]
    workflow_name: Optional[str] = None
    priority: int = 1
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.task_id:
            self.task_id = str(uuid.uuid4())


@dataclass
class TaskResult:
    """任务结果数据结构"""
    task_id: str
    status: TaskStatus
    progress: float = 0.0
    message: str = ""
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class WorkflowConfig:
    """工作流配置数据结构"""
    name: str
    version: str
    workflow_file: str
    description: str
    default_params: Dict[str, Any]
    param_mapping: Dict[str, str]
    param_rules: Dict[str, Dict[str, Any]]
    model_config: Dict[str, Any]
    task_type: TaskType


class BaseTaskProcessor(ABC):
    """任务处理器基类"""
    
    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        pass
    
    @abstractmethod
    def process_params(self, request: TaskRequest, config: WorkflowConfig) -> Dict[str, Any]:
        """处理参数"""
        pass
    
    @abstractmethod
    def get_supported_task_type(self) -> TaskType:
        """获取支持的任务类型"""
        pass


class BaseWorkflowExecutor(ABC):
    """工作流执行器基类"""
    
    @abstractmethod
    async def execute(self, workflow_config: WorkflowConfig, parameters: Dict[str, Any]) -> TaskResult:
        """执行工作流"""
        pass
    
    @abstractmethod
    def get_supported_task_types(self) -> List[TaskType]:
        """获取支持的任务类型"""
        pass


class BaseParameterValidator(ABC):
    """参数验证器基类"""
    
    @abstractmethod
    def validate(self, params: Dict[str, Any], rules: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """验证参数并返回验证结果"""
        pass


class BaseParameterMapper(ABC):
    """参数映射器基类"""
    
    @abstractmethod
    def map_parameters(self, frontend_params: Dict[str, Any], mapping_config: Dict[str, str]) -> Dict[str, Any]:
        """映射前端参数到工作流参数"""
        pass


class ConfigurationError(Exception):
    """配置错误异常"""
    pass


class ValidationError(Exception):
    """验证错误异常"""
    pass


class WorkflowExecutionError(Exception):
    """工作流执行错误异常"""
    pass


class TaskProcessingError(Exception):
    """任务处理错误异常"""
    pass


# 常用的参数类型定义
PARAMETER_TYPES = {
    'int': int,
    'float': float,
    'str': str,
    'bool': bool,
    'list': list,
    'dict': dict
}


# 默认的参数验证规则
DEFAULT_PARAM_RULES = {
    'width': {'type': 'int', 'min': 64, 'max': 2048, 'step': 64},
    'height': {'type': 'int', 'min': 64, 'max': 2048, 'step': 64},
    'steps': {'type': 'int', 'min': 1, 'max': 100},
    'cfg_scale': {'type': 'float', 'min': 1.0, 'max': 20.0},
    'batch_size': {'type': 'int', 'min': 1, 'max': 8},
    'seed': {'type': 'int', 'min': -1, 'max': 2147483647},
    'fps': {'type': 'int', 'min': 1, 'max': 60},
    'duration': {'type': 'float', 'min': 1.0, 'max': 10.0},
    'motion_strength': {'type': 'float', 'min': 0.1, 'max': 1.0}
}
