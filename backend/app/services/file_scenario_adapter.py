#!/usr/bin/env python3
"""
文件场景适配器
为不同的文件使用场景提供统一的接口适配
"""

import os
import logging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException
from fastapi.responses import Response

from .distributed_file_service import get_distributed_file_service, DistributedFileService

logger = logging.getLogger(__name__)


class FileScenarioAdapter:
    """文件场景适配器"""
    
    def __init__(self, distributed_service: DistributedFileService = None):
        self.service = distributed_service or get_distributed_file_service()
    
    async def handle_text_to_image_output(self, file_path: str) -> Response:
        """处理文生图输出获取场景"""
        logger.info(f"[SCENARIO_ADAPTER] 处理文生图输出: {file_path}")
        
        try:
            # 使用分布式文件服务获取文件
            response = await self.service.get_output_file(file_path)
            
            # 添加适合图片的响应头
            if hasattr(response, 'headers'):
                # 检查文件扩展名，设置合适的Content-Type
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in ['.jpg', '.jpeg']:
                    response.media_type = 'image/jpeg'
                elif file_ext in ['.png']:
                    response.media_type = 'image/png'
                elif file_ext in ['.webp']:
                    response.media_type = 'image/webp'
                elif file_ext in ['.gif']:
                    response.media_type = 'image/gif'
                
                # 设置缓存策略（图片可以缓存）
                response.headers.update({
                    'Cache-Control': 'public, max-age=3600',  # 1小时缓存
                    'Content-Disposition': f'inline; filename="{os.path.basename(file_path)}"'
                })
            
            logger.info(f"[SCENARIO_ADAPTER] 文生图输出处理成功: {file_path}")
            return response
            
        except Exception as e:
            logger.error(f"[SCENARIO_ADAPTER] 文生图输出处理失败: {file_path}, 错误: {e}")
            raise
    
    async def handle_image_to_video_output(self, file_path: str) -> Response:
        """处理图生视频输出获取场景"""
        logger.info(f"[SCENARIO_ADAPTER] 处理图生视频输出: {file_path}")
        
        try:
            # 使用分布式文件服务获取文件
            response = await self.service.get_output_file(file_path)
            
            # 添加适合视频的响应头
            if hasattr(response, 'headers'):
                # 检查文件扩展名，设置合适的Content-Type
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in ['.mp4']:
                    response.media_type = 'video/mp4'
                elif file_ext in ['.avi']:
                    response.media_type = 'video/avi'
                elif file_ext in ['.mov']:
                    response.media_type = 'video/quicktime'
                elif file_ext in ['.webm']:
                    response.media_type = 'video/webm'
                
                # 设置视频特定的响应头
                response.headers.update({
                    'Accept-Ranges': 'bytes',  # 支持断点续传
                    'Cache-Control': 'public, max-age=7200',  # 2小时缓存
                    'Content-Disposition': f'attachment; filename="{os.path.basename(file_path)}"'
                })
            
            logger.info(f"[SCENARIO_ADAPTER] 图生视频输出处理成功: {file_path}")
            return response
            
        except Exception as e:
            logger.error(f"[SCENARIO_ADAPTER] 图生视频输出处理失败: {file_path}, 错误: {e}")
            raise
    
    async def handle_task_file_download(self, task_id: str, file_index: int = 0) -> Response:
        """处理任务文件下载场景"""
        logger.info(f"[SCENARIO_ADAPTER] 处理任务文件下载: task_id={task_id}, index={file_index}")

        try:
            # 获取任务信息
            from ..database.task_status_manager import get_database_task_status_manager
            status_manager = get_database_task_status_manager()

            task_info = status_manager.get_task_status(task_id)
            if not task_info:
                raise HTTPException(status_code=404, detail="任务不存在")

            # 获取任务文件列表
            result_data = task_info.get('result_data', {})
            files = result_data.get('files', [])

            if not files:
                raise HTTPException(status_code=404, detail="任务没有生成文件")

            if file_index >= len(files):
                raise HTTPException(status_code=404, detail="文件索引超出范围")

            file_path = files[file_index]
            logger.info(f"[SCENARIO_ADAPTER] 任务 {task_id} 文件路径: {file_path}")

            # 根据任务类型选择处理方式
            task_type = task_info.get('task_type', '')

            if task_type == 'text_to_image':
                return await self.handle_text_to_image_output(file_path)
            elif task_type == 'image_to_video':
                return await self.handle_image_to_video_output(file_path)
            else:
                # 通用文件处理
                return await self.service.get_output_file(file_path)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[SCENARIO_ADAPTER] 任务文件下载失败: task_id={task_id}, 错误: {e}")
            raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

    async def handle_upload_file_download(self, file_path: str, file_id: str = None) -> Response:
        """处理上传文件下载场景（供从机使用）"""
        logger.info(f"[SCENARIO_ADAPTER] 处理上传文件下载: {file_path}, file_id: {file_id}")

        try:
            # 使用分布式文件服务获取上传文件
            response = await self.service.get_upload_file(file_path, file_id)

            # 添加适合上传文件的响应头
            if hasattr(response, 'headers'):
                # 检查文件扩展名，设置合适的Content-Type
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext in ['.jpg', '.jpeg']:
                    response.media_type = 'image/jpeg'
                elif file_ext in ['.png']:
                    response.media_type = 'image/png'
                elif file_ext in ['.webp']:
                    response.media_type = 'image/webp'

                # 设置上传文件特定的响应头
                response.headers.update({
                    'Cache-Control': 'public, max-age=1800',  # 30分钟缓存
                    'Content-Disposition': f'attachment; filename="{os.path.basename(file_path)}"'
                })

            logger.info(f"[SCENARIO_ADAPTER] 上传文件下载处理成功: {file_path}")
            return response

        except Exception as e:
            logger.error(f"[SCENARIO_ADAPTER] 上传文件下载处理失败: {file_path}, 错误: {e}")
            raise

    async def handle_image_upload_to_node(self, task_data: Dict[str, Any], target_node: str = None) -> Dict[str, Any]:
        """处理图片上传到从机场景"""
        logger.info(f"[SCENARIO_ADAPTER] 处理图片上传到从机: target_node={target_node}")

        try:
            # 检查任务数据中是否包含图片信息
            image_path = task_data.get('image')
            if not image_path:
                logger.info(f"[SCENARIO_ADAPTER] 任务不包含图片，无需下载")
                return task_data

            # 构建文件下载信息
            download_info = await self._prepare_file_download_info(image_path, task_data)

            if download_info:
                # 将下载信息添加到任务数据中
                task_data['image_download_info'] = download_info
                logger.info(f"[SCENARIO_ADAPTER] 已添加图片下载信息: {download_info['download_url']}")
            else:
                logger.error(f"[SCENARIO_ADAPTER] 文件下载信息准备失败，无法继续执行任务")
                raise Exception("文件下载信息准备失败")

            return task_data

        except Exception as e:
            logger.error(f"[SCENARIO_ADAPTER] 处理图片上传到从机失败: {e}")
            import traceback
            logger.error(f"[SCENARIO_ADAPTER] 错误堆栈: {traceback.format_exc()}")
            # 抛出异常，中止任务执行
            raise

    async def _prepare_file_download_info(self, file_path: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """准备文件下载信息"""
        try:
            # 获取文件信息
            from ..services.file_service import get_file_service
            file_service = get_file_service()

            # 尝试通过路径获取文件信息
            file_info = None

            # 如果任务数据中有file_id，优先使用
            if 'image_file_id' in task_data:
                file_info = file_service.get_file_info(task_data['image_file_id'])

            # 如果没有找到，尝试通过路径查找
            if not file_info:
                # 尝试通过文件路径查找文件信息
                try:
                    # 检查文件是否存在于uploads目录
                    from ..utils.path_utils import get_upload_dir
                    upload_dir = get_upload_dir()
                    full_file_path = os.path.join(upload_dir, file_path)

                    if os.path.exists(full_file_path):
                        # 构建基本文件信息
                        file_info = {
                            'file_id': None,
                            'file_path': full_file_path,
                            'file_size': os.path.getsize(full_file_path),
                            'filename': os.path.basename(file_path)
                        }
                        logger.info(f"[SCENARIO_ADAPTER] 通过路径找到文件: {full_file_path}")
                    else:
                        logger.warning(f"[SCENARIO_ADAPTER] 文件不存在: {full_file_path}")

                except Exception as e:
                    logger.warning(f"[SCENARIO_ADAPTER] 通过路径查找文件失败: {e}")

            # 构建下载URL
            from ..core.config_manager import get_config_manager
            config_manager = get_config_manager()

            # 获取主机地址 - 优先从分布式配置获取
            master_host = (
                config_manager.get_config('distributed.master_host') or
                config_manager.get_config('server.host') or
                'localhost'
            )
            master_port = (
                config_manager.get_config('distributed.master_port') or
                config_manager.get_config('server.port') or
                8000
            )

            # 构建下载URL
            if file_info and file_info.get('file_id'):
                download_url = f"http://{master_host}:{master_port}/api/v2/files/upload/{file_info['file_id']}"
            else:
                # 使用路径下载，确保路径格式正确
                normalized_path = file_path.replace('\\', '/')
                download_url = f"http://{master_host}:{master_port}/api/v2/files/upload/path/{normalized_path}"

            # 生成从机本地存储路径（保持时间分层结构）
            # 保持与主机相同的目录结构，例如：2025/07/26/140621_8b4dd229.png
            local_path = file_path  # 直接使用原始的相对路径结构
            local_filename = os.path.basename(file_path)  # 提取文件名

            download_info = {
                'file_id': file_info['file_id'] if file_info and file_info.get('file_id') else None,
                'download_url': download_url,
                'local_path': local_path,  # 相对于ComfyUI input目录的路径
                'filename': local_filename,
                'file_size': file_info['file_size'] if file_info else 0,
                'original_path': file_path  # 保留原始路径用于调试
            }

            logger.info(f"[SCENARIO_ADAPTER] 准备文件下载信息: {download_info}")
            return download_info

        except Exception as e:
            logger.error(f"[SCENARIO_ADAPTER] 准备文件下载信息失败: {e}")
            import traceback
            logger.error(f"[SCENARIO_ADAPTER] 错误堆栈: {traceback.format_exc()}")
            return None
    
    def get_file_type_from_path(self, file_path: str) -> str:
        """从文件路径判断文件类型"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
            return 'image'
        elif file_ext in ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.flv']:
            return 'video'
        elif file_ext in ['.mp3', '.wav', '.flac', '.aac']:
            return 'audio'
        else:
            return 'unknown'
    
    def is_output_file(self, file_path: str) -> bool:
        """判断是否为输出文件"""
        # 简单判断：包含日期格式的路径通常是输出文件
        import re
        date_pattern = r'\d{4}[/\\]\d{2}[/\\]\d{2}'
        return bool(re.search(date_pattern, file_path))
    
    def is_upload_file(self, file_path: str) -> bool:
        """判断是否为上传文件"""
        # 上传文件通常在uploads目录下
        return 'uploads' in file_path.lower()


# 全局适配器实例
_file_scenario_adapter = None


def get_file_scenario_adapter() -> FileScenarioAdapter:
    """获取文件场景适配器实例"""
    global _file_scenario_adapter
    if _file_scenario_adapter is None:
        _file_scenario_adapter = FileScenarioAdapter()
    return _file_scenario_adapter
