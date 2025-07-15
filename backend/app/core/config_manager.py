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


class ConfigValidationError(ConfigurationError):
    """配置验证错误"""
    pass


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
        try:
            # 基础结构验证
            required_sections = ['task_types', 'comfyui', 'redis']
            for section in required_sections:
                if section not in self.config_data:
                    raise ConfigValidationError(f"配置文件缺少必需的节: {section}")

            # 详细验证各个配置节
            self._validate_comfyui_config()
            self._validate_redis_config()
            self._validate_task_types_config()

            logger.debug("配置文件验证通过")

        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            raise

    def _validate_comfyui_config(self):
        """验证ComfyUI配置"""
        comfyui_config = self.config_data.get('comfyui', {})

        # 检查必需字段
        required_fields = ['host', 'port']
        for field in required_fields:
            if field not in comfyui_config:
                raise ConfigValidationError(f"ComfyUI配置缺少字段: {field}")

        # 验证端口号
        port = comfyui_config.get('port')
        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ConfigValidationError(f"ComfyUI端口号无效: {port}")

    def _validate_redis_config(self):
        """验证Redis配置"""
        redis_config = self.config_data.get('redis', {})

        # 检查必需字段
        required_fields = ['host', 'port']
        for field in required_fields:
            if field not in redis_config:
                raise ConfigValidationError(f"Redis配置缺少字段: {field}")

        # 验证端口号
        port = redis_config.get('port')
        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ConfigValidationError(f"Redis端口号无效: {port}")

    def _validate_task_types_config(self):
        """验证任务类型配置"""
        task_types = self.config_data.get('task_types', {})

        if not task_types:
            raise ConfigValidationError("至少需要配置一个任务类型")

        for task_type_name, task_config in task_types.items():
            if not isinstance(task_config, dict):
                raise ConfigValidationError(f"任务类型配置格式错误: {task_type_name}")

            # 验证工作流配置
            workflows = task_config.get('workflows', {})
            for workflow_name, workflow_config in workflows.items():
                self._validate_workflow_config(workflow_name, workflow_config)
    
    def _validate_workflow_config(self, workflow_name: str, workflow_config: dict):
        """验证单个工作流配置"""
        required_fields = ['name', 'version', 'workflow_file']
        for field in required_fields:
            if field not in workflow_config:
                raise ConfigValidationError(f"工作流 {workflow_name} 缺少字段: {field}")

        # 验证工作流文件是否存在
        workflow_file = workflow_config.get('workflow_file')
        if workflow_file and not os.path.exists(workflow_file):
            logger.warning(f"工作流文件不存在: {workflow_file} (工作流: {workflow_name})")

    def _load_workflow_configs(self):
        """加载工作流配置"""
        task_types = self.config_data.get('task_types', {})

        for task_type_name, task_config in task_types.items():
            if not task_config.get('enabled', True):
                logger.debug(f"跳过已禁用的任务类型: {task_type_name}")
                continue

            try:
                task_type = TaskType(task_type_name)
            except ValueError:
                logger.warning(f"未知的任务类型: {task_type_name}")
                continue

            workflows = task_config.get('workflows', {})
            for workflow_name, workflow_data in workflows.items():
                try:
                    # 处理工作流文件路径（支持相对路径）
                    workflow_file = workflow_data['workflow_file']
                    if not os.path.isabs(workflow_file):
                        # 相对路径，基于配置文件目录解析
                        config_dir = os.path.dirname(self.config_path)
                        workflow_file = os.path.join(config_dir, workflow_file)
                        workflow_file = os.path.normpath(workflow_file)

                    # 创建工作流配置对象
                    workflow_config = WorkflowConfig(
                        name=workflow_data['name'],
                        version=workflow_data['version'],
                        workflow_file=workflow_file,
                        description=workflow_data.get('description', ''),
                        default_params=workflow_data.get('default_params', {}),
                        param_mapping=workflow_data.get('param_mapping', {}),
                        param_rules=workflow_data.get('param_rules', {}),
                        model_config=workflow_data.get('model_config', {}),
                        task_type=task_type
                    )

                    self.workflow_configs[workflow_name] = workflow_config
                    logger.debug(f"✅ 加载工作流配置: {workflow_name}")

                except KeyError as e:
                    logger.error(f"❌ 工作流配置缺少必需字段 {e}: {workflow_name}")
                except Exception as e:
                    logger.error(f"❌ 加载工作流配置失败 {workflow_name}: {e}")

        logger.info(f"共加载 {len(self.workflow_configs)} 个工作流配置")
    
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

    def get_nodes_config(self) -> Dict[str, Any]:
        """获取节点配置"""
        return self.get_config('nodes')

    def get_static_nodes_config(self) -> List[Dict[str, Any]]:
        """获取静态节点配置"""
        nodes_config = self.get_nodes_config()
        return nodes_config.get('static_nodes', [])

    def get_health_check_config(self) -> Dict[str, Any]:
        """获取健康检查配置"""
        nodes_config = self.get_nodes_config()
        return nodes_config.get('health_check', {
            'interval': 30,
            'timeout': 5,
            'heartbeat_timeout': 60,
            'retry_attempts': 3
        })

    def get_load_balancing_config(self) -> Dict[str, Any]:
        """获取负载均衡配置"""
        nodes_config = self.get_nodes_config()
        return nodes_config.get('load_balancing', {
            'strategy': 'least_loaded',
            'enable_failover': True,
            'max_retries': 3
        })

    def get_discovery_mode(self) -> str:
        """获取节点发现模式"""
        nodes_config = self.get_nodes_config()
        return nodes_config.get('discovery_mode', 'static')

    def is_distributed_mode(self) -> bool:
        """检查是否为分布式模式"""
        nodes_config = self.get_nodes_config()
        static_nodes = nodes_config.get('static_nodes', [])
        return len(static_nodes) > 0 or self.get_discovery_mode() != 'static'


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    return config_manager


def reload_config():
    """重新加载配置"""
    config_manager.reload_config()
