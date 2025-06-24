from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import yaml
import os
from datetime import datetime, timedelta
from jose import jwt

router = APIRouter(prefix="/admin", tags=["Admin"])
security = HTTPBearer()

# 配置
ADMIN_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'admin_config.yaml')
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), '..', 'workflows')
MODULE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'module_config.yaml')
SECRET_KEY = "admin-secret-key"  # 可放到环境变量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 工具函数

def load_yaml(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=401, detail="无效管理员token")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="无效管理员token")

# 1. 管理员登录
@router.post("/login")
def admin_login(password: str = Body(..., embed=True)):
    config = load_yaml(ADMIN_CONFIG_PATH)
    admin_password = config.get("admin_password", "admin")
    if password == admin_password:
        token = create_access_token({"role": "admin"})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="密码错误")

# 2. 获取所有工作流
@router.get("/workflows")
def get_workflows(token=Depends(verify_admin_token)):
    try:
        files = [f for f in os.listdir(WORKFLOWS_DIR) if f.endswith('.json')]
        return {"workflows": [os.path.splitext(f)[0] for f in files]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. 获取指定工作流参数
@router.get("/workflow_config")
def get_workflow_config(name: str = Query(...), token=Depends(verify_admin_token)):
    path = os.path.join(WORKFLOWS_DIR, name + '.json')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="工作流不存在")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return {"config": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. 获取模块配置
@router.get("/module_config")
def get_module_config(module: str = Query(...), token=Depends(verify_admin_token)):
    config = load_yaml(MODULE_CONFIG_PATH)
    return config.get(module, {})

# 5. 设置模块配置
@router.post("/module_config")
def set_module_config(module: str = Body(...), config: Dict[str, Any] = Body(...), token=Depends(verify_admin_token)):
    all_config = load_yaml(MODULE_CONFIG_PATH)
    all_config[module] = config
    save_yaml(MODULE_CONFIG_PATH, all_config)
    return {"success": True} 