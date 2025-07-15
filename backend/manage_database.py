"""
数据库管理脚本
提供数据库初始化、重置、备份等功能
"""
import sys
import os
import argparse
import logging

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库"""
    try:
        print("🔧 正在初始化数据库...")
        
        # 初始化配置和连接
        from app.core.config_manager import get_config_manager
        from app.database.connection import initialize_database
        from app.database.init_db import create_tables, init_default_data, check_database_status
        
        config_manager = get_config_manager()
        config = config_manager.get_config()
        initialize_database(config)
        
        # 检查连接
        if not check_database_status():
            print("❌ 数据库连接失败")
            return False
        
        # 创建表
        if not create_tables():
            print("❌ 创建数据库表失败")
            return False
        
        # 初始化数据
        if not init_default_data():
            print("❌ 初始化默认数据失败")
            return False
        
        print("✅ 数据库初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


def reset_database():
    """重置数据库"""
    try:
        print("⚠️  正在重置数据库...")
        print("   这将删除所有现有数据！")
        
        confirm = input("确认重置数据库？(输入 'yes' 确认): ")
        if confirm.lower() != 'yes':
            print("❌ 操作已取消")
            return False
        
        # 初始化配置和连接
        from app.core.config_manager import get_config_manager
        from app.database.connection import initialize_database
        from app.database.init_db import reset_database
        
        config_manager = get_config_manager()
        config = config_manager.get_config()
        initialize_database(config)
        
        # 重置数据库
        if reset_database():
            print("✅ 数据库重置完成")
            return True
        else:
            print("❌ 数据库重置失败")
            return False
        
    except Exception as e:
        logger.error(f"数据库重置失败: {e}")
        return False


def test_database():
    """测试数据库"""
    try:
        print("🧪 正在测试数据库...")
        
        # 运行测试脚本
        from test_database import test_database_connection, test_task_status_manager, test_dao_operations
        
        # 测试连接
        if not test_database_connection():
            print("❌ 数据库连接测试失败")
            return False
        
        # 测试任务状态管理器
        if not test_task_status_manager():
            print("❌ 任务状态管理器测试失败")
            return False
        
        # 测试DAO操作
        if not test_dao_operations():
            print("❌ DAO操作测试失败")
            return False
        
        print("✅ 所有数据库测试通过")
        return True
        
    except Exception as e:
        logger.error(f"数据库测试失败: {e}")
        return False


def check_status():
    """检查数据库状态"""
    try:
        print("📊 正在检查数据库状态...")
        
        # 初始化配置和连接
        from app.core.config_manager import get_config_manager
        from app.database.connection import initialize_database, get_database_manager
        
        config_manager = get_config_manager()
        config = config_manager.get_config()
        initialize_database(config)
        
        # 检查连接
        db_manager = get_database_manager()
        test_results = db_manager.test_connections()
        
        print("\n数据库连接状态:")
        for db_name, success in test_results.items():
            status = "✅ 正常" if success else "❌ 失败"
            print(f"  {db_name}: {status}")
        
        # 检查表数量
        print("\n数据库表统计:")
        for db_name in ['client', 'admin', 'shared']:
            try:
                engine = db_manager.get_engine(db_name)
                with engine.connect() as conn:
                    result = conn.execute("SHOW TABLES")
                    tables = result.fetchall()
                    print(f"  {db_name}: {len(tables)} 个表")
            except Exception as e:
                print(f"  {db_name}: 无法获取表信息 ({e})")
        
        # 检查任务数量
        try:
            from app.database.dao.task_dao import GlobalTaskDAO, ClientTaskDAO
            
            global_dao = GlobalTaskDAO()
            client_dao = ClientTaskDAO()
            
            global_count = global_dao.count()
            client_count = client_dao.count()
            
            print(f"\n任务统计:")
            print(f"  全局任务: {global_count} 个")
            print(f"  客户端任务: {client_count} 个")
            
        except Exception as e:
            print(f"\n任务统计: 无法获取 ({e})")
        
        return True
        
    except Exception as e:
        logger.error(f"检查数据库状态失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ComfyUI 数据库管理工具')
    parser.add_argument('action', choices=['init', 'reset', 'test', 'status'], 
                       help='要执行的操作')
    
    args = parser.parse_args()
    
    print("🗄️  ComfyUI 数据库管理工具")
    print("=" * 50)
    
    if args.action == 'init':
        success = init_database()
    elif args.action == 'reset':
        success = reset_database()
    elif args.action == 'test':
        success = test_database()
    elif args.action == 'status':
        success = check_status()
    else:
        print("❌ 未知操作")
        success = False
    
    print("=" * 50)
    if success:
        print("✅ 操作完成")
    else:
        print("❌ 操作失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
