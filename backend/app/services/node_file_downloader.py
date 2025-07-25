#!/usr/bin/env python3
"""
从机文件下载器
负责从主机下载上传的文件到从机本地
"""

import os
import requests
import time
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class NodeFileDownloader:
    """从机文件下载器"""
    
    def __init__(self, comfyui_input_dir: str, master_token: str = None):
        self.input_dir = comfyui_input_dir
        self.master_token = master_token
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 2
    
    def download_file(self, download_info: Dict[str, Any]) -> str:
        """下载文件到本地"""
        try:
            file_id = download_info.get('file_id')
            download_url = download_info['download_url']
            local_path = download_info['local_path']
            expected_size = download_info.get('file_size', 0)
            filename = download_info.get('filename', os.path.basename(local_path))

            logger.info(f"[NODE_DOWNLOADER] 开始下载文件: {download_url}")
            logger.info(f"[NODE_DOWNLOADER] 目标路径: {local_path}")
            logger.info(f"[NODE_DOWNLOADER] 输入目录: {self.input_dir}")

            # 构建本地完整路径
            local_full_path = os.path.join(self.input_dir, local_path)

            # 确保目录存在
            local_dir = os.path.dirname(local_full_path)
            os.makedirs(local_dir, exist_ok=True)
            logger.info(f"[NODE_DOWNLOADER] 完整路径: {local_full_path}")
            logger.info(f"[NODE_DOWNLOADER] 目录创建: {local_dir}")
            
            # 检查文件是否已存在且大小正确
            if os.path.exists(local_full_path):
                actual_size = os.path.getsize(local_full_path)
                if expected_size > 0 and actual_size == expected_size:
                    logger.info(f"[NODE_DOWNLOADER] 文件已存在，跳过下载: {local_path}")
                    return local_full_path
                else:
                    logger.info(f"[NODE_DOWNLOADER] 文件存在但大小不匹配，重新下载: {local_path}")
            
            # 下载文件（带重试）
            for attempt in range(self.max_retries + 1):
                try:
                    success = self._download_with_retry(download_url, local_full_path, expected_size)
                    if success:
                        logger.info(f"[NODE_DOWNLOADER] 文件下载成功: {local_path}")
                        return local_full_path
                        
                except Exception as e:
                    if attempt < self.max_retries:
                        logger.warning(f"[NODE_DOWNLOADER] 下载失败，重试 {attempt + 1}/{self.max_retries}: {e}")
                        time.sleep(self.retry_delay * (2 ** attempt))  # 指数退避
                    else:
                        logger.error(f"[NODE_DOWNLOADER] 下载失败，已达最大重试次数: {e}")
                        raise
            
            raise Exception("下载失败，已达最大重试次数")
            
        except Exception as e:
            logger.error(f"[NODE_DOWNLOADER] 文件下载失败: {e}")
            raise
    
    def _download_with_retry(self, download_url: str, local_path: str, expected_size: int) -> bool:
        """执行实际的文件下载"""
        headers = {}
        if self.master_token:
            headers['Authorization'] = f'Bearer {self.master_token}'
        
        logger.debug(f"[NODE_DOWNLOADER] 请求URL: {download_url}")
        
        response = requests.get(download_url, headers=headers, stream=True, timeout=self.timeout)
        response.raise_for_status()
        
        # 流式下载
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # 验证文件大小
        actual_size = os.path.getsize(local_path)
        if expected_size > 0 and actual_size != expected_size:
            os.remove(local_path)
            raise Exception(f"文件大小不匹配: 期望{expected_size}, 实际{actual_size}")
        
        logger.debug(f"[NODE_DOWNLOADER] 文件下载完成: {local_path} ({actual_size} bytes)")
        return True
    
    def download_multiple_files(self, download_infos: List[Dict[str, Any]]) -> List[str]:
        """批量下载多个文件"""
        downloaded_files = []
        
        for download_info in download_infos:
            try:
                local_path = self.download_file(download_info)
                downloaded_files.append(local_path)
                
            except Exception as e:
                logger.error(f"[NODE_DOWNLOADER] 批量下载中的文件失败: {e}")
                # 清理已下载的文件
                self.cleanup_files(downloaded_files)
                raise
        
        return downloaded_files
    
    def cleanup_files(self, file_paths: List[str]):
        """清理文件"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"[NODE_DOWNLOADER] 已清理文件: {file_path}")
            except Exception as e:
                logger.warning(f"[NODE_DOWNLOADER] 清理文件失败: {file_path}, 错误: {e}")
    
    def check_master_connectivity(self, master_host: str) -> bool:
        """检查与主机的连接性"""
        try:
            test_url = f"{master_host}/api/v2/health"
            headers = {}
            if self.master_token:
                headers['Authorization'] = f'Bearer {self.master_token}'
            
            response = requests.get(test_url, headers=headers, timeout=5)
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"[NODE_DOWNLOADER] 主机连接检查失败: {e}")
            return False


class TaskFileProcessor:
    """任务文件处理器"""
    
    def __init__(self, downloader: NodeFileDownloader):
        self.downloader = downloader
    
    def process_task_files(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务中的文件下载"""
        logger.info(f"[TASK_FILE_PROCESSOR] 开始处理任务文件: {task_data.get('task_id')}")

        downloaded_files = []

        try:
            # 检查是否有图片下载信息
            if 'image_download_info' in task_data:
                download_info = task_data['image_download_info']
                logger.info(f"[TASK_FILE_PROCESSOR] 发现图片下载信息: {download_info['download_url']}")

                # 下载图片文件
                local_file_path = self.downloader.download_file(download_info)
                downloaded_files.append(local_file_path)

                # 更新任务数据中的图片路径为下载后的完整路径
                # 这样ComfyUI就能找到正确的文件
                task_data['image'] = local_file_path
                logger.info(f"[TASK_FILE_PROCESSOR] 图片路径已更新为完整路径: {local_file_path}")

                # 同时保留原始相对路径信息
                task_data['image_relative_path'] = download_info['local_path']
                logger.info(f"[TASK_FILE_PROCESSOR] 保留相对路径: {download_info['local_path']}")

            # 可以扩展处理其他类型的文件下载
            # 例如：模型文件、配置文件等

            # 将下载的文件列表添加到任务数据中，用于后续清理
            task_data['_downloaded_files'] = downloaded_files

            logger.info(f"[TASK_FILE_PROCESSOR] 任务文件处理完成: {len(downloaded_files)} 个文件")
            return task_data

        except Exception as e:
            logger.error(f"[TASK_FILE_PROCESSOR] 任务文件处理失败: {e}")
            # 清理已下载的文件
            self.downloader.cleanup_files(downloaded_files)
            raise
    
    def cleanup_task_files(self, task_data: Dict[str, Any]):
        """清理任务相关的下载文件"""
        downloaded_files = task_data.get('_downloaded_files', [])
        if downloaded_files:
            logger.info(f"[TASK_FILE_PROCESSOR] 开始清理任务文件: {len(downloaded_files)} 个文件")
            self.downloader.cleanup_files(downloaded_files)


def get_node_file_downloader(comfyui_input_dir: str = None, master_token: str = None) -> NodeFileDownloader:
    """获取从机文件下载器实例"""
    if comfyui_input_dir is None:
        # 尝试从配置中获取ComfyUI输入目录
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()
            comfyui_config = config_manager.get_comfyui_config()

            # 获取ComfyUI安装路径
            comfyui_path = comfyui_config.get('path', 'E:/ComfyUI/ComfyUI')
            comfyui_input_dir = os.path.join(comfyui_path, 'input')

            logger.info(f"[NODE_DOWNLOADER] 使用ComfyUI输入目录: {comfyui_input_dir}")

        except Exception as e:
            logger.warning(f"[NODE_DOWNLOADER] 无法从配置获取ComfyUI路径: {e}")
            # 回退到默认路径
            comfyui_input_dir = 'E:/ComfyUI/ComfyUI/input'
            logger.info(f"[NODE_DOWNLOADER] 使用默认ComfyUI输入目录: {comfyui_input_dir}")

    # 确保输入目录存在
    os.makedirs(comfyui_input_dir, exist_ok=True)

    if master_token is None:
        # 从配置中获取令牌
        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()
            master_token = config_manager.get_config('node.master_token')
        except Exception:
            logger.warning("无法获取主机令牌，将使用无认证模式")

    return NodeFileDownloader(comfyui_input_dir, master_token)


def get_task_file_processor(comfyui_input_dir: str = None, master_token: str = None) -> TaskFileProcessor:
    """获取任务文件处理器实例"""
    downloader = get_node_file_downloader(comfyui_input_dir, master_token)
    return TaskFileProcessor(downloader)
