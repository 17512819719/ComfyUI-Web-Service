"""
日志记录服务
负责访问日志、系统日志的数据库持久化
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from fastapi import Request

from ..database.dao.base_dao import BaseDAO
from ..database.models.client_models import ClientAccessLog
from ..database.models.shared_models import SystemLog

logger = logging.getLogger(__name__)


class LogService:
    """日志记录服务"""
    
    def __init__(self):
        self.access_log_dao = BaseDAO('client', ClientAccessLog)
        self.system_log_dao = BaseDAO('shared', SystemLog)
    
    def log_client_access(self, request: Request, user_info: Dict[str, Any] = None, 
                         response_status: int = 200, response_time: float = 0.0) -> bool:
        """记录客户端访问日志"""
        try:
            # 获取客户端信息
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get('user-agent', '')
            
            # 构建请求信息
            request_data = {
                'method': request.method,
                'url': str(request.url),
                'headers': dict(request.headers),
                'query_params': dict(request.query_params)
            }
            
            # 记录访问日志
            access_log = self.access_log_dao.create(
                client_id=user_info.get('client_id') if user_info else None,
                ip_address=client_ip,
                user_agent=user_agent,
                request_method=request.method,
                request_path=request.url.path,
                request_data=json.dumps(request_data, ensure_ascii=False),
                response_status=response_status,
                response_time=response_time,
                access_time=datetime.utcnow()
            )
            
            return access_log is not None
            
        except Exception as e:
            logger.error(f"记录访问日志失败: {e}")
            return False
    
    def log_system_event(self, event_type: str, event_data: Dict[str, Any], 
                        level: str = 'INFO', source: str = 'system') -> bool:
        """记录系统事件日志"""
        try:
            system_log = self.system_log_dao.create(
                log_level=level.upper(),
                event_type=event_type,
                message=event_data.get('message', ''),
                event_data=json.dumps(event_data, ensure_ascii=False),
                source=source,
                created_at=datetime.utcnow()
            )
            
            return system_log is not None
            
        except Exception as e:
            logger.error(f"记录系统日志失败: {e}")
            return False
    
    def get_client_access_logs(self, client_id: str = None, limit: int = 100, 
                              offset: int = 0) -> List[Dict[str, Any]]:
        """获取客户端访问日志"""
        try:
            with self.access_log_dao.get_session() as session:
                query = session.query(ClientAccessLog)
                
                if client_id:
                    query = query.filter(ClientAccessLog.client_id == client_id)
                
                logs = query.order_by(ClientAccessLog.access_time.desc()).offset(offset).limit(limit).all()
                
                return [self._access_log_to_dict(log) for log in logs]
                
        except Exception as e:
            logger.error(f"获取访问日志失败: {e}")
            return []
    
    def get_system_logs(self, event_type: str = None, level: str = None, 
                       limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取系统日志"""
        try:
            with self.system_log_dao.get_session() as session:
                query = session.query(SystemLog)
                
                if event_type:
                    query = query.filter(SystemLog.event_type == event_type)
                
                if level:
                    query = query.filter(SystemLog.log_level == level.upper())
                
                logs = query.order_by(SystemLog.created_at.desc()).offset(offset).limit(limit).all()
                
                return [self._system_log_to_dict(log) for log in logs]
                
        except Exception as e:
            logger.error(f"获取系统日志失败: {e}")
            return []
    
    def get_access_statistics(self, client_id: str = None, 
                            start_date: datetime = None, 
                            end_date: datetime = None) -> Dict[str, Any]:
        """获取访问统计信息"""
        try:
            with self.access_log_dao.get_session() as session:
                query = session.query(ClientAccessLog)
                
                if client_id:
                    query = query.filter(ClientAccessLog.client_id == client_id)
                
                if start_date:
                    query = query.filter(ClientAccessLog.access_time >= start_date)
                
                if end_date:
                    query = query.filter(ClientAccessLog.access_time <= end_date)
                
                total_requests = query.count()
                
                # 按状态码统计
                status_stats = {}
                for log in query.all():
                    status = str(log.response_status)
                    status_stats[status] = status_stats.get(status, 0) + 1
                
                # 按请求方法统计
                method_stats = {}
                for log in query.all():
                    method = log.request_method
                    method_stats[method] = method_stats.get(method, 0) + 1
                
                return {
                    'total_requests': total_requests,
                    'status_statistics': status_stats,
                    'method_statistics': method_stats
                }
                
        except Exception as e:
            logger.error(f"获取访问统计失败: {e}")
            return {}
    
    def clean_old_logs(self, days: int = 30) -> bool:
        """清理旧日志"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 清理访问日志
            with self.access_log_dao.get_session() as session:
                deleted_access = session.query(ClientAccessLog).filter(
                    ClientAccessLog.access_time < cutoff_date
                ).delete()
                session.commit()
            
            # 清理系统日志
            with self.system_log_dao.get_session() as session:
                deleted_system = session.query(SystemLog).filter(
                    SystemLog.created_at < cutoff_date
                ).delete()
                session.commit()
            
            logger.info(f"清理旧日志完成: 访问日志 {deleted_access} 条, 系统日志 {deleted_system} 条")
            return True
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
            return False
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # 返回直接连接的IP
        return request.client.host if request.client else 'unknown'
    
    def _access_log_to_dict(self, log: ClientAccessLog) -> Dict[str, Any]:
        """将访问日志转换为字典"""
        return {
            'id': log.id,
            'client_id': log.client_id,
            'ip_address': log.ip_address,
            'user_agent': log.user_agent,
            'request_method': log.request_method,
            'request_path': log.request_path,
            'request_data': json.loads(log.request_data) if log.request_data else {},
            'response_status': log.response_status,
            'response_time': log.response_time,
            'access_time': log.access_time.isoformat() if log.access_time else None
        }
    
    def _system_log_to_dict(self, log: SystemLog) -> Dict[str, Any]:
        """将系统日志转换为字典"""
        return {
            'id': log.id,
            'log_level': log.log_level,
            'event_type': log.event_type,
            'message': log.message,
            'event_data': json.loads(log.event_data) if log.event_data else {},
            'source': log.source,
            'created_at': log.created_at.isoformat() if log.created_at else None
        }


# 全局实例
_log_service = None

def get_log_service() -> LogService:
    """获取日志服务实例"""
    global _log_service
    if _log_service is None:
        _log_service = LogService()
    return _log_service


# 中间件函数
async def log_request_middleware(request: Request, call_next):
    """请求日志中间件"""
    start_time = datetime.utcnow()
    
    try:
        response = await call_next(request)
        
        # 计算响应时间
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()
        
        # 记录访问日志（异步执行，不阻塞响应）
        try:
            log_service = get_log_service()
            # 这里可以从request中获取用户信息
            user_info = getattr(request.state, 'user', None)
            log_service.log_client_access(request, user_info, response.status_code, response_time)
        except Exception as e:
            logger.error(f"记录访问日志失败: {e}")
        
        return response
        
    except Exception as e:
        # 记录错误日志
        try:
            log_service = get_log_service()
            log_service.log_system_event(
                event_type='request_error',
                event_data={
                    'message': f"请求处理失败: {str(e)}",
                    'path': request.url.path,
                    'method': request.method,
                    'error': str(e)
                },
                level='ERROR',
                source='middleware'
            )
        except:
            pass
        
        raise
