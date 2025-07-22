# 数据库结构文件

这个目录包含数据库的完整结构定义文件。

## 文件说明

- `client_database.sql` - 客户端数据库完整结构
- `admin_database.sql` - 管理后台数据库完整结构  
- `shared_database.sql` - 共享数据库完整结构

## 使用说明

这些文件是从您当前的数据库导出的完整结构，包含：
- 表结构定义
- 索引定义
- 约束定义
- 初始数据（如果有）

## 导出命令参考

如果需要重新导出数据库结构，可以使用以下命令：

```bash
# 导出客户端数据库结构
mysqldump -u root -p --no-data --routines --triggers comfyui_client > client_database.sql

# 导出管理后台数据库结构
mysqldump -u root -p --no-data --routines --triggers comfyui_admin > admin_database.sql

# 导出共享数据库结构
mysqldump -u root -p --no-data --routines --triggers comfyui_shared > shared_database.sql

# 如果需要包含数据
mysqldump -u root -p --routines --triggers comfyui_client > client_database_with_data.sql
```

## 注意事项

1. 这些文件代表数据库的当前状态
2. 新环境部署时会使用这些文件创建初始结构
3. 后续的结构变更通过迁移文件管理
4. 请定期更新这些文件以反映最新的数据库结构
