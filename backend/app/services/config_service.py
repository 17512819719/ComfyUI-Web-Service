"""
系统配置管理服务
负责系统配置的数据库持久化和动态更新
"""
import json
import yaml
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from ..database.dao.base_dao import BaseDAO
from ..database.models.shared_models import SystemConfig
from ..core.config_manager import get_config_manager

logger = logging.getLogger(__name__)


class ConfigService:
    """系统配置管理服务"""
    
    def __init__(self):
        self.config_dao = BaseDAO('shared', SystemConfig)
        self.config_manager = get_config_manager()
    
    def sync_config_to_database(self) -> bool:
        """将YAML配置文件同步到数据库"""
        try:
            # 获取当前配置
            config_data = self.config_manager.get_all_configs()
            
            for config_key, config_value in config_data.items():
                self._save_config_item(config_key, config_value, 'yaml_sync')
            
            logger.info("配置同步到数据库完成")
            return True
            
        except Exception as e:
            logger.error(f"配置同步失败: {e}")
            return False
    
    def get_config(self, config_key: str, default_value: Any = None) -> Any:
        """获取配置项（优先从数据库获取）"""
        try:
            with self.config_dao.get_session() as session:
                config = session.query(SystemConfig).filter(
                    SystemConfig.config_key == config_key,
                    SystemConfig.is_active == True
                ).first()
                
                if config:
                    return self._parse_config_value(config.config_value, config.value_type)
                
                # 如果数据库没有，从YAML文件获取
                return self.config_manager.get_config(config_key, default_value)
                
        except Exception as e:
            logger.error(f"获取配置失败 [{config_key}]: {e}")
            return default_value
    
    def set_config(self, config_key: str, config_value: Any, 
                   description: str = None, source: str = 'api') -> bool:
        """设置配置项"""
        try:
            return self._save_config_item(config_key, config_value, source, description)
            
        except Exception as e:
            logger.error(f"设置配置失败 [{config_key}]: {e}")
            return False
    
    def get_all_configs(self, category: str = None) -> Dict[str, Any]:
        """获取所有配置项"""
        try:
            with self.config_dao.get_session() as session:
                query = session.query(SystemConfig).filter(
                    SystemConfig.is_active == True
                )
                
                if category:
                    query = query.filter(SystemConfig.category == category)
                
                configs = query.all()
                
                result = {}
                for config in configs:
                    result[config.config_key] = self._parse_config_value(
                        config.config_value, config.value_type
                    )
                
                return result
                
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            return {}
    
    def update_config(self, config_key: str, config_value: Any) -> bool:
        """更新配置项"""
        try:
            with self.config_dao.get_session() as session:
                config = session.query(SystemConfig).filter(
                    SystemConfig.config_key == config_key,
                    SystemConfig.is_active == True
                ).first()
                
                if config:
                    config.config_value = self._serialize_config_value(config_value)
                    config.value_type = self._get_value_type(config_value)
                    config.updated_at = datetime.utcnow()
                    session.commit()
                    
                    logger.info(f"配置更新成功: {config_key}")
                    return True
                else:
                    # 如果不存在，创建新配置
                    return self.set_config(config_key, config_value, source='update')
                    
        except Exception as e:
            logger.error(f"更新配置失败 [{config_key}]: {e}")
            return False
    
    def delete_config(self, config_key: str) -> bool:
        """删除配置项（软删除）"""
        try:
            with self.config_dao.get_session() as session:
                config = session.query(SystemConfig).filter(
                    SystemConfig.config_key == config_key
                ).first()
                
                if config:
                    config.is_active = False
                    config.updated_at = datetime.utcnow()
                    session.commit()
                    
                    logger.info(f"配置删除成功: {config_key}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"删除配置失败 [{config_key}]: {e}")
            return False
    
    def get_config_history(self, config_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取配置变更历史"""
        try:
            with self.config_dao.get_session() as session:
                configs = session.query(SystemConfig).filter(
                    SystemConfig.config_key == config_key
                ).order_by(SystemConfig.created_at.desc()).limit(limit).all()
                
                return [self._config_to_dict(config) for config in configs]
                
        except Exception as e:
            logger.error(f"获取配置历史失败 [{config_key}]: {e}")
            return []
    
    def _save_config_item(self, config_key: str, config_value: Any, 
                         source: str, description: str = None) -> bool:
        """保存配置项到数据库"""
        try:
            # 先禁用旧配置
            with self.config_dao.get_session() as session:
                old_configs = session.query(SystemConfig).filter(
                    SystemConfig.config_key == config_key,
                    SystemConfig.is_active == True
                ).all()
                
                for old_config in old_configs:
                    old_config.is_active = False
                    old_config.updated_at = datetime.utcnow()
                
                session.commit()
            
            # 创建新配置
            config_record = self.config_dao.create(
                config_key=config_key,
                config_value=self._serialize_config_value(config_value),
                value_type=self._get_value_type(config_value),
                category=self._get_config_category(config_key),
                description=description or f"配置项: {config_key}",
                source=source,
                is_active=True
            )
            
            return config_record is not None
            
        except Exception as e:
            logger.error(f"保存配置项失败 [{config_key}]: {e}")
            return False
    
    def _serialize_config_value(self, value: Any) -> str:
        """序列化配置值"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            return str(value).lower()
        else:
            return str(value)
    
    def _parse_config_value(self, value_str: str, value_type: str) -> Any:
        """解析配置值"""
        try:
            if value_type == 'json':
                return json.loads(value_str)
            elif value_type == 'bool':
                return value_str.lower() in ('true', '1', 'yes', 'on')
            elif value_type == 'int':
                return int(value_str)
            elif value_type == 'float':
                return float(value_str)
            else:
                return value_str
        except:
            return value_str
    
    def _get_value_type(self, value: Any) -> str:
        """获取值类型"""
        if isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'
    
    def _get_config_category(self, config_key: str) -> str:
        """根据配置键获取分类"""
        if config_key.startswith('comfyui'):
            return 'comfyui'
        elif config_key.startswith('database'):
            return 'database'
        elif config_key.startswith('redis'):
            return 'redis'
        elif config_key.startswith('celery'):
            return 'celery'
        elif config_key.startswith('workflow'):
            return 'workflow'
        else:
            return 'general'
    
    def _config_to_dict(self, config: SystemConfig) -> Dict[str, Any]:
        """将配置记录转换为字典"""
        return {
            'id': config.id,
            'config_key': config.config_key,
            'config_value': self._parse_config_value(config.config_value, config.value_type),
            'value_type': config.value_type,
            'category': config.category,
            'description': config.description,
            'source': config.source,
            'is_active': config.is_active,
            'created_at': config.created_at.isoformat() if config.created_at else None,
            'updated_at': config.updated_at.isoformat() if config.updated_at else None
        }


# 全局实例
_config_service = None

def get_config_service() -> ConfigService:
    """获取配置服务实例"""
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service
