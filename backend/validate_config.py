#!/usr/bin/env python3
"""
配置验证脚本 - 检查配置文件的一致性和完整性
"""

import os
import sys
import yaml
import json
from pathlib import Path

def load_yaml_config(config_path: str) -> dict:
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 无法加载配置文件 {config_path}: {e}")
        return {}

def load_json_config(config_path: str) -> dict:
    """加载JSON配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 无法加载配置文件 {config_path}: {e}")
        return {}

def validate_config_structure():
    """验证配置文件结构"""
    print("🔍 验证配置文件结构...")
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查主配置文件
    config_path = os.path.join(current_dir, 'config.yaml')
    if not os.path.exists(config_path):
        print(f"❌ 主配置文件不存在: {config_path}")
        return False
    
    config = load_yaml_config(config_path)
    if not config:
        return False
    
    # 检查必需配置项
    required_sections = ['comfyui', 'defaults', 'models', 'workflows', 'mysql']
    missing_sections = []
    
    for section in required_sections:
        if section not in config:
            missing_sections.append(section)
    
    if missing_sections:
        print(f"❌ 缺少必需的配置节: {missing_sections}")
        return False
    
    print("✅ 主配置文件结构正确")
    return True

def check_config_consistency():
    """检查配置一致性"""
    print("\n🔍 检查配置一致性...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 加载主配置
    config_path = os.path.join(current_dir, 'config.yaml')
    config = load_yaml_config(config_path)
    
    # 加载工作流配置
    workflow_config_path = os.path.join(current_dir, 'workflows', 'workflow_config.json')
    workflow_config = load_json_config(workflow_config_path)
    
    issues = []
    
    # 检查模型配置一致性
    models = config.get('models', {})
    if 'default' not in models:
        issues.append("缺少默认模型配置")
    
    # 检查工作流配置
    workflows = config.get('workflows', {})
    if 'default_workflow' not in workflows:
        issues.append("缺少默认工作流配置")
    
    # 检查工作流描述
    workflow_descriptions = workflow_config.get('workflow_descriptions', {})
    workflow_settings = workflows.get('settings', {})
    
    # 检查工作流设置和描述是否一致
    for workflow_name in workflow_settings.keys():
        if workflow_name not in workflow_descriptions:
            issues.append(f"工作流 '{workflow_name}' 缺少描述信息")
    
    if issues:
        print("❌ 发现配置一致性问题:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("✅ 配置一致性检查通过")
    return True

def check_parameter_values():
    """检查参数值是否合理"""
    print("\n🔍 检查参数值...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.yaml')
    config = load_yaml_config(config_path)
    
    issues = []
    
    # 检查图像参数
    image_defaults = config.get('defaults', {}).get('image', {})
    
    width = image_defaults.get('default_width', 512)
    height = image_defaults.get('default_height', 512)
    
    if width % 64 != 0 or height % 64 != 0:
        issues.append(f"图像尺寸必须是64的倍数，当前: {width}x{height}")
    
    if width < 256 or height < 256:
        issues.append(f"图像尺寸太小: {width}x{height}")
    
    if width > 2048 or height > 2048:
        issues.append(f"图像尺寸太大: {width}x{height}")
    
    steps = image_defaults.get('default_steps', 20)
    if steps < 1 or steps > 100:
        issues.append(f"步数不合理: {steps}")
    
    cfg_scale = image_defaults.get('default_cfg_scale', 7.0)
    if cfg_scale < 1.0 or cfg_scale > 20.0:
        issues.append(f"CFG比例不合理: {cfg_scale}")
    
    # 检查视频参数
    video_defaults = config.get('defaults', {}).get('video', {})
    
    fps = video_defaults.get('default_fps', 8)
    if fps < 1 or fps > 60:
        issues.append(f"帧率不合理: {fps}")
    
    duration = video_defaults.get('default_duration', 5.0)
    if duration < 0.1 or duration > 60.0:
        issues.append(f"视频时长不合理: {duration}")
    
    if issues:
        print("❌ 发现参数值问题:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("✅ 参数值检查通过")
    return True

def check_file_paths():
    """检查文件路径"""
    print("\n🔍 检查文件路径...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.yaml')
    config = load_yaml_config(config_path)
    
    issues = []
    
    # 检查ComfyUI输出目录
    output_dir = config.get('comfyui', {}).get('output_dir', '')
    if output_dir and not os.path.exists(output_dir):
        issues.append(f"ComfyUI输出目录不存在: {output_dir}")
    
    # 检查工作流目录
    workflows_dir = os.path.join(current_dir, 'workflows')
    if not os.path.exists(workflows_dir):
        issues.append(f"工作流目录不存在: {workflows_dir}")
    
    if issues:
        print("❌ 发现文件路径问题:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("✅ 文件路径检查通过")
    return True

def generate_config_report():
    """生成配置报告"""
    print("\n📊 配置报告")
    print("=" * 50)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.yaml')
    config = load_yaml_config(config_path)
    
    # ComfyUI配置
    comfyui_config = config.get('comfyui', {})
    print(f"ComfyUI端口: {comfyui_config.get('port', 'N/A')}")
    print(f"ComfyUI输出目录: {comfyui_config.get('output_dir', 'N/A')}")
    
    # 默认配置
    defaults = config.get('defaults', {})
    image_defaults = defaults.get('image', {})
    print(f"\n图像默认参数:")
    print(f"  尺寸: {image_defaults.get('default_width', 'N/A')}x{image_defaults.get('default_height', 'N/A')}")
    print(f"  步数: {image_defaults.get('default_steps', 'N/A')}")
    print(f"  CFG比例: {image_defaults.get('default_cfg_scale', 'N/A')}")
    print(f"  采样器: {image_defaults.get('default_sampler', 'N/A')}")
    
    video_defaults = defaults.get('video', {})
    print(f"\n视频默认参数:")
    print(f"  帧率: {video_defaults.get('default_fps', 'N/A')}")
    print(f"  时长: {video_defaults.get('default_duration', 'N/A')}")
    print(f"  运动强度: {video_defaults.get('default_motion_strength', 'N/A')}")
    
    # 模型配置
    models = config.get('models', {})
    print(f"\n模型配置:")
    print(f"  默认模型: {models.get('default', {}).get('checkpoint', 'N/A')}")
    print(f"  文生图模型: {models.get('text_to_image', {}).get('checkpoint', 'N/A')}")
    print(f"  图生视频模型: {models.get('image_to_video', {}).get('checkpoint', 'N/A')}")
    
    # 工作流配置
    workflows = config.get('workflows', {})
    print(f"\n工作流配置:")
    print(f"  默认工作流: {workflows.get('default_workflow', 'N/A')}")
    print(f"  可用工作流: {list(workflows.get('settings', {}).keys())}")

def main():
    """主函数"""
    print("🔧 ComfyUI Web Service 配置验证工具")
    print("=" * 50)
    
    # 执行各项检查
    checks = [
        ("配置文件结构", validate_config_structure),
        ("配置一致性", check_config_consistency),
        ("参数值", check_parameter_values),
        ("文件路径", check_file_paths)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name}检查失败: {e}")
            all_passed = False
    
    # 生成报告
    generate_config_report()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 所有配置检查通过！")
        return 0
    else:
        print("❌ 配置检查发现问题，请根据上述提示修复配置")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 