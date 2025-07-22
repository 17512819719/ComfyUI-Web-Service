#!/usr/bin/env python3
"""
创建数据库迁移文件的便捷脚本
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path


def create_migration_file(name: str, database: str, description: str = None):
    """创建新的迁移文件"""
    
    # 获取当前日期
    today = datetime.now().strftime('%Y_%m_%d')
    
    # 生成文件名
    filename = f"{today}_{name}.sql"
    
    # 迁移文件路径
    migrations_dir = Path(__file__).parent.parent / "migrations"
    filepath = migrations_dir / filename
    
    # 检查文件是否已存在
    if filepath.exists():
        print(f"❌ 迁移文件已存在: {filepath}")
        return False
    
    # 生成文件内容
    content = generate_migration_template(database, description or name)
    
    # 创建文件
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 创建迁移文件: {filepath}")
        print(f"📝 请编辑文件添加您的SQL语句")
        return True
        
    except Exception as e:
        print(f"❌ 创建文件失败: {e}")
        return False


def generate_migration_template(database: str, description: str) -> str:
    """生成迁移文件模板"""
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 根据数据库类型生成不同的模板
    if database == 'client':
        use_statement = "USE comfyui_client;"
        example_table = "client_users"
    elif database == 'admin':
        use_statement = "USE comfyui_admin;"
        example_table = "admin_users"
    elif database == 'shared':
        use_statement = "USE comfyui_shared;"
        example_table = "global_tasks"
    else:
        use_statement = "-- USE comfyui_database_name;"
        example_table = "table_name"
    
    template = f"""-- Database: {database}
-- Description: {description}
-- Author: Migration Generator
-- Created: {timestamp}

{use_statement}

-- 示例：检查并添加字段
-- SET @column_exists = (
--     SELECT COUNT(*) 
--     FROM INFORMATION_SCHEMA.COLUMNS 
--     WHERE TABLE_SCHEMA = 'comfyui_{database}' 
--     AND TABLE_NAME = '{example_table}' 
--     AND COLUMN_NAME = 'new_field'
-- );
-- 
-- SET @sql = IF(@column_exists = 0, 
--     'ALTER TABLE {example_table} ADD COLUMN new_field VARCHAR(255) COMMENT ''新字段''',
--     'SELECT "new_field字段已存在" as message'
-- );
-- 
-- PREPARE stmt FROM @sql;
-- EXECUTE stmt;
-- DEALLOCATE PREPARE stmt;

-- 在此添加您的SQL语句


-- 验证迁移结果
-- SELECT 
--     '{description}完成' as status,
--     COUNT(*) as affected_rows
-- FROM {example_table};
"""
    
    return template


def list_migrations():
    """列出现有的迁移文件"""
    migrations_dir = Path(__file__).parent.parent / "migrations"
    
    if not migrations_dir.exists():
        print("❌ 迁移目录不存在")
        return
    
    # 获取所有SQL文件
    sql_files = list(migrations_dir.glob("*.sql"))
    
    if not sql_files:
        print("📝 没有找到迁移文件")
        return
    
    # 按文件名排序
    sql_files.sort()
    
    print("📋 现有迁移文件:")
    print("-" * 60)
    
    for file_path in sql_files:
        # 读取文件获取描述
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            description = ""
            database = ""
            
            for line in lines[:10]:  # 只检查前10行
                line = line.strip()
                if line.startswith('-- Description:'):
                    description = line.replace('-- Description:', '').strip()
                elif line.startswith('-- Database:'):
                    database = line.replace('-- Database:', '').strip()
            
            print(f"📄 {file_path.name}")
            if database:
                print(f"   数据库: {database}")
            if description:
                print(f"   描述: {description}")
            print()
            
        except Exception as e:
            print(f"📄 {file_path.name} (无法读取: {e})")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据库迁移文件管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 创建迁移文件
    create_parser = subparsers.add_parser('create', help='创建新的迁移文件')
    create_parser.add_argument('name', help='迁移名称（不包含日期前缀）')
    create_parser.add_argument('--database', '-d', 
                              choices=['client', 'admin', 'shared', 'all'],
                              required=True,
                              help='目标数据库')
    create_parser.add_argument('--description', '-desc',
                              help='迁移描述')
    
    # 列出迁移文件
    list_parser = subparsers.add_parser('list', help='列出现有迁移文件')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🗄️  数据库迁移文件管理工具")
    print("=" * 50)
    
    if args.command == 'create':
        success = create_migration_file(
            name=args.name,
            database=args.database,
            description=args.description
        )
        
        if success:
            print("\n💡 提示:")
            print("1. 请编辑生成的文件添加您的SQL语句")
            print("2. 使用条件语句确保迁移可以重复执行")
            print("3. 测试迁移文件后再部署到生产环境")
            print("4. 运行 'python database/tools/db_manager.py migrate' 执行迁移")
    
    elif args.command == 'list':
        list_migrations()


if __name__ == '__main__':
    main()
