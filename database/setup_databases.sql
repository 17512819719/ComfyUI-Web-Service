-- 数据库初始化脚本
-- 创建数据库用户和设置权限

-- 创建数据库用户
CREATE USER IF NOT EXISTS 'comfyui_client_user'@'localhost' IDENTIFIED BY 'client_password_123';
CREATE USER IF NOT EXISTS 'comfyui_admin_user'@'localhost' IDENTIFIED BY 'admin_password_456';
CREATE USER IF NOT EXISTS 'comfyui_shared_user'@'localhost' IDENTIFIED BY 'shared_password_789';

-- 创建数据库
CREATE DATABASE IF NOT EXISTS comfyui_client CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS comfyui_admin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS comfyui_shared CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 设置客户端用户权限
GRANT SELECT, INSERT, UPDATE, DELETE ON comfyui_client.* TO 'comfyui_client_user'@'localhost';
GRANT SELECT, INSERT, UPDATE ON comfyui_shared.* TO 'comfyui_client_user'@'localhost';

-- 设置管理端用户权限
GRANT ALL PRIVILEGES ON comfyui_admin.* TO 'comfyui_admin_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON comfyui_shared.* TO 'comfyui_admin_user'@'localhost';

-- 设置共享数据库用户权限
GRANT SELECT, INSERT, UPDATE, DELETE ON comfyui_shared.* TO 'comfyui_shared_user'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;

-- 显示创建的用户
SELECT User, Host FROM mysql.user WHERE User LIKE 'comfyui%';

-- 显示数据库
SHOW DATABASES LIKE 'comfyui%';
