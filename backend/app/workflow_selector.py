#!/usr/bin/env python3
"""
工作流选择器模块 - 独立的工作流模板管理
"""

import json
import os
from typing import Dict, List, Optional, Any
from .workflow_manager import workflow_manager

class WorkflowSelector:
    """工作流选择器 - 独立的工作流模板管理类"""
    
    def __init__(self, workflows_dir: str = "workflows"):
        if not os.path.isabs(workflows_dir):
            self.workflows_dir = os.path.join(os.path.dirname(__file__), '..', workflows_dir)
        else:
            self.workflows_dir = workflows_dir
        self.workflow_manager = workflow_manager
        self.default_workflow = "标准文生图"
        self.workflow_config = self._load_workflow_config()
    
    def _load_workflow_config(self) -> Dict[str, Any]:
        """加载工作流配置文件"""
        config_path = os.path.join(self.workflows_dir, "workflow_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载工作流配置失败: {e}")
        
        # 默认配置
        return {
            "default_workflow": self.default_workflow,
            "workflow_categories": {
                "text_to_image": ["SD35标准文生图"],
                "image_to_video": ["simplified_wan_i2v_workflow"]
            },
            "workflow_descriptions": {
                "SD35标准文生图": "SD3.5标准文生图工作流",
                "simplified_wan_i2v_workflow": "万相图生视频工作流"
            }
        }
    
    def get_available_workflows(self) -> List[str]:
        """获取所有可用的工作流"""
        return self.workflow_manager.list_workflows()
    
    def get_workflow_by_category(self, category: str) -> List[str]:
        """根据类别获取工作流"""
        return self.workflow_config.get("workflow_categories", {}).get(category, [])
    
    def get_workflow_description(self, workflow_name: str) -> str:
        """获取工作流描述"""
        return self.workflow_config.get("workflow_descriptions", {}).get(workflow_name, workflow_name)
    
    def get_default_workflow(self) -> str:
        """获取默认工作流"""
        return self.workflow_config.get("default_workflow", self.default_workflow)
    
    def set_default_workflow(self, workflow_name: str) -> bool:
        """设置默认工作流"""
        available_workflows = self.get_available_workflows()
        if workflow_name in available_workflows:
            self.workflow_config["default_workflow"] = workflow_name
            self._save_workflow_config()
            return True
        return False
    
    def create_workflow(self, parameters: Dict[str, Any], workflow_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """创建工作流"""
        if workflow_name is None:
            workflow_name = self.get_default_workflow()
        
        return self.workflow_manager.create_workflow_from_template(workflow_name, parameters)
    
    def validate_workflow(self, workflow_name: str) -> bool:
        """验证工作流是否存在且有效"""
        try:
            workflow = self.workflow_manager.load_workflow(workflow_name)
            return workflow is not None
        except Exception:
            return False
    
    def get_workflow_info(self, workflow_name: str) -> Dict[str, Any]:
        """获取工作流详细信息"""
        workflow = self.workflow_manager.load_workflow(workflow_name)
        if workflow is None:
            return {"error": "工作流不存在"}
        
        # 分析工作流节点
        nodes = workflow.get("nodes", [])
        node_types = {}
        for node in nodes:
            node_type = node.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        return {
            "name": workflow_name,
            "description": self.get_workflow_description(workflow_name),
            "node_count": len(nodes),
            "node_types": node_types,
            "has_output": any(node.get("type") in ["SaveImage", "VHS_VideoCombine"] for node in nodes)
        }
    
    def _save_workflow_config(self):
        """保存工作流配置"""
        config_path = os.path.join(self.workflows_dir, "workflow_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.workflow_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存工作流配置失败: {e}")

# 全局工作流选择器实例
workflow_selector = WorkflowSelector() 