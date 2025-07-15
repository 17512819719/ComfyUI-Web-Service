"""
数据库初始化脚本
创建表结构和初始数据
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from .models import Base
from .models.client_models import *
from .models.admin_models import *
from .models.shared_models import *
from .connection import get_database_manager

logger = logging.getLogger(__name__)


def create_tables():
    """创建所有数据库表"""
    try:
        db_manager = get_database_manager()
        
        # 为每个数据库创建表
        for db_name in ['client', 'admin', 'shared']:
            engine = db_manager.get_engine(db_name)
            
            logger.info(f"正在创建 {db_name} 数据库表...")
            
            # 创建表
            Base.metadata.create_all(bind=engine)
            
            logger.info(f"{db_name} 数据库表创建完成")
        
        logger.info("所有数据库表创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        return False


def init_default_data():
    """初始化默认数据"""
    try:
        from .dao.base_dao import BaseDAO
        from .models.admin_models import AdminUser, SystemConfig
        
        # 创建默认管理员用户
        admin_dao = BaseDAO('admin', AdminUser)
        
        # 检查是否已存在管理员
        if not admin_dao.exists(username='admin'):
            admin_user = admin_dao.create(
                username='admin',
                email='admin@example.com',
                password_hash='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx/LBK2.',  # 密码: admin123
                display_name='系统管理员',
                role='super_admin',
                status='active'
            )
            if admin_user:
                logger.info("默认管理员用户创建成功")
            else:
                logger.error("默认管理员用户创建失败")
        
        # 创建系统配置
        config_dao = BaseDAO('admin', SystemConfig)
        
        default_configs = [
            {
                'config_key': 'system.name',
                'config_value': 'ComfyUI Web Service',
                'config_type': 'string',
                'description': '系统名称',
                'is_public': True
            },
            {
                'config_key': 'system.version',
                'config_value': '2.0.0',
                'config_type': 'string',
                'description': '系统版本',
                'is_public': True
            },
            {
                'config_key': 'task.default_priority',
                'config_value': '1',
                'config_type': 'int',
                'description': '默认任务优先级',
                'is_public': False
            },
            {
                'config_key': 'task.max_concurrent',
                'config_value': '10',
                'config_type': 'int',
                'description': '最大并发任务数',
                'is_public': False
            },
            {
                'config_key': 'file.max_size',
                'config_value': '104857600',
                'config_type': 'int',
                'description': '最大文件大小(100MB)',
                'is_public': False
            },
            {
                'config_key': 'api.rate_limit',
                'config_value': '100',
                'config_type': 'int',
                'description': 'API速率限制(每分钟)',
                'is_public': False
            }
        ]
        
        for config in default_configs:
            if not config_dao.exists(config_key=config['config_key']):
                created_config = config_dao.create(**config)
                if created_config:
                    logger.info(f"系统配置创建成功: {config['config_key']}")
                else:
                    logger.error(f"系统配置创建失败: {config['config_key']}")
        
        logger.info("默认数据初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"初始化默认数据失败: {e}")
        return False


def check_database_status():
    """检查数据库状态"""
    try:
        db_manager = get_database_manager()
        
        # 测试连接
        test_results = db_manager.test_connections()
        
        all_connected = True
        for db_name, success in test_results.items():
            status = "✅" if success else "❌"
            logger.info(f"{status} {db_name} 数据库连接")
            if not success:
                all_connected = False
        
        if all_connected:
            logger.info("所有数据库连接正常")
        else:
            logger.error("部分数据库连接失败")
        
        return all_connected
        
    except Exception as e:
        logger.error(f"检查数据库状态失败: {e}")
        return False


def reset_database():
    """重置数据库（删除所有表并重新创建）"""
    try:
        db_manager = get_database_manager()
        
        logger.warning("正在重置数据库...")
        
        # 为每个数据库删除并重新创建表
        for db_name in ['client', 'admin', 'shared']:
            engine = db_manager.get_engine(db_name)
            
            logger.info(f"正在重置 {db_name} 数据库...")
            
            # 删除所有表
            Base.metadata.drop_all(bind=engine)
            
            # 重新创建表
            Base.metadata.create_all(bind=engine)
            
            logger.info(f"{db_name} 数据库重置完成")
        
        # 初始化默认数据
        init_default_data()
        
        logger.info("数据库重置完成")
        return True
        
    except Exception as e:
        logger.error(f"重置数据库失败: {e}")
        return False


def main():
    """主函数"""
    import sys
    import os
    
    # 添加项目根目录到路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 初始化数据库连接
    from ..core.config_manager import get_config_manager
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    from .connection import initialize_database
    initialize_database(config)
    
    # 检查数据库状态
    if not check_database_status():
        logger.error("数据库连接失败，请检查配置")
        return
    
    # 创建表
    if create_tables():
        logger.info("数据库表创建成功")
    else:
        logger.error("数据库表创建失败")
        return
    
    # 初始化默认数据
    if init_default_data():
        logger.info("默认数据初始化成功")
    else:
        logger.error("默认数据初始化失败")


if __name__ == "__main__":
    main()
