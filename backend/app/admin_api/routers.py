from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from ..admin_api import models, schemas, auth, utils
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import asyncio

router = APIRouter(prefix="/admin", tags=["Admin"])

# ==================== 用户管理 ====================

# 用户注册（仅管理员可用）
@router.post("/users", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(utils.get_db), token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        password_hash=hashed_password,
        email=user.email,
        is_active=True,
        is_superuser=user.is_superuser,
        role_id=user.role_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 用户登录
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(utils.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 更新最后登录时间
    setattr(user, 'last_login', datetime.utcnow())
    db.commit()
    
    access_token = auth.create_access_token({"sub": user.username, "is_superuser": user.is_superuser})
    return {"access_token": access_token, "token_type": "bearer"}

# 获取用户列表（仅管理员）
@router.get("/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(utils.get_db), token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    return db.query(models.User).all()

# ==================== 节点管理 ====================

@router.post("/nodes", response_model=schemas.NodeOut)
def create_node(node: schemas.NodeCreate, db: Session = Depends(utils.get_db), token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    
    new_node = models.Node(**node.dict())
    db.add(new_node)
    db.commit()
    db.refresh(new_node)
    return new_node

@router.get("/nodes", response_model=List[schemas.NodeOut])
def list_nodes(db: Session = Depends(utils.get_db), token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    return db.query(models.Node).all()

@router.put("/nodes/{node_id}", response_model=schemas.NodeOut)
def update_node(node_id: int, node: schemas.NodeCreate, db: Session = Depends(utils.get_db), token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    
    db_node = db.query(models.Node).filter(models.Node.id == node_id).first()
    if not db_node:
        raise HTTPException(status_code=404, detail="节点不存在")
    
    for key, value in node.dict().items():
        setattr(db_node, key, value)
    
    db.commit()
    db.refresh(db_node)
    return db_node

# ==================== 分布式节点管理 ====================

@router.get("/distributed/nodes")
def get_distributed_nodes(token: str = Depends(auth.oauth2_scheme)):
    """获取分布式节点状态"""
    payload = auth.decode_access_token(token)

    try:
        from ..core.config_manager import get_config_manager
        config_manager = get_config_manager()

        if not config_manager.is_distributed_mode():
            return {
                "mode": "single",
                "message": "当前为单机模式",
                "nodes": []
            }

        from ..core.node_manager import get_node_manager
        node_manager = get_node_manager()
        nodes_dict = node_manager.get_all_nodes()

        # 转换为API响应格式
        nodes_list = []
        for node_id, node in nodes_dict.items():
            # 获取节点实时状态
            try:
                import requests
                response = requests.get(f"{node.url}/system_stats", timeout=3)
                is_online = response.status_code == 200
                system_stats = response.json() if is_online else {}
            except:
                is_online = False
                system_stats = {}

            nodes_list.append({
                "node_id": node_id,
                "url": node.url,
                "host": node.host,
                "port": node.port,
                "status": "online" if is_online else "offline",
                "node_type": getattr(node, 'node_type', 'worker'),
                "max_concurrent": getattr(node, 'max_concurrent', 4),
                "current_tasks": len(getattr(node, 'current_tasks', [])),
                "capabilities": getattr(node, 'capabilities', []),
                "last_heartbeat": node.last_heartbeat.isoformat() if hasattr(node, 'last_heartbeat') and node.last_heartbeat else None,
                "system_stats": system_stats
            })

        return {
            "mode": "distributed",
            "total_nodes": len(nodes_list),
            "online_nodes": sum(1 for n in nodes_list if n["status"] == "online"),
            "nodes": nodes_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分布式节点状态失败: {str(e)}")

@router.post("/distributed/nodes/{node_id}/health-check")
def check_node_health(node_id: str, token: str = Depends(auth.oauth2_scheme)):
    """手动检查节点健康状态"""
    payload = auth.decode_access_token(token)

    try:
        from ..core.node_manager import get_node_manager
        node_manager = get_node_manager()

        # 执行健康检查
        async def _check_health():
            return await node_manager.check_node_health(node_id)

        is_healthy = asyncio.run(_check_health())

        return {
            "node_id": node_id,
            "is_healthy": is_healthy,
            "checked_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"节点健康检查失败: {str(e)}")

@router.get("/distributed/load-balancer/stats")
def get_load_balancer_stats(token: str = Depends(auth.oauth2_scheme)):
    """获取负载均衡器统计信息"""
    payload = auth.decode_access_token(token)

    try:
        from ..core.config_manager import get_config_manager
        config_manager = get_config_manager()

        if not config_manager.is_distributed_mode():
            return {"mode": "single", "message": "当前为单机模式"}

        from ..core.load_balancer import get_load_balancer
        load_balancer = get_load_balancer()

        # 获取负载均衡统计
        stats = {
            "strategy": getattr(load_balancer, 'strategy', 'unknown'),
            "total_requests": getattr(load_balancer, 'total_requests', 0),
            "node_selections": getattr(load_balancer, 'node_selections', {}),
            "last_selection_time": getattr(load_balancer, 'last_selection_time', None)
        }

        if stats["last_selection_time"]:
            stats["last_selection_time"] = stats["last_selection_time"].isoformat()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取负载均衡统计失败: {str(e)}")

# ==================== 任务管理 ====================

@router.get("/tasks", response_model=List[schemas.TaskOut])
def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    db: Session = Depends(utils.get_db),
    token: str = Depends(auth.oauth2_scheme)
):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    
    query = db.query(models.Task)
    if status:
        query = query.filter(models.Task.status == status)
    if task_type:
        query = query.filter(models.Task.task_type == task_type)
    
    return query.order_by(desc(models.Task.created_at)).offset(skip).limit(limit).all()

@router.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: str, db: Session = Depends(utils.get_db), token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(utils.get_db), token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    db.delete(task)
    db.commit()
    return {"message": "任务删除成功"}

# ==================== 系统监控 ====================

@router.get("/dashboard", response_model=schemas.SystemStatus)
def get_dashboard(db: Session = Depends(utils.get_db), token: str = Depends(auth.oauth2_scheme)):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    
    # 统计节点 - 集成分布式节点管理
    try:
        from ..core.config_manager import get_config_manager
        config_manager = get_config_manager()

        if config_manager.is_distributed_mode():
            # 分布式模式：从节点管理器获取实时状态
            from ..core.node_manager import get_node_manager
            node_manager = get_node_manager()
            nodes_dict = node_manager.get_all_nodes()

            total_nodes = len(nodes_dict)
            online_nodes = 0

            # 检查每个节点的在线状态
            for node_id, node in nodes_dict.items():
                try:
                    import requests
                    response = requests.get(f"{node.url}/system_stats", timeout=2)
                    if response.status_code == 200:
                        online_nodes += 1
                except:
                    pass
        else:
            # 单机模式：从数据库获取
            total_nodes = db.query(models.Node).count()
            online_nodes = db.query(models.Node).filter(models.Node.status == 'online').count()

    except Exception as e:
        # 降级到数据库统计
        total_nodes = db.query(models.Node).count()
        online_nodes = db.query(models.Node).filter(models.Node.status == 'online').count()
    
    # 统计任务
    total_tasks = db.query(models.Task).count()
    running_tasks = db.query(models.Task).filter(models.Task.status == 'running').count()
    completed_tasks = db.query(models.Task).filter(models.Task.status == 'completed').count()
    failed_tasks = db.query(models.Task).filter(models.Task.status == 'failed').count()
    
    # 系统负载（模拟数据）
    system_load = {
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "gpu_usage": 82.1
    }
    
    # 存储使用情况（模拟数据）
    storage_usage = {
        "total": "1TB",
        "used": "650GB",
        "available": "350GB",
        "usage_percent": 65.0
    }
    
    return schemas.SystemStatus(
        total_nodes=total_nodes,
        online_nodes=online_nodes,
        total_tasks=total_tasks,
        running_tasks=running_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        system_load=system_load,
        storage_usage=storage_usage
    )

@router.get("/logs", response_model=List[schemas.SystemLogOut])
def get_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    db: Session = Depends(utils.get_db),
    token: str = Depends(auth.oauth2_scheme)
):
    payload = auth.decode_access_token(token)
    db_user = db.query(models.User).filter(models.User.username == payload['sub']).first()
    if not db_user or not bool(db_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权限")
    
    query = db.query(models.SystemLog)
    if level:
        query = query.filter(models.SystemLog.level == level)
    if module:
        query = query.filter(models.SystemLog.module == module)
    
    return query.order_by(desc(models.SystemLog.created_at)).offset(skip).limit(limit).all() 