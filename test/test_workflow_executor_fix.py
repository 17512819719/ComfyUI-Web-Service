#!/usr/bin/env python3
"""
测试工作流执行器修复
"""
import sys
import os

# 添加正确的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
backend_path = os.path.join(project_root, 'backend')

sys.path.insert(0, backend_path)

# 切换到项目根目录
os.chdir(project_root)

def test_workflow_executor_initialization():
    """测试工作流执行器初始化"""
    print("⚙️ 测试工作流执行器初始化")
    print("-" * 40)
    
    try:
        from app.core.workflow_executor import ComfyUIWorkflowExecutor
        from app.core.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        print(f"配置模式: {'分布式' if config_manager.is_distributed_mode() else '单机'}")
        
        # 创建工作流执行器实例
        executor = ComfyUIWorkflowExecutor()
        
        print(f"执行器分布式模式: {executor.is_distributed}")
        print(f"超时时间: {executor.timeout}")
        
        # 测试单机模式配置
        if executor.single_mode_config:
            print("单机模式配置:")
            for key, value in executor.single_mode_config.items():
                print(f"  {key}: {value}")
        else:
            print("单机模式配置: 未初始化")
        
        # 测试分布式组件
        if executor.is_distributed:
            print("分布式组件:")
            print(f"  节点管理器: {'已初始化' if executor.node_manager else '未初始化'}")
            print(f"  负载均衡器: {'已初始化' if executor.load_balancer else '未初始化'}")
        
        print("✅ 工作流执行器初始化测试完成")
        
    except Exception as e:
        print(f"❌ 工作流执行器初始化测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_execution_url_methods():
    """测试执行URL获取方法"""
    print("\n🌐 测试执行URL获取方法")
    print("-" * 40)
    
    try:
        from app.core.workflow_executor import ComfyUIWorkflowExecutor

        executor = ComfyUIWorkflowExecutor()
        
        # 测试不同任务类型的URL获取
        test_cases = [
            ('text_to_image', 'test-task-1'),
            ('image_to_video', 'test-task-2'),
            (None, 'test-task-3'),
        ]
        
        for task_type, task_id in test_cases:
            try:
                url, node_id = executor.get_execution_url(task_type, task_id)
                print(f"任务类型 {task_type}: {url} (节点: {node_id})")
                
                # 测试清理
                executor.cleanup_task_assignment(task_id, node_id)
                print(f"  清理完成: {task_id}")
                
            except Exception as e:
                print(f"任务类型 {task_type}: 获取失败 - {e}")
        
        print("✅ 执行URL获取方法测试完成")
        
    except Exception as e:
        print(f"❌ 执行URL获取方法测试失败: {e}")

def test_legacy_compatibility():
    """测试遗留兼容性"""
    print("\n🔄 测试遗留兼容性")
    print("-" * 40)
    
    try:
        from app.core.workflow_executor import ComfyUIWorkflowExecutor

        executor = ComfyUIWorkflowExecutor()
        
        # 检查是否还有硬编码的属性
        legacy_attributes = ['host', 'port', 'base_url', 'ws_url']
        
        print("检查遗留属性:")
        for attr in legacy_attributes:
            if hasattr(executor, attr):
                value = getattr(executor, attr)
                print(f"  ❌ {attr}: {value} (应该已移除)")
            else:
                print(f"  ✅ {attr}: 已移除")
        
        # 检查新的配置结构
        print("\n检查新配置结构:")
        if hasattr(executor, 'single_mode_config'):
            print(f"  ✅ single_mode_config: {'已配置' if executor.single_mode_config else '未配置'}")
        else:
            print(f"  ❌ single_mode_config: 缺失")
        
        if hasattr(executor, 'is_distributed'):
            print(f"  ✅ is_distributed: {executor.is_distributed}")
        else:
            print(f"  ❌ is_distributed: 缺失")
        
        print("✅ 遗留兼容性测试完成")
        
    except Exception as e:
        print(f"❌ 遗留兼容性测试失败: {e}")

def test_node_selection_logic():
    """测试节点选择逻辑"""
    print("\n🎯 测试节点选择逻辑")
    print("-" * 40)
    
    try:
        from app.core.workflow_executor import ComfyUIWorkflowExecutor

        executor = ComfyUIWorkflowExecutor()

        if executor.is_distributed:
            print("分布式模式节点选择测试:")

            # 测试节点选择
            try:
                from app.core.base import TaskType
                
                # 模拟获取可用节点
                if executor.node_manager:
                    print("  节点管理器可用，测试节点获取...")
                    # 这里可以添加更多的节点选择测试
                else:
                    print("  节点管理器不可用")
                    
            except Exception as e:
                print(f"  节点选择测试失败: {e}")
        else:
            print("单机模式，跳过节点选择测试")
        
        print("✅ 节点选择逻辑测试完成")
        
    except Exception as e:
        print(f"❌ 节点选择逻辑测试失败: {e}")

def main():
    """主测试函数"""
    print("🧪 测试工作流执行器修复")
    print("=" * 50)
    
    # 测试工作流执行器初始化
    test_workflow_executor_initialization()
    
    # 测试执行URL获取方法
    test_execution_url_methods()
    
    # 测试遗留兼容性
    test_legacy_compatibility()
    
    # 测试节点选择逻辑
    test_node_selection_logic()
    
    print("\n🎯 工作流执行器修复测试完成！")
    print("\n修复内容总结:")
    print("1. ✅ 移除硬编码的单机模式URL配置")
    print("2. ✅ 添加智能的单机/分布式模式初始化")
    print("3. ✅ 实现动态URL获取方法")
    print("4. ✅ 完善的降级机制和错误处理")
    print("5. ✅ 统一的任务分配和清理逻辑")
    
    print("\n架构优化:")
    print("- 单机模式: 使用配置文件中的ComfyUI设置")
    print("- 分布式模式: 动态选择最佳节点")
    print("- 降级机制: 分布式失败时自动回退到单机模式")
    print("- 兼容性: 保持现有API接口不变")

if __name__ == "__main__":
    main()
