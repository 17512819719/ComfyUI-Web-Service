import sys
import os
# 移除sys.path.insert，因为现在所有文件都在根目录

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Form, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uuid
from typing import Optional, List, Dict
import json
from datetime import datetime
import random

from auth import verify_token, create_access_token
from tasks import generate_image_task, generate_video_task, get_task_result
from models import TaskStatus, GenerationRequest
from workflow_manager import workflow_manager
from workflow_selector import workflow_selector

app = FastAPI(title="ComfyUI分布式服务", version="1.0.0")
security = HTTPBearer()

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 文件存储目录
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 简单的任务状态存储（生产环境应使用数据库）
task_status_store: Dict[str, Dict] = {}

def cleanup_completed_tasks():
    """清理已完成的任务状态"""
    current_time = datetime.now()
    tasks_to_remove = []
    
    for task_id, task_info in task_status_store.items():
        # 清理已完成或失败的任务（保留1小时）
        if task_info["status"] in ["completed", "failed"]:
            updated_at = task_info["updated_at"]
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
            if (current_time - updated_at).total_seconds() > 3600:  # 1小时
                tasks_to_remove.append(task_id)
    
    for task_id in tasks_to_remove:
        del task_status_store[task_id]
        print(f"[DEBUG] 清理已完成任务: {task_id}")
    
    return len(tasks_to_remove)

@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """用户登录"""
    # 这里应该验证用户凭据
    if username == "z" and password == "z":  # 示例，实际应查数据库
        token = create_access_token({"sub": username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="认证失败")

@app.post("/api/generate/image")
async def generate_image(
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: int = Form(512),
    height: int = Form(512),
    steps: int = Form(20),
    cfg_scale: float = Form(7.0),
    seed: int = Form(-1),
    batch_size: int = Form(1),
    workflow_template: str = Form("SD35标准文生图"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """文生图接口"""
    user = verify_token(credentials.credentials)
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)
    task_id = str(uuid.uuid4())
    
    # 创建生成请求
    request_data = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "seed": seed,
        "batch_size": batch_size,
        "workflow_template": workflow_template,
        "task_id": task_id,
        "user_id": user["sub"]
    }
    
    # 初始化任务状态
    task_status_store[task_id] = {
        "status": TaskStatus.QUEUED,
        "progress": 0,
        "message": "任务已提交到队列",
        "result_url": None,
        "error_message": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "request_data": request_data
    }
    
    try:
        # 提交到任务队列
        task = generate_image_task.delay(request_data)
        
        # 更新任务状态，记录Celery任务ID
        task_status_store[task_id]["celery_task_id"] = task.id
        
        return {
            "task_id": task_id,
            "status": TaskStatus.QUEUED,
            "message": "任务已提交到队列"
        }
    except Exception as e:
        # 如果提交失败，更新状态
        task_status_store[task_id]["status"] = TaskStatus.FAILED
        task_status_store[task_id]["error_message"] = str(e)
        task_status_store[task_id]["updated_at"] = datetime.now()
        
        raise HTTPException(status_code=500, detail=f"任务提交失败: {str(e)}")

@app.post("/api/generate/video")
async def generate_video(
    image: UploadFile = File(...),
    duration: float = Form(5.0),
    fps: int = Form(8),
    motion_strength: float = Form(0.8),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """图生视频接口"""
    user = verify_token(credentials.credentials)
    
    # 保存上传的图片
    task_id = str(uuid.uuid4())
    # 确保文件名不为空
    if not image.filename or not image.filename.strip():
        raise HTTPException(status_code=400, detail="上传的文件名不能为空")
    
    image_path = os.path.join(UPLOAD_DIR, f"{task_id}_{image.filename}")
    
    with open(image_path, "wb") as buffer:
        content = await image.read()
        buffer.write(content)
    
    request_data = {
        "image_path": image_path,
        "duration": duration,
        "fps": fps,
        "motion_strength": motion_strength,
        "task_id": task_id,
        "user_id": user["sub"]
    }
    
    # 初始化任务状态
    task_status_store[task_id] = {
        "status": TaskStatus.QUEUED,
        "progress": 0,
        "message": "视频生成任务已提交",
        "result_url": None,
        "error_message": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "request_data": request_data
    }
    
    try:
        # 提交到任务队列
        task = generate_video_task.delay(request_data)
        
        # 更新任务状态，记录Celery任务ID
        task_status_store[task_id]["celery_task_id"] = task.id
        
        return {
            "task_id": task_id,
            "status": TaskStatus.QUEUED,
            "message": "视频生成任务已提交"
        }
    except Exception as e:
        # 如果提交失败，更新状态
        task_status_store[task_id]["status"] = TaskStatus.FAILED
        task_status_store[task_id]["error_message"] = str(e)
        task_status_store[task_id]["updated_at"] = datetime.now()
        
        raise HTTPException(status_code=500, detail=f"任务提交失败: {str(e)}")

@app.get("/api/task/status/{task_id}")
async def get_task_status(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """查询任务状态"""
    verify_token(credentials.credentials)
    
    # 定期清理已完成的任务
    cleanup_completed_tasks()
    
    # 从存储中获取任务状态
    if task_id not in task_status_store:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = task_status_store[task_id]
    
    # 如果有Celery任务ID，尝试获取最新状态
    if "celery_task_id" in task_info:
        try:
            celery_result = get_task_result(task_info["celery_task_id"])
            if celery_result:
                # 更新任务状态
                task_info.update(celery_result)
                task_info["updated_at"] = datetime.now()
                print(f"[DEBUG] 更新任务 {task_id} 状态: {celery_result}")
        except Exception as e:
            # 如果获取Celery状态失败，记录错误但不影响返回
            print(f"获取Celery任务状态失败: {e}")
    
    return {
        "task_id": task_id,
        "status": task_info["status"],
        "progress": task_info.get("progress", 0),
        "message": task_info.get("message", ""),
        "result_url": task_info.get("result_url"),
        "error_message": task_info.get("error_message"),
        "created_at": task_info["created_at"],
        "updated_at": task_info["updated_at"]
    }

@app.get("/api/download/{task_id}")
async def download_result(
    task_id: str,
    index: Optional[int] = Query(None, description="批量图片索引，从0开始"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """下载生成结果，支持批量图片下载"""
    verify_token(credentials.credentials)
    
    # 检查任务状态
    if task_id not in task_status_store:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = task_status_store[task_id]
    if task_info["status"] != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    # 查找结果文件
    result_url = task_info.get("result_url")
    if not result_url:
        raise HTTPException(status_code=404, detail="结果文件未找到")
    
    # 支持批量图片
    if isinstance(result_url, list):
        if index is None:
            raise HTTPException(status_code=400, detail="请指定要下载的图片索引index")
        if index < 0 or index >= len(result_url):
            raise HTTPException(status_code=404, detail="图片索引超出范围")
        file_path = result_url[index]
    else:
        file_path = result_url
    
    if os.path.exists(file_path):
        filename = os.path.basename(file_path)
        return FileResponse(file_path, filename=filename)
    else:
        raise HTTPException(status_code=404, detail="文件未找到")

@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "active_tasks": len([t for t in task_status_store.values() if t["status"] in [TaskStatus.QUEUED, TaskStatus.PROCESSING]])
    }

@app.get("/api/debug/tasks")
async def debug_tasks():
    """调试接口：查看所有任务状态"""
    return {
        "total_tasks": len(task_status_store),
        "tasks": task_status_store
    }

@app.get("/api/debug/nodes")
async def debug_nodes():
    """调试接口：查看节点状态"""
    from tasks import COMFYUI_NODES
    return {
        "nodes": COMFYUI_NODES
    }

@app.post("/api/debug/reset-nodes")
async def reset_nodes():
    """调试接口：重置所有节点状态"""
    from tasks import reset_node_status, check_and_reset_stuck_nodes
    
    # 检查并重置卡住的节点
    reset_count = check_and_reset_stuck_nodes()
    
    # 重置所有节点状态
    reset_node_status()
    
    return {
        "message": "节点状态已重置",
        "reset_stuck_nodes": reset_count,
        "timestamp": datetime.now()
    }

@app.get("/api/workflows")
async def list_workflows(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """列出所有可用的工作流模板"""
    user = verify_token(credentials.credentials)
    workflows = workflow_selector.get_available_workflows()
    return {
        "workflows": workflows,
        "count": len(workflows),
        "default_workflow": workflow_selector.get_default_workflow()
    }

@app.get("/api/workflows/{workflow_name}")
async def get_workflow_info(
    workflow_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """获取指定工作流的详细信息"""
    user = verify_token(credentials.credentials)
    workflow_info = workflow_selector.get_workflow_info(workflow_name)
    if "error" not in workflow_info:
        return workflow_info
    else:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_name} 不存在")

@app.post("/api/workflows/{workflow_name}/set-default")
async def set_default_workflow(
    workflow_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """设置默认工作流"""
    user = verify_token(credentials.credentials)
    success = workflow_selector.set_default_workflow(workflow_name)
    if success:
        return {
            "message": f"已设置 {workflow_name} 为默认工作流",
            "default_workflow": workflow_name
        }
    else:
        raise HTTPException(status_code=400, detail=f"工作流 {workflow_name} 不存在或无效")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)