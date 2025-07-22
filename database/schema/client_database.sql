/*
 Navicat Premium Dump SQL

 Source Server         : okazaki
 Source Server Type    : MySQL
 Source Server Version : 80300 (8.3.0)
 Source Host           : localhost:3306
 Source Schema         : comfyui_client

 Target Server Type    : MySQL
 Target Server Version : 80300 (8.3.0)
 File Encoding         : 65001

 Date: 22/07/2025 12:14:21
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for client_access_logs
-- ----------------------------
DROP TABLE IF EXISTS `client_access_logs`;
CREATE TABLE `client_access_logs`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `client_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '客户端ID',
  `action` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作类型',
  `endpoint` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'API端点',
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'IP地址',
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '用户代理',
  `response_time` int NULL DEFAULT NULL COMMENT '响应时间(毫秒)',
  `status_code` int NULL DEFAULT NULL COMMENT '状态码',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_client_id`(`client_id`) USING BTREE,
  INDEX `idx_action`(`action`) USING BTREE,
  INDEX `idx_created_at`(`created_at`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '客户端访问日志表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for client_task_parameters
-- ----------------------------
DROP TABLE IF EXISTS `client_task_parameters`;
CREATE TABLE `client_task_parameters`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` bigint NOT NULL COMMENT '任务ID',
  `parameter_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '参数名称',
  `parameter_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '参数值',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_task_id`(`task_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '客户端任务参数表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for client_task_results
-- ----------------------------
DROP TABLE IF EXISTS `client_task_results`;
CREATE TABLE `client_task_results`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` bigint NOT NULL COMMENT '任务ID',
  `result_type` enum('image','video') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '结果类型',
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件路径',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件名',
  `file_size` bigint NULL DEFAULT NULL COMMENT '文件大小(字节)',
  `width` int NULL DEFAULT NULL COMMENT '图片/视频宽度',
  `height` int NULL DEFAULT NULL COMMENT '图片/视频高度',
  `duration` decimal(10, 2) NULL DEFAULT NULL COMMENT '视频时长(秒)',
  `thumbnail_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '缩略图路径',
  `download_count` int NULL DEFAULT 0 COMMENT '下载次数',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `result_metadata` json NULL COMMENT '元数据',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_task_id`(`task_id`) USING BTREE,
  INDEX `idx_result_type`(`result_type`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 242 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '客户端任务结果表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for client_tasks
-- ----------------------------
DROP TABLE IF EXISTS `client_tasks`;
CREATE TABLE `client_tasks`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务UUID',
  `client_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '客户端ID',
  `task_type` enum('text_to_image','image_to_video') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务类型',
  `workflow_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '工作流名称',
  `prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '正向提示词',
  `negative_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '反向提示词',
  `status` enum('queued','processing','completed','failed','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'queued' COMMENT '任务状态',
  `progress` decimal(5, 2) NULL DEFAULT 0.00 COMMENT '进度百分比',
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '状态消息',
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '错误消息',
  `estimated_time` int NULL DEFAULT NULL COMMENT '预估处理时间(秒)',
  `actual_time` int NULL DEFAULT NULL COMMENT '实际处理时间(秒)',
  `started_at` timestamp NULL DEFAULT NULL COMMENT '开始处理时间',
  `completed_at` timestamp NULL DEFAULT NULL COMMENT '完成时间',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `model_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '使用的模型名称',
  `width` int NULL DEFAULT NULL COMMENT '图片宽度',
  `height` int NULL DEFAULT NULL COMMENT '图片高度',
  `steps` int NULL DEFAULT NULL COMMENT '采样步数',
  `cfg_scale` decimal(4, 2) NULL DEFAULT NULL COMMENT 'CFG引导强度',
  `sampler` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '采样器',
  `scheduler` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '调度器',
  `seed` bigint NULL DEFAULT NULL COMMENT '随机种子',
  `batch_size` int NULL DEFAULT 1 COMMENT '批量大小',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `task_id`(`task_id`) USING BTREE,
  INDEX `idx_task_id`(`task_id`) USING BTREE,
  INDEX `idx_client_id`(`client_id`) USING BTREE,
  INDEX `idx_status`(`status`) USING BTREE,
  INDEX `idx_task_type`(`task_type`) USING BTREE,
  INDEX `idx_created_at`(`created_at`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 75 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '客户端任务表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for client_uploads
-- ----------------------------
DROP TABLE IF EXISTS `client_uploads`;
CREATE TABLE `client_uploads`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `upload_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '上传UUID',
  `file_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件UUID',
  `client_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '客户端ID',
  `original_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始文件名',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '存储文件名',
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `file_size` bigint NOT NULL COMMENT '文件大小(字节)',
  `mime_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'MIME类型',
  `file_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件哈希',
  `upload_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'image' COMMENT '上传类型',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'completed' COMMENT '上传状态',
  `width` int NULL DEFAULT NULL COMMENT '图片宽度',
  `height` int NULL DEFAULT NULL COMMENT '图片高度',
  `is_processed` tinyint(1) NULL DEFAULT 0 COMMENT '是否已处理',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `file_id`(`file_id`) USING BTREE,
  UNIQUE INDEX `unique_file_id`(`file_id`) USING BTREE,
  UNIQUE INDEX `upload_id`(`upload_id`) USING BTREE,
  INDEX `idx_file_id`(`file_id`) USING BTREE,
  INDEX `idx_client_id`(`client_id`) USING BTREE,
  INDEX `idx_created_at`(`created_at`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 25 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '客户端上传文件表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for client_users
-- ----------------------------
DROP TABLE IF EXISTS `client_users`;
CREATE TABLE `client_users`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `client_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '客户端ID（UUID）',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '用户名',
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '密码哈希',
  `session_token` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '会话令牌',
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'IP地址',
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '用户代理',
  `nickname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '昵称',
  `quota_limit` int NULL DEFAULT 50 COMMENT '每日配额限制',
  `quota_used` int NULL DEFAULT 0 COMMENT '今日已使用配额',
  `quota_reset_date` date NULL DEFAULT NULL COMMENT '配额重置日期',
  `is_active` tinyint(1) NULL DEFAULT 1 COMMENT '是否活跃',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_access_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `client_id`(`client_id`) USING BTREE,
  UNIQUE INDEX `session_token`(`session_token`) USING BTREE,
  UNIQUE INDEX `username`(`username`) USING BTREE,
  INDEX `idx_client_id`(`client_id`) USING BTREE,
  INDEX `idx_session_token`(`session_token`) USING BTREE,
  INDEX `idx_ip_address`(`ip_address`) USING BTREE,
  INDEX `idx_username`(`username`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '客户端用户表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
