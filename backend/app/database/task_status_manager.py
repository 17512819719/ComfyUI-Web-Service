"""
基于数据库的任务状态管理器
替代原有的Redis内存存储方式
"""
import logging
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from .dao.task_dao import GlobalTaskDAO, ClientTaskDAO
from ..core.task_status_manager import TaskStatusManager as BaseTaskStatusManager

logger = logging.getLogger(__name__)


class DatabaseTaskStatusManager(BaseTaskStatusManager):
    """基于数据库的任务状态管理器"""
    
    def __init__(self):
        self.global_task_dao = GlobalTaskDAO()
        self.client_task_dao = ClientTaskDAO()
        logger.info("数据库任务状态管理器已初始化")
    
    def set_task_status(self, task_id: str, status_data: Dict[str, Any]) -> bool:
        """设置任务状态"""
        try:
            # 提取结果数据
            result_data = status_data.pop('result_data', None)

            # 为全局任务过滤字段
            global_status_data = self._filter_global_task_fields(status_data.copy())

            # 为客户端任务过滤字段
            client_status_data = self._filter_client_task_fields(status_data.copy())

            # 更新全局任务状态
            global_updated = self.global_task_dao.update_task_status(task_id, global_status_data)

            # 更新客户端任务状态（如果存在）
            client_updated = self.client_task_dao.update_task_status(task_id, client_status_data)

            # 如果任务完成且有结果数据，保存结果
            if result_data and status_data.get('status') == 'completed':
                self._save_task_results(task_id, result_data)

            if global_updated or client_updated:
                logger.debug(f"任务状态已更新: {task_id} -> {status_data.get('status', 'unknown')}")
                return True
            else:
                logger.warning(f"任务状态更新失败，任务不存在: {task_id}")
                return False

        except Exception as e:
            logger.error(f"设置任务状态失败 [{task_id}]: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        try:
            # logger.info(f"[DB_GET] 开始获取任务状态: {task_id}")  

            # 首先尝试从全局任务获取
            global_task = self.global_task_dao.get_task_by_task_id(task_id)
            if global_task:
                logger.info(f"[DB_GET] 任务 {task_id} 从全局任务表获取成功")
                task_dict = self._task_to_dict(global_task)
                return task_dict

            # 如果全局任务不存在，尝试从客户端任务获取
            client_task = self.client_task_dao.get_task_by_task_id(task_id)
            if client_task:
                logger.info(f"[DB_GET] 任务 {task_id} 从客户端任务表获取成功")
                task_dict = self._task_to_dict(client_task)
                return task_dict

            logger.warning(f"[DB_GET] 任务 {task_id} 在数据库中不存在")
            return None

        except Exception as e:
            logger.error(f"[DB_GET] 获取任务状态失败 [{task_id}]: {e}")
            import traceback
            logger.error(f"[DB_GET] 错误堆栈: {traceback.format_exc()}")
            return None
    
    def update_task_status(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新任务状态（合并更新）"""
        try:
            # 获取当前状态
            current_status = self.get_task_status(task_id)
            if not current_status:
                logger.warning(f"任务不存在，无法更新: {task_id}")
                return False
            
            # 合并更新数据
            current_status.update(updates)
            current_status['updated_at'] = datetime.now()
            
            # 保存更新
            return self.set_task_status(task_id, current_status)
            
        except Exception as e:
            logger.error(f"更新任务状态失败 [{task_id}]: {e}")
            return False
    
    def delete_task_status(self, task_id: str) -> bool:
        """删除任务状态"""
        try:
            # 删除全局任务
            global_deleted = self.global_task_dao.delete_by_field('task_id', task_id)
            
            # 删除客户端任务
            client_deleted = self.client_task_dao.delete_by_field('task_id', task_id)
            
            return global_deleted or client_deleted
            
        except Exception as e:
            logger.error(f"删除任务状态失败 [{task_id}]: {e}")
            return False
    
    def list_tasks(self, status: str = None, limit: int = 100) -> Dict[str, Dict[str, Any]]:
        """列出任务"""
        try:
            tasks = {}
            
            # 获取全局任务
            if status:
                global_tasks = self.global_task_dao.get_tasks_by_status(status, limit)
            else:
                global_tasks = self.global_task_dao.get_all(limit=limit)
            
            for task in global_tasks:
                tasks[task.task_id] = self._task_to_dict(task)
            
            return tasks
            
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return {}
    
    def get_user_tasks(self, user_id: str, source_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户任务"""
        try:
            if source_type == 'client':
                tasks = self.client_task_dao.get_tasks_by_client(user_id, limit=limit)
            else:
                tasks = self.global_task_dao.get_tasks_by_user(user_id, source_type, limit=limit)
            
            return [self._task_to_dict(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"获取用户任务失败 [{user_id}]: {e}")
            return []
    
    def get_running_tasks(self) -> List[Dict[str, Any]]:
        """获取正在运行的任务"""
        try:
            tasks = self.global_task_dao.get_running_tasks()
            return [self._task_to_dict(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"获取运行中任务失败: {e}")
            return []
    
    def create_task(self, task_data: Dict[str, Any], source_type: str = 'client') -> bool:
        """创建任务"""
        task_id = task_data.get('task_id', 'unknown')
        try:
            logger.info(f"[DB_CREATE] 开始创建任务 {task_id}, source_type: {source_type}")

            # 提取参数
            parameters = task_data.pop('parameters', [])

            if source_type == 'client':
                # 为客户端任务准备数据（包含所有必要字段）
                client_task_data = {
                    'task_id': task_data.get('task_id'),
                    'client_id': task_data.get('client_id'),
                    'task_type': task_data.get('task_type'),
                    'workflow_name': task_data.get('workflow_name'),
                    'prompt': task_data.get('prompt', ''),
                    'negative_prompt': task_data.get('negative_prompt', ''),
                    # 添加关键生成参数
                    'model_name': task_data.get('model_name'),
                    'width': task_data.get('width'),
                    'height': task_data.get('height'),
                    'steps': task_data.get('steps'),
                    'cfg_scale': task_data.get('cfg_scale'),
                    'sampler': task_data.get('sampler'),
                    'scheduler': task_data.get('scheduler'),
                    'seed': task_data.get('seed'),
                    'batch_size': task_data.get('batch_size', 1),
                    'status': task_data.get('status'),
                    'progress': task_data.get('progress', 0),
                    'message': task_data.get('message'),
                    'estimated_time': task_data.get('estimated_time')
                }

                # 创建客户端任务
                logger.info(f"[DB_CREATE] 任务 {task_id} 开始创建客户端任务...")
                client_task = self.client_task_dao.create_task(client_task_data, parameters)
                if not client_task:
                    logger.error(f"[DB_CREATE] 任务 {task_id} 客户端任务创建失败")
                    return False
                else:
                    logger.info(f"[DB_CREATE] 任务 {task_id} 客户端任务创建成功，数据库ID: {client_task.id}")

                # 为全局任务准备数据（包含所有必要字段）
                global_task_data = {
                    'task_id': task_data.get('task_id'),
                    'source_type': source_type,
                    'source_user_id': task_data.get('client_id', ''),  # 使用client_id作为source_user_id
                    'task_type': task_data.get('task_type'),
                    'workflow_name': task_data.get('workflow_name'),
                    'prompt': task_data.get('prompt', ''),
                    'negative_prompt': task_data.get('negative_prompt', ''),
                    # 添加关键生成参数
                    'model_name': task_data.get('model_name'),
                    'width': task_data.get('width'),
                    'height': task_data.get('height'),
                    'steps': task_data.get('steps'),
                    'cfg_scale': task_data.get('cfg_scale'),
                    'sampler': task_data.get('sampler'),
                    'scheduler': task_data.get('scheduler'),
                    'seed': task_data.get('seed'),
                    'batch_size': task_data.get('batch_size', 1),
                    'status': task_data.get('status'),
                    'priority': task_data.get('priority', 1),
                    'progress': task_data.get('progress', 0),
                    'message': task_data.get('message'),
                    'estimated_time': task_data.get('estimated_time')
                }

                # 同步到全局任务
                logger.info(f"[DB_CREATE] 任务 {task_id} 开始创建全局任务...")
                global_task = self.global_task_dao.create_task(global_task_data, parameters)

                if global_task:
                    logger.info(f"[DB_CREATE] 任务 {task_id} 全局任务创建成功，数据库ID: {global_task.id}")
                    return True
                else:
                    logger.error(f"[DB_CREATE] 任务 {task_id} 全局任务创建失败")
                    return False
            else:
                # 直接创建全局任务
                logger.info(f"[DB_CREATE] 任务 {task_id} 直接创建全局任务...")
                task_data['source_type'] = source_type
                global_task = self.global_task_dao.create_task(task_data, parameters)

                if global_task:
                    logger.info(f"[DB_CREATE] 任务 {task_id} 全局任务创建成功，数据库ID: {global_task.id}")
                    return True
                else:
                    logger.error(f"[DB_CREATE] 任务 {task_id} 全局任务创建失败")
                    return False

        except Exception as e:
            logger.error(f"[DB_CREATE] 任务 {task_id} 创建失败: {e}")
            import traceback
            logger.error(f"[DB_CREATE] 错误堆栈: {traceback.format_exc()}")
            return False

    def _save_task_results(self, task_id: str, result_data: Dict[str, Any]) -> bool:
        """保存任务结果到数据库"""
        try:
            # 保存到全局任务结果表
            global_task = self.global_task_dao.get_task_by_task_id(task_id)
            if global_task:
                self._save_global_task_results(global_task.id, result_data)

            # 保存到客户端任务结果表
            client_task = self.client_task_dao.get_task_by_task_id(task_id)
            if client_task:
                self._save_client_task_results(client_task.id, result_data)

            logger.info(f"任务结果已保存: {task_id}")
            return True

        except Exception as e:
            logger.error(f"保存任务结果失败 [{task_id}]: {e}")
            return False

    def _save_global_task_results(self, task_db_id: int, result_data: Dict[str, Any]):
        """保存全局任务结果"""
        from .dao.task_dao import GlobalTaskResultDAO
        from .models.shared_models import GlobalTaskResult

        result_dao = GlobalTaskResultDAO()

        # 处理文件列表
        files = result_data.get('files', [])
        for i, file_path in enumerate(files):
            result_record = {
                'task_id': task_db_id,
                'result_type': 'image',
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'result_metadata': {
                    'original_filename': os.path.basename(file_path),
                    'result_index': i
                }
            }
            result_dao.create(**result_record)

    def _save_client_task_results(self, task_db_id: int, result_data: Dict[str, Any]):
        """保存客户端任务结果"""
        from .dao.task_dao import ClientTaskResultDAO
        from .models.client_models import ClientTaskResult

        result_dao = ClientTaskResultDAO()

        # 处理文件列表
        files = result_data.get('files', [])
        for i, file_path in enumerate(files):
            result_record = {
                'task_id': task_db_id,
                'result_type': 'image',
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'result_metadata': {
                    'original_filename': os.path.basename(file_path),
                    'result_index': i
                }
            }
            result_dao.create(**result_record)
    
    def add_task_result(self, task_id: str, result_data: Dict[str, Any]) -> bool:
        """添加任务结果"""
        try:
            # 添加到全局任务结果
            global_added = self.global_task_dao.add_task_result(task_id, result_data)
            
            # 添加到客户端任务结果
            client_added = self.client_task_dao.add_task_result(task_id, result_data)
            
            return global_added or client_added
            
        except Exception as e:
            logger.error(f"添加任务结果失败 [{task_id}]: {e}")
            return False
    
    def get_task_results(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务结果"""
        try:
            # 首先尝试从全局任务获取结果
            results = self.global_task_dao.get_task_results(task_id)
            if results:
                return [self._result_to_dict(result) for result in results]
            
            # 如果全局任务没有结果，尝试从客户端任务获取
            results = self.client_task_dao.get_task_results(task_id)
            return [self._result_to_dict(result) for result in results]
            
        except Exception as e:
            logger.error(f"获取任务结果失败 [{task_id}]: {e}")
            return []
    
    def _task_to_dict(self, task) -> Dict[str, Any]:
        """将任务对象转换为字典"""
        task_dict = {
            'task_id': task.task_id,
            'status': task.status,
            'progress': float(task.progress) if task.progress else 0.0,
            'message': task.message,
            'error_message': task.error_message,
            'task_type': task.task_type,
            'workflow_name': task.workflow_name,
            'prompt': getattr(task, 'prompt', ''),
            'negative_prompt': getattr(task, 'negative_prompt', ''),
            'estimated_time': task.estimated_time,
            'actual_time': task.actual_time,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'updated_at': task.updated_at.isoformat() if task.updated_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'celery_task_id': getattr(task, 'celery_task_id', None),
            'node_id': getattr(task, 'node_id', None),
            'source_type': getattr(task, 'source_type', 'client'),
            'source_user_id': getattr(task, 'source_user_id', getattr(task, 'client_id', ''))
        }

        # 如果任务已完成，添加结果数据
        if task.status == 'completed':
            try:
                results = self.get_task_results(task.task_id)
                if results:
                    # 提取文件路径列表并转换为URL
                    files = [result.get('file_path') for result in results if result.get('file_path')]
                    if files:
                        # 生成可访问的URL列表
                        result_urls = []
                        for i, file_path in enumerate(files):
                            # 尝试生成静态文件URL
                            static_url = self._convert_file_path_to_url(file_path)
                            if static_url:
                                result_urls.append(static_url)
                            else:
                                # 兜底使用下载接口
                                result_urls.append(f"/api/v2/tasks/{task.task_id}/download?index={i}")

                        task_dict['result_data'] = {
                            'files': files,
                            'task_id': task.task_id
                        }
                        # 添加前端需要的URL字段
                        task_dict['resultUrls'] = result_urls
                        task_dict['resultUrl'] = result_urls[0] if result_urls else None
            except Exception as e:
                logger.error(f"获取任务结果失败 [{task.task_id}]: {e}")
                task_dict['result_data'] = None
                task_dict['resultUrls'] = []
                task_dict['resultUrl'] = None
        else:
            task_dict['result_data'] = None
            task_dict['resultUrls'] = []
            task_dict['resultUrl'] = None

        return task_dict

    def _convert_file_path_to_url(self, file_path: str) -> str:
        """将文件路径转换为静态文件URL"""
        import os
        import re

        # 调试日志
        logger.debug(f"转换文件路径: {file_path}")

        # 检查是否为分布式模式
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()
            if config_manager.is_distributed_mode():
                # 分布式模式下，相对路径文件应该通过代理接口访问
                # 不生成静态文件URL，直接返回None使用下载接口
                logger.debug(f"分布式模式，使用代理接口访问文件: {file_path}")
                return None
        except Exception as e:
            logger.warning(f"检查分布式模式失败: {e}")

        # 标准化路径分隔符
        file_path = file_path.replace('\\', '/')

        # 尝试匹配backend/outputs目录
        if '/backend/outputs/' in file_path or 'backend/outputs/' in file_path:
            # 使用正则表达式匹配outputs之后的路径
            match = re.search(r'backend/outputs/(.+)$', file_path)
            if match:
                url_path = match.group(1)
                logger.debug(f"Backend输出URL: /outputs/{url_path}")
                return f"/outputs/{url_path}"

        # 尝试匹配项目根目录下的outputs目录
        if '/outputs/' in file_path:
            # 使用正则表达式匹配最后一个outputs之后的路径
            match = re.search(r'outputs/(.+)$', file_path)
            if match:
                url_path = match.group(1)
                logger.debug(f"项目输出URL: /outputs/{url_path}")
                return f"/outputs/{url_path}"

        # 尝试匹配ComfyUI output目录
        if '/ComfyUI/output/' in file_path or 'ComfyUI/output/' in file_path:
            # 使用正则表达式匹配output之后的路径
            match = re.search(r'ComfyUI/output/(.+)$', file_path)
            if match:
                url_path = match.group(1)
                logger.debug(f"ComfyUI输出URL: /comfyui-output/{url_path}")
                return f"/comfyui-output/{url_path}"

        # 尝试匹配任何output目录（兜底）
        if '/output/' in file_path:
            match = re.search(r'output/(.+)$', file_path)
            if match:
                url_path = match.group(1)
                logger.debug(f"通用输出URL: /comfyui-output/{url_path}")
                return f"/comfyui-output/{url_path}"

        # 默认返回None（使用下载接口作为兜底）
        logger.debug(f"无法转换路径: {file_path}")
        return None

    def _result_to_dict(self, result) -> Dict[str, Any]:
        """将结果对象转换为字典"""
        return {
            'result_type': result.result_type,
            'file_path': result.file_path,
            'file_name': result.file_name,
            'file_size': result.file_size,
            'width': result.width,
            'height': result.height,
            'duration': float(result.duration) if result.duration else None,
            'thumbnail_path': getattr(result, 'thumbnail_path', None),
            'download_count': result.download_count,
            'created_at': result.created_at.isoformat() if result.created_at else None
        }

    def _filter_global_task_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤全局任务表字段"""
        allowed_fields = {
            'status', 'priority', 'progress', 'message', 'error_message',
            'celery_task_id', 'node_id', 'estimated_time', 'actual_time',
            'started_at', 'completed_at',
            # 生成参数字段
            'model_name', 'width', 'height', 'steps', 'cfg_scale',
            'sampler', 'scheduler', 'seed', 'batch_size'
        }
        return {k: v for k, v in data.items() if k in allowed_fields}

    def _filter_client_task_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤客户端任务表字段"""
        allowed_fields = {
            'status', 'progress', 'message', 'error_message',
            'estimated_time', 'actual_time', 'started_at', 'completed_at',
            # 生成参数字段
            'model_name', 'width', 'height', 'steps', 'cfg_scale',
            'sampler', 'scheduler', 'seed', 'batch_size'
        }
        return {k: v for k, v in data.items() if k in allowed_fields}


# 全局实例
_db_task_status_manager: Optional[DatabaseTaskStatusManager] = None


def get_database_task_status_manager() -> DatabaseTaskStatusManager:
    """获取数据库任务状态管理器实例"""
    global _db_task_status_manager
    if _db_task_status_manager is None:
        _db_task_status_manager = DatabaseTaskStatusManager()
    return _db_task_status_manager
