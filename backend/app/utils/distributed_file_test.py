#!/usr/bin/env python3
"""
分布式文件服务测试和诊断工具
用于测试主机和从机之间的文件传输功能
"""

import os
import sys
import logging
import asyncio
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)


class DistributedFileTestSuite:
    """分布式文件服务测试套件"""
    
    def __init__(self):
        self.test_results = []
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("=" * 60)
        print("分布式文件服务测试套件")
        print("=" * 60)
        
        tests = [
            ("配置检查", self.test_configuration),
            ("节点连接性", self.test_node_connectivity),
            ("文件服务状态", self.test_file_service_status),
            ("上传文件访问", self.test_upload_file_access),
            ("文件下载器", self.test_file_downloader),
            ("任务文件处理", self.test_task_file_processing)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n[测试] {test_name}...")
            try:
                result = await test_func()
                results[test_name] = result
                status = "✓ 通过" if result.get('success', False) else "✗ 失败"
                print(f"[结果] {status}: {result.get('message', '')}")
                
                if not result.get('success', False) and result.get('details'):
                    print(f"[详情] {result['details']}")
                    
            except Exception as e:
                results[test_name] = {
                    'success': False,
                    'message': f'测试异常: {str(e)}',
                    'error': str(e)
                }
                print(f"[结果] ✗ 异常: {str(e)}")
        
        # 生成测试报告
        self.generate_test_report(results)
        return results
    
    async def test_configuration(self) -> Dict[str, Any]:
        """测试配置"""
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()
            
            # 检查分布式模式
            distributed_enabled = config_manager.is_distributed_mode()
            
            # 检查节点配置
            static_nodes = config_manager.get_config('nodes.static_nodes', [])
            
            # 检查ComfyUI配置
            comfyui_config = config_manager.get_comfyui_config()
            
            details = {
                'distributed_enabled': distributed_enabled,
                'static_nodes_count': len(static_nodes),
                'comfyui_config': comfyui_config,
                'static_nodes': static_nodes
            }
            
            success = distributed_enabled and len(static_nodes) > 0
            message = f"分布式模式: {'启用' if distributed_enabled else '禁用'}, 静态节点: {len(static_nodes)}个"
            
            return {
                'success': success,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'配置检查失败: {str(e)}',
                'error': str(e)
            }
    
    async def test_node_connectivity(self) -> Dict[str, Any]:
        """测试节点连接性"""
        try:
            from ..services.distributed_file_service import get_distributed_file_service
            service = get_distributed_file_service()
            
            online_nodes = service.node_manager.get_online_nodes()
            
            connectivity_results = []
            for node in online_nodes:
                try:
                    import requests
                    response = requests.get(f"{node['url']}/system_stats", timeout=5)
                    connectivity_results.append({
                        'node_id': node['node_id'],
                        'url': node['url'],
                        'status': 'online' if response.status_code == 200 else 'error',
                        'response_code': response.status_code
                    })
                except Exception as e:
                    connectivity_results.append({
                        'node_id': node['node_id'],
                        'url': node['url'],
                        'status': 'offline',
                        'error': str(e)
                    })
            
            online_count = sum(1 for r in connectivity_results if r['status'] == 'online')
            success = online_count > 0
            
            return {
                'success': success,
                'message': f'在线节点: {online_count}/{len(connectivity_results)}',
                'details': {
                    'total_nodes': len(connectivity_results),
                    'online_nodes': online_count,
                    'connectivity_results': connectivity_results
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'节点连接性测试失败: {str(e)}',
                'error': str(e)
            }
    
    async def test_file_service_status(self) -> Dict[str, Any]:
        """测试文件服务状态"""
        try:
            from ..services.distributed_file_service import diagnose_file_service
            diagnosis = diagnose_file_service()
            
            success = diagnosis.get('status') == 'healthy'
            
            return {
                'success': success,
                'message': f"文件服务状态: {diagnosis.get('status', 'unknown')}",
                'details': diagnosis
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'文件服务状态检查失败: {str(e)}',
                'error': str(e)
            }
    
    async def test_upload_file_access(self) -> Dict[str, Any]:
        """测试上传文件访问"""
        try:
            from ..utils.path_utils import get_upload_dir
            upload_dir = get_upload_dir()
            
            # 检查上传目录
            upload_exists = os.path.exists(upload_dir)
            
            # 列出上传文件
            upload_files = []
            if upload_exists:
                for root, dirs, files in os.walk(upload_dir):
                    for file in files[:5]:  # 只列出前5个文件
                        rel_path = os.path.relpath(os.path.join(root, file), upload_dir)
                        upload_files.append({
                            'path': rel_path,
                            'size': os.path.getsize(os.path.join(root, file)),
                            'exists': True
                        })
            
            return {
                'success': upload_exists,
                'message': f"上传目录: {'存在' if upload_exists else '不存在'}, 文件数: {len(upload_files)}",
                'details': {
                    'upload_dir': upload_dir,
                    'upload_dir_exists': upload_exists,
                    'sample_files': upload_files
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'上传文件访问测试失败: {str(e)}',
                'error': str(e)
            }
    
    async def test_file_downloader(self) -> Dict[str, Any]:
        """测试文件下载器"""
        try:
            from ..services.node_file_downloader import get_node_file_downloader
            downloader = get_node_file_downloader()
            
            # 检查ComfyUI输入目录
            input_dir_exists = os.path.exists(downloader.input_dir)
            
            # 检查distributed子目录
            distributed_dir = os.path.join(downloader.input_dir, 'distributed')
            distributed_dir_exists = os.path.exists(distributed_dir)
            
            return {
                'success': input_dir_exists,
                'message': f"ComfyUI输入目录: {'存在' if input_dir_exists else '不存在'}",
                'details': {
                    'input_dir': downloader.input_dir,
                    'input_dir_exists': input_dir_exists,
                    'distributed_dir': distributed_dir,
                    'distributed_dir_exists': distributed_dir_exists,
                    'master_token_configured': bool(downloader.master_token)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'文件下载器测试失败: {str(e)}',
                'error': str(e)
            }
    
    async def test_task_file_processing(self) -> Dict[str, Any]:
        """测试任务文件处理"""
        try:
            from ..services.file_scenario_adapter import get_file_scenario_adapter
            adapter = get_file_scenario_adapter()
            
            # 模拟任务数据
            mock_task_data = {
                'task_id': 'test-task-123',
                'task_type': 'image_to_video',
                'image': 'test/sample.jpg'
            }
            
            # 测试文件下载信息准备
            updated_task_data = await adapter.handle_image_upload_to_node(mock_task_data, 'test-node')
            
            has_download_info = 'image_download_info' in updated_task_data
            
            return {
                'success': True,  # 这个测试主要检查是否能正常运行
                'message': f"任务文件处理: {'包含下载信息' if has_download_info else '无下载信息'}",
                'details': {
                    'has_download_info': has_download_info,
                    'download_info': updated_task_data.get('image_download_info', {}),
                    'original_image_path': mock_task_data.get('image'),
                    'updated_task_keys': list(updated_task_data.keys())
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'任务文件处理测试失败: {str(e)}',
                'error': str(e)
            }
    
    def generate_test_report(self, results: Dict[str, Any]):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get('success', False))
        
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {total_tests - passed_tests}")
        print(f"成功率: {(passed_tests / total_tests * 100):.1f}%")
        
        print("\n详细结果:")
        for test_name, result in results.items():
            status = "✓" if result.get('success', False) else "✗"
            print(f"  {status} {test_name}: {result.get('message', '')}")


async def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    test_suite = DistributedFileTestSuite()
    results = await test_suite.run_all_tests()
    
    # 返回结果
    return results


if __name__ == "__main__":
    asyncio.run(main())
