"""
路径处理工具
统一处理项目中的文件路径，支持相对路径和绝对路径
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_project_root() -> str:
    """获取项目根目录"""
    # 从当前文件位置向上查找项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # backend/app/utils -> backend -> project_root
    project_root = os.path.dirname(os.path.dirname(current_dir))
    return project_root


def resolve_path(path: str, base_dir: Optional[str] = None) -> str:
    """
    解析路径，支持相对路径和绝对路径
    
    Args:
        path: 要解析的路径
        base_dir: 基础目录，如果为None则使用项目根目录
    
    Returns:
        解析后的绝对路径
    """
    if os.path.isabs(path):
        return os.path.normpath(path)
    
    if base_dir is None:
        base_dir = get_project_root()
    
    resolved_path = os.path.join(base_dir, path)
    return os.path.normpath(resolved_path)


def get_output_dir() -> str:
    """获取ComfyUI输出目录"""
    try:
        from ..core.config_manager import get_config_manager
        config_manager = get_config_manager()
        comfyui_config = config_manager.get_comfyui_config()
        output_dir = comfyui_config.get('output_dir', 'outputs')
        
        return resolve_path(output_dir)
    except Exception as e:
        logger.error(f"获取输出目录失败: {e}")
        # 返回默认输出目录
        return resolve_path('outputs')


def get_upload_dir() -> str:
    """获取上传目录"""
    return resolve_path('uploads')


def get_workflow_file_path(workflow_file: str) -> str:
    """获取工作流文件的完整路径"""
    return resolve_path(workflow_file)


def ensure_dir_exists(dir_path: str) -> bool:
    """确保目录存在，如果不存在则创建"""
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 [{dir_path}]: {e}")
        return False


def is_safe_path(file_path: str, base_dir: str) -> bool:
    """
    检查文件路径是否安全（防止路径遍历攻击）
    
    Args:
        file_path: 要检查的文件路径
        base_dir: 基础目录
    
    Returns:
        如果路径安全返回True，否则返回False
    """
    try:
        # 获取绝对路径
        abs_file_path = os.path.abspath(file_path)
        abs_base_dir = os.path.abspath(base_dir)
        
        # 检查文件路径是否在基础目录内
        return abs_file_path.startswith(abs_base_dir)
    except Exception:
        return False


def get_relative_path(file_path: str, base_dir: Optional[str] = None) -> str:
    """
    获取相对于基础目录的相对路径
    
    Args:
        file_path: 文件路径
        base_dir: 基础目录，如果为None则使用项目根目录
    
    Returns:
        相对路径
    """
    if base_dir is None:
        base_dir = get_project_root()
    
    try:
        return os.path.relpath(file_path, base_dir)
    except ValueError:
        # 如果无法计算相对路径，返回原路径
        return file_path


def normalize_path_separators(path: str) -> str:
    """标准化路径分隔符（统一使用正斜杠）"""
    return path.replace('\\', '/')


def get_file_info(file_path: str) -> dict:
    """
    获取文件信息
    
    Args:
        file_path: 文件路径
    
    Returns:
        包含文件信息的字典
    """
    try:
        if not os.path.exists(file_path):
            return {'exists': False}
        
        stat = os.stat(file_path)
        return {
            'exists': True,
            'size': stat.st_size,
            'modified_time': stat.st_mtime,
            'is_file': os.path.isfile(file_path),
            'is_dir': os.path.isdir(file_path),
            'basename': os.path.basename(file_path),
            'dirname': os.path.dirname(file_path),
            'extension': os.path.splitext(file_path)[1]
        }
    except Exception as e:
        logger.error(f"获取文件信息失败 [{file_path}]: {e}")
        return {'exists': False, 'error': str(e)}


def clean_filename(filename: str) -> str:
    """
    清理文件名，移除不安全的字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        清理后的文件名
    """
    import re
    
    # 移除或替换不安全的字符
    unsafe_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(unsafe_chars, '_', filename)
    
    # 移除开头和结尾的空格和点
    cleaned = cleaned.strip(' .')
    
    # 确保文件名不为空
    if not cleaned:
        cleaned = 'unnamed_file'
    
    return cleaned


def get_unique_filename(dir_path: str, filename: str) -> str:
    """
    获取唯一的文件名（如果文件已存在，则添加数字后缀）
    
    Args:
        dir_path: 目录路径
        filename: 原始文件名
    
    Returns:
        唯一的文件名
    """
    base_name, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    
    while os.path.exists(os.path.join(dir_path, unique_filename)):
        unique_filename = f"{base_name}_{counter}{ext}"
        counter += 1
    
    return unique_filename


def copy_file_to_output(source_path: str, target_filename: Optional[str] = None) -> Optional[str]:
    """
    复制文件到输出目录
    
    Args:
        source_path: 源文件路径
        target_filename: 目标文件名，如果为None则使用源文件名
    
    Returns:
        目标文件路径，如果失败返回None
    """
    try:
        import shutil
        
        output_dir = get_output_dir()
        ensure_dir_exists(output_dir)
        
        if target_filename is None:
            target_filename = os.path.basename(source_path)
        
        # 清理文件名
        target_filename = clean_filename(target_filename)
        
        # 获取唯一文件名
        target_filename = get_unique_filename(output_dir, target_filename)
        
        target_path = os.path.join(output_dir, target_filename)
        
        # 复制文件
        shutil.copy2(source_path, target_path)
        
        logger.info(f"文件复制成功: {source_path} -> {target_path}")
        return target_path
        
    except Exception as e:
        logger.error(f"复制文件失败: {e}")
        return None
