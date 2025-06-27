-- ComfyUI 后台管理系统数据库更新脚本
-- 添加节点、任务、系统日志等表

USE comfyui_admin;

-- 创建节点表
CREATE TABLE IF NOT EXISTS nodes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL COMMENT '节点名称',
    ip_address VARCHAR(45) NOT NULL COMMENT 'IP地址',
    port INT DEFAULT 8188 COMMENT '端口',
    status VARCHAR(20) DEFAULT 'offline' COMMENT '状态: online, offline, busy, maintenance',
    gpu_info JSON COMMENT 'GPU信息',
    cpu_info JSON COMMENT 'CPU信息',
    memory_info JSON COMMENT '内存信息',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    last_heartbeat TIMESTAMP NULL COMMENT '最后心跳时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='节点表';

-- 创建任务表
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) UNIQUE NOT NULL COMMENT '任务UUID',
    task_type VARCHAR(20) NOT NULL COMMENT '任务类型: image, video',
    status VARCHAR(20) DEFAULT 'queued' COMMENT '状态: queued, running, completed, failed',
    priority INT DEFAULT 0 COMMENT '优先级',
    prompt TEXT COMMENT '提示词',
    negative_prompt TEXT COMMENT '负面提示词',
    parameters JSON COMMENT '任务参数',
    result_url VARCHAR(255) COMMENT '结果URL',
    error_message TEXT COMMENT '错误信息',
    progress FLOAT DEFAULT 0.0 COMMENT '进度',
    user_id INT COMMENT '用户ID',
    node_id INT COMMENT '节点ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_at TIMESTAMP NULL COMMENT '开始时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务表';

-- 创建系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level VARCHAR(10) NOT NULL COMMENT '日志级别: INFO, WARNING, ERROR',
    module VARCHAR(50) NOT NULL COMMENT '模块名称',
    message TEXT NOT NULL COMMENT '日志消息',
    details JSON COMMENT '详细信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';

-- 插入一些测试数据
INSERT INTO nodes (name, ip_address, port, status, gpu_info, cpu_info, memory_info) VALUES 
('主节点', '127.0.0.1', 8188, 'online', 
 '{"gpu_name": "RTX 4090", "memory_total": "24GB", "memory_used": "12GB"}',
 '{"cpu_name": "Intel i9-13900K", "cores": 24, "usage": 45.2}',
 '{"total": "64GB", "used": "32GB", "available": "32GB"}'
) ON DUPLICATE KEY UPDATE name = VALUES(name);

-- 插入一些测试任务
INSERT INTO tasks (task_id, task_type, status, prompt, parameters, user_id) VALUES 
('test-task-001', 'image', 'completed', '一只可爱的小猫', 
 '{"width": 512, "height": 512, "steps": 20}', 1),
('test-task-002', 'video', 'running', '美丽的风景', 
 '{"duration": 5.0, "fps": 8}', 1)
ON DUPLICATE KEY UPDATE task_type = VALUES(task_type);

-- 插入一些系统日志
INSERT INTO system_logs (level, module, message, details) VALUES 
('INFO', 'system', '系统启动成功', '{"version": "1.0.0"}'),
('WARNING', 'node', '节点响应超时', '{"node_id": 1, "timeout": 30}'),
('ERROR', 'task', '任务执行失败', '{"task_id": "test-task-003", "error": "GPU内存不足"}')
ON DUPLICATE KEY UPDATE message = VALUES(message);

-- 验证表结构
SHOW TABLES;

-- 显示各表数据统计
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'nodes', COUNT(*) FROM nodes
UNION ALL
SELECT 'tasks', COUNT(*) FROM tasks
UNION ALL
SELECT 'system_logs', COUNT(*) FROM system_logs; 