"""
文件管理服务
负责文件上传、存储、查询等操作的数据库集成
"""
import os
import uuid
import hashlib
import mimetypes
from datetime import datetime
from typing import Optional, List, Dict, Any
from PIL import Image
import logging

from ..database.dao.base_dao import BaseDAO
from ..database.models.client_models import ClientUpload
from ..database.models.shared_models import GlobalFile
from ..utils.path_utils import get_upload_dir, clean_filename, ensure_dir_exists

logger = logging.getLogger(__name__)


class FileService:
    """文件管理服务"""
    
    def __init__(self):
        self.client_upload_dao = BaseDAO('client', ClientUpload)
        self.global_file_dao = BaseDAO('shared', GlobalFile)
    
    def calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def get_image_dimensions(self, file_path: str) -> tuple:
        """获取图片尺寸"""
        try:
            with Image.open(file_path) as img:
                return img.size  # (width, height)
        except Exception:
            return (0, 0)
    
    def save_uploaded_file(self, file_content: bytes, original_filename: str, 
                          client_id: str, file_type: str = 'image') -> Optional[Dict[str, Any]]:
        """保存上传的文件并记录到数据库"""
        try:
            # 创建日期目录结构
            now = datetime.now()
            date_path = now.strftime("%Y/%m/%d")
            upload_date_dir = os.path.join(get_upload_dir(), date_path)
            ensure_dir_exists(upload_date_dir)
            
            # 生成唯一文件名
            file_extension = original_filename.split('.')[-1].lower() if '.' in original_filename else ''
            timestamp = now.strftime("%H%M%S")
            file_id = str(uuid.uuid4())
            unique_filename = f"{timestamp}_{file_id[:8]}.{file_extension}"
            file_path = os.path.join(upload_date_dir, unique_filename)
            
            # 保存文件
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # 获取文件信息
            file_size = len(file_content)
            mime_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
            file_hash = self.calculate_file_hash(file_path)
            
            # 获取图片尺寸（如果是图片）
            width, height = 0, 0
            if file_type == 'image' and mime_type.startswith('image/'):
                width, height = self.get_image_dimensions(file_path)
            
            # 保存到客户端上传表
            client_upload = self.client_upload_dao.create(
                file_id=file_id,
                client_id=client_id,
                original_name=clean_filename(original_filename),
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                width=width,
                height=height,
                is_processed=False
            )
            
            if not client_upload:
                # 如果数据库保存失败，删除文件
                os.remove(file_path)
                return None
            
            # 同步到全局文件表
            global_file = self.global_file_dao.create(
                file_id=file_id,
                source_type='client_upload',
                source_user_id=client_id,
                original_name=clean_filename(original_filename),
                file_name=unique_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                file_hash=file_hash,
                file_type=file_type,
                width=width,
                height=height
            )
            
            logger.info(f"文件上传成功: {original_filename} -> {file_path}")
            
            return {
                'file_id': file_id,
                'original_name': original_filename,
                'file_name': unique_filename,
                'file_path': file_path,
                'file_size': file_size,
                'mime_type': mime_type,
                'width': width,
                'height': height,
                'upload_time': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return None

    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """通过文件ID获取文件信息"""
        try:
            # 先从客户端上传表查找
            client_upload = self.client_upload_dao.get_by_field('file_id', file_id)
            if client_upload:
                return {
                    'file_id': client_upload.file_id,
                    'original_name': client_upload.original_name,
                    'file_path': client_upload.file_path,
                    'file_size': client_upload.file_size,
                    'mime_type': client_upload.mime_type,
                    'width': client_upload.width,
                    'height': client_upload.height,
                    'created_at': client_upload.created_at.isoformat() if client_upload.created_at else None
                }

            # 如果客户端表没有，从全局文件表查找
            global_file = self.global_file_dao.get_by_field('file_id', file_id)
            if global_file:
                return {
                    'file_id': global_file.file_id,
                    'original_name': global_file.original_name,
                    'file_path': global_file.file_path,
                    'file_size': global_file.file_size,
                    'mime_type': global_file.mime_type,
                    'width': global_file.width,
                    'height': global_file.height,
                    'created_at': global_file.created_at.isoformat() if global_file.created_at else None
                }

            return None

        except Exception as e:
            logger.error(f"获取文件信息失败 [{file_id}]: {e}")
            return None

    def get_file_info_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """通过文件路径获取文件信息"""
        try:
            # 先从客户端上传表查找
            client_upload = self.client_upload_dao.get_by_field('file_path', file_path)
            if client_upload:
                return {
                    'file_id': client_upload.file_id,
                    'original_name': client_upload.original_name,
                    'file_path': client_upload.file_path,
                    'file_size': client_upload.file_size,
                    'mime_type': client_upload.mime_type,
                    'width': client_upload.width,
                    'height': client_upload.height,
                    'created_at': client_upload.created_at.isoformat() if client_upload.created_at else None
                }

            # 如果客户端表没有，从全局文件表查找
            global_file = self.global_file_dao.get_by_field('file_path', file_path)
            if global_file:
                return {
                    'file_id': global_file.file_id,
                    'original_name': global_file.original_name,
                    'file_path': global_file.file_path,
                    'file_size': global_file.file_size,
                    'mime_type': global_file.mime_type,
                    'width': global_file.width,
                    'height': global_file.height,
                    'created_at': global_file.created_at.isoformat() if global_file.created_at else None
                }

            return None

        except Exception as e:
            logger.error(f"通过路径获取文件信息失败 [{file_path}]: {e}")
            return None
    
    def get_user_files(self, client_id: str, file_type: str = None,
                      limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取用户上传的文件列表"""
        try:
            with self.client_upload_dao.get_session() as session:
                query = session.query(ClientUpload).filter(
                    ClientUpload.client_id == client_id
                )

                # 由于数据库表中没有upload_type字段，暂时忽略file_type过滤
                # if file_type:
                #     query = query.filter(ClientUpload.upload_type == file_type)

                uploads = query.order_by(ClientUpload.created_at.desc()).offset(offset).limit(limit).all()

                return [self._upload_to_dict(upload) for upload in uploads]

        except Exception as e:
            logger.error(f"获取用户文件失败: {e}")
            return []
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        try:
            # 先从客户端上传表查询
            with self.client_upload_dao.get_session() as session:
                upload = session.query(ClientUpload).filter(
                    ClientUpload.file_id == file_id
                ).first()

                if upload:
                    return self._upload_to_dict(upload)

            # 如果客户端表没有，从全局文件表查询
            with self.global_file_dao.get_session() as session:
                file_record = session.query(GlobalFile).filter(
                    GlobalFile.file_id == file_id
                ).first()

                if file_record:
                    return self._global_file_to_dict(file_record)

            return None

        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
    
    def delete_file(self, file_id: str, client_id: str) -> bool:
        """删除文件"""
        try:
            # 获取文件信息
            with self.client_upload_dao.get_session() as session:
                upload = session.query(ClientUpload).filter(
                    ClientUpload.file_id == file_id,
                    ClientUpload.client_id == client_id
                ).first()

                if not upload:
                    return False

                # 删除物理文件
                if os.path.exists(upload.file_path):
                    os.remove(upload.file_path)

                # 由于数据库表中没有status字段，直接删除记录
                session.delete(upload)
                session.commit()

            # 同步更新全局文件表 - 直接删除记录
            with self.global_file_dao.get_session() as session:
                file_record = session.query(GlobalFile).filter(
                    GlobalFile.file_id == file_id
                ).first()

                if file_record:
                    session.delete(file_record)
                    session.commit()

            logger.info(f"文件删除成功: {file_id}")
            return True

        except Exception as e:
            logger.error(f"文件删除失败: {e}")
            return False
    
    def _upload_to_dict(self, upload: ClientUpload) -> Dict[str, Any]:
        """将上传记录转换为字典"""
        return {
            'file_id': upload.file_id,
            'original_name': upload.original_name,
            'file_name': os.path.basename(upload.file_path),  # 从路径中提取文件名
            'file_path': upload.file_path,
            'file_size': upload.file_size,
            'mime_type': upload.mime_type,
            'file_type': 'image',  # 默认为image类型
            'width': upload.width,
            'height': upload.height,
            'status': 'completed' if upload.is_processed else 'pending',
            'upload_time': upload.created_at.isoformat() if upload.created_at else None
        }
    
    def _global_file_to_dict(self, file_record: GlobalFile) -> Dict[str, Any]:
        """将全局文件记录转换为字典"""
        return {
            'file_id': file_record.file_id,
            'original_name': file_record.original_name,
            'file_name': file_record.file_name,
            'file_path': file_record.file_path,
            'file_size': file_record.file_size,
            'mime_type': file_record.mime_type,
            'file_type': file_record.file_type,
            'width': file_record.width,
            'height': file_record.height,
            'status': file_record.status,
            'upload_time': file_record.created_at.isoformat() if file_record.created_at else None
        }


# 全局实例
_file_service = None

def get_file_service() -> FileService:
    """获取文件服务实例"""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
