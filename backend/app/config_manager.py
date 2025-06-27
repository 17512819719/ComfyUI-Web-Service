#!/usr/bin/env python3
"""
配置管理器 - 统一管理所有配置，解决解耦问题
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path

class ConfigManager:
    """统一的配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.workflow_config = self._load_workflow_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载主配置文件"""
        config_file = os.path.join(os.path.dirname(__file__), '..', self.config_path)
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"警告: 无法加载配置文件 {config_file}: {e}")
            return {}
    
    def _load_workflow_config(self) -> Dict[str, Any]:
        """加载工作流配置文件"""
        workflow_config_path = os.path.join(os.path.dirname(__file__), '..', 'workflows', 'workflow_config.json')
        try:
            with open(workflow_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 无法加载工作流配置文件 {workflow_config_path}: {e}")
            return {}
    
    def get_comfyui_config(self) -> Dict[str, Any]:
        """获取ComfyUI配置"""
        return self.config.get('comfyui', {})
    
    def get_mysql_config(self) -> Dict[str, Any]:
        """获取MySQL配置"""
        return self.config.get('mysql', {})
    
    def get_defaults(self, category: Optional[str] = None) -> Dict[str, Any]:
        """获取默认配置"""
        defaults = self.config.get('defaults', {})
        if category:
            return defaults.get(category, {})
        return defaults
    
    def get_model_config(self, task_type: Optional[str] = None) -> Dict[str, Any]:
        """获取模型配置"""
        models = self.config.get('models', {})
        if task_type:
            return models.get(task_type, models.get('default', {}))
        return models.get('default', {})
    
    def get_workflow_config(self) -> Dict[str, Any]:
        """获取工作流配置"""
        return self.config.get('workflows', {})
    
    def get_workflow_settings(self, workflow_name: str) -> Dict[str, Any]:
        """获取特定工作流的设置"""
        workflow_config = self.get_workflow_config()
        settings = workflow_config.get('settings', {})
        return settings.get(workflow_name, {})
    
    def get_parameter_value(self, param_name: str, workflow_name: Optional[str] = None, 
                          task_type: Optional[str] = None, category: Optional[str] = None) -> Any:
        """
        获取参数值，按优先级返回：
        1. 工作流特定设置
        2. 任务类型特定设置
        3. 全局默认设置
        4. 硬编码默认值
        """
        # 硬编码默认值
        hardcoded_defaults = {
            'width': 512,
            'height': 512,
            'steps': 20,
            'cfg_scale': 7.0,
            'sampler': 'euler',
            'scheduler': 'normal',
            'fps': 8,
            'duration': 5.0,
            'motion_strength': 0.8,
            'checkpoint': 'realisticVisionV60B1_v51HyperVAE.safetensors'
        }
        
        # 1. 工作流特定设置
        if workflow_name:
            workflow_settings = self.get_workflow_settings(workflow_name)
            if param_name in workflow_settings:
                return workflow_settings[param_name]
        
        # 2. 任务类型特定设置
        if task_type:
            task_defaults = self.get_defaults(task_type)
            if param_name in task_defaults:
                return task_defaults[param_name]
        
        # 3. 全局默认设置
        if category:
            category_defaults = self.get_defaults(category)
            if param_name in category_defaults:
                return category_defaults[param_name]
        
        # 4. 硬编码默认值
        return hardcoded_defaults.get(param_name)
    
    def get_image_generation_params(self, workflow_name: Optional[str] = None, 
                                  request_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取图像生成参数"""
        if request_params is None:
            request_params = {}
        
        # 基础参数
        params = {
            'width': request_params.get('width', 
                self.get_parameter_value('width', workflow_name, 'text_to_image', 'image')),
            'height': request_params.get('height', 
                self.get_parameter_value('height', workflow_name, 'text_to_image', 'image')),
            'steps': request_params.get('steps', 
                self.get_parameter_value('steps', workflow_name, 'text_to_image', 'image')),
            'cfg_scale': request_params.get('cfg_scale', 
                self.get_parameter_value('cfg_scale', workflow_name, 'text_to_image', 'image')),
            'sampler_name': request_params.get('sampler_name', 
                self.get_parameter_value('sampler', workflow_name, 'text_to_image', 'image')),
            'scheduler': request_params.get('scheduler', 
                self.get_parameter_value('scheduler', workflow_name, 'text_to_image', 'image')),
            'ckpt_name': request_params.get('ckpt_name', 
                self.get_model_config('text_to_image').get('checkpoint', 
                self.get_parameter_value('checkpoint', workflow_name, 'text_to_image', 'image')))
        }
        
        return params
    
    def get_video_generation_params(self, workflow_name: Optional[str] = None, 
                                  request_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取视频生成参数"""
        if request_params is None:
            request_params = {}
        
        # 基础参数
        params = {
            'fps': request_params.get('fps', 
                self.get_parameter_value('fps', workflow_name, 'image_to_video', 'video')),
            'duration': request_params.get('duration', 
                self.get_parameter_value('duration', workflow_name, 'image_to_video', 'video')),
            'motion_strength': request_params.get('motion_strength', 
                self.get_parameter_value('motion_strength', workflow_name, 'image_to_video', 'video')),
            'model_name': request_params.get('model_name', 
                self.get_model_config('image_to_video').get('checkpoint', 
                self.get_parameter_value('checkpoint', workflow_name, 'image_to_video', 'video')))
        }
        
        return params
    
    def merge_workflow_config(self) -> Dict[str, Any]:
        """合并工作流配置，解决重复问题"""
        # 使用主配置文件中的工作流配置
        main_workflow_config = self.get_workflow_config()
        
        # 合并工作流配置文件中的描述信息
        workflow_descriptions = self.workflow_config.get('workflow_descriptions', {})
        
        merged_config = {
            'default_workflow': main_workflow_config.get('default_workflow', '标准文生图'),
            'workflow_categories': main_workflow_config.get('categories', {}),
            'workflow_descriptions': workflow_descriptions,
            'workflow_settings': main_workflow_config.get('settings', {})
        }
        
        return merged_config
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置完整性"""
        issues = []
        warnings = []
        
        # 检查必需配置
        required_configs = [
            ('comfyui.port', self.get_comfyui_config().get('port')),
            ('comfyui.output_dir', self.get_comfyui_config().get('output_dir')),
            ('mysql.host', self.get_mysql_config().get('host')),
            ('mysql.database', self.get_mysql_config().get('database'))
        ]
        
        for config_path, value in required_configs:
            if not value:
                issues.append(f"缺少必需配置: {config_path}")
        
        # 检查模型文件
        model_config = self.get_model_config()
        if not model_config.get('checkpoint'):
            warnings.append("未配置默认模型文件")
        
        # 检查工作流配置
        workflow_config = self.get_workflow_config()
        if not workflow_config.get('default_workflow'):
            warnings.append("未配置默认工作流")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

# 全局配置管理器实例
config_manager = ConfigManager() 