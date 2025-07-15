"""
管理端数据库模型
"""
from sqlalchemy import Column, BigInteger, String, Text, Integer, Boolean, DECIMAL, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class AdminUser(Base, TimestampMixin):
    """管理员用户表"""
    __tablename__ = 'admin_users'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    email = Column(String(100), unique=True, nullable=False, comment='邮箱')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    display_name = Column(String(100), comment='显示名称')
    role = Column(String(20), default='viewer', comment='管理员角色')
    status = Column(String(20), default='active', comment='用户状态')
    permissions = Column(JSON, comment='权限列表')
    last_login_ip = Column(String(45), comment='最后登录IP')
    login_count = Column(Integer, default=0, comment='登录次数')
    last_login_at = Column(DateTime, comment='最后登录时间')
    
    # 关系
    created_workflows = relationship("WorkflowTemplate", back_populates="creator")
    
    # 索引
    __table_args__ = (
        Index('idx_username', 'username'),
        Index('idx_email', 'email'),
        Index('idx_role', 'role'),
        Index('idx_status', 'status'),
    )


class WorkflowTemplate(Base, TimestampMixin):
    """工作流模板表"""
    __tablename__ = 'workflow_templates'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment='工作流名称')
    display_name = Column(String(200), comment='显示名称')
    task_type = Column(String(20), nullable=False, comment='任务类型')
    version = Column(String(20), default='1.0', comment='版本')
    description = Column(Text, comment='描述')
    workflow_file = Column(String(500), nullable=False, comment='工作流文件路径')
    config_data = Column(JSON, comment='配置数据')
    is_enabled = Column(Boolean, default=True, comment='是否启用')
    is_default = Column(Boolean, default=False, comment='是否默认工作流')
    max_concurrent_tasks = Column(Integer, default=4, comment='最大并发任务数')
    estimated_time = Column(Integer, default=60, comment='预估处理时间(秒)')
    usage_count = Column(Integer, default=0, comment='使用次数')
    success_rate = Column(DECIMAL(5, 2), default=0.00, comment='成功率')
    created_by = Column(BigInteger, ForeignKey('admin_users.id', ondelete='SET NULL'), comment='创建者ID')
    
    # 关系
    creator = relationship("AdminUser", back_populates="created_workflows")
    parameters = relationship("WorkflowParameter", back_populates="workflow", cascade="all, delete-orphan")
    workflow_models = relationship("WorkflowModel", back_populates="workflow", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_task_type', 'task_type'),
        Index('idx_is_enabled', 'is_enabled'),
    )


class WorkflowParameter(Base, TimestampMixin):
    """工作流参数配置表"""
    __tablename__ = 'workflow_parameters'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id = Column(BigInteger, ForeignKey('workflow_templates.id', ondelete='CASCADE'), nullable=False)
    parameter_name = Column(String(100), nullable=False, comment='参数名称')
    parameter_type = Column(String(20), nullable=False, comment='参数类型')
    default_value = Column(Text, comment='默认值')
    min_value = Column(DECIMAL(20, 6), comment='最小值')
    max_value = Column(DECIMAL(20, 6), comment='最大值')
    options = Column(JSON, comment='选项列表(用于select类型)')
    is_required = Column(Boolean, default=False, comment='是否必需')
    display_name = Column(String(200), comment='显示名称')
    description = Column(Text, comment='参数描述')
    node_id = Column(String(50), comment='节点ID')
    field_path = Column(String(200), comment='字段路径')
    sort_order = Column(Integer, default=0, comment='排序')
    
    # 关系
    workflow = relationship("WorkflowTemplate", back_populates="parameters")
    
    # 索引
    __table_args__ = (
        Index('idx_workflow_id', 'workflow_id'),
        Index('idx_parameter_name', 'parameter_name'),
    )


class Model(Base, TimestampMixin):
    """模型表"""
    __tablename__ = 'models'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment='模型名称')
    display_name = Column(String(300), comment='显示名称')
    model_type = Column(String(20), nullable=False, comment='模型类型')
    file_path = Column(String(500), nullable=False, comment='文件路径')
    file_size = Column(BigInteger, comment='文件大小(字节)')
    file_hash = Column(String(64), comment='文件哈希')
    version = Column(String(50), comment='版本')
    description = Column(Text, comment='描述')
    tags = Column(JSON, comment='标签')
    base_model = Column(String(100), comment='基础模型')
    resolution = Column(String(20), comment='支持分辨率')
    is_enabled = Column(Boolean, default=True, comment='是否启用')
    download_count = Column(Integer, default=0, comment='下载次数')
    usage_count = Column(Integer, default=0, comment='使用次数')
    
    # 关系
    workflow_models = relationship("WorkflowModel", back_populates="model", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_model_type', 'model_type'),
        Index('idx_is_enabled', 'is_enabled'),
        Index('idx_file_hash', 'file_hash'),
    )


class WorkflowModel(Base):
    """工作流模型关联表"""
    __tablename__ = 'workflow_models'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    workflow_id = Column(BigInteger, ForeignKey('workflow_templates.id', ondelete='CASCADE'), nullable=False)
    model_id = Column(BigInteger, ForeignKey('models.id', ondelete='CASCADE'), nullable=False)
    is_default = Column(Boolean, default=False, comment='是否默认模型')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP')
    
    # 关系
    workflow = relationship("WorkflowTemplate", back_populates="workflow_models")
    model = relationship("Model", back_populates="workflow_models")
    
    # 索引
    __table_args__ = (
        Index('idx_workflow_id', 'workflow_id'),
        Index('idx_model_id', 'model_id'),
        Index('uk_workflow_model', 'workflow_id', 'model_id', unique=True),
    )


class Node(Base, TimestampMixin):
    """节点表"""
    __tablename__ = 'nodes'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    node_id = Column(String(100), unique=True, nullable=False, comment='节点ID')
    name = Column(String(200), nullable=False, comment='节点名称')
    host = Column(String(255), nullable=False, comment='主机地址')
    port = Column(Integer, nullable=False, comment='端口')
    api_url = Column(String(500), nullable=False, comment='API地址')
    node_type = Column(String(20), default='worker', comment='节点类型')
    status = Column(String(20), default='offline', comment='节点状态')
    current_load = Column(Integer, default=0, comment='当前负载')
    max_load = Column(Integer, default=4, comment='最大负载')
    cpu_usage = Column(DECIMAL(5, 2), default=0.00, comment='CPU使用率')
    memory_usage = Column(DECIMAL(5, 2), default=0.00, comment='内存使用率')
    gpu_usage = Column(DECIMAL(5, 2), default=0.00, comment='GPU使用率')
    gpu_memory_usage = Column(DECIMAL(5, 2), default=0.00, comment='GPU内存使用率')
    supported_task_types = Column(JSON, comment='支持的任务类型')
    capabilities = Column(JSON, comment='节点能力')
    version = Column(String(50), comment='版本')
    last_heartbeat = Column(DateTime, comment='最后心跳时间')
    total_tasks = Column(Integer, default=0, comment='总任务数')
    completed_tasks = Column(Integer, default=0, comment='完成任务数')
    failed_tasks = Column(Integer, default=0, comment='失败任务数')
    average_processing_time = Column(DECIMAL(10, 2), default=0.00, comment='平均处理时间(秒)')
    
    # 索引
    __table_args__ = (
        Index('idx_node_id', 'node_id'),
        Index('idx_status', 'status'),
        Index('idx_node_type', 'node_type'),
        Index('idx_last_heartbeat', 'last_heartbeat'),
    )


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = 'system_logs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False, comment='日志级别')
    module = Column(String(100), comment='模块名称')
    message = Column(Text, nullable=False, comment='日志消息')
    details = Column(JSON, comment='详细信息')
    admin_user_id = Column(BigInteger, ForeignKey('admin_users.id', ondelete='SET NULL'), comment='管理员用户ID')
    task_id = Column(String(36), comment='任务ID')
    node_id = Column(BigInteger, ForeignKey('nodes.id', ondelete='SET NULL'), comment='节点ID')
    ip_address = Column(String(45), comment='IP地址')
    user_agent = Column(Text, comment='用户代理')
    created_at = Column(DateTime, server_default='CURRENT_TIMESTAMP')

    # 索引
    __table_args__ = (
        Index('idx_level', 'level'),
        Index('idx_module', 'module'),
        Index('idx_created_at', 'created_at'),
        Index('idx_admin_user_id', 'admin_user_id'),
    )


class PerformanceMetric(Base):
    """性能监控表"""
    __tablename__ = 'performance_metrics'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    metric_type = Column(String(20), nullable=False, comment='指标类型')
    metric_name = Column(String(100), nullable=False, comment='指标名称')
    metric_value = Column(DECIMAL(20, 6), nullable=False, comment='指标值')
    unit = Column(String(20), comment='单位')
    tags = Column(JSON, comment='标签')
    node_id = Column(BigInteger, ForeignKey('nodes.id', ondelete='CASCADE'), comment='节点ID')
    recorded_at = Column(DateTime, server_default='CURRENT_TIMESTAMP', comment='记录时间')

    # 索引
    __table_args__ = (
        Index('idx_metric_type', 'metric_type'),
        Index('idx_metric_name', 'metric_name'),
        Index('idx_recorded_at', 'recorded_at'),
        Index('idx_node_id', 'node_id'),
    )


class SystemConfig(Base, TimestampMixin):
    """系统配置表"""
    __tablename__ = 'system_configs'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, comment='配置键')
    config_value = Column(Text, comment='配置值')
    config_type = Column(String(20), default='string', comment='配置类型')
    description = Column(Text, comment='描述')
    is_public = Column(Boolean, default=False, comment='是否公开')

    # 索引
    __table_args__ = (
        Index('idx_config_key', 'config_key'),
        Index('idx_is_public', 'is_public'),
    )
