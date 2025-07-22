/*
 Navicat Premium Dump SQL

 Source Server         : okazaki
 Source Server Type    : MySQL
 Source Server Version : 80300 (8.3.0)
 Source Host           : localhost:3306
 Source Schema         : comfyui_admin

 Target Server Type    : MySQL
 Target Server Version : 80300 (8.3.0)
 File Encoding         : 65001

 Date: 22/07/2025 12:13:51
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for admin_users
-- ----------------------------
DROP TABLE IF EXISTS `admin_users`;
CREATE TABLE `admin_users`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '邮箱',
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希',
  `display_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '显示名称',
  `role` enum('super_admin','admin','operator','viewer') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'viewer' COMMENT '管理员角色',
  `status` enum('active','inactive','locked') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'active' COMMENT '用户状态',
  `permissions` json NULL COMMENT '权限列表',
  `last_login_ip` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '最后登录IP',
  `login_count` int NULL DEFAULT 0 COMMENT '登录次数',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_login_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `username`(`username`) USING BTREE,
  UNIQUE INDEX `email`(`email`) USING BTREE,
  INDEX `idx_username`(`username`) USING BTREE,
  INDEX `idx_email`(`email`) USING BTREE,
  INDEX `idx_role`(`role`) USING BTREE,
  INDEX `idx_status`(`status`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '管理员用户表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of admin_users
-- ----------------------------
INSERT INTO `admin_users` VALUES (1, 'admin', 'admin@example.com', '$2b$2b$2b$12$iXWCAhutrVU0knnNQ9YTCOoYjLufb9WzpdaL9yeYJLtvrRm5dYbie', '系统管理员', 'super_admin', 'active', NULL, NULL, 0, '2025-07-15 10:08:19', '2025-07-22 11:06:29', NULL);

-- ----------------------------
-- Table structure for models
-- ----------------------------
DROP TABLE IF EXISTS `models`;
CREATE TABLE `models`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模型名称',
  `display_name` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '显示名称',
  `model_type` enum('checkpoint','lora','vae','controlnet','embedding') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模型类型',
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `file_size` bigint NULL DEFAULT NULL COMMENT '文件大小(字节)',
  `file_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件哈希',
  `version` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '版本',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '描述',
  `tags` json NULL COMMENT '标签',
  `base_model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '基础模型',
  `resolution` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '支持分辨率',
  `is_enabled` tinyint(1) NULL DEFAULT 1 COMMENT '是否启用',
  `download_count` int NULL DEFAULT 0 COMMENT '下载次数',
  `usage_count` int NULL DEFAULT 0 COMMENT '使用次数',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_name`(`name`) USING BTREE,
  INDEX `idx_model_type`(`model_type`) USING BTREE,
  INDEX `idx_is_enabled`(`is_enabled`) USING BTREE,
  INDEX `idx_file_hash`(`file_hash`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '模型表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of models
-- ----------------------------

-- ----------------------------
-- Table structure for nodes
-- ----------------------------
DROP TABLE IF EXISTS `nodes`;
CREATE TABLE `nodes`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `node_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点ID',
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点名称',
  `host` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '主机地址',
  `port` int NOT NULL COMMENT '端口',
  `api_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'API地址',
  `node_type` enum('master','worker') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'worker' COMMENT '节点类型',
  `status` enum('online','offline','busy','error') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'offline' COMMENT '节点状态',
  `current_load` int NULL DEFAULT 0 COMMENT '当前负载',
  `max_load` int NULL DEFAULT 4 COMMENT '最大负载',
  `cpu_usage` decimal(5, 2) NULL DEFAULT 0.00 COMMENT 'CPU使用率',
  `memory_usage` decimal(5, 2) NULL DEFAULT 0.00 COMMENT '内存使用率',
  `gpu_usage` decimal(5, 2) NULL DEFAULT 0.00 COMMENT 'GPU使用率',
  `gpu_memory_usage` decimal(5, 2) NULL DEFAULT 0.00 COMMENT 'GPU内存使用率',
  `supported_task_types` json NULL COMMENT '支持的任务类型',
  `capabilities` json NULL COMMENT '节点能力',
  `version` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '版本',
  `last_heartbeat` timestamp NULL DEFAULT NULL COMMENT '最后心跳时间',
  `total_tasks` int NULL DEFAULT 0 COMMENT '总任务数',
  `completed_tasks` int NULL DEFAULT 0 COMMENT '完成任务数',
  `failed_tasks` int NULL DEFAULT 0 COMMENT '失败任务数',
  `average_processing_time` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '平均处理时间(秒)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `node_id`(`node_id`) USING BTREE,
  INDEX `idx_node_id`(`node_id`) USING BTREE,
  INDEX `idx_status`(`status`) USING BTREE,
  INDEX `idx_node_type`(`node_type`) USING BTREE,
  INDEX `idx_last_heartbeat`(`last_heartbeat`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '节点表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of nodes
-- ----------------------------

-- ----------------------------
-- Table structure for performance_metrics
-- ----------------------------
DROP TABLE IF EXISTS `performance_metrics`;
CREATE TABLE `performance_metrics`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `metric_type` enum('system','task','node','api') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '指标类型',
  `metric_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '指标名称',
  `metric_value` decimal(20, 6) NOT NULL COMMENT '指标值',
  `unit` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '单位',
  `tags` json NULL COMMENT '标签',
  `node_id` bigint NULL DEFAULT NULL COMMENT '节点ID',
  `recorded_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_metric_type`(`metric_type`) USING BTREE,
  INDEX `idx_metric_name`(`metric_name`) USING BTREE,
  INDEX `idx_recorded_at`(`recorded_at`) USING BTREE,
  INDEX `idx_node_id`(`node_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '性能监控表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of performance_metrics
-- ----------------------------

-- ----------------------------
-- Table structure for system_configs
-- ----------------------------
DROP TABLE IF EXISTS `system_configs`;
CREATE TABLE `system_configs`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '配置键',
  `config_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '配置值',
  `config_type` enum('string','int','float','boolean','json') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'string' COMMENT '配置类型',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '描述',
  `is_public` tinyint(1) NULL DEFAULT 0 COMMENT '是否公开',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `config_key`(`config_key`) USING BTREE,
  INDEX `idx_config_key`(`config_key`) USING BTREE,
  INDEX `idx_is_public`(`is_public`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '系统配置表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of system_configs
-- ----------------------------
INSERT INTO `system_configs` VALUES (1, 'system.name', 'ComfyUI Web Service', 'string', '系统名称', 1, '2025-07-15 10:08:19', '2025-07-15 10:08:19');
INSERT INTO `system_configs` VALUES (2, 'system.version', '2.0.0', 'string', '系统版本', 1, '2025-07-15 10:08:19', '2025-07-15 10:08:19');
INSERT INTO `system_configs` VALUES (3, 'task.default_priority', '1', 'int', '默认任务优先级', 0, '2025-07-15 10:08:19', '2025-07-15 10:08:19');
INSERT INTO `system_configs` VALUES (4, 'task.max_concurrent', '10', 'int', '最大并发任务数', 0, '2025-07-15 10:08:19', '2025-07-15 10:08:19');
INSERT INTO `system_configs` VALUES (5, 'file.max_size', '104857600', 'int', '最大文件大小(100MB)', 0, '2025-07-15 10:08:19', '2025-07-15 10:08:19');
INSERT INTO `system_configs` VALUES (6, 'api.rate_limit', '100', 'int', 'API速率限制(每分钟)', 0, '2025-07-15 10:08:19', '2025-07-15 10:08:19');

-- ----------------------------
-- Table structure for system_logs
-- ----------------------------
DROP TABLE IF EXISTS `system_logs`;
CREATE TABLE `system_logs`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `level` enum('DEBUG','INFO','WARNING','ERROR','CRITICAL') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '日志级别',
  `module` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '模块名称',
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '日志消息',
  `details` json NULL COMMENT '详细信息',
  `admin_user_id` bigint NULL DEFAULT NULL COMMENT '管理员用户ID',
  `task_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '任务ID',
  `node_id` bigint NULL DEFAULT NULL COMMENT '节点ID',
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'IP地址',
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '用户代理',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `node_id`(`node_id`) USING BTREE,
  INDEX `idx_level`(`level`) USING BTREE,
  INDEX `idx_module`(`module`) USING BTREE,
  INDEX `idx_created_at`(`created_at`) USING BTREE,
  INDEX `idx_admin_user_id`(`admin_user_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '系统日志表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of system_logs
-- ----------------------------

-- ----------------------------
-- Table structure for workflow_models
-- ----------------------------
DROP TABLE IF EXISTS `workflow_models`;
CREATE TABLE `workflow_models`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `workflow_id` bigint NOT NULL COMMENT '工作流ID',
  `model_id` bigint NOT NULL COMMENT '模型ID',
  `is_default` tinyint(1) NULL DEFAULT 0 COMMENT '是否默认模型',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_workflow_model`(`workflow_id`, `model_id`) USING BTREE,
  INDEX `idx_workflow_id`(`workflow_id`) USING BTREE,
  INDEX `idx_model_id`(`model_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '工作流模型关联表' ROW_FORMAT = Fixed;

-- ----------------------------
-- Records of workflow_models
-- ----------------------------

-- ----------------------------
-- Table structure for workflow_parameters
-- ----------------------------
DROP TABLE IF EXISTS `workflow_parameters`;
CREATE TABLE `workflow_parameters`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `workflow_id` bigint NOT NULL COMMENT '工作流ID',
  `parameter_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '参数名称',
  `parameter_type` enum('string','int','float','boolean','select','file') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '参数类型',
  `default_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '默认值',
  `min_value` decimal(20, 6) NULL DEFAULT NULL COMMENT '最小值',
  `max_value` decimal(20, 6) NULL DEFAULT NULL COMMENT '最大值',
  `options` json NULL COMMENT '选项列表(用于select类型)',
  `is_required` tinyint(1) NULL DEFAULT 0 COMMENT '是否必需',
  `display_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '显示名称',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '参数描述',
  `node_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '节点ID',
  `field_path` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '字段路径',
  `sort_order` int NULL DEFAULT 0 COMMENT '排序',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_workflow_id`(`workflow_id`) USING BTREE,
  INDEX `idx_parameter_name`(`parameter_name`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '工作流参数配置表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of workflow_parameters
-- ----------------------------

-- ----------------------------
-- Table structure for workflow_templates
-- ----------------------------
DROP TABLE IF EXISTS `workflow_templates`;
CREATE TABLE `workflow_templates`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '工作流名称',
  `display_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '显示名称',
  `task_type` enum('text_to_image','image_to_video') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务类型',
  `version` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '1.0' COMMENT '版本',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '描述',
  `workflow_file` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '工作流文件路径',
  `config_data` json NULL COMMENT '配置数据',
  `is_enabled` tinyint(1) NULL DEFAULT 1 COMMENT '是否启用',
  `is_default` tinyint(1) NULL DEFAULT 0 COMMENT '是否默认工作流',
  `max_concurrent_tasks` int NULL DEFAULT 4 COMMENT '最大并发任务数',
  `estimated_time` int NULL DEFAULT 60 COMMENT '预估处理时间(秒)',
  `usage_count` int NULL DEFAULT 0 COMMENT '使用次数',
  `success_rate` decimal(5, 2) NULL DEFAULT 0.00 COMMENT '成功率',
  `created_by` bigint NULL DEFAULT NULL COMMENT '创建者ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name`) USING BTREE,
  INDEX `created_by`(`created_by`) USING BTREE,
  INDEX `idx_name`(`name`) USING BTREE,
  INDEX `idx_task_type`(`task_type`) USING BTREE,
  INDEX `idx_is_enabled`(`is_enabled`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '工作流模板表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of workflow_templates
-- ----------------------------

SET FOREIGN_KEY_CHECKS = 1;
