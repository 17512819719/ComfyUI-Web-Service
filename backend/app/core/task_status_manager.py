"""
任务状态管理器
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import redis

logger = logging.getLogger(__name__)


class TaskStatusManager:
    """基于Redis的任务状态管理器"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        # 测试连接
        self.redis_client.ping()
        self.key_prefix = "comfyui:task:"
        logger.info("任务状态管理器已连接到Redis")
        
    def _get_key(self, task_id: str) -> str:
        """获取Redis键名"""
        return f"{self.key_prefix}{task_id}"
    
    def set_task_status(self, task_id: str, status_data: Dict[str, Any]) -> bool:
        """设置任务状态"""
        try:
            status_data['updated_at'] = datetime.now().isoformat()
            key = self._get_key(task_id)
            json_data = json.dumps(status_data, ensure_ascii=False)
            self.redis_client.set(key, json_data, ex=86400)  # 24小时过期

            logger.debug(f"任务状态已保存: {task_id} -> {status_data.get('status', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"保存任务状态失败 [{task_id}]: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        try:
            key = self._get_key(task_id)
            json_data = self.redis_client.get(key)
            if json_data:
                return json.loads(json_data)
            return None

        except Exception as e:
            logger.error(f"获取任务状态失败 [{task_id}]: {e}")
            return None
    
    def update_task_status(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新任务状态（合并更新）"""
        try:
            current_status = self.get_task_status(task_id) or {}
            current_status.update(updates)
            return self.set_task_status(task_id, current_status)
            
        except Exception as e:
            logger.error(f"更新任务状态失败 [{task_id}]: {e}")
            return False
    
    def delete_task_status(self, task_id: str) -> bool:
        """删除任务状态"""
        try:
            key = self._get_key(task_id)
            result = self.redis_client.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"删除任务状态失败 [{task_id}]: {e}")
            return False
    
    def list_tasks(self, pattern: str = "*") -> Dict[str, Dict[str, Any]]:
        """列出所有任务"""
        try:
            search_pattern = f"{self.key_prefix}{pattern}"
            keys = self.redis_client.keys(search_pattern)

            tasks = {}
            for key in keys:
                task_id = key.replace(self.key_prefix, "")
                task_data = self.get_task_status(task_id)
                if task_data:
                    tasks[task_id] = task_data
            return tasks

        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return {}
    
    def cleanup_expired_tasks(self, max_age_hours: int = 24) -> int:
        """清理过期任务"""
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            tasks = self.list_tasks()
            
            deleted_count = 0
            for task_id, task_data in tasks.items():
                updated_at_str = task_data.get('updated_at')
                if updated_at_str:
                    try:
                        updated_at = datetime.fromisoformat(updated_at_str)
                        if updated_at < cutoff_time:
                            if self.delete_task_status(task_id):
                                deleted_count += 1
                    except ValueError:
                        # 无效的时间格式，删除
                        if self.delete_task_status(task_id):
                            deleted_count += 1
                            
            logger.info(f"清理了 {deleted_count} 个过期任务")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理过期任务失败: {e}")
            return 0


# 全局任务状态管理器实例
_task_status_manager = None


def get_task_status_manager() -> TaskStatusManager:
    """获取任务状态管理器实例"""
    global _task_status_manager
    if _task_status_manager is None:
        _task_status_manager = TaskStatusManager()
    return _task_status_manager
