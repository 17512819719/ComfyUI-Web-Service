"""
性能监控服务
负责系统性能指标的收集和数据库持久化
"""
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

from ..database.dao.base_dao import BaseDAO
from ..database.models.shared_models import PerformanceMetric

logger = logging.getLogger(__name__)


class PerformanceService:
    """性能监控服务"""
    
    def __init__(self):
        self.metric_dao = BaseDAO('shared', PerformanceMetric)
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统性能指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used
            memory_total = memory.total
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_used = disk.used
            disk_total = disk.total
            
            # 网络IO
            network = psutil.net_io_counters()
            
            # 进程信息
            process_count = len(psutil.pids())
            
            return {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'memory_percent': memory_percent,
                'memory_used': memory_used,
                'memory_total': memory_total,
                'disk_percent': disk_percent,
                'disk_used': disk_used,
                'disk_total': disk_total,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'process_count': process_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return {}
    
    def record_performance_metric(self, metric_type: str, metric_name: str,
                                 metric_value: float, metadata: Dict[str, Any] = None) -> bool:
        """记录性能指标"""
        try:
            metric = self.metric_dao.create(
                metric_type=metric_type,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_metadata=metadata or {},
                recorded_at=datetime.utcnow()
            )
            
            return metric is not None
            
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
            return False
    
    def record_system_metrics(self) -> bool:
        """记录系统性能指标到数据库"""
        try:
            metrics = self.collect_system_metrics()
            if not metrics:
                return False
            
            # 记录各项指标
            success_count = 0
            
            # CPU指标
            if self.record_performance_metric('system', 'cpu_percent', metrics['cpu_percent']):
                success_count += 1
            
            # 内存指标
            if self.record_performance_metric('system', 'memory_percent', metrics['memory_percent']):
                success_count += 1
            
            # 磁盘指标
            if self.record_performance_metric('system', 'disk_percent', metrics['disk_percent']):
                success_count += 1
            
            # 进程数量
            if self.record_performance_metric('system', 'process_count', metrics['process_count']):
                success_count += 1
            
            logger.debug(f"记录系统指标完成: {success_count} 项")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"记录系统指标失败: {e}")
            return False
    
    def record_task_performance(self, task_id: str, task_type: str, 
                               execution_time: float, memory_usage: float = None) -> bool:
        """记录任务性能指标"""
        try:
            metadata = {
                'task_id': task_id,
                'task_type': task_type
            }
            
            if memory_usage is not None:
                metadata['memory_usage'] = memory_usage

            return self.record_performance_metric(
                metric_type='task',
                metric_name='execution_time',
                metric_value=execution_time,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"记录任务性能失败: {e}")
            return False
    
    def get_performance_metrics(self, metric_type: str = None, metric_name: str = None,
                               start_time: datetime = None, end_time: datetime = None,
                               limit: int = 100) -> List[Dict[str, Any]]:
        """获取性能指标"""
        try:
            with self.metric_dao.get_session() as session:
                query = session.query(PerformanceMetric)
                
                if metric_type:
                    query = query.filter(PerformanceMetric.metric_type == metric_type)
                
                if metric_name:
                    query = query.filter(PerformanceMetric.metric_name == metric_name)
                
                if start_time:
                    query = query.filter(PerformanceMetric.recorded_at >= start_time)
                
                if end_time:
                    query = query.filter(PerformanceMetric.recorded_at <= end_time)
                
                metrics = query.order_by(PerformanceMetric.recorded_at.desc()).limit(limit).all()
                
                return [self._metric_to_dict(metric) for metric in metrics]
                
        except Exception as e:
            logger.error(f"获取性能指标失败: {e}")
            return []
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            with self.metric_dao.get_session() as session:
                # CPU平均使用率
                cpu_metrics = session.query(PerformanceMetric).filter(
                    PerformanceMetric.metric_type == 'system',
                    PerformanceMetric.metric_name == 'cpu_percent',
                    PerformanceMetric.recorded_at >= start_time
                ).all()
                
                cpu_avg = sum(m.metric_value for m in cpu_metrics) / len(cpu_metrics) if cpu_metrics else 0
                
                # 内存平均使用率
                memory_metrics = session.query(PerformanceMetric).filter(
                    PerformanceMetric.metric_type == 'system',
                    PerformanceMetric.metric_name == 'memory_percent',
                    PerformanceMetric.recorded_at >= start_time
                ).all()
                
                memory_avg = sum(m.metric_value for m in memory_metrics) / len(memory_metrics) if memory_metrics else 0
                
                # 任务执行时间统计
                task_metrics = session.query(PerformanceMetric).filter(
                    PerformanceMetric.metric_type == 'task',
                    PerformanceMetric.metric_name == 'execution_time',
                    PerformanceMetric.recorded_at >= start_time
                ).all()
                
                task_count = len(task_metrics)
                task_avg_time = sum(m.metric_value for m in task_metrics) / task_count if task_metrics else 0
                
                return {
                    'time_range': f'{hours} hours',
                    'cpu_average': round(cpu_avg, 2),
                    'memory_average': round(memory_avg, 2),
                    'task_count': task_count,
                    'task_average_time': round(task_avg_time, 2),
                    'data_points': len(cpu_metrics) + len(memory_metrics) + len(task_metrics)
                }
                
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {}
    
    def clean_old_metrics(self, days: int = 7) -> bool:
        """清理旧的性能指标"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            with self.metric_dao.get_session() as session:
                deleted_count = session.query(PerformanceMetric).filter(
                    PerformanceMetric.recorded_at < cutoff_date
                ).delete()
                session.commit()
            
            logger.info(f"清理旧性能指标完成: {deleted_count} 条")
            return True
            
        except Exception as e:
            logger.error(f"清理旧性能指标失败: {e}")
            return False
    
    def _metric_to_dict(self, metric: PerformanceMetric) -> Dict[str, Any]:
        """将性能指标转换为字典"""
        return {
            'id': metric.id,
            'metric_type': metric.metric_type,
            'metric_name': metric.metric_name,
            'metric_value': metric.metric_value,
            'metadata': metric.metric_metadata,
            'recorded_at': metric.recorded_at.isoformat() if metric.recorded_at else None
        }


# 全局实例
_performance_service = None

def get_performance_service() -> PerformanceService:
    """获取性能监控服务实例"""
    global _performance_service
    if _performance_service is None:
        _performance_service = PerformanceService()
    return _performance_service


# 定时任务函数
def collect_system_metrics_task():
    """定时收集系统指标的任务"""
    try:
        performance_service = get_performance_service()
        performance_service.record_system_metrics()
    except Exception as e:
        logger.error(f"定时收集系统指标失败: {e}")


# 性能监控装饰器
def monitor_performance(metric_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录性能指标
                performance_service = get_performance_service()
                performance_service.record_performance_metric(
                    metric_type='function',
                    metric_name=metric_name or func.__name__,
                    metric_value=execution_time
                )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                
                # 记录失败的性能指标
                performance_service = get_performance_service()
                performance_service.record_performance_metric(
                    metric_type='function_error',
                    metric_name=metric_name or func.__name__,
                    metric_value=execution_time,
                    metadata={'error': str(e)}
                )
                
                raise
        return wrapper
    return decorator
