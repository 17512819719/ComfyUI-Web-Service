"""
数据访问对象基类
"""
import logging
from typing import List, Optional, Dict, Any, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..connection import get_database_manager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseDAO:
    """数据访问对象基类"""
    
    def __init__(self, db_name: str, model_class: Type[T]):
        self.db_name = db_name
        self.model_class = model_class
        self.db_manager = get_database_manager()
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.db_manager.get_session_direct(self.db_name)
    
    def create(self, **kwargs) -> Optional[T]:
        """创建记录"""
        session = self.get_session()
        try:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"创建记录失败 [{self.model_class.__name__}]: {e}")
            return None
        finally:
            session.close()
    
    def get_by_id(self, id_value: Any) -> Optional[T]:
        """根据ID获取记录"""
        session = self.get_session()
        try:
            return session.query(self.model_class).filter(
                self.model_class.id == id_value
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"查询记录失败 [{self.model_class.__name__}]: {e}")
            return None
        finally:
            session.close()
    
    def get_by_field(self, field_name: str, field_value: Any) -> Optional[T]:
        """根据字段获取记录"""
        session = self.get_session()
        try:
            field = getattr(self.model_class, field_name)
            return session.query(self.model_class).filter(
                field == field_value
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"查询记录失败 [{self.model_class.__name__}]: {e}")
            return None
        finally:
            session.close()
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """获取所有记录"""
        session = self.get_session()
        try:
            query = session.query(self.model_class)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"查询记录失败 [{self.model_class.__name__}]: {e}")
            return []
        finally:
            session.close()
    
    def update(self, id_value: Any, **kwargs) -> bool:
        """更新记录"""
        session = self.get_session()
        try:
            result = session.query(self.model_class).filter(
                self.model_class.id == id_value
            ).update(kwargs)
            session.commit()
            return result > 0
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"更新记录失败 [{self.model_class.__name__}]: {e}")
            return False
        finally:
            session.close()
    
    def update_by_field(self, field_name: str, field_value: Any, **kwargs) -> bool:
        """根据字段更新记录"""
        session = self.get_session()
        try:
            field = getattr(self.model_class, field_name)
            result = session.query(self.model_class).filter(
                field == field_value
            ).update(kwargs)
            session.commit()
            return result > 0
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"更新记录失败 [{self.model_class.__name__}]: {e}")
            return False
        finally:
            session.close()
    
    def delete(self, id_value: Any) -> bool:
        """删除记录"""
        session = self.get_session()
        try:
            result = session.query(self.model_class).filter(
                self.model_class.id == id_value
            ).delete()
            session.commit()
            return result > 0
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"删除记录失败 [{self.model_class.__name__}]: {e}")
            return False
        finally:
            session.close()
    
    def delete_by_field(self, field_name: str, field_value: Any) -> bool:
        """根据字段删除记录"""
        session = self.get_session()
        try:
            field = getattr(self.model_class, field_name)
            result = session.query(self.model_class).filter(
                field == field_value
            ).delete()
            session.commit()
            return result > 0
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"删除记录失败 [{self.model_class.__name__}]: {e}")
            return False
        finally:
            session.close()
    
    def count(self, **filters) -> int:
        """统计记录数"""
        session = self.get_session()
        try:
            query = session.query(self.model_class)
            for field_name, field_value in filters.items():
                if hasattr(self.model_class, field_name):
                    field = getattr(self.model_class, field_name)
                    query = query.filter(field == field_value)
            return query.count()
        except SQLAlchemyError as e:
            logger.error(f"统计记录失败 [{self.model_class.__name__}]: {e}")
            return 0
        finally:
            session.close()
    
    def exists(self, **filters) -> bool:
        """检查记录是否存在"""
        return self.count(**filters) > 0
    
    def bulk_create(self, records: List[Dict[str, Any]]) -> bool:
        """批量创建记录"""
        session = self.get_session()
        try:
            instances = [self.model_class(**record) for record in records]
            session.add_all(instances)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"批量创建记录失败 [{self.model_class.__name__}]: {e}")
            return False
        finally:
            session.close()
