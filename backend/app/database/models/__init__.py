"""
数据库模型包
包含三个数据库的所有ORM模型
"""

from .base import Base
from .client_models import *
from .admin_models import *
from .shared_models import *

__all__ = [
    'Base',
    # 客户端模型
    'ClientUser',
    'ClientTask',
    'ClientTaskParameter',
    'ClientTaskResult',
    'ClientUpload',
    'ClientAccessLog',
    # 管理端模型
    'AdminUser',
    'WorkflowTemplate',
    'WorkflowParameter',
    'Model',
    'WorkflowModel',
    'Node',
    'SystemLog',
    'PerformanceMetric',
    'SystemConfig',
    # 共享模型
    'GlobalTask',
    'GlobalTaskParameter',
    'GlobalTaskResult',
    'NodeTaskAssignment',
    'GlobalFile',
    'TaskQueueStatus',
    'SystemStatistic',
]
