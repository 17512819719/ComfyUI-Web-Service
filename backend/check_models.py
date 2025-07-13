#!/usr/bin/env python3
"""
检查ComfyUI可用的模型
"""
import json
import requests

def check_available_models():
    """检查可用的模型"""
    try:
        print("获取ComfyUI对象信息...")
        response = requests.get("http://localhost:8188/object_info", timeout=30)
        
        if response.status_code != 200:
            print(f"获取对象信息失败: {response.status_code}")
            return
        
        object_info = response.json()
        
        # 检查CheckpointLoaderSimple节点
        if "CheckpointLoaderSimple" in object_info:
            checkpoint_info = object_info["CheckpointLoaderSimple"]
            if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                ckpt_name_info = checkpoint_info["input"]["required"].get("ckpt_name")
                if ckpt_name_info and len(ckpt_name_info) > 0:
                    available_models = ckpt_name_info[0]
                    print(f"可用的Checkpoint模型 ({len(available_models)} 个):")
                    for i, model in enumerate(available_models[:10]):  # 只显示前10个
                        print(f"  {i+1}. {model}")
                    if len(available_models) > 10:
                        print(f"  ... 还有 {len(available_models) - 10} 个模型")
                    
                    # 返回第一个可用的模型
                    return available_models[0] if available_models else None
                else:
                    print("未找到ckpt_name参数信息")
            else:
                print("CheckpointLoaderSimple节点信息格式异常")
        else:
            print("未找到CheckpointLoaderSimple节点")
            
        return None
        
    except Exception as e:
        print(f"检查模型失败: {e}")
        return None

def test_simple_workflow():
    """测试一个简单的工作流"""
    try:
        # 获取可用的模型
        available_model = check_available_models()
        if not available_model:
            print("没有可用的模型，无法测试")
            return False
        
        print(f"\n使用模型: {available_model}")
        
        # 创建一个简单的工作流
        simple_workflow = {
            "1": {
                "inputs": {
                    "ckpt_name": available_model
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {
                    "text": "a beautiful cat",
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "3": {
                "inputs": {
                    "text": "",
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "4": {
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "5": {
                "inputs": {
                    "seed": 123456,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0]
                },
                "class_type": "KSampler"
            },
            "6": {
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode"
            },
            "7": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage"
            }
        }
        
        print("提交简单工作流...")
        response = requests.post(
            "http://localhost:8188/prompt",
            json={"prompt": simple_workflow},
            timeout=30
        )
        
        print(f"提交响应状态: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 简单工作流提交成功，任务ID: {result.get('prompt_id')}")
            return True
        else:
            print(f"❌ 简单工作流提交失败")
            return False
            
    except Exception as e:
        print(f"测试简单工作流失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始检查ComfyUI模型...")
    test_simple_workflow()
