-- ComfyUI管理后台数据库
-- 专门用于系统管理、节点管理、监控等功能

CREATE DATABASE IF NOT EXISTS comfyui_admin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE comfyui_admin;

-- 管理员用户表
CREATE TABLE admin_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    display_name VARCHAR(100) COMMENT '显示名称',
    role ENUM('super_admin', 'admin', 'operator', 'viewer') DEFAULT 'viewer' COMMENT '管理员角色',
    status ENUM('active', 'inactive', 'locked') DEFAULT 'active' COMMENT '用户状态',
    permissions JSON COMMENT '权限列表',
    last_login_ip VARCHAR(45) COMMENT '最后登录IP',
    login_count INT DEFAULT 0 COMMENT '登录次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_status (status)
) COMMENT '管理员用户表';

-- 工作流模板表
CREATE TABLE workflow_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL COMMENT '工作流名称',
    display_name VARCHAR(200) COMMENT '显示名称',
    task_type ENUM('text_to_image', 'image_to_video') NOT NULL COMMENT '任务类型',
    version VARCHAR(20) DEFAULT '1.0' COMMENT '版本',
    description TEXT COMMENT '描述',
    workflow_file VARCHAR(500) NOT NULL COMMENT '工作流文件路径',
    config_data JSON COMMENT '配置数据',
    is_enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否默认工作流',
    max_concurrent_tasks INT DEFAULT 4 COMMENT '最大并发任务数',
    estimated_time INT DEFAULT 60 COMMENT '预估处理时间(秒)',
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    success_rate DECIMAL(5,2) DEFAULT 0.00 COMMENT '成功率',
    created_by BIGINT COMMENT '创建者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES admin_users(id) ON DELETE SET NULL,
    INDEX idx_name (name),
    INDEX idx_task_type (task_type),
    INDEX idx_is_enabled (is_enabled)
) COMMENT '工作流模板表';

-- 工作流参数配置表
CREATE TABLE workflow_parameters (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT NOT NULL COMMENT '工作流ID',
    parameter_name VARCHAR(100) NOT NULL COMMENT '参数名称',
    parameter_type ENUM('string', 'int', 'float', 'boolean', 'select', 'file') NOT NULL COMMENT '参数类型',
    default_value TEXT COMMENT '默认值',
    min_value DECIMAL(20,6) COMMENT '最小值',
    max_value DECIMAL(20,6) COMMENT '最大值',
    options JSON COMMENT '选项列表(用于select类型)',
    is_required BOOLEAN DEFAULT FALSE COMMENT '是否必需',
    display_name VARCHAR(200) COMMENT '显示名称',
    description TEXT COMMENT '参数描述',
    node_id VARCHAR(50) COMMENT '节点ID',
    field_path VARCHAR(200) COMMENT '字段路径',
    sort_order INT DEFAULT 0 COMMENT '排序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflow_templates(id) ON DELETE CASCADE,
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_parameter_name (parameter_name)
) COMMENT '工作流参数配置表';

-- 模型表
CREATE TABLE models (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL COMMENT '模型名称',
    display_name VARCHAR(300) COMMENT '显示名称',
    model_type ENUM('checkpoint', 'lora', 'vae', 'controlnet', 'embedding') NOT NULL COMMENT '模型类型',
    file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
    file_size BIGINT COMMENT '文件大小(字节)',
    file_hash VARCHAR(64) COMMENT '文件哈希',
    version VARCHAR(50) COMMENT '版本',
    description TEXT COMMENT '描述',
    tags JSON COMMENT '标签',
    base_model VARCHAR(100) COMMENT '基础模型',
    resolution VARCHAR(20) COMMENT '支持分辨率',
    is_enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    usage_count INT DEFAULT 0 COMMENT '使用次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_model_type (model_type),
    INDEX idx_is_enabled (is_enabled),
    INDEX idx_file_hash (file_hash)
) COMMENT '模型表';

-- 工作流模型关联表
CREATE TABLE workflow_models (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    workflow_id BIGINT NOT NULL COMMENT '工作流ID',
    model_id BIGINT NOT NULL COMMENT '模型ID',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否默认模型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflow_templates(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
    UNIQUE KEY uk_workflow_model (workflow_id, model_id),
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_model_id (model_id)
) COMMENT '工作流模型关联表';

-- 节点表
CREATE TABLE nodes (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    node_id VARCHAR(100) UNIQUE NOT NULL COMMENT '节点ID',
    name VARCHAR(200) NOT NULL COMMENT '节点名称',
    host VARCHAR(255) NOT NULL COMMENT '主机地址',
    port INT NOT NULL COMMENT '端口',
    api_url VARCHAR(500) NOT NULL COMMENT 'API地址',
    node_type ENUM('master', 'worker') DEFAULT 'worker' COMMENT '节点类型',
    status ENUM('online', 'offline', 'busy', 'error') DEFAULT 'offline' COMMENT '节点状态',
    current_load INT DEFAULT 0 COMMENT '当前负载',
    max_load INT DEFAULT 4 COMMENT '最大负载',
    cpu_usage DECIMAL(5,2) DEFAULT 0.00 COMMENT 'CPU使用率',
    memory_usage DECIMAL(5,2) DEFAULT 0.00 COMMENT '内存使用率',
    gpu_usage DECIMAL(5,2) DEFAULT 0.00 COMMENT 'GPU使用率',
    gpu_memory_usage DECIMAL(5,2) DEFAULT 0.00 COMMENT 'GPU内存使用率',
    supported_task_types JSON COMMENT '支持的任务类型',
    capabilities JSON COMMENT '节点能力',
    version VARCHAR(50) COMMENT '版本',
    last_heartbeat TIMESTAMP NULL COMMENT '最后心跳时间',
    total_tasks INT DEFAULT 0 COMMENT '总任务数',
    completed_tasks INT DEFAULT 0 COMMENT '完成任务数',
    failed_tasks INT DEFAULT 0 COMMENT '失败任务数',
    average_processing_time DECIMAL(10,2) DEFAULT 0.00 COMMENT '平均处理时间(秒)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_node_id (node_id),
    INDEX idx_status (status),
    INDEX idx_node_type (node_type),
    INDEX idx_last_heartbeat (last_heartbeat)
) COMMENT '节点表';

-- 系统日志表
CREATE TABLE system_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') NOT NULL COMMENT '日志级别',
    module VARCHAR(100) COMMENT '模块名称',
    message TEXT NOT NULL COMMENT '日志消息',
    details JSON COMMENT '详细信息',
    admin_user_id BIGINT COMMENT '管理员用户ID',
    task_id VARCHAR(36) COMMENT '任务ID',
    node_id BIGINT COMMENT '节点ID',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE SET NULL,
    INDEX idx_level (level),
    INDEX idx_module (module),
    INDEX idx_created_at (created_at),
    INDEX idx_admin_user_id (admin_user_id)
) COMMENT '系统日志表';

-- 性能监控表
CREATE TABLE performance_metrics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    metric_type ENUM('system', 'task', 'node', 'api') NOT NULL COMMENT '指标类型',
    metric_name VARCHAR(100) NOT NULL COMMENT '指标名称',
    metric_value DECIMAL(20,6) NOT NULL COMMENT '指标值',
    unit VARCHAR(20) COMMENT '单位',
    tags JSON COMMENT '标签',
    node_id BIGINT COMMENT '节点ID',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE,
    INDEX idx_metric_type (metric_type),
    INDEX idx_metric_name (metric_name),
    INDEX idx_recorded_at (recorded_at),
    INDEX idx_node_id (node_id)
) COMMENT '性能监控表';

-- 系统配置表
CREATE TABLE system_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(100) UNIQUE NOT NULL COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_type ENUM('string', 'int', 'float', 'boolean', 'json') DEFAULT 'string' COMMENT '配置类型',
    description TEXT COMMENT '描述',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key),
    INDEX idx_is_public (is_public)
) COMMENT '系统配置表';

-- 插入默认管理员
INSERT INTO admin_users (username, email, password_hash, display_name, role, status) VALUES
('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx/LBK2.', '系统管理员', 'super_admin', 'active');

-- 插入系统配置
INSERT INTO system_configs (config_key, config_value, config_type, description, is_public) VALUES
('system.name', 'ComfyUI Web Service', 'string', '系统名称', TRUE),
('system.version', '2.0.0', 'string', '系统版本', TRUE),
('task.default_priority', '1', 'int', '默认任务优先级', FALSE),
('task.max_concurrent', '10', 'int', '最大并发任务数', FALSE),
('file.max_size', '104857600', 'int', '最大文件大小(100MB)', FALSE),
('api.rate_limit', '100', 'int', 'API速率限制(每分钟)', FALSE);
