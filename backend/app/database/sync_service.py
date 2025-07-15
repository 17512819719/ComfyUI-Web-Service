"""
数据同步服务
负责客户端和管理端数据到共享数据库的同步
"""
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .connection import get_database_manager
from .models.client_models import ClientTask
from .models.shared_models import GlobalTask
from .dao.task_dao import GlobalTaskDAO, ClientTaskDAO

logger = logging.getLogger(__name__)


class DataSyncService:
    """数据同步服务"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.global_task_dao = GlobalTaskDAO()
        self.client_task_dao = ClientTaskDAO()
        self.sync_interval = 30  # 同步间隔（秒）
        self.is_running = False
    
    async def start_sync_service(self):
        """启动同步服务"""
        if self.is_running:
            logger.warning("同步服务已在运行")
            return
        
        self.is_running = True
        logger.info("数据同步服务已启动")
        
        try:
            while self.is_running:
                await self.sync_client_to_shared()
                await asyncio.sleep(self.sync_interval)
        except Exception as e:
            logger.error(f"同步服务异常: {e}")
        finally:
            self.is_running = False
            logger.info("数据同步服务已停止")
    
    def stop_sync_service(self):
        """停止同步服务"""
        self.is_running = False
    
    async def sync_client_to_shared(self):
        """同步客户端数据到共享数据库"""
        try:
            # 获取需要同步的客户端任务
            client_session = self.db_manager.get_session_direct('client')
            shared_session = self.db_manager.get_session_direct('shared')
            
            try:
                # 查找最近更新的客户端任务
                recent_time = datetime.now() - timedelta(minutes=5)
                client_tasks = client_session.query(ClientTask).filter(
                    ClientTask.updated_at >= recent_time
                ).all()
                
                synced_count = 0
                for client_task in client_tasks:
                    if await self._sync_single_task(client_task, shared_session):
                        synced_count += 1
                
                if synced_count > 0:
                    shared_session.commit()
                    logger.debug(f"同步了 {synced_count} 个客户端任务到共享数据库")
                
            except SQLAlchemyError as e:
                shared_session.rollback()
                logger.error(f"同步客户端任务失败: {e}")
            finally:
                client_session.close()
                shared_session.close()
                
        except Exception as e:
            logger.error(f"同步服务执行失败: {e}")
    
    async def _sync_single_task(self, client_task: ClientTask, shared_session: Session) -> bool:
        """同步单个任务"""
        try:
            # 检查共享数据库中是否已存在该任务
            existing_task = shared_session.query(GlobalTask).filter(
                GlobalTask.task_id == client_task.task_id
            ).first()
            
            if existing_task:
                # 更新现有任务
                existing_task.status = client_task.status
                existing_task.progress = client_task.progress
                existing_task.message = client_task.message
                existing_task.error_message = client_task.error_message
                existing_task.actual_time = client_task.actual_time
                existing_task.started_at = client_task.started_at
                existing_task.completed_at = client_task.completed_at
                existing_task.updated_at = client_task.updated_at
            else:
                # 创建新任务
                global_task = GlobalTask(
                    task_id=client_task.task_id,
                    source_type='client',
                    source_user_id=client_task.client_id,
                    task_type=client_task.task_type,
                    workflow_name=client_task.workflow_name,
                    status=client_task.status,
                    priority=1,  # 默认优先级
                    progress=client_task.progress,
                    message=client_task.message,
                    error_message=client_task.error_message,
                    estimated_time=client_task.estimated_time,
                    actual_time=client_task.actual_time,
                    started_at=client_task.started_at,
                    completed_at=client_task.completed_at,
                    created_at=client_task.created_at,
                    updated_at=client_task.updated_at
                )
                shared_session.add(global_task)
            
            return True
            
        except Exception as e:
            logger.error(f"同步任务失败 [{client_task.task_id}]: {e}")
            return False
    
    def sync_task_immediately(self, task_id: str) -> bool:
        """立即同步指定任务"""
        try:
            client_session = self.db_manager.get_session_direct('client')
            shared_session = self.db_manager.get_session_direct('shared')
            
            try:
                # 获取客户端任务
                client_task = client_session.query(ClientTask).filter(
                    ClientTask.task_id == task_id
                ).first()
                
                if not client_task:
                    logger.warning(f"客户端任务不存在: {task_id}")
                    return False
                
                # 同步任务
                success = asyncio.run(self._sync_single_task(client_task, shared_session))
                if success:
                    shared_session.commit()
                    logger.info(f"任务立即同步成功: {task_id}")
                
                return success
                
            except SQLAlchemyError as e:
                shared_session.rollback()
                logger.error(f"立即同步任务失败: {e}")
                return False
            finally:
                client_session.close()
                shared_session.close()
                
        except Exception as e:
            logger.error(f"立即同步任务异常 [{task_id}]: {e}")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步服务状态"""
        return {
            'is_running': self.is_running,
            'sync_interval': self.sync_interval,
            'last_sync_time': datetime.now().isoformat()
        }
    
    def update_sync_config(self, config: Dict[str, Any]):
        """更新同步配置"""
        if 'sync_interval' in config:
            self.sync_interval = max(10, config['sync_interval'])  # 最小10秒
            logger.info(f"同步间隔已更新为: {self.sync_interval}秒")


# 全局同步服务实例
_sync_service = None


def get_sync_service() -> DataSyncService:
    """获取同步服务实例"""
    global _sync_service
    if _sync_service is None:
        _sync_service = DataSyncService()
    return _sync_service


async def start_data_sync():
    """启动数据同步服务"""
    sync_service = get_sync_service()
    await sync_service.start_sync_service()


def stop_data_sync():
    """停止数据同步服务"""
    sync_service = get_sync_service()
    sync_service.stop_sync_service()
