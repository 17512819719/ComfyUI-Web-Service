#!/usr/bin/env python3
"""
工作流选择器模块 - 独立的工作流模板管理
"""

import json
import os
from typing import Dict, List, Optional, Any
from .workflow_manager import WorkflowManager

class WorkflowSelector:
    """工作流选择器 - 独立的工作流模板管理类"""
    
    def __init__(self, workflows_dir: str = "workflows"):
        if not os.path.isabs(workflows_dir):
            self.workflows_dir = os.path.join(os.path.dirname(__file__), '..', workflows_dir)
        else:
            self.workflows_dir = workflows_dir
        self.workflow_manager = WorkflowManager(self.workflows_dir)
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
            "workflow_categories": {},
            "workflow_descriptions": {}
        }
    
    def get_available_workflows(self) -> List[str]:
        """获取所有可用的工作流名称"""
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
        available = self.get_available_workflows()
        if workflow_name in available:
            self.workflow_config["default_workflow"] = workflow_name
            self._save_workflow_config()
            return True
        return False
    
    def get_workflow_info(self, workflow_name: str) -> Dict[str, Any]:
        """获取工作流详细信息"""
        workflow = self.workflow_manager.load_workflow(workflow_name)
        if workflow is None:
            return {"error": "工作流不存在"}
        return {
            "name": workflow.get("name", workflow_name),
            "description": workflow.get("description", ""),
            "parameters": workflow.get("parameters", []),
            "raw": workflow
        }
    
    def create_workflow(self, parameters: Dict[str, Any], workflow_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if workflow_name is None:
            workflow_name = self.get_default_workflow()
        return self.workflow_manager.create_workflow_from_template(workflow_name, parameters)
    
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