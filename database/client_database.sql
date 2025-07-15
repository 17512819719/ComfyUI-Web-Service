-- ComfyUI客户端数据库
-- 专门用于客户端用户的任务提交和结果查看

CREATE DATABASE IF NOT EXISTS comfyui_client CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE comfyui_client;

-- 客户端用户表（简化版）
CREATE TABLE client_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id VARCHAR(36) UNIQUE NOT NULL COMMENT '客户端ID（UUID）',
    session_token VARCHAR(64) UNIQUE COMMENT '会话令牌',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    nickname VARCHAR(100) COMMENT '昵称',
    quota_limit INT DEFAULT 50 COMMENT '每日配额限制',
    quota_used INT DEFAULT 0 COMMENT '今日已使用配额',
    quota_reset_date DATE COMMENT '配额重置日期',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_access_at TIMESTAMP NULL,
    INDEX idx_client_id (client_id),
    INDEX idx_session_token (session_token),
    INDEX idx_ip_address (ip_address)
) COMMENT '客户端用户表';

-- 客户端任务表
CREATE TABLE client_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(36) UNIQUE NOT NULL COMMENT '任务UUID',
    client_id VARCHAR(36) NOT NULL COMMENT '客户端ID',
    task_type ENUM('text_to_image', 'image_to_video') NOT NULL COMMENT '任务类型',
    workflow_name VARCHAR(100) NOT NULL COMMENT '工作流名称',
    prompt TEXT COMMENT '正向提示词',
    negative_prompt TEXT COMMENT '反向提示词',
    status ENUM('queued', 'processing', 'completed', 'failed', 'cancelled') DEFAULT 'queued' COMMENT '任务状态',
    progress DECIMAL(5,2) DEFAULT 0.00 COMMENT '进度百分比',
    message TEXT COMMENT '状态消息',
    error_message TEXT COMMENT '错误消息',
    estimated_time INT COMMENT '预估处理时间(秒)',
    actual_time INT COMMENT '实际处理时间(秒)',
    started_at TIMESTAMP NULL COMMENT '开始处理时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_client_id (client_id),
    INDEX idx_status (status),
    INDEX idx_task_type (task_type),
    INDEX idx_created_at (created_at)
) COMMENT '客户端任务表';

-- 客户端任务参数表
CREATE TABLE client_task_parameters (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL COMMENT '任务ID',
    parameter_name VARCHAR(100) NOT NULL COMMENT '参数名称',
    parameter_value TEXT COMMENT '参数值',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES client_tasks(id) ON DELETE CASCADE,
    INDEX idx_task_id (task_id)
) COMMENT '客户端任务参数表';

-- 客户端任务结果表
CREATE TABLE client_task_results (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL COMMENT '任务ID',
    result_type ENUM('image', 'video') NOT NULL COMMENT '结果类型',
    file_path VARCHAR(500) COMMENT '文件路径',
    file_name VARCHAR(255) COMMENT '文件名',
    file_size BIGINT COMMENT '文件大小(字节)',
    width INT COMMENT '图片/视频宽度',
    height INT COMMENT '图片/视频高度',
    duration DECIMAL(10,2) COMMENT '视频时长(秒)',
    thumbnail_path VARCHAR(500) COMMENT '缩略图路径',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES client_tasks(id) ON DELETE CASCADE,
    INDEX idx_task_id (task_id),
    INDEX idx_result_type (result_type)
) COMMENT '客户端任务结果表';

-- 客户端上传文件表
CREATE TABLE client_uploads (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    file_id VARCHAR(36) UNIQUE NOT NULL COMMENT '文件UUID',
    client_id VARCHAR(36) NOT NULL COMMENT '客户端ID',
    original_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
    file_size BIGINT NOT NULL COMMENT '文件大小(字节)',
    mime_type VARCHAR(100) NOT NULL COMMENT 'MIME类型',
    width INT COMMENT '图片宽度',
    height INT COMMENT '图片高度',
    is_processed BOOLEAN DEFAULT FALSE COMMENT '是否已处理',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_file_id (file_id),
    INDEX idx_client_id (client_id),
    INDEX idx_created_at (created_at)
) COMMENT '客户端上传文件表';

-- 客户端访问日志表（简化版）
CREATE TABLE client_access_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id VARCHAR(36) COMMENT '客户端ID',
    action VARCHAR(100) NOT NULL COMMENT '操作类型',
    endpoint VARCHAR(200) COMMENT 'API端点',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    response_time INT COMMENT '响应时间(毫秒)',
    status_code INT COMMENT '状态码',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_client_id (client_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) COMMENT '客户端访问日志表';

-- 插入示例数据
INSERT INTO client_users (client_id, nickname, quota_limit) VALUES
('demo-client-001', '演示用户', 100);
