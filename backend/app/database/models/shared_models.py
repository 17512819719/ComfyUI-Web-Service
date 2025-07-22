"""
共享数据库模型
"""
from sqlalchemy import Column, BigInteger, String, Text, Integer, Boolean, DECIMAL, DateTime, ForeignKey, JSON, Index, Date
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class GlobalTask(Base, TimestampMixin):
    """全局任务表"""
    __tablename__ = 'global_tasks'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False, comment='任务UUID')
    source_type = Column(String(20), nullable=False, comment='任务来源')
    source_user_id = Column(String(36), nullable=False, comment='来源用户ID')
    task_type = Column(String(20), nullable=False, comment='任务类型')
    workflow_name = Column(String(100), nullable=False, comment='工作流名称')
    prompt = Column(Text, comment='正向提示词')
    negative_prompt = Column(Text, comment='反向提示词')

    # 生成参数
    model_name = Column(String(200), comment='使用的模型名称')
    width = Column(Integer, comment='图片宽度')
    height = Column(Integer, comment='图片高度')
    steps = Column(Integer, comment='采样步数')
    cfg_scale = Column(DECIMAL(4, 2), comment='CFG引导强度')
    sampler = Column(String(50), comment='采样器')
    scheduler = Column(String(50), comment='调度器')
    seed = Column(BigInteger, comment='随机种子')
    batch_size = Column(Integer, default=1, comment='批量大小')

    status = Column(String(20), default='queued', comment='任务状态')
    priority = Column(Integer, default=1, comment='任务优先级')
    progress = Column(DECIMAL(5, 2), default=0.00, comment='进度百分比')
    message = Column(Text, comment='状态消息')
    error_message = Column(Text, comment='错误消息')
    celery_task_id = Column(String(36), comment='Celery任务ID')
    node_id = Column(String(100), comment='执行节点ID')
    estimated_time = Column(Integer, comment='预估处理时间(秒)')
    actual_time = Column(Integer, comment='实际处理时间(秒)')
    started_at = Column(DateTime, comment='开始处理时间')
    completed_at = Column(DateTime, comment='完成时间')
    
    # 关系
    parameters = relationship("GlobalTaskParameter", back_populates="task", cascade="all, delete-orphan")
    results = relationship("GlobalTaskResult", back_populates="task", cascade="all, delete-orphan")
    assignments = relationship("NodeTaskAssignment", back_populates="task", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_source_type', 'source_type'),
        Index('idx_source_user_id', 'source_user_id'),
        Index('idx_status', 'status'),
        Index('idx_task_type', 'task_type'),
        Index('idx_created_at', 'created_at'),
        Index('idx_node_id', 'node_id'),
        Index('idx_celery_task_id', 'celery_task_id'),
    )


class GlobalTaskParameter(Base):
    """全局任务参数表"""
    __tablename__ = 'global_task_parameters'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('global_tasks.id', ondelete='CASCADE'), nullable=False)
    parameter_name = Column(String(100), nullable=False, comment='参数名称')
    parameter_value = Column(Text, comment='参数值')
    parameter_type = Column(String(20), default='string', comment='参数类型')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP')
    
    # 关系
    task = relationship("GlobalTask", back_populates="parameters")
    
    # 索引
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_parameter_name', 'parameter_name'),
    )


class GlobalTaskResult(Base):
    """全局任务结果表"""
    __tablename__ = 'global_task_results'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('global_tasks.id', ondelete='CASCADE'), nullable=False)
    result_type = Column(String(20), nullable=False, comment='结果类型')
    file_path = Column(String(500), comment='文件路径')
    file_name = Column(String(255), comment='文件名')
    file_size = Column(BigInteger, comment='文件大小(字节)')
    mime_type = Column(String(100), comment='MIME类型')
    width = Column(Integer, comment='图片/视频宽度')
    height = Column(Integer, comment='图片/视频高度')
    duration = Column(DECIMAL(10, 2), comment='视频时长(秒)')
    thumbnail_path = Column(String(500), comment='缩略图路径')
    result_metadata = Column(JSON, comment='元数据')
    download_count = Column(Integer, default=0, comment='下载次数')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP')
    
    # 关系
    task = relationship("GlobalTask", back_populates="results")
    
    # 索引
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_result_type', 'result_type'),
    )


class NodeTaskAssignment(Base):
    """节点任务分配表"""
    __tablename__ = 'node_task_assignments'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_id = Column(String(100), nullable=False, comment='节点ID')
    task_id = Column(BigInteger, ForeignKey('global_tasks.id', ondelete='CASCADE'), nullable=False)
    assigned_at = Column(DateTime, server_default='CURRENT_TIMESTAMP', comment='分配时间')
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    status = Column(String(20), default='assigned', comment='分配状态')
    
    # 关系
    task = relationship("GlobalTask", back_populates="assignments")
    
    # 索引
    __table_args__ = (
        Index('idx_node_id', 'node_id'),
        Index('idx_task_id', 'task_id'),
        Index('idx_status', 'status'),
        Index('idx_assigned_at', 'assigned_at'),
    )


class GlobalFile(Base, TimestampMixin):
    """全局文件表"""
    __tablename__ = 'global_files'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_id = Column(String(36), unique=True, nullable=False, comment='文件UUID')
    source_type = Column(String(20), nullable=False, comment='文件来源')
    source_user_id = Column(String(36), comment='来源用户ID')
    original_name = Column(String(255), nullable=False, comment='原始文件名')
    file_name = Column(String(255), nullable=False, comment='存储文件名')
    file_path = Column(String(500), nullable=False, comment='文件路径')
    file_size = Column(BigInteger, nullable=False, comment='文件大小(字节)')
    mime_type = Column(String(100), nullable=False, comment='MIME类型')
    file_hash = Column(String(64), comment='文件哈希')
    file_type = Column(String(20), nullable=False, comment='文件类型')
    width = Column(Integer, comment='图片/视频宽度')
    height = Column(Integer, comment='图片/视频高度')
    duration = Column(DECIMAL(10, 2), comment='视频/音频时长(秒)')
    file_metadata = Column(JSON, comment='元数据')
    is_public = Column(Boolean, default=False, comment='是否公开')
    is_temporary = Column(Boolean, default=False, comment='是否临时文件')
    expires_at = Column(DateTime, comment='过期时间')
    download_count = Column(Integer, default=0, comment='下载次数')
    
    # 索引
    __table_args__ = (
        Index('idx_file_id', 'file_id'),
        Index('idx_source_type', 'source_type'),
        Index('idx_source_user_id', 'source_user_id'),
        Index('idx_file_type', 'file_type'),
        Index('idx_file_hash', 'file_hash'),
        Index('idx_is_temporary', 'is_temporary'),
        Index('idx_expires_at', 'expires_at'),
    )


class TaskQueueStatus(Base, TimestampMixin):
    """任务队列状态表（Redis备份）"""
    __tablename__ = 'task_queue_status'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False, comment='任务ID')
    queue_name = Column(String(100), nullable=False, comment='队列名称')
    status = Column(String(20), nullable=False, comment='队列状态')
    result = Column(Text, comment='执行结果')
    traceback = Column(Text, comment='错误堆栈')
    worker = Column(String(100), comment='工作进程')
    retries = Column(Integer, default=0, comment='重试次数')
    eta = Column(DateTime, comment='预计执行时间')
    
    # 索引
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_queue_name', 'queue_name'),
        Index('idx_status', 'status'),
        Index('idx_worker', 'worker'),
    )


class SystemStatistic(Base, TimestampMixin):
    """系统统计表"""
    __tablename__ = 'system_statistics'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stat_date = Column(Date, nullable=False, comment='统计日期')
    total_tasks = Column(Integer, default=0, comment='总任务数')
    completed_tasks = Column(Integer, default=0, comment='完成任务数')
    failed_tasks = Column(Integer, default=0, comment='失败任务数')
    client_tasks = Column(Integer, default=0, comment='客户端任务数')
    admin_tasks = Column(Integer, default=0, comment='管理端任务数')
    text_to_image_tasks = Column(Integer, default=0, comment='文生图任务数')
    image_to_video_tasks = Column(Integer, default=0, comment='图生视频任务数')
    total_processing_time = Column(BigInteger, default=0, comment='总处理时间(秒)')
    average_processing_time = Column(DECIMAL(10, 2), default=0.00, comment='平均处理时间(秒)')
    active_nodes = Column(Integer, default=0, comment='活跃节点数')
    total_file_size = Column(BigInteger, default=0, comment='总文件大小(字节)')
    
    # 索引
    __table_args__ = (
        Index('uk_stat_date', 'stat_date', unique=True),
        Index('idx_stat_date', 'stat_date'),
    )


class SystemConfig(Base, TimestampMixin):
    """系统配置表"""
    __tablename__ = 'system_configs'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, comment='配置键')
    config_value = Column(Text, nullable=False, comment='配置值')
    value_type = Column(String(20), default='string', comment='值类型')
    category = Column(String(50), default='general', comment='配置分类')
    description = Column(Text, comment='配置描述')
    source = Column(String(50), default='manual', comment='配置来源')
    is_active = Column(Boolean, default=True, comment='是否激活')

    # 索引 - 合并到 __table_args__
    __table_args__ = (
        Index('idx_config_key', 'config_key'),
        Index('idx_category', 'category'),
        Index('idx_is_active', 'is_active'),
        {'extend_existing': True}
    )


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = 'system_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    log_level = Column(String(10), nullable=False, comment='日志级别')
    event_type = Column(String(50), nullable=False, comment='事件类型')
    message = Column(Text, comment='日志消息')
    event_data = Column(JSON, comment='事件数据')
    source = Column(String(50), default='system', comment='日志来源')
    created_at = Column(DateTime, nullable=False, comment='创建时间')

    # 索引
    __table_args__ = (
        Index('idx_log_level', 'log_level'),
        Index('idx_event_type', 'event_type'),
        Index('idx_created_at', 'created_at'),
        Index('idx_source', 'source'),
        {'extend_existing': True}
    )


class PerformanceMetric(Base):
    """性能指标表"""
    __tablename__ = 'performance_metrics'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    metric_type = Column(String(50), nullable=False, comment='指标类型')
    metric_name = Column(String(100), nullable=False, comment='指标名称')
    metric_value = Column(DECIMAL(15, 4), nullable=False, comment='指标值')
    metric_metadata = Column(JSON, comment='元数据')
    recorded_at = Column(DateTime, nullable=False, comment='记录时间')

    # 索引
    __table_args__ = (
        Index('idx_metric_type', 'metric_type'),
        Index('idx_metric_name', 'metric_name'),
        Index('idx_recorded_at', 'recorded_at'),
        Index('idx_type_name', 'metric_type', 'metric_name'),
        {'extend_existing': True}
    )
