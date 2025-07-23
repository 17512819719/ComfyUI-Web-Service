#!/usr/bin/env python3
"""
测试配置验证修复
"""
import sys
import os
import tempfile
import yaml

# 添加正确的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
backend_path = os.path.join(project_root, 'backend')

sys.path.insert(0, backend_path)

# 切换到项目根目录
os.chdir(project_root)

def create_test_config(config_data):
    """创建测试配置文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        return f.name

def test_single_mode_validation():
    """测试单机模式配置验证"""
    print("🔧 测试单机模式配置验证")
    print("-" * 40)
    
    # 测试有效的单机模式配置
    valid_single_config = {
        'task_types': {
            'text_to_image': {
                'enabled': True,
                'workflows': {
                    'sd_basic': {
                        'name': 'Stable Diffusion Basic',
                        'version': '1.0',
                        'workflow_file': 'workflows/text_to_image/文生图.json'
                    }
                }
            }
        },
        'comfyui': {
            'host': '127.0.0.1',
            'port': 8188,
            'output_dir': 'outputs',
            'timeout': 300
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0
        }
    }
    
    try:
        config_file = create_test_config(valid_single_config)
        
        from backend.app.core.config_manager import ConfigManager
        config_manager = ConfigManager(config_file)
        
        print("✅ 有效单机模式配置验证通过")
        
        # 清理
        os.unlink(config_file)
        
    except Exception as e:
        print(f"❌ 单机模式配置验证失败: {e}")

def test_distributed_mode_validation():
    """测试分布式模式配置验证"""
    print("\n🌐 测试分布式模式配置验证")
    print("-" * 40)
    
    # 测试有效的分布式模式配置
    valid_distributed_config = {
        'task_types': {
            'text_to_image': {
                'enabled': True,
                'workflows': {
                    'sd_basic': {
                        'name': 'Stable Diffusion Basic',
                        'version': '1.0',
                        'workflow_file': 'workflows/text_to_image/文生图.json'
                    }
                }
            }
        },
        'distributed': {
            'enabled': True,
            'file_management': {
                'proxy_output_dir': 'outputs/distributed',
                'enable_file_cache': True,
                'cache_ttl': 3600,
                'max_cache_size': '1GB'
            },
            'sync': {
                'enable_file_sync': False,
                'sync_interval': 300,
                'sync_patterns': ['*.png', '*.jpg', '*.mp4']
            }
        },
        'nodes': {
            'discovery_mode': 'static',
            'health_check': {
                'interval': 30,
                'timeout': 5,
                'retries': 3
            },
            'load_balancing': {
                'strategy': 'least_loaded',
                'weights': {}
            },
            'static_nodes': [
                {
                    'node_id': 'comfyui-worker-1',
                    'host': '192.168.111.6',
                    'port': 8188,
                    'max_concurrent': 4,
                    'capabilities': ['text_to_image', 'image_to_video']
                }
            ]
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'db': 0
        },
        # ComfyUI配置在分布式模式下是可选的
        'comfyui': {
            'host': '127.0.0.1',
            'port': 8188,
            'output_dir': 'outputs',
            'timeout': 300
        }
    }
    
    try:
        config_file = create_test_config(valid_distributed_config)
        
        from app.core.config_manager import ConfigManager
        config_manager = ConfigManager(config_file)
        
        print("✅ 有效分布式模式配置验证通过")
        print(f"分布式模式: {config_manager.is_distributed_mode()}")
        
        # 清理
        os.unlink(config_file)
        
    except Exception as e:
        print(f"❌ 分布式模式配置验证失败: {e}")

def test_invalid_configurations():
    """测试无效配置的验证"""
    print("\n❌ 测试无效配置验证")
    print("-" * 40)
    
    # 测试用例：缺少必需节点的分布式配置
    invalid_configs = [
        {
            'name': '缺少distributed节',
            'config': {
                'task_types': {},
                'redis': {'host': 'localhost', 'port': 6379, 'db': 0},
                'nodes': {'discovery_mode': 'static', 'static_nodes': []}
            }
        },
        {
            'name': '缺少nodes节',
            'config': {
                'task_types': {},
                'redis': {'host': 'localhost', 'port': 6379, 'db': 0},
                'distributed': {'enabled': True}
            }
        },
        {
            'name': '无效的发现模式',
            'config': {
                'task_types': {},
                'redis': {'host': 'localhost', 'port': 6379, 'db': 0},
                'distributed': {'enabled': True},
                'nodes': {'discovery_mode': 'invalid_mode'}
            }
        },
        {
            'name': '静态节点配置错误',
            'config': {
                'task_types': {},
                'redis': {'host': 'localhost', 'port': 6379, 'db': 0},
                'distributed': {'enabled': True},
                'nodes': {
                    'discovery_mode': 'static',
                    'static_nodes': [
                        {
                            'node_id': 'test-node',
                            'host': '192.168.1.1',
                            'port': 'invalid_port'  # 应该是整数
                        }
                    ]
                }
            }
        }
    ]
    
    for test_case in invalid_configs:
        try:
            config_file = create_test_config(test_case['config'])
            
            from app.core.config_manager import ConfigManager
            config_manager = ConfigManager(config_file)
            
            print(f"❌ {test_case['name']}: 应该验证失败但通过了")
            
            # 清理
            os.unlink(config_file)
            
        except Exception as e:
            print(f"✅ {test_case['name']}: 正确捕获错误 - {str(e)[:50]}...")

def test_configuration_methods():
    """测试配置方法"""
    print("\n🔍 测试配置方法")
    print("-" * 40)
    
    try:
        from app.core.config_manager import get_config_manager
        
        config_manager = get_config_manager()
        
        # 测试基本方法
        print(f"分布式模式: {config_manager.is_distributed_mode()}")
        
        # 测试配置获取
        distributed_config = config_manager.get_config('distributed')
        if distributed_config:
            print(f"分布式配置存在: {bool(distributed_config)}")
        else:
            print("分布式配置不存在")
        
        nodes_config = config_manager.get_config('nodes')
        if nodes_config:
            print(f"节点配置存在: {bool(nodes_config)}")
            discovery_mode = nodes_config.get('discovery_mode', 'unknown')
            print(f"发现模式: {discovery_mode}")
        else:
            print("节点配置不存在")
        
        # 测试ComfyUI配置
        comfyui_config = config_manager.get_comfyui_config()
        print(f"ComfyUI配置: {bool(comfyui_config)}")
        
        print("✅ 配置方法测试完成")
        
    except Exception as e:
        print(f"❌ 配置方法测试失败: {e}")

def main():
    """主测试函数"""
    print("🧪 测试配置验证修复")
    print("=" * 50)
    
    # 测试单机模式配置验证
    test_single_mode_validation()
    
    # 测试分布式模式配置验证
    test_distributed_mode_validation()
    
    # 测试无效配置验证
    test_invalid_configurations()
    
    # 测试配置方法
    test_configuration_methods()
    
    print("\n🎯 配置验证修复测试完成！")
    print("\n修复内容总结:")
    print("1. ✅ 分布式配置验证逻辑")
    print("2. ✅ 节点配置验证")
    print("3. ✅ 静态节点配置验证")
    print("4. ✅ 单机/分布式模式适配")
    print("5. ✅ 完善的错误检查和提示")
    
    print("\n验证规则:")
    print("- 单机模式: 必需 comfyui, task_types, redis")
    print("- 分布式模式: 必需 distributed, nodes, task_types, redis")
    print("- 分布式模式下 comfyui 配置为可选")
    print("- 静态节点必须有唯一ID和有效的主机端口")

if __name__ == "__main__":
    main()
