"""
配置管理器
统一管理所有工作流的配置
"""
import os
import yaml
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from .base import (
    TaskType, WorkflowConfig, ParameterMergeStrategy,
    ConfigurationError
)

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), '..', '..', 'config.yaml'
        )
        self.config_data: Dict[str, Any] = {}
        self.workflow_configs: Dict[str, WorkflowConfig] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
            
            # 验证配置结构
            self._validate_config()
            
            # 加载工作流配置
            self._load_workflow_configs()
            
            logger.info(f"配置文件加载成功: {self.config_path}")
            
        except FileNotFoundError:
            raise ConfigurationError(f"配置文件不存在: {self.config_path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ConfigurationError(f"加载配置文件失败: {e}")
    
    def _validate_config(self):
        """验证配置文件结构"""
        required_sections = ['task_types', 'comfyui', 'redis']
        for section in required_sections:
            if section not in self.config_data:
                raise ConfigurationError(f"配置文件缺少必需的节: {section}")
    
    def _load_workflow_configs(self):
        """加载工作流配置"""
        task_types = self.config_data.get('task_types', {})
        
        for task_type_name, task_config in task_types.items():
            if not task_config.get('enabled', True):
                continue
            
            try:
                task_type = TaskType(task_type_name)
            except ValueError:
                logger.warning(f"未知的任务类型: {task_type_name}")
                continue
            
            workflows = task_config.get('workflows', {})
            for workflow_name, workflow_data in workflows.items():
                try:
                    workflow_config = WorkflowConfig(
                        name=workflow_data['name'],
                        version=workflow_data['version'],
                        workflow_file=workflow_data['workflow_file'],
                        description=workflow_data.get('description', ''),
                        default_params=workflow_data.get('default_params', {}),
                        param_mapping=workflow_data.get('param_mapping', {}),
                        param_rules=workflow_data.get('param_rules', {}),
                        model_config=workflow_data.get('model_config', {}),
                        task_type=task_type
                    )
                    
                    self.workflow_configs[workflow_name] = workflow_config
                    logger.debug(f"加载工作流配置: {workflow_name}")
                    
                except KeyError as e:
                    logger.error(f"工作流配置缺少必需字段 {e}: {workflow_name}")
                except Exception as e:
                    logger.error(f"加载工作流配置失败 {workflow_name}: {e}")
    
    def reload_config(self):
        """重新加载配置文件"""
        logger.info("重新加载配置文件...")
        self.config_data.clear()
        self.workflow_configs.clear()
        self._load_config()
    
    def get_config(self, section: str = None) -> Dict[str, Any]:
        """获取配置数据"""
        if section:
            return self.config_data.get(section, {})
        return self.config_data
    
    def get_task_type_config(self, task_type: TaskType) -> Dict[str, Any]:
        """获取任务类型配置"""
        return self.config_data.get('task_types', {}).get(task_type.value, {})
    
    def get_workflow_config(self, workflow_name: str) -> Optional[WorkflowConfig]:
        """获取工作流配置"""
        return self.workflow_configs.get(workflow_name)

    def get_workflow_config_raw(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """获取原始工作流配置数据（包含新的参数映射结构）"""
        if not workflow_name:
            logger.warning("工作流名称为空")
            return None

        # 遍历所有任务类型查找工作流
        task_types = self.config_data.get('task_types', {})
        if not task_types:
            logger.warning("配置文件中没有task_types节点")
            return None

        for task_type_name, task_config in task_types.items():
            if not isinstance(task_config, dict):
                continue
            workflows = task_config.get('workflows', {})
            if workflow_name in workflows:
                workflow_config = workflows[workflow_name]
                if not workflow_config:
                    logger.warning(f"工作流配置为空: {workflow_name}")
                return workflow_config

        logger.warning(f"未找到工作流配置: {workflow_name}")
        return None
    
    def get_workflows_by_task_type(self, task_type: TaskType) -> List[WorkflowConfig]:
        """根据任务类型获取工作流列表"""
        return [
            config for config in self.workflow_configs.values()
            if config.task_type == task_type
        ]
    
    def get_default_workflow(self, task_type: TaskType) -> Optional[WorkflowConfig]:
        """获取任务类型的默认工作流"""
        task_config = self.get_task_type_config(task_type)
        default_workflow_name = task_config.get('default_workflow')
        
        if default_workflow_name:
            return self.get_workflow_config(default_workflow_name)
        
        # 如果没有指定默认工作流，返回第一个可用的工作流
        workflows = self.get_workflows_by_task_type(task_type)
        return workflows[0] if workflows else None
    
    def get_available_workflows(self) -> Dict[str, List[str]]:
        """获取所有可用的工作流"""
        result = {}
        for task_type in TaskType:
            workflows = self.get_workflows_by_task_type(task_type)
            result[task_type.value] = [w.name for w in workflows]
        return result
    
    def get_parameter_merge_strategy(self) -> ParameterMergeStrategy:
        """获取参数合并策略"""
        strategy_name = self.config_data.get('parameter_strategies', {}).get(
            'merge_strategy', 'smart_merge'
        )
        try:
            return ParameterMergeStrategy(strategy_name)
        except ValueError:
            logger.warning(f"未知的参数合并策略: {strategy_name}，使用默认策略")
            return ParameterMergeStrategy.SMART_MERGE
    
    def get_comfyui_config(self) -> Dict[str, Any]:
        """获取ComfyUI配置"""
        return self.get_config('comfyui')
    
    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        return self.get_config('redis')
    
    def get_mysql_config(self) -> Dict[str, Any]:
        """获取MySQL配置"""
        return self.get_config('mysql')
    
    def get_task_queue_config(self) -> Dict[str, Any]:
        """获取任务队列配置"""
        return self.get_config('task_queue')
    
    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.get_config('system')
    
    def is_task_type_enabled(self, task_type: TaskType) -> bool:
        """检查任务类型是否启用"""
        task_config = self.get_task_type_config(task_type)
        return task_config.get('enabled', False)
    
    def get_max_concurrent_tasks(self, task_type: TaskType) -> int:
        """获取任务类型的最大并发数"""
        task_config = self.get_task_type_config(task_type)
        return task_config.get('max_concurrent_tasks', 1)
    
    def get_task_priority(self, task_type: TaskType) -> int:
        """获取任务类型的优先级"""
        task_config = self.get_task_type_config(task_type)
        return task_config.get('priority', 1)


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    return config_manager


def reload_config():
    """重新加载配置"""
    config_manager.reload_config()
