#!/usr/bin/env python3
"""
数据库迁移管理器
自动检测和执行数据库结构变更
"""

import os
import sys
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, config_path: str = None):
        """初始化迁移管理器"""
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        self.config = self._load_config(config_path)
        self.engines = self._create_engines()
        
        # 确保迁移记录表存在
        self._ensure_migration_tables()
    
    def _load_config(self, config_path: str = None) -> Dict:
        """加载数据库配置"""
        if config_path is None:
            config_path = project_root / "backend" / "config.yaml"
        
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config['mysql']
    
    def _create_engines(self) -> Dict:
        """创建数据库引擎"""
        engines = {}
        
        for db_name in ['client', 'admin', 'shared']:
            db_config = self.config[db_name]
            
            # 支持容器环境的主机名
            host = os.getenv(f'MYSQL_HOST', db_config['host'])
            port = os.getenv(f'MYSQL_PORT', db_config['port'])
            password = os.getenv(f'MYSQL_ROOT_PASSWORD', db_config['password'])
            
            connection_string = (
                f"mysql+pymysql://root:{password}@{host}:{port}/"
                f"{db_config['database']}?charset=utf8mb4"
            )
            
            engines[db_name] = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        
        return engines
    
    def _ensure_migration_tables(self):
        """确保迁移记录表存在"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS migration_history (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            database_name VARCHAR(50) NOT NULL,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            execution_time_ms INT,
            checksum VARCHAR(64),
            status ENUM('success', 'failed', 'rollback') DEFAULT 'success',
            error_message TEXT,
            INDEX idx_migration_name (migration_name),
            INDEX idx_database_name (database_name),
            INDEX idx_executed_at (executed_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据库迁移历史记录';
        """
        
        for db_name, engine in self.engines.items():
            try:
                with engine.connect() as conn:
                    conn.execute(text(create_table_sql))
                    conn.commit()
                logger.info(f"确保 {db_name} 数据库迁移表存在")
            except Exception as e:
                logger.error(f"创建 {db_name} 迁移表失败: {e}")
    
    def get_migration_files(self) -> List[Dict]:
        """获取所有迁移文件"""
        migrations = []
        
        # 扫描迁移文件
        for file_path in self.migrations_dir.glob("*.sql"):
            if file_path.name.startswith('.'):
                continue
                
            # 解析文件名获取信息
            migration_info = self._parse_migration_file(file_path)
            if migration_info:
                migrations.append(migration_info)
        
        # 按版本号排序
        migrations.sort(key=lambda x: x['version'])
        return migrations
    
    def _parse_migration_file(self, file_path: Path) -> Optional[Dict]:
        """解析迁移文件信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取元数据
            metadata = self._extract_metadata(content)
            
            # 从文件名提取版本信息
            filename = file_path.stem
            version_match = re.match(r'^(\d{4})_(\d{2})_(\d{2})_(.+)$', filename)
            
            if version_match:
                year, month, day, name = version_match.groups()
                version = f"{year}{month}{day}"
            else:
                # 兼容旧格式
                version = "00000000"
                name = filename
            
            return {
                'file_path': file_path,
                'filename': filename,
                'version': version,
                'name': name,
                'database': metadata.get('database', 'client'),
                'description': metadata.get('description', ''),
                'content': content,
                'checksum': self._calculate_checksum(content)
            }
            
        except Exception as e:
            logger.error(f"解析迁移文件 {file_path} 失败: {e}")
            return None
    
    def _extract_metadata(self, content: str) -> Dict:
        """从SQL文件中提取元数据"""
        metadata = {}
        
        # 提取注释中的元数据
        lines = content.split('\n')
        for line in lines[:20]:  # 只检查前20行
            line = line.strip()
            if line.startswith('--'):
                comment = line[2:].strip()
                
                # 解析键值对
                if ':' in comment:
                    key, value = comment.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key in ['database', 'description', 'version', 'author']:
                        metadata[key] = value
                
                # 检测数据库
                if 'USE ' in comment.upper():
                    db_match = re.search(r'USE\s+(\w+)', comment.upper())
                    if db_match:
                        db_name = db_match.group(1).lower()
                        if 'client' in db_name:
                            metadata['database'] = 'client'
                        elif 'admin' in db_name:
                            metadata['database'] = 'admin'
                        elif 'shared' in db_name:
                            metadata['database'] = 'shared'
        
        return metadata
    
    def _calculate_checksum(self, content: str) -> str:
        """计算文件内容校验和"""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def is_migration_executed(self, migration: Dict) -> bool:
        """检查迁移是否已执行"""
        db_name = migration['database']
        engine = self.engines[db_name]
        
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM migration_history WHERE migration_name = :name"),
                    {"name": migration['filename']}
                )
                count = result.scalar()
                return count > 0
        except Exception as e:
            logger.error(f"检查迁移状态失败: {e}")
            return False
    
    def execute_migration(self, migration: Dict) -> bool:
        """执行单个迁移"""
        db_name = migration['database']
        engine = self.engines[db_name]
        
        logger.info(f"执行迁移: {migration['filename']} -> {db_name} 数据库")
        
        start_time = datetime.now()
        
        try:
            with engine.connect() as conn:
                # 开始事务
                trans = conn.begin()
                
                try:
                    # 执行迁移SQL
                    statements = self._split_sql_statements(migration['content'])
                    
                    for statement in statements:
                        if statement.strip():
                            conn.execute(text(statement))
                    
                    # 记录迁移历史
                    execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    conn.execute(text("""
                        INSERT INTO migration_history 
                        (migration_name, database_name, execution_time_ms, checksum, status)
                        VALUES (:name, :db_name, :exec_time, :checksum, 'success')
                    """), {
                        "name": migration['filename'],
                        "db_name": db_name,
                        "exec_time": execution_time,
                        "checksum": migration['checksum']
                    })
                    
                    # 提交事务
                    trans.commit()
                    
                    logger.info(f"迁移 {migration['filename']} 执行成功 ({execution_time}ms)")
                    return True
                    
                except Exception as e:
                    # 回滚事务
                    trans.rollback()
                    
                    # 记录失败
                    conn.execute(text("""
                        INSERT INTO migration_history 
                        (migration_name, database_name, status, error_message)
                        VALUES (:name, :db_name, 'failed', :error)
                    """), {
                        "name": migration['filename'],
                        "db_name": db_name,
                        "error": str(e)
                    })
                    conn.commit()
                    
                    logger.error(f"迁移 {migration['filename']} 执行失败: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"迁移 {migration['filename']} 连接失败: {e}")
            return False
    
    def _split_sql_statements(self, content: str) -> List[str]:
        """分割SQL语句"""
        # 移除注释
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        content = ' '.join(lines)
        
        # 按分号分割语句
        statements = []
        current_statement = ""
        
        for char in content:
            current_statement += char
            if char == ';':
                statement = current_statement.strip()
                if statement and not statement.upper().startswith('USE '):
                    statements.append(statement)
                current_statement = ""
        
        # 添加最后一个语句（如果没有分号结尾）
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    def run_migrations(self, target_version: str = None) -> bool:
        """运行所有待执行的迁移"""
        migrations = self.get_migration_files()
        
        if not migrations:
            logger.info("没有找到迁移文件")
            return True
        
        executed_count = 0
        failed_count = 0
        
        for migration in migrations:
            # 检查版本限制
            if target_version and migration['version'] > target_version:
                continue
            
            # 检查是否已执行
            if self.is_migration_executed(migration):
                logger.debug(f"迁移 {migration['filename']} 已执行，跳过")
                continue
            
            # 执行迁移
            if self.execute_migration(migration):
                executed_count += 1
            else:
                failed_count += 1
        
        logger.info(f"迁移完成: 执行 {executed_count} 个，失败 {failed_count} 个")
        return failed_count == 0
    
    def get_migration_status(self) -> Dict:
        """获取迁移状态"""
        migrations = self.get_migration_files()
        status = {
            'total': len(migrations),
            'executed': 0,
            'pending': 0,
            'failed': 0,
            'details': []
        }
        
        for migration in migrations:
            is_executed = self.is_migration_executed(migration)
            
            detail = {
                'filename': migration['filename'],
                'version': migration['version'],
                'database': migration['database'],
                'description': migration['description'],
                'executed': is_executed
            }
            
            if is_executed:
                status['executed'] += 1
            else:
                status['pending'] += 1
            
            status['details'].append(detail)
        
        return status


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库迁移管理器')
    parser.add_argument('command', choices=['status', 'migrate'], help='命令')
    parser.add_argument('--version', help='目标版本')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    manager = MigrationManager()
    
    if args.command == 'status':
        status = manager.get_migration_status()
        print(f"迁移状态: {status['executed']}/{status['total']} 已执行")
        
        for detail in status['details']:
            status_text = "✓" if detail['executed'] else "✗"
            print(f"  {status_text} {detail['filename']} ({detail['database']})")
    
    elif args.command == 'migrate':
        success = manager.run_migrations(args.version)
        if success:
            print("迁移完成")
        else:
            print("迁移失败")
            sys.exit(1)


if __name__ == '__main__':
    main()
