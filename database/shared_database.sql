-- 共享数据库
-- 存储客户端和管理端都需要访问的数据

CREATE DATABASE IF NOT EXISTS comfyui_shared CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE comfyui_shared;

-- 全局任务表（统一任务管理）
CREATE TABLE global_tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(36) UNIQUE NOT NULL COMMENT '任务UUID',
    source_type ENUM('client', 'admin') NOT NULL COMMENT '任务来源',
    source_user_id VARCHAR(36) NOT NULL COMMENT '来源用户ID',
    task_type ENUM('text_to_image', 'image_to_video') NOT NULL COMMENT '任务类型',
    workflow_name VARCHAR(100) NOT NULL COMMENT '工作流名称',
    prompt TEXT COMMENT '正向提示词',
    negative_prompt TEXT COMMENT '反向提示词',
    status ENUM('queued', 'processing', 'completed', 'failed', 'cancelled') DEFAULT 'queued' COMMENT '任务状态',
    priority INT DEFAULT 1 COMMENT '任务优先级',
    progress DECIMAL(5,2) DEFAULT 0.00 COMMENT '进度百分比',
    message TEXT COMMENT '状态消息',
    error_message TEXT COMMENT '错误消息',
    celery_task_id VARCHAR(36) COMMENT 'Celery任务ID',
    node_id VARCHAR(100) COMMENT '执行节点ID',
    estimated_time INT COMMENT '预估处理时间(秒)',
    actual_time INT COMMENT '实际处理时间(秒)',
    started_at TIMESTAMP NULL COMMENT '开始处理时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_source_type (source_type),
    INDEX idx_source_user_id (source_user_id),
    INDEX idx_status (status),
    INDEX idx_task_type (task_type),
    INDEX idx_created_at (created_at),
    INDEX idx_node_id (node_id),
    INDEX idx_celery_task_id (celery_task_id)
) COMMENT '全局任务表';

-- 全局任务参数表
CREATE TABLE global_task_parameters (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL COMMENT '任务ID',
    parameter_name VARCHAR(100) NOT NULL COMMENT '参数名称',
    parameter_value TEXT COMMENT '参数值',
    parameter_type ENUM('string', 'int', 'float', 'boolean', 'json') DEFAULT 'string' COMMENT '参数类型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES global_tasks(id) ON DELETE CASCADE,
    INDEX idx_task_id (task_id),
    INDEX idx_parameter_name (parameter_name)
) COMMENT '全局任务参数表';

-- 全局任务结果表
CREATE TABLE global_task_results (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id BIGINT NOT NULL COMMENT '任务ID',
    result_type ENUM('image', 'video', 'json', 'file') NOT NULL COMMENT '结果类型',
    file_path VARCHAR(500) COMMENT '文件路径',
    file_name VARCHAR(255) COMMENT '文件名',
    file_size BIGINT COMMENT '文件大小(字节)',
    mime_type VARCHAR(100) COMMENT 'MIME类型',
    width INT COMMENT '图片/视频宽度',
    height INT COMMENT '图片/视频高度',
    duration DECIMAL(10,2) COMMENT '视频时长(秒)',
    thumbnail_path VARCHAR(500) COMMENT '缩略图路径',
    result_metadata JSON COMMENT '元数据',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES global_tasks(id) ON DELETE CASCADE,
    INDEX idx_task_id (task_id),
    INDEX idx_result_type (result_type)
) COMMENT '全局任务结果表';

-- 节点任务分配表
CREATE TABLE node_task_assignments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    node_id VARCHAR(100) NOT NULL COMMENT '节点ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '分配时间',
    started_at TIMESTAMP NULL COMMENT '开始时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    status ENUM('assigned', 'running', 'completed', 'failed', 'cancelled') DEFAULT 'assigned' COMMENT '分配状态',
    FOREIGN KEY (task_id) REFERENCES global_tasks(id) ON DELETE CASCADE,
    INDEX idx_node_id (node_id),
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_assigned_at (assigned_at)
) COMMENT '节点任务分配表';

-- 全局文件表
CREATE TABLE global_files (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    file_id VARCHAR(36) UNIQUE NOT NULL COMMENT '文件UUID',
    source_type ENUM('client', 'admin', 'system') NOT NULL COMMENT '文件来源',
    source_user_id VARCHAR(36) COMMENT '来源用户ID',
    original_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_name VARCHAR(255) NOT NULL COMMENT '存储文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
    file_size BIGINT NOT NULL COMMENT '文件大小(字节)',
    mime_type VARCHAR(100) NOT NULL COMMENT 'MIME类型',
    file_hash VARCHAR(64) COMMENT '文件哈希',
    file_type ENUM('image', 'video', 'audio', 'document', 'other') NOT NULL COMMENT '文件类型',
    width INT COMMENT '图片/视频宽度',
    height INT COMMENT '图片/视频高度',
    duration DECIMAL(10,2) COMMENT '视频/音频时长(秒)',
    metadata JSON COMMENT '元数据',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开',
    is_temporary BOOLEAN DEFAULT FALSE COMMENT '是否临时文件',
    expires_at TIMESTAMP NULL COMMENT '过期时间',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_file_id (file_id),
    INDEX idx_source_type (source_type),
    INDEX idx_source_user_id (source_user_id),
    INDEX idx_file_type (file_type),
    INDEX idx_file_hash (file_hash),
    INDEX idx_is_temporary (is_temporary),
    INDEX idx_expires_at (expires_at)
) COMMENT '全局文件表';

-- 任务队列状态表（Redis备份）
CREATE TABLE task_queue_status (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(36) UNIQUE NOT NULL COMMENT '任务ID',
    queue_name VARCHAR(100) NOT NULL COMMENT '队列名称',
    status ENUM('pending', 'started', 'retry', 'failure', 'success') NOT NULL COMMENT '队列状态',
    result TEXT COMMENT '执行结果',
    traceback TEXT COMMENT '错误堆栈',
    worker VARCHAR(100) COMMENT '工作进程',
    retries INT DEFAULT 0 COMMENT '重试次数',
    eta TIMESTAMP NULL COMMENT '预计执行时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_queue_name (queue_name),
    INDEX idx_status (status),
    INDEX idx_worker (worker)
) COMMENT '任务队列状态表';

-- 系统统计表
CREATE TABLE system_statistics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    stat_date DATE NOT NULL COMMENT '统计日期',
    total_tasks INT DEFAULT 0 COMMENT '总任务数',
    completed_tasks INT DEFAULT 0 COMMENT '完成任务数',
    failed_tasks INT DEFAULT 0 COMMENT '失败任务数',
    client_tasks INT DEFAULT 0 COMMENT '客户端任务数',
    admin_tasks INT DEFAULT 0 COMMENT '管理端任务数',
    text_to_image_tasks INT DEFAULT 0 COMMENT '文生图任务数',
    image_to_video_tasks INT DEFAULT 0 COMMENT '图生视频任务数',
    total_processing_time BIGINT DEFAULT 0 COMMENT '总处理时间(秒)',
    average_processing_time DECIMAL(10,2) DEFAULT 0.00 COMMENT '平均处理时间(秒)',
    active_nodes INT DEFAULT 0 COMMENT '活跃节点数',
    total_file_size BIGINT DEFAULT 0 COMMENT '总文件大小(字节)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stat_date (stat_date),
    INDEX idx_stat_date (stat_date)
) COMMENT '系统统计表';
