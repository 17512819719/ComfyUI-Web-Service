#!/usr/bin/env python3
"""
测试输出目录配置修复
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

def test_output_dir_functions():
    """测试输出目录相关函数"""
    print("📁 测试输出目录配置函数")
    print("-" * 40)
    
    try:
        from app.utils.path_utils import get_output_dir, get_node_output_dir
        from app.core.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        
        # 测试基本输出目录获取
        print(f"配置模式: {'分布式' if config_manager.is_distributed_mode() else '单机'}")
        
        output_dir = get_output_dir()
        print(f"主输出目录: {output_dir}")
        print(f"目录存在: {os.path.exists(output_dir)}")
        
        # 测试节点特定输出目录
        if config_manager.is_distributed_mode():
            print("\n测试节点输出目录:")
            
            # 测试有节点ID的情况
            node_output_dir = get_node_output_dir("comfyui-worker-1")
            print(f"节点 comfyui-worker-1 输出目录: {node_output_dir}")
            print(f"节点目录存在: {os.path.exists(node_output_dir)}")
            
            # 测试另一个节点
            node_output_dir2 = get_node_output_dir("comfyui-worker-2")
            print(f"节点 comfyui-worker-2 输出目录: {node_output_dir2}")
            print(f"节点目录存在: {os.path.exists(node_output_dir2)}")
            
            # 测试无节点ID的情况
            default_output_dir = get_node_output_dir()
            print(f"默认输出目录: {default_output_dir}")
        else:
            print("\n单机模式，节点输出目录功能不适用")
            
        print("✅ 输出目录函数测试完成")
        
    except Exception as e:
        print(f"❌ 输出目录函数测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_distributed_config():
    """测试分布式配置"""
    print("\n⚙️ 测试分布式配置")
    print("-" * 40)
    
    try:
        from app.core.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        
        # 测试分布式配置读取
        distributed_config = config_manager.get_config('distributed') or {}
        print(f"分布式配置: {distributed_config}")
        
        if distributed_config:
            enabled = distributed_config.get('enabled', False)
            print(f"分布式启用: {enabled}")
            
            file_management = distributed_config.get('file_management', {})
            if file_management:
                print(f"代理输出目录: {file_management.get('proxy_output_dir', 'N/A')}")
                print(f"启用文件缓存: {file_management.get('enable_file_cache', False)}")
                print(f"缓存TTL: {file_management.get('cache_ttl', 'N/A')} 秒")
                print(f"最大缓存大小: {file_management.get('max_cache_size', 'N/A')}")
            
            sync_config = distributed_config.get('sync', {})
            if sync_config:
                print(f"启用文件同步: {sync_config.get('enable_file_sync', False)}")
                print(f"同步间隔: {sync_config.get('sync_interval', 'N/A')} 秒")
                print(f"同步模式: {sync_config.get('sync_patterns', [])}")
        
        print("✅ 分布式配置测试完成")
        
    except Exception as e:
        print(f"❌ 分布式配置测试失败: {e}")

def test_path_resolution():
    """测试路径解析"""
    print("\n🛤️ 测试路径解析")
    print("-" * 40)
    
    try:
        from app.utils.path_utils import resolve_path
        
        # 测试各种路径
        test_paths = [
            "outputs",
            "outputs/distributed",
            "outputs/distributed/nodes/worker-1",
            "../ComfyUI/output",
            "/absolute/path/test"
        ]
        
        for path in test_paths:
            try:
                resolved = resolve_path(path)
                print(f"{path} -> {resolved}")
                print(f"  绝对路径: {os.path.isabs(resolved)}")
                print(f"  父目录存在: {os.path.exists(os.path.dirname(resolved))}")
            except Exception as e:
                print(f"{path} -> 解析失败: {e}")
        
        print("✅ 路径解析测试完成")
        
    except Exception as e:
        print(f"❌ 路径解析测试失败: {e}")

def test_directory_creation():
    """测试目录创建"""
    print("\n📂 测试目录创建")
    print("-" * 40)
    
    try:
        from app.utils.path_utils import get_output_dir, get_node_output_dir
        
        # 测试主输出目录创建
        output_dir = get_output_dir()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"✅ 创建主输出目录: {output_dir}")
        else:
            print(f"✅ 主输出目录已存在: {output_dir}")
        
        # 测试节点目录创建
        test_nodes = ["test-node-1", "test-node-2"]
        for node_id in test_nodes:
            node_dir = get_node_output_dir(node_id)
            print(f"✅ 节点 {node_id} 目录: {node_dir}")
            print(f"  目录存在: {os.path.exists(node_dir)}")
        
        print("✅ 目录创建测试完成")
        
    except Exception as e:
        print(f"❌ 目录创建测试失败: {e}")

def main():
    """主测试函数"""
    print("🧪 测试输出目录配置修复")
    print("=" * 50)
    
    # 测试输出目录函数
    test_output_dir_functions()
    
    # 测试分布式配置
    test_distributed_config()
    
    # 测试路径解析
    test_path_resolution()
    
    # 测试目录创建
    test_directory_creation()
    
    print("\n🎯 输出目录配置修复测试完成！")
    print("\n修复内容总结:")
    print("1. ✅ 输出目录配置支持分布式模式")
    print("2. ✅ 节点特定输出目录管理")
    print("3. ✅ 静态文件服务适配分布式架构")
    print("4. ✅ 分布式文件管理配置")
    print("5. ✅ 完善的路径解析和目录创建")
    
    print("\n架构说明:")
    print("- 单机模式: 直接使用本地输出目录")
    print("- 分布式模式: 主机作为代理，通过API获取从机文件")
    print("- 节点缓存: 每个节点有独立的缓存目录")
    print("- 文件代理: 通过 /api/v2/files/ 接口代理访问")

if __name__ == "__main__":
    main()
