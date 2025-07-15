-- 为客户端用户表添加认证字段
-- 执行时间: 2025-07-15

USE comfyui_client;

-- 添加用户名和密码字段
ALTER TABLE client_users 
ADD COLUMN username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名' AFTER client_id,
ADD COLUMN password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希' AFTER username;

-- 添加用户名索引
ALTER TABLE client_users 
ADD INDEX idx_username (username);

-- 更新现有数据（如果有的话）
-- 为现有记录设置默认用户名和密码
UPDATE client_users 
SET username = CONCAT('user_', id),
    password_hash = '$2b$12$LQv3c1yqBWVHxkd0LQ4lqO.8kJIGYNvFAUOrgHzxAhJ5S9xtLg7EK' -- 对应密码 "password123"
WHERE username IS NULL OR username = '';

-- 插入测试用户数据
INSERT IGNORE INTO client_users (client_id, username, password_hash, nickname, quota_limit, is_active) VALUES
('test-client-z', 'z', '$2b$12$LQv3c1yqBWVHxkd0LQ4lqO.8kJIGYNvFAUOrgHzxAhJ5S9xtLg7EK', '测试用户', 100, TRUE),
('demo-client-001', 'demo', '$2b$12$LQv3c1yqBWVHxkd0LQ4lqO.8kJIGYNvFAUOrgHzxAhJ5S9xtLg7EK', '演示用户', 50, TRUE),
('admin-client-001', 'admin', '$2b$12$LQv3c1yqBWVHxkd0LQ4lqO.8kJIGYNvFAUOrgHzxAhJ5S9xtLg7EK', '管理员用户', 1000, TRUE);

-- 验证数据
SELECT username, nickname, quota_limit, is_active, created_at FROM client_users;
