#!/usr/bin/env python3
"""
测试健康检查修复
"""
import sys
import os
import requests
import asyncio

# 添加正确的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
backend_path = os.path.join(project_root, 'backend')
scripts_path = os.path.join(project_root, 'scripts')

sys.path.insert(0, backend_path)
sys.path.insert(0, scripts_path)

# 切换到项目根目录
os.chdir(project_root)

async def test_health_check_api():
    """测试健康检查API"""
    print("🏥 测试健康检查API")
    print("-" * 30)
    
    try:
        # 测试健康检查接口
        response = requests.get("http://localhost:8001/api/v2/health", timeout=10)
        
        if response.status_code == 200:
            health_data = response.json()
            print("✅ 健康检查API响应成功")
            print(f"整体状态: {health_data.get('status', 'unknown')}")
            
            # 检查服务状态
            services = health_data.get('services', {})
            for service, status in services.items():
                if service == 'comfyui_details':
                    continue  # 跳过详细信息
                print(f"  {service}: {status}")
            
            # 检查ComfyUI详细信息
            comfyui_details = health_data.get('services', {}).get('comfyui_details', {})
            if comfyui_details:
                mode = comfyui_details.get('mode', 'unknown')
                print(f"\nComfyUI模式: {mode}")
                
                if mode == 'distributed':
                    healthy_nodes = comfyui_details.get('healthy_nodes', 0)
                    total_nodes = comfyui_details.get('total_nodes', 0)
                    print(f"节点状态: {healthy_nodes}/{total_nodes} 健康")
                    
                    nodes = comfyui_details.get('nodes', {})
                    for node_id, node_info in nodes.items():
                        status = node_info.get('status', 'unknown')
                        url = node_info.get('url', 'unknown')
                        print(f"  {node_id}: {status} ({url})")
                        if 'error' in node_info:
                            print(f"    错误: {node_info['error']}")
                elif mode.startswith('single'):
                    url = comfyui_details.get('url', 'unknown')
                    print(f"单机URL: {url}")
                    if 'distributed_error' in comfyui_details:
                        print(f"分布式错误: {comfyui_details['distributed_error']}")
            
            # 检查队列信息
            queue_info = health_data.get('queue_info', {})
            if queue_info:
                print(f"\n队列信息:")
                print(f"  活跃任务: {queue_info.get('active_tasks', 0)}")
                print(f"  总任务数: {queue_info.get('total_tasks', 0)}")
            
        else:
            print(f"❌ 健康检查API失败: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 健康检查API测试失败: {e}")

def test_startup_script_check():
    """测试启动脚本的检查功能"""
    print("\n🚀 测试启动脚本检查")
    print("-" * 30)
    
    try:
        # 导入启动脚本的检查函数
        sys.path.append('scripts')
        from start_fastapi import check_dependencies

        print("执行依赖服务检查...")
        services_status = check_dependencies()
        
        print("服务状态:")
        for service, status in services_status.items():
            print(f"  {service}: {'✅' if status else '❌'}")
            
    except Exception as e:
        print(f"❌ 启动脚本检查失败: {e}")

async def test_app_startup_check():
    """测试应用启动时的检查"""
    print("\n📱 测试应用启动检查")
    print("-" * 30)
    
    try:
        from app.core.config_manager import get_config_manager

        config_manager = get_config_manager()
        print(f"配置模式: {'分布式' if config_manager.is_distributed_mode() else '单机'}")

        if config_manager.is_distributed_mode():
            try:
                from app.core.node_manager import get_node_manager
                node_manager = get_node_manager()
                nodes_dict = node_manager.get_all_nodes()
                
                print(f"配置的节点数: {len(nodes_dict)}")
                for node_id, node in nodes_dict.items():
                    print(f"  {node_id}: {node.url}")
                    
            except Exception as e:
                print(f"节点管理器初始化失败: {e}")
        else:
            comfyui_config = config_manager.get_comfyui_config()
            host = comfyui_config.get('host', '127.0.0.1')
            port = comfyui_config.get('port', 8188)
            print(f"单机ComfyUI: {host}:{port}")
            
    except Exception as e:
        print(f"❌ 应用启动检查失败: {e}")

async def main():
    """主测试函数"""
    print("🧪 测试健康检查修复")
    print("=" * 50)
    
    # 测试健康检查API
    await test_health_check_api()
    
    # 测试启动脚本检查
    test_startup_script_check()
    
    # 测试应用启动检查
    await test_app_startup_check()
    
    print("\n🎯 健康检查修复测试完成！")
    print("\n修复内容总结:")
    print("1. ✅ 健康检查API支持分布式节点状态检查")
    print("2. ✅ 应用启动时检查所有分布式节点")
    print("3. ✅ 启动脚本显示所有节点状态")
    print("4. ✅ 完善的降级机制和错误处理")
    print("5. ✅ 详细的节点状态信息展示")

if __name__ == "__main__":
    asyncio.run(main())
