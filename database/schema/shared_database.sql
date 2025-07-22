/*
 Navicat Premium Dump SQL

 Source Server         : okazaki
 Source Server Type    : MySQL
 Source Server Version : 80300 (8.3.0)
 Source Host           : localhost:3306
 Source Schema         : comfyui_shared

 Target Server Type    : MySQL
 Target Server Version : 80300 (8.3.0)
 File Encoding         : 65001

 Date: 22/07/2025 12:14:44
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for global_files
-- ----------------------------
DROP TABLE IF EXISTS `global_files`;
CREATE TABLE `global_files`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件UUID',
  `source_type` enum('client','admin','system') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件来源',
  `source_user_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '来源用户ID',
  `original_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始文件名',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '存储文件名',
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件路径',
  `file_size` bigint NOT NULL COMMENT '文件大小(字节)',
  `mime_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'MIME类型',
  `file_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件哈希',
  `file_type` enum('image','video','audio','document','other') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件类型',
  `width` int NULL DEFAULT NULL COMMENT '图片/视频宽度',
  `height` int NULL DEFAULT NULL COMMENT '图片/视频高度',
  `duration` decimal(10, 2) NULL DEFAULT NULL COMMENT '视频/音频时长(秒)',
  `file_metadata` json NULL COMMENT '元数据',
  `is_public` tinyint(1) NULL DEFAULT 0 COMMENT '是否公开',
  `is_temporary` tinyint(1) NULL DEFAULT 0 COMMENT '是否临时文件',
  `expires_at` timestamp NULL DEFAULT NULL COMMENT '过期时间',
  `download_count` int NULL DEFAULT 0 COMMENT '下载次数',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'active' COMMENT '文件状态',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `file_id`(`file_id`) USING BTREE,
  INDEX `idx_file_id`(`file_id`) USING BTREE,
  INDEX `idx_source_type`(`source_type`) USING BTREE,
  INDEX `idx_source_user_id`(`source_user_id`) USING BTREE,
  INDEX `idx_file_type`(`file_type`) USING BTREE,
  INDEX `idx_file_hash`(`file_hash`) USING BTREE,
  INDEX `idx_is_temporary`(`is_temporary`) USING BTREE,
  INDEX `idx_expires_at`(`expires_at`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 22 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '全局文件表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for global_task_parameters
-- ----------------------------
DROP TABLE IF EXISTS `global_task_parameters`;
CREATE TABLE `global_task_parameters`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` bigint NOT NULL COMMENT '任务ID',
  `parameter_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '参数名称',
  `parameter_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '参数值',
  `parameter_type` enum('string','int','float','boolean','json') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'string' COMMENT '参数类型',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_task_id`(`task_id`) USING BTREE,
  INDEX `idx_parameter_name`(`parameter_name`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '全局任务参数表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for global_task_results
-- ----------------------------
DROP TABLE IF EXISTS `global_task_results`;
CREATE TABLE `global_task_results`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` bigint NOT NULL COMMENT '任务ID',
  `result_type` enum('image','video','json','file') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '结果类型',
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件路径',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件名',
  `file_size` bigint NULL DEFAULT NULL COMMENT '文件大小(字节)',
  `mime_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'MIME类型',
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
) ENGINE = MyISAM AUTO_INCREMENT = 244 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '全局任务结果表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for global_tasks
-- ----------------------------
DROP TABLE IF EXISTS `global_tasks`;
CREATE TABLE `global_tasks`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务UUID',
  `source_type` enum('client','admin') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务来源',
  `source_user_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '来源用户ID',
  `task_type` enum('text_to_image','image_to_video') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务类型',
  `workflow_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '工作流名称',
  `prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '正向提示词',
  `negative_prompt` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '反向提示词',
  `status` enum('queued','processing','completed','failed','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'queued' COMMENT '任务状态',
  `priority` int NULL DEFAULT 1 COMMENT '任务优先级',
  `progress` decimal(5, 2) NULL DEFAULT 0.00 COMMENT '进度百分比',
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '状态消息',
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '错误消息',
  `celery_task_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'Celery任务ID',
  `node_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '执行节点ID',
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
  INDEX `idx_source_type`(`source_type`) USING BTREE,
  INDEX `idx_source_user_id`(`source_user_id`) USING BTREE,
  INDEX `idx_status`(`status`) USING BTREE,
  INDEX `idx_task_type`(`task_type`) USING BTREE,
  INDEX `idx_created_at`(`created_at`) USING BTREE,
  INDEX `idx_node_id`(`node_id`) USING BTREE,
  INDEX `idx_celery_task_id`(`celery_task_id`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 74 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '全局任务表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for node_task_assignments
-- ----------------------------
DROP TABLE IF EXISTS `node_task_assignments`;
CREATE TABLE `node_task_assignments`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `node_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点ID',
  `task_id` bigint NOT NULL COMMENT '任务ID',
  `assigned_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '分配时间',
  `started_at` timestamp NULL DEFAULT NULL COMMENT '开始时间',
  `completed_at` timestamp NULL DEFAULT NULL COMMENT '完成时间',
  `status` enum('assigned','running','completed','failed','cancelled') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'assigned' COMMENT '分配状态',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_node_id`(`node_id`) USING BTREE,
  INDEX `idx_task_id`(`task_id`) USING BTREE,
  INDEX `idx_status`(`status`) USING BTREE,
  INDEX `idx_assigned_at`(`assigned_at`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '节点任务分配表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for system_statistics
-- ----------------------------
DROP TABLE IF EXISTS `system_statistics`;
CREATE TABLE `system_statistics`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stat_date` date NOT NULL COMMENT '统计日期',
  `total_tasks` int NULL DEFAULT 0 COMMENT '总任务数',
  `completed_tasks` int NULL DEFAULT 0 COMMENT '完成任务数',
  `failed_tasks` int NULL DEFAULT 0 COMMENT '失败任务数',
  `client_tasks` int NULL DEFAULT 0 COMMENT '客户端任务数',
  `admin_tasks` int NULL DEFAULT 0 COMMENT '管理端任务数',
  `text_to_image_tasks` int NULL DEFAULT 0 COMMENT '文生图任务数',
  `image_to_video_tasks` int NULL DEFAULT 0 COMMENT '图生视频任务数',
  `total_processing_time` bigint NULL DEFAULT 0 COMMENT '总处理时间(秒)',
  `average_processing_time` decimal(10, 2) NULL DEFAULT 0.00 COMMENT '平均处理时间(秒)',
  `active_nodes` int NULL DEFAULT 0 COMMENT '活跃节点数',
  `total_file_size` bigint NULL DEFAULT 0 COMMENT '总文件大小(字节)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_stat_date`(`stat_date`) USING BTREE,
  INDEX `idx_stat_date`(`stat_date`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '系统统计表' ROW_FORMAT = Fixed;

-- ----------------------------
-- Table structure for task_queue_status
-- ----------------------------
DROP TABLE IF EXISTS `task_queue_status`;
CREATE TABLE `task_queue_status`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务ID',
  `queue_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '队列名称',
  `status` enum('pending','started','retry','failure','success') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '队列状态',
  `result` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '执行结果',
  `traceback` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '错误堆栈',
  `worker` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '工作进程',
  `retries` int NULL DEFAULT 0 COMMENT '重试次数',
  `eta` timestamp NULL DEFAULT NULL COMMENT '预计执行时间',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `task_id`(`task_id`) USING BTREE,
  INDEX `idx_task_id`(`task_id`) USING BTREE,
  INDEX `idx_queue_name`(`queue_name`) USING BTREE,
  INDEX `idx_status`(`status`) USING BTREE,
  INDEX `idx_worker`(`worker`) USING BTREE
) ENGINE = MyISAM AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '任务队列状态表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
