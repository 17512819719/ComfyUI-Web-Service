# 数据库迁移系统

## 概述

数据库迁移系统用于管理数据库结构的版本化变更，确保在不同环境中部署时能够自动处理数据库升级。

## 迁移文件命名规范

```
YYYY_MM_DD_description.sql
```

例如：
- `2024_07_22_add_user_avatar_field.sql`
- `2024_07_23_create_notification_table.sql`

## 迁移文件格式

```sql
-- Database: client|admin|shared|all
-- Description: 迁移描述
-- Author: 作者名称
-- Created: YYYY-MM-DD HH:MM:SS

USE comfyui_database_name;

-- 安全的条件SQL语句
SET @column_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'comfyui_client' 
    AND TABLE_NAME = 'client_users' 
    AND COLUMN_NAME = 'avatar_url'
);

SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE client_users ADD COLUMN avatar_url VARCHAR(500) COMMENT ''用户头像URL''',
    'SELECT "avatar_url字段已存在" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 验证结果
SELECT 'add_user_avatar_field completed' as status;
```

## 使用方法

### 1. 创建新的迁移文件

```bash
# 创建新迁移
python database/tools/create_migration.py create add_user_avatar --database client --description "添加用户头像字段"
```

### 2. 编辑迁移文件

在生成的文件中添加您的SQL语句，确保使用条件语句以支持重复执行。

### 3. 执行迁移

```bash
# 运行所有待执行的迁移
python database/tools/db_manager.py migrate

# 查看迁移状态
python database/tools/db_manager.py migration-status
```

## Docker 环境

在 Docker 环境中，迁移会在容器启动时自动执行：

```bash
# 启动服务（自动执行迁移）
cd docker/
./deploy.sh start -d

# 手动执行迁移
./deploy.sh migrate

# 查看迁移状态
./deploy.sh db-status
```

## 安全的SQL编写

### 1. 检查字段是否存在

```sql
SET @column_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'comfyui_client' 
    AND TABLE_NAME = 'client_users' 
    AND COLUMN_NAME = 'new_field'
);

SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE client_users ADD COLUMN new_field VARCHAR(255)',
    'SELECT "字段已存在" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
```

### 2. 检查索引是否存在

```sql
SET @index_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.STATISTICS 
    WHERE TABLE_SCHEMA = 'comfyui_client' 
    AND TABLE_NAME = 'client_users' 
    AND INDEX_NAME = 'idx_new_field'
);

SET @sql = IF(@index_exists = 0, 
    'ALTER TABLE client_users ADD INDEX idx_new_field (new_field)',
    'SELECT "索引已存在" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
```

### 3. 检查表是否存在

```sql
SET @table_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_SCHEMA = 'comfyui_client' 
    AND TABLE_NAME = 'new_table'
);

SET @sql = IF(@table_exists = 0, 
    'CREATE TABLE new_table (id BIGINT PRIMARY KEY AUTO_INCREMENT)',
    'SELECT "表已存在" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
```

## 迁移历史

系统会在每个数据库中创建 `migration_history` 表来跟踪迁移执行状态：

```sql
CREATE TABLE migration_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    database_name VARCHAR(50) NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INT,
    checksum VARCHAR(64),
    status ENUM('success', 'failed', 'rollback') DEFAULT 'success',
    error_message TEXT
);
```

## 最佳实践

1. **向后兼容**: 添加字段时使用默认值，不要删除现有字段
2. **原子性**: 每个迁移文件应该是一个完整的变更单元
3. **可重复执行**: 使用条件语句确保迁移可以安全地重复执行
4. **测试**: 在开发环境中充分测试迁移
5. **备份**: 在生产环境执行迁移前备份数据库

## 故障排除

### 迁移失败

1. 查看迁移状态：`python database/tools/db_manager.py migration-status`
2. 检查错误日志
3. 手动修复问题后重新运行迁移

### 迁移冲突

1. 检查是否有重复的迁移文件
2. 确认迁移文件的版本号顺序
3. 解决数据库结构冲突后重新运行
