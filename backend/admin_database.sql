-- ComfyUI 后台管理系统数据库初始化脚本
-- 创建时间: 2024-01-XX
-- 数据库: comfyui_admin

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS comfyui_admin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE comfyui_admin;

-- 创建角色表
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(32) UNIQUE NOT NULL COMMENT '角色名称',
    description VARCHAR(128) DEFAULT '' COMMENT '角色描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(32) UNIQUE NOT NULL COMMENT '用户名',
    password_hash VARCHAR(128) NOT NULL COMMENT '密码哈希',
    email VARCHAR(64) UNIQUE COMMENT '邮箱',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    is_superuser BOOLEAN DEFAULT FALSE COMMENT '是否超级管理员',
    role_id INT COMMENT '角色ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    last_login TIMESTAMP NULL COMMENT '最后登录时间',
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 插入初始角色数据
INSERT INTO roles (name, description) VALUES 
('admin', '系统管理员'),
('user', '普通用户'),
('guest', '访客用户')
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- 插入超级管理员账号
-- 用户名: admin
-- 密码: admin (bcrypt哈希)
INSERT INTO users (username, password_hash, email, is_active, is_superuser, role_id) 
VALUES (
    'admin', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uO.G', 
    'admin@comfyui.com', 
    TRUE, 
    TRUE, 
    (SELECT id FROM roles WHERE name = 'admin')
) ON DUPLICATE KEY UPDATE 
    password_hash = VALUES(password_hash),
    email = VALUES(email),
    is_active = VALUES(is_active),
    is_superuser = VALUES(is_superuser),
    role_id = VALUES(role_id);

-- 验证数据插入结果
SELECT '=== 角色数据 ===' as info;
SELECT * FROM roles;

SELECT '=== 用户数据 ===' as info;
SELECT 
    u.id, 
    u.username, 
    u.email, 
    u.is_active, 
    u.is_superuser, 
    r.name as role_name,
    u.created_at
FROM users u 
LEFT JOIN roles r ON u.role_id = r.id;

-- 显示登录信息
SELECT '=== 登录信息 ===' as info;
SELECT 
    '超级管理员账号创建成功！' as message,
    '用户名: admin' as username,
    '密码: admin' as password,
    '请及时修改密码！' as warning; 