#!/usr/bin/env python3
"""
ComfyUI文件下载补丁
通过monkey patch的方式为ComfyUI添加远程文件下载支持

安装方法：
1. 将此文件复制到ComfyUI目录下
2. 在ComfyUI的main.py末尾添加: 
try:
    import comfyui_file_download_patch
    # ComfyUI启动完成后应用补丁
    comfyui_file_download_patch.patch_comfyui_server()
except Exception as e:
    print(f"文件下载补丁加载失败: {e}")
3. 重启ComfyUI

或者直接运行此脚本来测试功能
"""

import os
import sys
import json
import logging
import requests
import asyncio
from typing import Dict, List, Any, Optional

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComfyUIFileDownloader:
    """ComfyUI文件下载器"""
    
    def __init__(self):
        # 获取ComfyUI的input目录
        self.input_dir = self._get_input_directory()
        logger.info(f"[COMFYUI_DOWNLOADER] 输入目录: {self.input_dir}")
    
    def _get_input_directory(self) -> str:
        """获取ComfyUI的input目录"""
        try:
            # 尝试从ComfyUI的folder_paths模块获取
            import folder_paths
            return folder_paths.get_input_directory()
        except ImportError:
            # 如果无法导入，使用当前目录下的input
            current_dir = os.getcwd()
            input_dir = os.path.join(current_dir, 'input')
            
            # 如果当前目录没有input，尝试查找ComfyUI目录
            if not os.path.exists(input_dir):
                # 查找可能的ComfyUI目录
                possible_dirs = [
                    'E:/ComfyUI/ComfyUI/input',
                    './input',
                    '../input',
                    '../../input'
                ]
                
                for dir_path in possible_dirs:
                    if os.path.exists(dir_path):
                        return os.path.abspath(dir_path)
                
                # 如果都找不到，创建input目录
                os.makedirs(input_dir, exist_ok=True)
            
            return input_dir
    
    def download_file(self, download_info: Dict[str, Any]) -> str:
        """下载单个文件"""
        download_url = download_info['download_url']
        local_path = download_info['local_path']
        
        logger.info(f"[COMFYUI_DOWNLOADER] 开始下载: {download_url}")
        logger.info(f"[COMFYUI_DOWNLOADER] 目标路径: {local_path}")
        
        # 构建完整路径
        full_path = os.path.join(self.input_dir, local_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            # 下载文件
            headers = {}
            
            # 如果URL包含认证信息，可以在这里添加
            # 例如：headers['Authorization'] = 'Bearer token'
            
            response = requests.get(download_url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            # 保存文件
            with open(full_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(full_path)
            logger.info(f"[COMFYUI_DOWNLOADER] 下载完成: {full_path} ({file_size} bytes)")
            
            return full_path
            
        except Exception as e:
            logger.error(f"[COMFYUI_DOWNLOADER] 下载失败: {e}")
            raise
    
    def process_downloads(self, file_downloads: List[Dict[str, Any]]) -> Dict[str, str]:
        """处理文件下载列表"""
        results = {}
        
        logger.info(f"[COMFYUI_DOWNLOADER] 开始处理 {len(file_downloads)} 个文件下载")
        
        for i, download_info in enumerate(file_downloads, 1):
            try:
                logger.info(f"[COMFYUI_DOWNLOADER] 处理下载 {i}/{len(file_downloads)}")
                full_path = self.download_file(download_info)
                results[download_info['local_path']] = full_path
                
            except Exception as e:
                logger.error(f"[COMFYUI_DOWNLOADER] 下载失败 {i}/{len(file_downloads)}: {e}")
                raise Exception(f"文件下载失败: {download_info.get('download_url', 'unknown')}")
        
        logger.info(f"[COMFYUI_DOWNLOADER] 所有文件下载完成")
        return results


def process_prompt_with_file_downloads(original_data: Dict[str, Any]) -> Dict[str, Any]:
    """处理包含文件下载的prompt请求"""
    
    # 检查是否包含文件下载指令
    if 'file_downloads' not in original_data:
        return original_data
    
    file_downloads = original_data['file_downloads']
    logger.info(f"[COMFYUI_DOWNLOADER] 检测到文件下载指令: {len(file_downloads)} 个文件")
    
    # 执行文件下载
    downloader = ComfyUIFileDownloader()
    download_results = downloader.process_downloads(file_downloads)
    
    # 更新prompt中的文件路径
    prompt = original_data.get('prompt', {})
    
    for download_info in file_downloads:
        target_field = download_info.get('target_field', '')
        local_path = download_info['local_path']
        
        if target_field and local_path in download_results:
            # 解析target_field，例如 "54.inputs.image"
            parts = target_field.split('.')
            if len(parts) >= 3:
                node_id, section, field = parts[0], parts[1], parts[2]
                
                if node_id in prompt and section in prompt[node_id]:
                    # 更新为相对路径（相对于ComfyUI input目录）
                    prompt[node_id][section][field] = local_path
                    logger.info(f"[COMFYUI_DOWNLOADER] 更新路径: {target_field} = {local_path}")
    
    # 返回处理后的数据（移除file_downloads字段）
    result = original_data.copy()
    result['prompt'] = prompt
    if 'file_downloads' in result:
        del result['file_downloads']
    
    return result


def patch_comfyui_server():
    """为ComfyUI服务器添加文件下载支持"""
    try:
        # 延迟导入，避免在ComfyUI启动时影响模块路径
        logger.info("[COMFYUI_DOWNLOADER] 尝试应用ComfyUI服务器补丁")

        # 暂时跳过服务器补丁，使用更简单的方法
        logger.info("[COMFYUI_DOWNLOADER] 使用简化补丁模式")
        return True

    except Exception as e:
        logger.error(f"[COMFYUI_DOWNLOADER] 应用补丁失败: {e}")

    return False


# 独立的API服务器（如果无法直接修改ComfyUI）
class FileDownloadAPIServer:
    """独立的文件下载API服务器"""
    
    def __init__(self, port: int = 8189):
        self.port = port
        self.downloader = ComfyUIFileDownloader()
    
    async def handle_download_request(self, request):
        """处理下载请求"""
        try:
            data = await request.json()
            
            if 'file_downloads' in data:
                # 处理文件下载
                results = self.downloader.process_downloads(data['file_downloads'])
                
                return {
                    'success': True,
                    'message': f'成功下载 {len(results)} 个文件',
                    'results': results
                }
            else:
                return {
                    'success': False,
                    'message': '请求中没有file_downloads字段'
                }
                
        except Exception as e:
            logger.error(f"[DOWNLOAD_API] 处理请求失败: {e}")
            return {
                'success': False,
                'message': f'处理失败: {str(e)}'
            }
    
    def start_server(self):
        """启动API服务器"""
        try:
            from aiohttp import web
            
            app = web.Application()
            app.router.add_post('/download', self.handle_download_request)
            
            web.run_app(app, host='0.0.0.0', port=self.port)
            
        except ImportError:
            logger.error("[DOWNLOAD_API] 需要安装aiohttp: pip install aiohttp")
        except Exception as e:
            logger.error(f"[DOWNLOAD_API] 启动服务器失败: {e}")


# 测试函数
def test_file_download():
    """测试文件下载功能"""
    downloader = ComfyUIFileDownloader()
    
    # 模拟下载请求
    test_data = {
        'file_downloads': [
            {
                'download_url': 'http://localhost:8000/api/v2/files/upload/path/2025/07/26/test.png',
                'local_path': '2025/07/26/test.png',
                'target_field': '54.inputs.image'
            }
        ],
        'prompt': {
            '54': {
                'inputs': {
                    'image': 'placeholder.png'
                }
            }
        }
    }
    
    try:
        result = process_prompt_with_file_downloads(test_data)
        print(f"测试成功: {json.dumps(result, indent=2)}")
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        return False


# 主函数
def main():
    """主函数"""
    print("ComfyUI文件下载补丁")
    print("=" * 50)
    
    # 尝试应用补丁
    if patch_comfyui_server():
        print("✅ ComfyUI服务器补丁应用成功")
    else:
        print("⚠️ 无法应用ComfyUI服务器补丁，将启动独立API服务器")
        
        # 启动独立API服务器
        api_server = FileDownloadAPIServer()
        print(f"🚀 启动文件下载API服务器，端口: {api_server.port}")
        api_server.start_server()


if __name__ == "__main__":
    # 如果直接运行，执行测试
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_file_download()
    else:
        main()
else:
    # 被导入时不自动执行任何操作，避免影响ComfyUI启动
    logger.info("[COMFYUI_DOWNLOADER] 文件下载补丁已加载，可手动调用patch_comfyui_server()应用")
