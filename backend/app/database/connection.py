"""
数据库连接管理器
支持三数据库架构：客户端、管理端、共享数据库
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库连接管理器"""
    
    def __init__(self):
        self.engines: Dict[str, Engine] = {}
        self.session_makers: Dict[str, sessionmaker] = {}
        self._initialized = False
    
    def initialize(self, config: Dict[str, Any]):
        """初始化数据库连接"""
        try:
            mysql_config = config.get('mysql', {})
            
            # 初始化三个数据库连接
            for db_name in ['client', 'admin', 'shared']:
                db_config = mysql_config.get(db_name, {})
                if not db_config:
                    raise ValueError(f"缺少数据库配置: {db_name}")
                
                # 构建数据库URL
                url = self._build_database_url(db_config)
                
                # 创建引擎
                engine = create_engine(
                    url,
                    poolclass=QueuePool,
                    pool_size=db_config.get('pool_size', 5),
                    max_overflow=db_config.get('max_overflow', 10),
                    pool_timeout=db_config.get('pool_timeout', 30),
                    pool_recycle=db_config.get('pool_recycle', 3600),
                    pool_pre_ping=True,
                    echo=False  # 生产环境设为False
                )
                
                # 创建会话工厂
                session_maker = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=engine
                )
                
                self.engines[db_name] = engine
                self.session_makers[db_name] = session_maker
                
                logger.info(f"数据库连接已初始化: {db_name} -> {db_config['database']}")
            
            self._initialized = True
            logger.info("数据库管理器初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _build_database_url(self, config: Dict[str, Any]) -> str:
        """构建数据库连接URL"""
        host = config.get('host', 'localhost')
        port = config.get('port', 3306)
        user = config.get('user', 'root')
        password = config.get('password', '')
        database = config.get('database', '')
        charset = config.get('charset', 'utf8mb4')
        
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
    
    def get_engine(self, db_name: str) -> Engine:
        """获取数据库引擎"""
        if not self._initialized:
            raise RuntimeError("数据库管理器未初始化")
        
        if db_name not in self.engines:
            raise ValueError(f"未知的数据库: {db_name}")
        
        return self.engines[db_name]
    
    def get_session_maker(self, db_name: str) -> sessionmaker:
        """获取会话工厂"""
        if not self._initialized:
            raise RuntimeError("数据库管理器未初始化")
        
        if db_name not in self.session_makers:
            raise ValueError(f"未知的数据库: {db_name}")
        
        return self.session_makers[db_name]
    
    @contextmanager
    def get_session(self, db_name: str):
        """获取数据库会话（上下文管理器）"""
        session_maker = self.get_session_maker(db_name)
        session = session_maker()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败 [{db_name}]: {e}")
            raise
        finally:
            session.close()
    
    def get_session_direct(self, db_name: str) -> Session:
        """直接获取数据库会话（需要手动管理）"""
        session_maker = self.get_session_maker(db_name)
        return session_maker()
    
    def test_connections(self) -> Dict[str, bool]:
        """测试所有数据库连接"""
        results = {}
        
        for db_name, engine in self.engines.items():
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                results[db_name] = True
                logger.info(f"数据库连接测试成功: {db_name}")
            except Exception as e:
                results[db_name] = False
                logger.error(f"数据库连接测试失败 [{db_name}]: {e}")
        
        return results
    
    def close_all(self):
        """关闭所有数据库连接"""
        for db_name, engine in self.engines.items():
            try:
                engine.dispose()
                logger.info(f"数据库连接已关闭: {db_name}")
            except Exception as e:
                logger.error(f"关闭数据库连接失败 [{db_name}]: {e}")
        
        self.engines.clear()
        self.session_makers.clear()
        self._initialized = False


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def initialize_database(config: Dict[str, Any]):
    """初始化数据库连接"""
    db_manager = get_database_manager()
    db_manager.initialize(config)


# 便捷函数
def get_client_session():
    """获取客户端数据库会话"""
    return get_database_manager().get_session('client')


def get_admin_session():
    """获取管理端数据库会话"""
    return get_database_manager().get_session('admin')


def get_shared_session():
    """获取共享数据库会话"""
    return get_database_manager().get_session('shared')


def get_client_session_direct():
    """直接获取客户端数据库会话"""
    return get_database_manager().get_session_direct('client')


def get_admin_session_direct():
    """直接获取管理端数据库会话"""
    return get_database_manager().get_session_direct('admin')


def get_shared_session_direct():
    """直接获取共享数据库会话"""
    return get_database_manager().get_session_direct('shared')
