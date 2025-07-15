"""
输出文件管理器
管理ComfyUI生成的文件，支持按日期分类存储
"""
import os
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .path_utils import get_output_dir, ensure_dir_exists, get_file_info, clean_filename

logger = logging.getLogger(__name__)


class OutputManager:
    """输出文件管理器"""
    
    def __init__(self):
        self.output_dir = get_output_dir()
        ensure_dir_exists(self.output_dir)
    
    def get_date_subdir(self, date: Optional[datetime] = None) -> str:
        """获取按日期分类的子目录"""
        if date is None:
            date = datetime.now()
        
        # 格式：YYYY/MM/DD
        date_path = date.strftime("%Y/%m/%d")
        full_path = os.path.join(self.output_dir, date_path)
        ensure_dir_exists(full_path)
        
        return full_path
    
    def organize_output_files(self, file_paths: List[str], task_id: str) -> List[str]:
        """
        整理输出文件，按日期分类存储
        
        Args:
            file_paths: 原始文件路径列表
            task_id: 任务ID
        
        Returns:
            整理后的文件路径列表
        """
        organized_paths = []
        date_subdir = self.get_date_subdir()
        
        for i, file_path in enumerate(file_paths):
            try:
                if not os.path.exists(file_path):
                    logger.warning(f"文件不存在: {file_path}")
                    continue
                
                # 生成新文件名
                original_name = os.path.basename(file_path)
                name, ext = os.path.splitext(original_name)
                
                # 添加任务ID和索引
                if len(file_paths) > 1:
                    new_name = f"{task_id}_{i+1:03d}_{name}{ext}"
                else:
                    new_name = f"{task_id}_{name}{ext}"
                
                new_name = clean_filename(new_name)
                new_path = os.path.join(date_subdir, new_name)
                
                # 确保文件名唯一
                counter = 1
                while os.path.exists(new_path):
                    name_part, ext_part = os.path.splitext(new_name)
                    new_name = f"{name_part}_({counter}){ext_part}"
                    new_path = os.path.join(date_subdir, new_name)
                    counter += 1
                
                # 复制文件
                shutil.copy2(file_path, new_path)
                organized_paths.append(new_path)
                
                logger.info(f"文件已整理: {file_path} -> {new_path}")
                
            except Exception as e:
                logger.error(f"整理文件失败 [{file_path}]: {e}")
                # 如果整理失败，保留原路径
                organized_paths.append(file_path)
        
        return organized_paths
    
    def get_task_files(self, task_id: str) -> List[str]:
        """获取任务的所有输出文件"""
        files = []
        
        try:
            # 遍历输出目录查找包含任务ID的文件
            for root, dirs, filenames in os.walk(self.output_dir):
                for filename in filenames:
                    if task_id in filename:
                        file_path = os.path.join(root, filename)
                        files.append(file_path)
            
            # 按修改时间排序
            files.sort(key=lambda x: os.path.getmtime(x))
            
        except Exception as e:
            logger.error(f"获取任务文件失败 [{task_id}]: {e}")
        
        return files
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """
        清理旧文件
        
        Args:
            days: 保留天数
        
        Returns:
            删除的文件数量
        """
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        try:
            for root, dirs, filenames in os.walk(self.output_dir):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    
                    try:
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                            deleted_count += 1
                            logger.debug(f"删除旧文件: {file_path}")
                    except Exception as e:
                        logger.error(f"删除文件失败 [{file_path}]: {e}")
                
                # 删除空目录
                try:
                    if not os.listdir(root) and root != self.output_dir:
                        os.rmdir(root)
                        logger.debug(f"删除空目录: {root}")
                except Exception:
                    pass
            
            logger.info(f"清理完成，删除了 {deleted_count} 个旧文件")
            
        except Exception as e:
            logger.error(f"清理旧文件失败: {e}")
        
        return deleted_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_date': {},
            'by_type': {}
        }
        
        try:
            for root, dirs, filenames in os.walk(self.output_dir):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    file_info = get_file_info(file_path)
                    
                    if file_info['exists']:
                        stats['total_files'] += 1
                        stats['total_size'] += file_info['size']
                        
                        # 按日期统计
                        rel_path = os.path.relpath(root, self.output_dir)
                        date_key = rel_path.replace('\\', '/') if rel_path != '.' else 'root'
                        if date_key not in stats['by_date']:
                            stats['by_date'][date_key] = {'files': 0, 'size': 0}
                        stats['by_date'][date_key]['files'] += 1
                        stats['by_date'][date_key]['size'] += file_info['size']
                        
                        # 按类型统计
                        ext = file_info['extension'].lower()
                        if ext not in stats['by_type']:
                            stats['by_type'][ext] = {'files': 0, 'size': 0}
                        stats['by_type'][ext]['files'] += 1
                        stats['by_type'][ext]['size'] += file_info['size']
            
        except Exception as e:
            logger.error(f"获取存储统计失败: {e}")
        
        return stats
    
    def create_thumbnail(self, image_path: str, max_size: tuple = (200, 200)) -> Optional[str]:
        """
        创建缩略图
        
        Args:
            image_path: 原图路径
            max_size: 最大尺寸 (width, height)
        
        Returns:
            缩略图路径，失败返回None
        """
        try:
            from PIL import Image
            
            # 生成缩略图路径
            dir_path = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            thumb_filename = f"{name}_thumb{ext}"
            thumb_path = os.path.join(dir_path, thumb_filename)
            
            # 创建缩略图
            with Image.open(image_path) as img:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(thumb_path, optimize=True, quality=85)
            
            logger.debug(f"缩略图创建成功: {thumb_path}")
            return thumb_path
            
        except Exception as e:
            logger.error(f"创建缩略图失败 [{image_path}]: {e}")
            return None
    
    def get_file_url(self, file_path: str, base_url: str = "/api/v2/files") -> str:
        """
        获取文件的访问URL
        
        Args:
            file_path: 文件路径
            base_url: 基础URL
        
        Returns:
            文件访问URL
        """
        try:
            # 获取相对于输出目录的路径
            rel_path = os.path.relpath(file_path, self.output_dir)
            # 标准化路径分隔符
            rel_path = rel_path.replace('\\', '/')
            return f"{base_url}/{rel_path}"
        except Exception as e:
            logger.error(f"生成文件URL失败 [{file_path}]: {e}")
            return ""


# 全局输出管理器实例
_output_manager: Optional[OutputManager] = None


def get_output_manager() -> OutputManager:
    """获取输出管理器实例"""
    global _output_manager
    if _output_manager is None:
        _output_manager = OutputManager()
    return _output_manager
