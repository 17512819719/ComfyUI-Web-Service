from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func, Text, Float, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False)
    description = Column(String(128), default='')
    users = relationship('User', back_populates='role')

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(64), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role_id = Column(Integer, ForeignKey('roles.id'))
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime)
    role = relationship('Role', back_populates='users')
    tasks = relationship('Task', back_populates='user')

class Node(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    ip_address = Column(String(45), nullable=False)
    port = Column(Integer, default=8188)
    status = Column(String(20), default='offline')  # online, offline, busy, maintenance
    gpu_info = Column(JSON)  # GPU型号、显存等
    cpu_info = Column(JSON)  # CPU信息
    memory_info = Column(JSON)  # 内存信息
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_heartbeat = Column(DateTime)
    tasks = relationship('Task', back_populates='node')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False)  # UUID
    task_type = Column(String(20), nullable=False)  # image, video
    status = Column(String(20), default='queued')  # queued, running, completed, failed
    priority = Column(Integer, default=0)
    prompt = Column(Text)
    negative_prompt = Column(Text)
    parameters = Column(JSON)  # 任务参数
    result_url = Column(String(255))
    error_message = Column(Text)
    progress = Column(Float, default=0.0)
    user_id = Column(Integer, ForeignKey('users.id'))
    node_id = Column(Integer, ForeignKey('nodes.id'))
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    user = relationship('User', back_populates='tasks')
    node = relationship('Node', back_populates='tasks')

class SystemLog(Base):
    __tablename__ = 'system_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON)
    created_at = Column(DateTime, server_default=func.now()) 