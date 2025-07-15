"""
任务相关数据访问对象
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc

from .base_dao import BaseDAO
from ..models.shared_models import GlobalTask, GlobalTaskParameter, GlobalTaskResult
from ..models.client_models import ClientTask, ClientTaskParameter, ClientTaskResult
from ..connection import get_database_manager

logger = logging.getLogger(__name__)


class GlobalTaskDAO(BaseDAO):
    """全局任务数据访问对象"""
    
    def __init__(self):
        super().__init__('shared', GlobalTask)
    
    def create_task(self, task_data: Dict[str, Any], parameters: List[Dict[str, Any]] = None) -> Optional[GlobalTask]:
        """创建任务及其参数"""
        session = self.get_session()
        try:
            # 创建任务
            task = GlobalTask(**task_data)
            session.add(task)
            session.flush()  # 获取任务ID
            
            # 创建参数
            if parameters:
                for param in parameters:
                    param['task_id'] = task.id
                    task_param = GlobalTaskParameter(**param)
                    session.add(task_param)
            
            session.commit()
            session.refresh(task)
            return task
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"创建全局任务失败: {e}")
            return None
        finally:
            session.close()
    
    def get_task_by_task_id(self, task_id: str) -> Optional[GlobalTask]:
        """根据task_id获取任务"""
        return self.get_by_field('task_id', task_id)
    
    def get_task_by_celery_id(self, celery_task_id: str) -> Optional[GlobalTask]:
        """根据celery_task_id获取任务"""
        return self.get_by_field('celery_task_id', celery_task_id)
    
    def update_task_status(self, task_id: str, status_data: Dict[str, Any]) -> bool:
        """更新任务状态"""
        status_data['updated_at'] = datetime.now()
        return self.update_by_field('task_id', task_id, **status_data)
    
    def get_tasks_by_user(self, source_user_id: str, source_type: str = None, 
                         limit: int = 50, offset: int = 0) -> List[GlobalTask]:
        """获取用户的任务列表"""
        session = self.get_session()
        try:
            query = session.query(GlobalTask).filter(
                GlobalTask.source_user_id == source_user_id
            )
            if source_type:
                query = query.filter(GlobalTask.source_type == source_type)
            
            return query.order_by(desc(GlobalTask.created_at)).offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"查询用户任务失败: {e}")
            return []
        finally:
            session.close()
    
    def get_tasks_by_status(self, status: str, limit: int = 100) -> List[GlobalTask]:
        """根据状态获取任务"""
        session = self.get_session()
        try:
            return session.query(GlobalTask).filter(
                GlobalTask.status == status
            ).order_by(GlobalTask.created_at).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"查询状态任务失败: {e}")
            return []
        finally:
            session.close()
    
    def get_running_tasks(self) -> List[GlobalTask]:
        """获取正在运行的任务"""
        session = self.get_session()
        try:
            return session.query(GlobalTask).filter(
                or_(
                    GlobalTask.status == 'queued',
                    GlobalTask.status == 'processing'
                )
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"查询运行中任务失败: {e}")
            return []
        finally:
            session.close()
    
    def add_task_result(self, task_id: str, result_data: Dict[str, Any]) -> bool:
        """添加任务结果"""
        session = self.get_session()
        try:
            # 获取任务
            task = session.query(GlobalTask).filter(
                GlobalTask.task_id == task_id
            ).first()
            
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            # 创建结果记录
            result_data['task_id'] = task.id
            result = GlobalTaskResult(**result_data)
            session.add(result)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加任务结果失败: {e}")
            return False
        finally:
            session.close()
    
    def get_task_results(self, task_id: str) -> List[GlobalTaskResult]:
        """获取任务结果"""
        session = self.get_session()
        try:
            task = session.query(GlobalTask).filter(
                GlobalTask.task_id == task_id
            ).first()
            
            if not task:
                return []
            
            return session.query(GlobalTaskResult).filter(
                GlobalTaskResult.task_id == task.id
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"查询任务结果失败: {e}")
            return []
        finally:
            session.close()


class ClientTaskDAO(BaseDAO):
    """客户端任务数据访问对象"""

    def __init__(self):
        super().__init__('client', ClientTask)

    def create_task(self, task_data: Dict[str, Any], parameters: List[Dict[str, Any]] = None) -> Optional[ClientTask]:
        """创建客户端任务及其参数"""
        session = self.get_session()
        try:
            # 创建任务
            task = ClientTask(**task_data)
            session.add(task)
            session.flush()  # 获取任务ID

            # 创建参数
            if parameters:
                for param in parameters:
                    param['task_id'] = task.id
                    task_param = ClientTaskParameter(**param)
                    session.add(task_param)

            session.commit()
            session.refresh(task)
            return task
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"创建客户端任务失败: {e}")
            return None
        finally:
            session.close()

    def get_task_by_task_id(self, task_id: str) -> Optional[ClientTask]:
        """根据task_id获取任务"""
        return self.get_by_field('task_id', task_id)

    def update_task_status(self, task_id: str, status_data: Dict[str, Any]) -> bool:
        """更新任务状态"""
        status_data['updated_at'] = datetime.now()
        return self.update_by_field('task_id', task_id, **status_data)

    def get_tasks_by_client(self, client_id: str, limit: int = 50, offset: int = 0) -> List[ClientTask]:
        """获取客户端的任务列表"""
        session = self.get_session()
        try:
            return session.query(ClientTask).filter(
                ClientTask.client_id == client_id
            ).order_by(desc(ClientTask.created_at)).offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"查询客户端任务失败: {e}")
            return []
        finally:
            session.close()

    def get_task_results(self, task_id: str) -> List[ClientTaskResult]:
        """获取任务结果"""
        session = self.get_session()
        try:
            task = session.query(ClientTask).filter(
                ClientTask.task_id == task_id
            ).first()

            if not task:
                return []

            return session.query(ClientTaskResult).filter(
                ClientTaskResult.task_id == task.id
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"查询客户端任务结果失败: {e}")
            return []
        finally:
            session.close()


class GlobalTaskResultDAO(BaseDAO):
    """全局任务结果数据访问对象"""

    def __init__(self):
        from ..models.shared_models import GlobalTaskResult
        super().__init__('shared', GlobalTaskResult)


class ClientTaskResultDAO(BaseDAO):
    """客户端任务结果数据访问对象"""

    def __init__(self):
        from ..models.client_models import ClientTaskResult
        super().__init__('client', ClientTaskResult)
    
    def add_task_result(self, task_id: str, result_data: Dict[str, Any]) -> bool:
        """添加任务结果"""
        session = self.get_session()
        try:
            # 获取任务
            task = session.query(ClientTask).filter(
                ClientTask.task_id == task_id
            ).first()
            
            if not task:
                logger.error(f"客户端任务不存在: {task_id}")
                return False
            
            # 创建结果记录
            result_data['task_id'] = task.id
            result = ClientTaskResult(**result_data)
            session.add(result)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"添加客户端任务结果失败: {e}")
            return False
        finally:
            session.close()
    
    def get_task_results(self, task_id: str) -> List[ClientTaskResult]:
        """获取任务结果"""
        session = self.get_session()
        try:
            task = session.query(ClientTask).filter(
                ClientTask.task_id == task_id
            ).first()
            
            if not task:
                return []
            
            return session.query(ClientTaskResult).filter(
                ClientTaskResult.task_id == task.id
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"查询客户端任务结果失败: {e}")
            return []
        finally:
            session.close()
