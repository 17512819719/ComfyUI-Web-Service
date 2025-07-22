"""
客户端数据库模型
"""
from sqlalchemy import Column, BigInteger, String, Text, Integer, Boolean, DECIMAL, DateTime, ForeignKey, JSON, Index, DECIMAL
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ClientUser(Base, TimestampMixin):
    """客户端用户表"""
    __tablename__ = 'client_users'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(String(36), unique=True, nullable=False, comment='客户端ID（UUID）')
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    session_token = Column(String(64), unique=True, comment='会话令牌')
    ip_address = Column(String(45), comment='IP地址')
    user_agent = Column(Text, comment='用户代理')
    nickname = Column(String(100), comment='昵称')
    quota_limit = Column(Integer, default=50, comment='每日配额限制')
    quota_used = Column(Integer, default=0, comment='今日已使用配额')
    quota_reset_date = Column(DateTime, comment='配额重置日期')
    is_active = Column(Boolean, default=True, comment='是否活跃')
    last_access_at = Column(DateTime, comment='最后访问时间')
    
    # 关系
    uploads = relationship("ClientUpload", back_populates="client_user")
    
    # 索引
    __table_args__ = (
        Index('idx_client_id', 'client_id'),
        Index('idx_username', 'username'),
        Index('idx_session_token', 'session_token'),
        Index('idx_ip_address', 'ip_address'),
    )


class ClientTask(Base, TimestampMixin):
    """客户端任务表"""
    __tablename__ = 'client_tasks'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False, comment='任务UUID')
    client_id = Column(String(36), ForeignKey('client_users.client_id'), nullable=False, comment='客户端ID')
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
    progress = Column(DECIMAL(5, 2), default=0.00, comment='进度百分比')
    message = Column(Text, comment='状态消息')
    error_message = Column(Text, comment='错误消息')
    estimated_time = Column(Integer, comment='预估处理时间(秒)')
    actual_time = Column(Integer, comment='实际处理时间(秒)')
    started_at = Column(DateTime, comment='开始处理时间')
    completed_at = Column(DateTime, comment='完成时间')
    
    # 关系
    client_user = relationship("ClientUser")
    parameters = relationship("ClientTaskParameter", back_populates="task", cascade="all, delete-orphan")
    results = relationship("ClientTaskResult", back_populates="task", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_client_id', 'client_id'),
        Index('idx_status', 'status'),
        Index('idx_task_type', 'task_type'),
        Index('idx_created_at', 'created_at'),
    )


class ClientTaskParameter(Base):
    """客户端任务参数表"""
    __tablename__ = 'client_task_parameters'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('client_tasks.id', ondelete='CASCADE'), nullable=False)
    parameter_name = Column(String(100), nullable=False, comment='参数名称')
    parameter_value = Column(Text, comment='参数值')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP')
    
    # 关系
    task = relationship("ClientTask", back_populates="parameters")
    
    # 索引
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
    )


class ClientTaskResult(Base):
    """客户端任务结果表"""
    __tablename__ = 'client_task_results'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey('client_tasks.id', ondelete='CASCADE'), nullable=False)
    result_type = Column(String(20), nullable=False, comment='结果类型')
    file_path = Column(String(500), comment='文件路径')
    file_name = Column(String(255), comment='文件名')
    file_size = Column(BigInteger, comment='文件大小(字节)')
    width = Column(Integer, comment='图片/视频宽度')
    height = Column(Integer, comment='图片/视频高度')
    duration = Column(DECIMAL(10, 2), comment='视频时长(秒)')
    thumbnail_path = Column(String(500), comment='缩略图路径')
    result_metadata = Column(JSON, comment='元数据')
    download_count = Column(Integer, default=0, comment='下载次数')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP')
    
    # 关系
    task = relationship("ClientTask", back_populates="results")
    
    # 索引
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_result_type', 'result_type'),
    )


class ClientUpload(Base):
    """客户端上传文件表"""
    __tablename__ = 'client_uploads'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_id = Column(String(36), unique=True, nullable=False, comment='文件UUID')
    client_id = Column(String(36), ForeignKey('client_users.client_id'), nullable=False, comment='客户端ID')
    original_name = Column(String(255), nullable=False, comment='原始文件名')
    file_path = Column(String(500), nullable=False, comment='文件路径')
    file_size = Column(BigInteger, nullable=False, comment='文件大小(字节)')
    mime_type = Column(String(100), nullable=False, comment='MIME类型')
    width = Column(Integer, comment='图片宽度')
    height = Column(Integer, comment='图片高度')
    is_processed = Column(Boolean, default=False, comment='是否已处理')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP')

    # 关系
    client_user = relationship("ClientUser", back_populates="uploads")

    # 索引
    __table_args__ = (
        Index('idx_file_id', 'file_id'),
        Index('idx_client_id', 'client_id'),
        Index('idx_created_at', 'created_at'),
        {'extend_existing': True}
    )


class ClientAccessLog(Base):
    """客户端访问日志表"""
    __tablename__ = 'client_access_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(String(36), comment='客户端ID')
    ip_address = Column(String(45), comment='IP地址')
    user_agent = Column(Text, comment='用户代理')
    request_method = Column(String(10), nullable=False, comment='请求方法')
    request_path = Column(String(500), nullable=False, comment='请求路径')
    request_data = Column(Text, comment='请求数据')
    response_status = Column(Integer, comment='响应状态码')
    response_time = Column(DECIMAL(10, 4), comment='响应时间(秒)')
    access_time = Column(DateTime, nullable=False, comment='访问时间')

    # 索引
    __table_args__ = (
        Index('idx_client_id', 'client_id'),
        Index('idx_request_method', 'request_method'),
        Index('idx_access_time', 'access_time'),
        Index('idx_response_status', 'response_status'),
        {'extend_existing': True}
    )
