#!/usr/bin/env python3
"""
数据库管理工具
提供数据库初始化、迁移、状态检查等功能
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

# 导入迁移管理器
try:
    from migration_manager import MigrationManager
    MIGRATION_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入迁移管理器: {e}")
    MIGRATION_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_migrations():
    """运行数据库迁移"""
    if not MIGRATION_AVAILABLE:
        print("❌ 迁移管理器不可用")
        return False
    
    try:
        print("🔄 正在运行数据库迁移...")
        
        manager = MigrationManager()
        
        # 获取迁移状态
        status = manager.get_migration_status()
        print(f"📊 迁移状态: {status['executed']}/{status['total']} 已执行")
        
        if status['pending'] > 0:
            print(f"🔄 发现 {status['pending']} 个待执行的迁移")
            
            # 执行迁移
            success = manager.run_migrations()
            
            if success:
                print("✅ 数据库迁移完成")
                return True
            else:
                print("❌ 数据库迁移失败")
                return False
        else:
            print("✅ 数据库已是最新版本")
            return True
            
    except Exception as e:
        logger.error(f"运行迁移失败: {e}")
        print(f"❌ 运行迁移失败: {e}")
        return False


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
        
        # 运行迁移
        if not run_migrations():
            print("❌ 数据库迁移失败")
            return False
        
        # 初始化数据
        if not init_default_data():
            print("❌ 初始化默认数据失败")
            return False
        
        print("✅ 数据库初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        print(f"❌ 初始化数据库失败: {e}")
        return False


def check_database_status():
    """检查数据库状态"""
    try:
        print("🔍 正在检查数据库状态...")
        
        # 导入数据库管理器
        from app.database.connection import get_database_manager
        
        db_manager = get_database_manager()
        
        # 检查连接
        print("\n数据库连接状态:")
        for db_name in ['client', 'admin', 'shared']:
            try:
                engine = db_manager.get_engine(db_name)
                with engine.connect() as conn:
                    conn.execute("SELECT 1")
                print(f"  ✅ {db_name}: 连接正常")
            except Exception as e:
                print(f"  ❌ {db_name}: 连接失败 ({e})")
        
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
        
        return True
        
    except Exception as e:
        logger.error(f"检查数据库状态失败: {e}")
        return False


def migration_status():
    """显示迁移状态"""
    if not MIGRATION_AVAILABLE:
        print("❌ 迁移管理器不可用")
        return False
    
    try:
        manager = MigrationManager()
        status = manager.get_migration_status()
        
        print(f"📊 迁移状态总览:")
        print(f"  总计: {status['total']} 个迁移文件")
        print(f"  已执行: {status['executed']} 个")
        print(f"  待执行: {status['pending']} 个")
        print(f"  失败: {status['failed']} 个")
        
        if status['details']:
            print(f"\n📋 详细信息:")
            for detail in status['details']:
                status_icon = "✅" if detail['executed'] else "⏳"
                print(f"  {status_icon} {detail['filename']}")
                print(f"     数据库: {detail['database']}")
                print(f"     版本: {detail['version']}")
                if detail['description']:
                    print(f"     描述: {detail['description']}")
                print()
        
        return True
        
    except Exception as e:
        logger.error(f"获取迁移状态失败: {e}")
        print(f"❌ 获取迁移状态失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='ComfyUI 数据库管理工具')
    parser.add_argument('action', choices=['init', 'migrate', 'status', 'migration-status'], 
                       help='要执行的操作')
    
    args = parser.parse_args()
    
    print("🗄️  ComfyUI 数据库管理工具")
    print("=" * 50)
    
    if args.action == 'init':
        success = init_database()
    elif args.action == 'migrate':
        success = run_migrations()
    elif args.action == 'status':
        success = check_database_status()
    elif args.action == 'migration-status':
        success = migration_status()
    else:
        print("❌ 未知操作")
        success = False
    
    if success:
        print("\n🎉 操作完成")
    else:
        print("\n💥 操作失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
