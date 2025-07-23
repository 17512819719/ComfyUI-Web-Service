from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

# 角色相关
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = ''

class RoleCreate(RoleBase):
    pass

class RoleOut(RoleBase):
    id: int
    model_config={
        "from_attributes" : True
    }

# 用户相关
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    role_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    role: Optional[RoleOut]
    created_at: datetime
    last_login: Optional[datetime]
    model_config={
        "from_attributes" : True
    }

# 节点相关
class NodeBase(BaseModel):
    name: str
    ip_address: str
    port: Optional[int] = 8188
    status: Optional[str] = 'offline'
    gpu_info: Optional[Dict[str, Any]] = None
    cpu_info: Optional[Dict[str, Any]] = None
    memory_info: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True

class NodeCreate(NodeBase):
    pass

class NodeOut(NodeBase):
    id: int
    created_at: datetime
    last_heartbeat: Optional[datetime]
    model_config={
        "from_attributes" : True
    }

# 任务相关
class TaskBase(BaseModel):
    task_type: str
    priority: Optional[int] = 0
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

class TaskCreate(TaskBase):
    pass

class TaskOut(TaskBase):
    id: int
    task_id: str
    status: str
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    progress: float
    user_id: Optional[int] = None
    node_id: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    user: Optional[UserOut] = None
    node: Optional[NodeOut] = None
    model_config={
        "from_attributes" : True
    }

# 系统监控相关
class SystemStatus(BaseModel):
    total_nodes: int
    online_nodes: int
    total_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    system_load: Dict[str, float]
    storage_usage: Dict[str, Any]

class SystemLogBase(BaseModel):
    level: str
    module: str
    message: str
    details: Optional[Dict[str, Any]] = None

class SystemLogOut(SystemLogBase):
    id: int
    created_at: datetime
    model_config={
        "from_attributes" : True
    }