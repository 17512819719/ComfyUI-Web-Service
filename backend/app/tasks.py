from celery import Celery
import requests
import json
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
import yaml
from .workflow_selector import workflow_selector
from .config_manager import config_manager

# Celery配置
celery_app = Celery(
    "comfyui_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# ComfyUI节点配置
COMFYUI_NODES = [
    {"host": "localhost", "port": 8188, "available": True},
    # 添加更多节点
    # {"host": "192.168.1.100", "port": 8188, "available": True},
]

# ComfyUI输出目录配置
COMFYUI_OUTPUT_DIR = r"E:\ComfyUI\ComfyUI\output"  # ComfyUI的真实输出目录

# 使用配置管理器
CONFIG = config_manager

def get_available_node():
    """获取可用的ComfyUI节点"""
    print(f"[DEBUG] 当前节点状态: {[{'host': n['host'], 'port': n['port'], 'available': n['available']} for n in COMFYUI_NODES]}")
    
    for node in COMFYUI_NODES:
        if node["available"]:
            try:
                print(f"[DEBUG] 尝试连接节点: {node['host']}:{node['port']}")
                # 禁用代理，直接连接本地服务
                response = requests.get(
                    f"http://{node['host']}:{node['port']}/system_stats", 
                    timeout=5,
                    proxies={'http': '', 'https': ''}  # 禁用代理
                )
                print(f"[DEBUG] 节点响应状态码: {response.status_code}")
                if response.status_code == 200:
                    print(f"[DEBUG] 成功连接到节点: {node['host']}:{node['port']}")
                    return node
                else:
                    print(f"[DEBUG] 节点响应异常: {response.status_code} - {response.text}")
            except requests.exceptions.ConnectionError as e:
                print(f"[DEBUG] 连接节点失败: {node['host']}:{node['port']} - {e}")
                continue
            except requests.exceptions.Timeout as e:
                print(f"[DEBUG] 连接节点超时: {node['host']}:{node['port']} - {e}")
                continue
            except Exception as e:
                print(f"[DEBUG] 连接节点异常: {node['host']}:{node['port']} - {e}")
                continue
    
    print("[DEBUG] 没有可用的ComfyUI节点")
    return None

def reset_node_status():
    """重置所有节点状态为可用"""
    for node in COMFYUI_NODES:
        node["available"] = True
    print("[DEBUG] 已重置所有节点状态为可用")

def check_and_reset_stuck_nodes():
    """检查并重置卡住的节点"""
    stuck_nodes = []
    for node in COMFYUI_NODES:
        if not node["available"]:
            try:
                # 尝试连接节点，如果能连接说明节点实际上是可用的
                response = requests.get(
                    f"http://{node['host']}:{node['port']}/system_stats", 
                    timeout=3,
                    proxies={'http': '', 'https': ''}
                )
                if response.status_code == 200:
                    print(f"[DEBUG] 发现卡住的节点，重置为可用: {node['host']}:{node['port']}")
                    node["available"] = True
                    stuck_nodes.append(node)
            except:
                # 如果连接失败，保持不可用状态
                pass
    
    if stuck_nodes:
        print(f"[DEBUG] 重置了 {len(stuck_nodes)} 个卡住的节点")
    return len(stuck_nodes)

def get_task_result(task_id: str) -> Optional[Dict[str, Any]]:
    """获取Celery任务结果"""
    try:
        from celery.result import AsyncResult
        result = AsyncResult(task_id, app=celery_app)
        
        print(f"[DEBUG] 获取任务 {task_id} 状态: {result.state}")
        
        if result.ready():
            if result.successful():
                task_result = result.get()
                print(f"[DEBUG] 任务 {task_id} 成功完成: {task_result}")
                return task_result
            else:
                error_msg = str(result.info) if result.info else "任务执行失败"
                print(f"[DEBUG] 任务 {task_id} 失败: {error_msg}")
                return {
                    "status": "failed",
                    "error_message": error_msg,
                    "progress": 0
                }
        elif result.state == "PENDING":
            return {"status": "queued", "progress": 0, "message": "任务排队中"}
        elif result.state == "STARTED":
            return {"status": "processing", "progress": 25, "message": "任务已开始"}
        elif result.state == "PROGRESS":
            # 确保result.info是字典类型
            if isinstance(result.info, dict):
                progress = result.info.get("progress", 50)
                message = result.info.get("message", "处理中")
            else:
                progress = 50
                message = "处理中"
            return {"status": "processing", "progress": progress, "message": message}
        else:
            return {"status": "processing", "progress": 50, "message": "处理中"}
    except Exception as e:
        print(f"获取任务结果失败: {e}")
        return None

def create_image_workflow(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """创建文生图工作流，支持从JSON文件加载或使用默认工作流"""
    # 优先使用指定的工作流模板
    workflow_template = request_data.get('workflow_template', '标准文生图')
    
    # 尝试从JSON文件加载工作流
    workflow = workflow_selector.create_workflow(
        request_data,
        workflow_template
    )
    
    if workflow:
        print(f"[DEBUG] 成功从模板加载工作流: {workflow_template}")
        return workflow
    
    # 如果加载失败，使用配置管理器获取参数
    print(f"[DEBUG] 无法加载工作流模板 {workflow_template}，使用配置管理器获取参数")
    
    # 使用配置管理器获取参数
    params = CONFIG.get_image_generation_params(workflow_template, request_data)
    batch_size = request_data.get('batch_size', 1)
    
    workflow = {
        "3": {
            "inputs": {
                "seed": request_data.get("seed", 42),
                "steps": params["steps"],
                "cfg": params["cfg_scale"],
                "sampler_name": params["sampler_name"],
                "scheduler": params["scheduler"],
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": params["ckpt_name"]
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": params["width"],
                "height": params["height"],
                "batch_size": batch_size
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": request_data["prompt"],
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": request_data["negative_prompt"],
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": f"ComfyUI_{request_data['task_id']}",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }
    return workflow

@celery_app.task(bind=True)
def generate_image_task(self, request_data: Dict[str, Any]):
    """文生图任务"""
    task_id = request_data["task_id"]
    node = None
    
    print(f"[DEBUG] 开始执行任务: {task_id}")
    
    # 更新任务状态为处理中
    self.update_state(
        state="PROGRESS",
        meta={"progress": 10, "message": "正在连接ComfyUI节点..."}
    )
    
    try:
        # 检查并重置卡住的节点
        check_and_reset_stuck_nodes()
        
        node = get_available_node()
        if not node:
            print(f"[ERROR] 任务 {task_id}: 没有可用的ComfyUI节点")
            return {
                "status": "failed", 
                "error_message": "没有可用的ComfyUI节点",
                "progress": 0
            }

        print(f"[DEBUG] 任务 {task_id}: 分配到节点 {node['host']}:{node['port']}")
        
        # 标记节点为忙碌
        node["available"] = False
        print(f"[DEBUG] 任务 {task_id}: 节点已标记为忙碌")
        
        # 更新进度
        self.update_state(
            state="PROGRESS",
            meta={"progress": 20, "message": "正在创建工作流..."}
        )

        # 创建工作流
        workflow = create_image_workflow(request_data)
        print(f"[DEBUG] 任务 {task_id}: 即将向ComfyUI提交workflow")
        print(f"[DEBUG] 任务 {task_id}: 工作流类型: {type(workflow)}")
        print(f"[DEBUG] 任务 {task_id}: 工作流内容预览: {str(workflow)[:500]}...")
        
        # 验证工作流结构
        if not workflow:
            print(f"[ERROR] 任务 {task_id}: 工作流创建失败")
            return {
                "status": "failed",
                "error_message": "工作流创建失败",
                "progress": 20
            }
        
        # 检查工作流是否有节点
        if not isinstance(workflow, dict) or not workflow:
            print(f"[ERROR] 任务 {task_id}: 工作流格式错误 - 不是有效的字典或为空")
            return {
                "status": "failed",
                "error_message": "工作流格式错误",
                "progress": 20
            }
        
        # 检查是否有输出节点
        output_nodes = []
        for node_id, node_data in workflow.items():
            if isinstance(node_data, dict) and node_data.get('class_type') in ['SaveImage', 'VHS_VideoCombine', 'SaveVideo', 'SaveAudio']:
                output_nodes.append(f"{node_data.get('class_type')}(ID:{node_id})")
        
        if not output_nodes:
            print(f"[WARNING] 任务 {task_id}: 工作流中没有找到输出节点！")
            print(f"[WARNING] 任务 {task_id}: 这可能导致 'Prompt has no outputs' 错误")
        else:
            print(f"[DEBUG] 任务 {task_id}: 找到输出节点: {output_nodes}")
        
        print(f"[DEBUG] 任务 {task_id}: 工作流节点数量: {len(workflow)}")
        print(f"[DEBUG] 任务 {task_id}: 工作流节点类型: {[node_data.get('class_type', 'unknown') for node_data in workflow.values() if isinstance(node_data, dict)]}")

        # 更新进度
        self.update_state(
            state="PROGRESS",
            meta={"progress": 30, "message": "正在提交到ComfyUI..."}
        )

        # 提交到ComfyUI
        try:
            print(f"[DEBUG] 任务 {task_id}: 准备提交到 {node['host']}:{node['port']}/prompt")
            print(f"[DEBUG] 任务 {task_id}: 请求数据: {{'prompt': workflow}}")
            
            response = requests.post(
                f"http://{node['host']}:{node['port']}/prompt",
                json={"prompt": workflow},
                timeout=30,
                proxies={'http': '', 'https': ''}  # 禁用代理
            )
            print(f"[DEBUG] 任务 {task_id}: ComfyUI响应状态码: {response.status_code}")
            print(f"[DEBUG] 任务 {task_id}: ComfyUI响应内容: {response.text}")
        except Exception as e:
            print(f"[ERROR] 任务 {task_id}: 请求ComfyUI出错: {e}")
            raise

        if response.status_code == 200:
            result = response.json()
            prompt_id = result["prompt_id"]
            print(f"[DEBUG] 任务 {task_id}: 获得prompt_id: {prompt_id}")

            # 更新进度
            self.update_state(
                state="PROGRESS",
                meta={"progress": 50, "message": "正在生成图像..."}
            )

            # 轮询任务状态
            max_wait_time = 300  # 5分钟超时
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    history_response = requests.get(
                        f"http://{node['host']}:{node['port']}/history/{prompt_id}",
                        timeout=10,
                        proxies={'http': '', 'https': ''}  # 禁用代理
                    )

                    if history_response.status_code == 200:
                        history = history_response.json()
                        if prompt_id in history:
                            # 任务完成，获取结果
                            outputs = history[prompt_id]["outputs"]
                            print(f"[DEBUG] 任务 {task_id}: 任务完成，获取到outputs")
                            
                            # 查找保存的图像
                            result_files = []
                            for node_id, output in outputs.items():
                                if "images" in output:
                                    for image_info in output["images"]:
                                        filename = image_info.get("filename")
                                        if filename and filename.strip():
                                            result_file = os.path.join(COMFYUI_OUTPUT_DIR, filename)
                                            if os.path.exists(result_file):
                                                result_files.append(result_file)
                            if result_files:
                                print(f"[DEBUG] 任务 {task_id}: 找到图片文件: {result_files}")
                                return {
                                    "status": "completed",
                                    "progress": 100,
                                    "message": "图像生成完成",
                                    "result_url": result_files if len(result_files) > 1 else result_files[0],
                                    "outputs": outputs
                                }
                            else:
                                print(f"[DEBUG] 任务 {task_id}: 图片文件未找到: {result_files}")
                                # 尝试列出ComfyUI输出目录的内容
                                if os.path.exists(COMFYUI_OUTPUT_DIR):
                                    files = os.listdir(COMFYUI_OUTPUT_DIR)
                                    print(f"[DEBUG] 任务 {task_id}: ComfyUI输出目录内容: {files}")
                                else:
                                    print(f"[DEBUG] 任务 {task_id}: ComfyUI输出目录不存在: {COMFYUI_OUTPUT_DIR}")
                                return {
                                    "status": "failed",
                                    "error_message": "生成的图像文件未找到",
                                    "progress": 90
                                }

                    # 更新进度（模拟进度增长）
                    elapsed = time.time() - start_time
                    progress = min(50 + int((elapsed / max_wait_time) * 40), 90)
                    self.update_state(
                        state="PROGRESS",
                        meta={"progress": progress, "message": f"正在生成图像... ({progress}%)"}
                    )

                    time.sleep(2)  # 2秒后重新检查

                except requests.RequestException as e:
                    print(f"[DEBUG] 任务 {task_id}: 检查任务状态时出错: {e}")
                    time.sleep(5)
                    continue

            # 超时
            print(f"[ERROR] 任务 {task_id}: 任务执行超时")
            return {
                "status": "failed",
                "error_message": "任务执行超时",
                "progress": 90
            }

        else:
            print(f"[ERROR] 任务 {task_id}: 提交任务失败: {response.status_code}")
            return {
                "status": "failed",
                "error_message": f"提交任务失败: {response.status_code}",
                "progress": 30
            }

    except Exception as e:
        print(f"[ERROR] 任务 {task_id}: 任务执行异常: {e}")
        return {
            "status": "failed",
            "error_message": str(e),
            "progress": 0
        }
    finally:
        # 确保节点被释放
        if node:
            node["available"] = True
            print(f"[DEBUG] 任务 {task_id}: 节点 {node['host']}:{node['port']} 已释放")
        else:
            print(f"[DEBUG] 任务 {task_id}: 没有节点需要释放")

@celery_app.task(bind=True)
def generate_video_task(self, request_data: Dict[str, Any]):
    """图生视频任务（需要相应的ComfyUI视频生成工作流）"""
    # 类似实现，但使用视频生成的工作流
    task_id = request_data["task_id"]
    
    self.update_state(
        state="PROGRESS",
        meta={"progress": 10, "message": "视频生成功能暂未实现..."}
    )
    
    return {
        "status": "failed",
        "error_message": "视频生成功能暂未实现",
        "progress": 0
    }