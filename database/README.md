# ComfyUI Web Service 数据库设计

## 数据库架构概述

本项目采用**三数据库分离架构**，将不同功能模块的数据分别存储，提高系统的可维护性和安全性。

### 数据库分工

#### 1. 客户端数据库 (comfyui_client)
- **用途**: 存储客户端用户数据和基础任务信息
- **访问者**: Client-ComfyUI.html 前端
- **特点**: 
  - 简化的用户管理（基于客户端ID）
  - 基础任务状态跟踪
  - 文件上传管理
  - 访问日志记录

#### 2. 管理后台数据库 (comfyui_admin)  
- **用途**: 存储系统管理、配置和监控数据
- **访问者**: Vue.js 管理后台
- **特点**:
  - 完整的管理员用户系统
  - 工作流模板管理
  - 模型管理
  - 节点管理
  - 系统监控和日志

#### 3. 共享数据库 (comfyui_shared)
- **用途**: 存储需要跨系统访问的核心数据
- **访问者**: 客户端和管理端都可访问
- **特点**:
  - 统一的任务管理
  - 全局文件存储
  - 节点任务分配
  - 系统统计数据

## 数据库表结构

### 客户端数据库表
- `client_users` - 客户端用户表
- `client_tasks` - 客户端任务表  
- `client_task_parameters` - 客户端任务参数表
- `client_task_results` - 客户端任务结果表
- `client_uploads` - 客户端上传文件表
- `client_access_logs` - 客户端访问日志表

### 管理后台数据库表
- `admin_users` - 管理员用户表
- `workflow_templates` - 工作流模板表
- `workflow_parameters` - 工作流参数配置表
- `models` - 模型表
- `workflow_models` - 工作流模型关联表
- `nodes` - 节点表
- `system_logs` - 系统日志表
- `performance_metrics` - 性能监控表
- `system_configs` - 系统配置表

### 共享数据库表
- `global_tasks` - 全局任务表
- `global_task_parameters` - 全局任务参数表
- `global_task_results` - 全局任务结果表
- `node_task_assignments` - 节点任务分配表
- `global_files` - 全局文件表
- `task_queue_status` - 任务队列状态表
- `system_statistics` - 系统统计表

## 数据流程

### 任务提交流程
1. **客户端提交任务**:
   - 数据写入 `client_tasks`
   - 同步到 `global_tasks`
   - 任务分配到节点 `node_task_assignments`

2. **管理端监控**:
   - 从 `global_tasks` 读取所有任务
   - 从 `nodes` 读取节点状态
   - 写入监控数据到 `performance_metrics`

### 文件管理流程
1. **文件上传**:
   - 客户端上传记录到 `client_uploads`
   - 全局文件信息记录到 `global_files`

2. **结果文件**:
   - 任务结果文件记录到 `global_task_results`
   - 客户端可通过 `client_task_results` 查看

## 安装和配置

### 1. 创建数据库和用户
```bash
mysql -u root -p < database/setup_databases.sql
```

### 2. 创建表结构
```bash
# 创建客户端数据库表
mysql -u root -p < database/client_database.sql

# 创建管理后台数据库表  
mysql -u root -p < database/admin_database.sql

# 创建共享数据库表
mysql -u root -p < database/shared_database.sql
```

### 3. 配置应用连接
修改 `backend/config.yaml` 中的数据库配置：

```yaml
# MySQL数据库配置
mysql:
  client:
    host: localhost
    port: 3306
    user: comfyui_client_user
    password: "client_password_123"
    database: comfyui_client
    
  admin:
    host: localhost
    port: 3306
    user: comfyui_admin_user
    password: "admin_password_456"
    database: comfyui_admin
    
  shared:
    host: localhost
    port: 3306
    user: comfyui_shared_user
    password: "shared_password_789"
    database: comfyui_shared
```

## 数据同步策略

### 实时同步
- 客户端任务 → 共享数据库（实时）
- 任务状态更新 → 所有相关表（实时）

### 定时同步
- 统计数据汇总（每小时）
- 性能指标聚合（每分钟）

### 数据清理
- 客户端数据：30天自动清理
- 临时文件：24小时自动清理
- 日志数据：根据级别分别保留7-90天

## 安全考虑

### 权限分离
- 客户端用户：只能访问客户端和共享数据库的读写权限
- 管理端用户：完全访问管理端数据库，共享数据库读写权限
- 共享用户：仅访问共享数据库

### 数据隔离
- 客户端数据与管理端数据完全分离
- 敏感配置信息仅存储在管理端数据库
- 客户端无法直接访问系统配置和节点信息

### 备份策略
- 每日自动备份所有数据库
- 备份文件保留30天
- 支持增量备份和全量备份

## 性能优化

### 索引策略
- 所有主要查询字段都建立了索引
- 复合索引优化多条件查询
- 定期分析和优化慢查询

### 连接池配置
- 客户端数据库：10个连接，最大20个
- 管理端数据库：5个连接，最大10个  
- 共享数据库：15个连接，最大30个

### 分区策略
- 大表按时间分区（如日志表、统计表）
- 历史数据自动归档

## 监控和维护

### 监控指标
- 数据库连接数
- 查询响应时间
- 磁盘使用率
- 表大小增长

### 维护任务
- 定期优化表结构
- 清理过期数据
- 更新统计信息
- 检查索引效率
