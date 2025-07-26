#!/usr/bin/env python3
"""
统一分布式文件服务
处理主机和从机之间的文件传输、代理和管理
"""

import os
import asyncio
import aiohttp
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List, AsyncIterator
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, Response, FileResponse
import logging

logger = logging.getLogger(__name__)


class FileLocation:
    """文件位置枚举"""
    LOCAL = "local"
    NODE = "node"
    MASTER = "master"


class FileTransferService:
    """文件传输核心服务"""
    
    def __init__(self, timeout: int = 30, retry_count: int = 3, chunk_size: int = 8192):
        self.timeout = timeout
        self.retry_count = retry_count
        self.chunk_size = chunk_size
    
    async def download_file(self, url: str, local_path: str = None, 
                           headers: Dict[str, str] = None) -> str:
        """下载文件到本地"""
        headers = headers or {}
        
        logger.info(f"[FILE_TRANSFER] 开始下载文件: {url}")
        
        for attempt in range(self.retry_count + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.get(url, headers=headers) as response:
                        response.raise_for_status()
                        
                        # 确保目录存在
                        if local_path:
                            os.makedirs(os.path.dirname(local_path), exist_ok=True)
                            
                            with open(local_path, 'wb') as f:
                                async for chunk in response.content.iter_chunked(self.chunk_size):
                                    f.write(chunk)
                            
                            logger.info(f"[FILE_TRANSFER] 文件下载成功: {local_path}")
                            return local_path
                        else:
                            content = await response.read()
                            logger.info(f"[FILE_TRANSFER] 文件内容获取成功: {len(content)} bytes")
                            return content
                            
            except Exception as e:
                if attempt < self.retry_count:
                    logger.warning(f"[FILE_TRANSFER] 下载失败，重试 {attempt + 1}/{self.retry_count}: {e}")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                else:
                    logger.error(f"[FILE_TRANSFER] 下载失败，已达最大重试次数: {e}")
                    raise
    
    async def stream_file(self, url: str, headers: Dict[str, str] = None) -> AsyncIterator[bytes]:
        """流式获取文件内容"""
        headers = headers or {}
        
        logger.info(f"[FILE_TRANSFER] 开始流式获取文件: {url}")
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    
                    async for chunk in response.content.iter_chunked(self.chunk_size):
                        yield chunk
                        
        except Exception as e:
            logger.error(f"[FILE_TRANSFER] 流式获取失败: {e}")
            raise
    
    def sync_get_file(self, url: str, headers: Dict[str, str] = None) -> Response:
        """同步获取文件（用于兼容现有代码）"""
        headers = headers or {}
        
        logger.info(f"[FILE_TRANSFER] 同步获取文件: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            content = response.content
            content_type = response.headers.get('content-type', 'application/octet-stream')
            
            logger.info(f"[FILE_TRANSFER] 同步获取成功: {len(content)} bytes, 类型: {content_type}")
            
            return Response(
                content=content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"inline; filename={os.path.basename(url)}"
                }
            )
            
        except Exception as e:
            logger.error(f"[FILE_TRANSFER] 同步获取失败: {e}")
            raise


class NodeManager:
    """节点管理器"""
    
    def __init__(self):
        self._nodes_cache = None
        self._cache_time = 0
        self._cache_ttl = 30  # 30秒缓存
    
    def get_online_nodes(self) -> List[Dict[str, Any]]:
        """获取在线节点列表"""
        import time
        current_time = time.time()

        # 检查缓存
        if self._nodes_cache and (current_time - self._cache_time) < self._cache_ttl:
            return self._nodes_cache

        try:
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()

            online_nodes = []

            # 检查是否为分布式模式
            if config_manager.is_distributed_mode():
                # 分布式模式：从节点管理器获取节点
                try:
                    from ..core.node_manager import get_node_manager
                    node_manager = get_node_manager()
                    nodes_dict = node_manager.get_all_nodes()

                    for node in nodes_dict.values():
                        if hasattr(node, 'status') and node.status.value == 'online':
                            online_nodes.append({
                                'node_id': node.node_id,
                                'url': node.url,
                                'status': node.status.value
                            })

                except Exception as e:
                    logger.warning(f"[NODE_MANAGER] 从节点管理器获取节点失败: {e}")

            else:
                # 单机模式：检查本地ComfyUI是否可用
                try:
                    comfyui_config = config_manager.get_comfyui_config()
                    comfyui_url = comfyui_config.get('url', 'http://127.0.0.1:8188')

                    # 简单的健康检查
                    import requests
                    response = requests.get(f"{comfyui_url}/system_stats", timeout=5)
                    if response.status_code == 200:
                        online_nodes.append({
                            'node_id': 'local',
                            'url': comfyui_url,
                            'status': 'online'
                        })

                except Exception as e:
                    logger.warning(f"[NODE_MANAGER] 本地ComfyUI健康检查失败: {e}")

            # 更新缓存
            self._nodes_cache = online_nodes
            self._cache_time = current_time

            logger.info(f"[NODE_MANAGER] 获取到 {len(online_nodes)} 个在线节点")
            for node in online_nodes:
                logger.info(f"[NODE_MANAGER] 节点: {node['node_id']} - {node['url']} ({node['status']})")

            return online_nodes

        except Exception as e:
            logger.error(f"[NODE_MANAGER] 获取节点列表失败: {e}")
            import traceback
            logger.error(f"[NODE_MANAGER] 错误堆栈: {traceback.format_exc()}")
            return []
    
    def find_node_for_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """为文件查找合适的节点"""
        online_nodes = self.get_online_nodes()
        
        # 简单策略：返回第一个在线节点
        # 后续可以根据负载、文件位置等优化
        if online_nodes:
            selected_node = online_nodes[0]
            logger.info(f"[NODE_MANAGER] 为文件 {file_path} 选择节点: {selected_node['node_id']}")
            return selected_node
        
        logger.warning(f"[NODE_MANAGER] 没有找到可用节点处理文件: {file_path}")
        return None


class DistributedFileService:
    """统一分布式文件服务"""
    
    def __init__(self):
        self.transfer_service = FileTransferService()
        self.node_manager = NodeManager()
    
    def check_local_file(self, file_path: str, base_dir: str = None) -> Optional[str]:
        """检查本地文件是否存在"""
        if base_dir is None:
            from ..utils.path_utils import get_output_dir
            base_dir = get_output_dir()

        # 清理文件路径，移除可能的API路径前缀
        clean_file_path = file_path
        if clean_file_path.startswith('upload/path/'):
            clean_file_path = clean_file_path[12:]  # 移除 'upload/path/' 前缀

        full_path = os.path.join(base_dir, clean_file_path)

        # 安全检查
        from ..utils.path_utils import is_safe_path
        if not is_safe_path(full_path, base_dir):
            logger.warning(f"[DISTRIBUTED_FILE] 不安全的文件路径: {clean_file_path}")
            return None

        if os.path.exists(full_path):
            logger.info(f"[DISTRIBUTED_FILE] 本地文件存在: {full_path}")
            return full_path

        # logger.info(f"[DISTRIBUTED_FILE] 本地文件不存在: {full_path}")
        return None
    
    async def proxy_from_node(self, file_path: str, node_info: Dict[str, Any] = None) -> Response:
        """从节点代理获取文件（文生图/图生视频场景）"""
        # logger.info(f"[DISTRIBUTED_FILE] 开始代理获取文件: {file_path}")
        
        # 如果没有指定节点，自动查找
        if node_info is None:
            node_info = self.node_manager.find_node_for_file(file_path)
            if not node_info:
                raise HTTPException(status_code=404, detail="没有可用的节点")
        
        try:
            # 构建节点文件URL
            node_url = f"{node_info['url']}/view"
            params = {"filename": os.path.basename(file_path)}
            
            # 处理子目录
            if '/' in file_path or '\\' in file_path:
                subfolder = os.path.dirname(file_path)
                params["subfolder"] = subfolder
                # logger.debug(f"[DISTRIBUTED_FILE] 从节点获取文件: filename={params['filename']}, subfolder='{subfolder}'")
            else:
                logger.debug(f"[DISTRIBUTED_FILE] 从节点获取文件: filename={params['filename']}, 无子目录")

            # 构建完整URL
            import urllib.parse
            query_string = urllib.parse.urlencode(params)
            full_url = f"{node_url}?{query_string}"
            
            # 使用同步方式获取（兼容现有逻辑）
            response = self.transfer_service.sync_get_file(full_url)
            
            # logger.info(f"[DISTRIBUTED_FILE] 成功从节点 {node_info['node_id']} 代理文件: {file_path}")
            return response
            
        except Exception as e:
            # logger.error(f"[DISTRIBUTED_FILE] 从节点 {node_info['node_id']} 代理文件失败: {e}")
            raise HTTPException(status_code=404, detail=f"无法从节点获取文件: {str(e)}")
    
    async def get_output_file(self, file_path: str) -> Response:
        """获取输出文件（统一入口）"""
        # logger.info(f"[DISTRIBUTED_FILE] 获取输出文件请求: {file_path}")

        # 1. 首先检查本地文件
        local_file_path = self.check_local_file(file_path)
        if local_file_path:
            logger.info(f"[DISTRIBUTED_FILE] 返回本地文件: {local_file_path}")
            return FileResponse(local_file_path)

        # 2. 本地文件不存在，尝试从节点代理获取
        # logger.info(f"[DISTRIBUTED_FILE] 本地文件不存在，尝试从节点获取: {file_path}")

        # 尝试所有在线节点
        online_nodes = self.node_manager.get_online_nodes()

        if not online_nodes:
            # logger.warning(f"[DISTRIBUTED_FILE] 没有可用的在线节点")
            # 尝试回退到原始输出目录检查
            return await self._fallback_local_check(file_path)

        for node in online_nodes:
            try:
                response = await self.proxy_from_node(file_path, node)
                logger.info(f"[DISTRIBUTED_FILE] 成功从节点 {node['node_id']} 获取文件: {file_path}")
                return response

            except Exception as e:
                logger.warning(f"[DISTRIBUTED_FILE] 从节点 {node['node_id']} 获取文件失败: {e}")
                continue

        # 所有节点都失败，尝试回退检查
        logger.warning(f"[DISTRIBUTED_FILE] 所有节点都无法提供文件，尝试回退检查: {file_path}")
        return await self._fallback_local_check(file_path)

    async def get_upload_file(self, file_path: str, file_id: str = None) -> Response:
        """获取上传文件（用于从机下载主机上传的文件）"""
        logger.info(f"[DISTRIBUTED_FILE] 获取上传文件请求: {file_path}, file_id: {file_id}")

        # 1. 检查上传目录中的本地文件
        local_file_path = self.check_local_file(file_path, self._get_upload_base_dir())
        if local_file_path:
            logger.info(f"[DISTRIBUTED_FILE] 返回本地上传文件: {local_file_path}")
            return FileResponse(local_file_path)

        # 2. 如果有file_id，尝试通过文件服务获取
        if file_id:
            try:
                from ..services.file_service import get_file_service
                file_service = get_file_service()
                file_info = file_service.get_file_info(file_id)

                if file_info and os.path.exists(file_info['file_path']):
                    # logger.info(f"[DISTRIBUTED_FILE] 通过file_id找到上传文件: {file_info['file_path']}")
                    return FileResponse(file_info['file_path'])

            except Exception as e:
                logger.warning(f"[DISTRIBUTED_FILE] 通过file_id获取文件失败: {e}")

        # 3. 尝试在上传目录的不同位置查找
        return await self._fallback_upload_check(file_path)

    def _get_upload_base_dir(self) -> str:
        """获取上传文件基础目录"""
        from ..utils.path_utils import get_upload_dir
        return get_upload_dir()

    async def _fallback_upload_check(self, file_path: str) -> Response:
        """回退检查上传文件"""
        try:
            # 清理文件路径，移除可能的API路径前缀
            clean_file_path = file_path
            if clean_file_path.startswith('upload/path/'):
                clean_file_path = clean_file_path[12:]  # 移除 'upload/path/' 前缀

            # 标准化文件路径
            normalized_file_path = clean_file_path.replace('\\', '/').replace('/', os.sep)

            # 可能的上传目录
            from ..utils.path_utils import get_project_root
            project_root = get_project_root()

            possible_dirs = [
                self._get_upload_base_dir(),
                os.path.join(project_root, 'uploads'),
                os.path.join(project_root, 'backend', 'uploads')
            ]

            logger.info(f"[DISTRIBUTED_FILE] 回退检查上传文件: {file_path} -> 清理后: {clean_file_path}")

            for upload_dir in possible_dirs:
                if os.path.exists(upload_dir):
                    # 尝试清理后的路径
                    full_path = os.path.join(upload_dir, clean_file_path)
                    if os.path.exists(full_path):
                        logger.info(f"[DISTRIBUTED_FILE] 回退检查找到上传文件: {full_path}")
                        return FileResponse(full_path)

                    # 尝试标准化路径
                    full_path_normalized = os.path.join(upload_dir, normalized_file_path)
                    if os.path.exists(full_path_normalized):
                        logger.info(f"[DISTRIBUTED_FILE] 回退检查找到上传文件(标准化): {full_path_normalized}")
                        return FileResponse(full_path_normalized)

                    # 尝试原始路径（兼容性）
                    full_path_original = os.path.join(upload_dir, file_path)
                    if os.path.exists(full_path_original):
                        logger.info(f"[DISTRIBUTED_FILE] 回退检查找到上传文件(原始): {full_path_original}")
                        return FileResponse(full_path_original)

            # 所有尝试都失败
            logger.error(f"[DISTRIBUTED_FILE] 回退检查也无法找到上传文件: {file_path}")
            logger.error(f"[DISTRIBUTED_FILE] 已检查的目录: {possible_dirs}")
            logger.error(f"[DISTRIBUTED_FILE] 清理后的路径: {clean_file_path}")
            raise HTTPException(status_code=404, detail=f"上传文件不存在: {clean_file_path}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[DISTRIBUTED_FILE] 上传文件回退检查异常: {e}")
            import traceback
            logger.error(f"[DISTRIBUTED_FILE] 错误堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"上传文件获取失败: {str(e)}")

    async def _fallback_local_check(self, file_path: str) -> Response:
        """回退到本地文件检查"""
        try:
            # 标准化文件路径（处理Windows和Linux路径分隔符）
            normalized_file_path = file_path.replace('\\', '/').replace('/', os.sep)

            # 尝试在项目的outputs目录中查找
            from ..utils.path_utils import get_project_root
            project_root = get_project_root()

            # 可能的输出目录
            possible_dirs = [
                os.path.join(project_root, 'outputs'),
                os.path.join(project_root, 'backend', 'outputs'),
                os.path.join(project_root, 'ComfyUI', 'output'),
                'E:/ComfyUI/ComfyUI/output',  # 用户的ComfyUI路径
                'E:\\ComfyUI\\ComfyUI\\output'  # Windows路径格式
            ]

            logger.info(f"[DISTRIBUTED_FILE] 回退检查文件: {file_path} (标准化: {normalized_file_path})")

            for output_dir in possible_dirs:
                if os.path.exists(output_dir):
                    # 尝试原始路径
                    full_path = os.path.join(output_dir, file_path)
                    if os.path.exists(full_path):
                        logger.info(f"[DISTRIBUTED_FILE] 回退检查找到文件: {full_path}")
                        return FileResponse(full_path)

                    # 尝试标准化路径
                    full_path_normalized = os.path.join(output_dir, normalized_file_path)
                    if os.path.exists(full_path_normalized):
                        logger.info(f"[DISTRIBUTED_FILE] 回退检查找到文件(标准化): {full_path_normalized}")
                        return FileResponse(full_path_normalized)

                    logger.debug(f"[DISTRIBUTED_FILE] 检查目录 {output_dir}: 文件不存在")
                else:
                    logger.debug(f"[DISTRIBUTED_FILE] 目录不存在: {output_dir}")

            # 所有尝试都失败
            logger.error(f"[DISTRIBUTED_FILE] 回退检查也无法找到文件: {file_path}")
            logger.error(f"[DISTRIBUTED_FILE] 已检查的目录: {possible_dirs}")
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[DISTRIBUTED_FILE] 回退检查异常: {e}")
            import traceback
            logger.error(f"[DISTRIBUTED_FILE] 错误堆栈: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"文件获取失败: {str(e)}")


# 全局服务实例
_distributed_file_service = None


def get_distributed_file_service() -> DistributedFileService:
    """获取分布式文件服务实例"""
    global _distributed_file_service
    if _distributed_file_service is None:
        _distributed_file_service = DistributedFileService()
    return _distributed_file_service


def diagnose_file_service() -> Dict[str, Any]:
    """诊断分布式文件服务状态"""
    service = get_distributed_file_service()

    diagnosis = {
        'timestamp': datetime.now().isoformat(),
        'service_status': 'initialized',
        'nodes': [],
        'config': {},
        'directories': {}
    }

    try:
        # 检查节点状态
        online_nodes = service.node_manager.get_online_nodes()
        diagnosis['nodes'] = online_nodes
        diagnosis['node_count'] = len(online_nodes)

        # 检查配置
        from ..core.config_manager import get_config_manager
        config_manager = get_config_manager()
        diagnosis['config'] = {
            'distributed_mode': config_manager.is_distributed_mode(),
            'comfyui_config': config_manager.get_comfyui_config()
        }

        # 检查目录
        from ..utils.path_utils import get_output_dir, get_upload_dir, get_project_root
        diagnosis['directories'] = {
            'project_root': get_project_root(),
            'output_dir': get_output_dir(),
            'upload_dir': get_upload_dir(),
            'output_dir_exists': os.path.exists(get_output_dir()),
            'upload_dir_exists': os.path.exists(get_upload_dir())
        }

        diagnosis['status'] = 'healthy'

    except Exception as e:
        diagnosis['status'] = 'error'
        diagnosis['error'] = str(e)
        logger.error(f"[DIAGNOSIS] 诊断失败: {e}")

    return diagnosis
