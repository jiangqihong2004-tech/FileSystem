/*
 FileManager 数据库结构 - v3.0 (优化版)
 ⚠️ 警告：此脚本会删除并重建整个数据库，仅用于全新安装！
 如需保留现有数据，请手动执行 ALTER 语句增量更新。

 优化点：
 1. 添加外键约束（FOREIGN KEY）
 2. 添加 CHECK 约束（role, status, is_delete）
 3. 添加联合索引（user_id+folder_id, user_id+is_delete）
 4. 添加扩展字段（remark）
 5. 优化系统设置表

 Server: MySQL 8.0+
 Date: 2026-06-26
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 数据库
-- ----------------------------
DROP DATABASE IF EXISTS `file_manager`;
CREATE DATABASE `file_manager` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `file_manager`;

-- ----------------------------
-- 用户表
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '用户主键',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'SHA256加密密码',
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '邮箱',
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'user' COMMENT '角色: admin/user',
  `status` tinyint NULL DEFAULT 1 COMMENT '状态: 0待审核 1正常 2禁用',
  `storage_quota` bigint NULL DEFAULT 1073741824 COMMENT '存储配额（字节），默认1GB',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '备注（扩展字段）',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_username`(`username` ASC) USING BTREE,
  INDEX `idx_user_status`(`status`) USING BTREE,
  CONSTRAINT `ck_user_role` CHECK (`role` IN ('admin', 'user')),
  CONSTRAINT `ck_user_status` CHECK (`status` IN (0, 1, 2))
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- 文件夹表
-- ----------------------------
DROP TABLE IF EXISTS `folder`;
CREATE TABLE `folder` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '文件夹主键',
  `user_id` int NOT NULL COMMENT '所属用户ID',
  `parent_id` int NOT NULL DEFAULT 0 COMMENT '父文件夹ID, 0为根目录',
  `folder_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件夹名称',
  `folder_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '逻辑路径',
  `file_count` int NULL DEFAULT 0 COMMENT '文件总数',
  `total_size` bigint NULL DEFAULT 0 COMMENT '总大小（字节）',
  `is_delete` tinyint NULL DEFAULT 0 COMMENT '0正常 1回收站软删除',
  `delete_time` datetime NULL DEFAULT NULL COMMENT '删除时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '备注（扩展字段）',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_folder_user_id`(`user_id`) USING BTREE,
  INDEX `idx_folder_parent_id`(`parent_id`) USING BTREE,
  INDEX `idx_folder_user_parent`(`user_id`, `parent_id`) USING BTREE,
  INDEX `idx_folder_user_delete`(`user_id`, `is_delete`) USING BTREE,
  CONSTRAINT `fk_folder_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ck_folder_is_delete` CHECK (`is_delete` IN (0, 1))
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- 文件表
-- ----------------------------
DROP TABLE IF EXISTS `file`;
CREATE TABLE `file` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '文件主键',
  `user_id` int NOT NULL COMMENT '上传用户ID',
  `folder_id` int NOT NULL DEFAULT 0 COMMENT '所属文件夹ID, 0为根目录',
  `original_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始文件名',
  `save_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'UUID存储文件名',
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '磁盘完整路径',
  `file_size` bigint NOT NULL COMMENT '文件字节大小',
  `file_suffix` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '文件后缀',
  `upload_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `is_delete` tinyint NULL DEFAULT 0 COMMENT '0正常 1回收站软删除',
  `delete_time` datetime NULL DEFAULT NULL COMMENT '删除时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '备注（扩展字段）',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_file_user_id`(`user_id`) USING BTREE,
  INDEX `idx_file_folder_id`(`folder_id`) USING BTREE,
  INDEX `idx_file_user_folder`(`user_id`, `folder_id`) USING BTREE,
  INDEX `idx_file_user_delete`(`user_id`, `is_delete`) USING BTREE,
  INDEX `idx_file_upload_time`(`upload_time`) USING BTREE,
  CONSTRAINT `fk_file_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ck_file_is_delete` CHECK (`is_delete` IN (0, 1))
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- 系统设置表
-- ----------------------------
DROP TABLE IF EXISTS `system_setting`;
CREATE TABLE `system_setting` (
  `id` int NOT NULL AUTO_INCREMENT,
  `setting_key` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '配置键',
  `setting_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL COMMENT '配置值',
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '配置描述',
  `create_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_setting_key`(`setting_key`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- 初始数据：管理员账号（密码请自行替换为 <SHA256(your_admin_password)>）
-- ----------------------------
INSERT INTO `user` (`username`, `password`, `email`, `role`, `status`)
VALUES ('your_admin_username', '<SHA256(your_admin_password)>', 'your_email@example.com', 'admin', 1);

-- ----------------------------
-- 初始数据：系统默认设置
-- ----------------------------
INSERT INTO `system_setting` (`setting_key`, `setting_value`, `description`) VALUES
('site_name', 'FileManager 文件管理系统', '网站名称'),
('site_url', 'http://localhost:8000', '网站地址'),
('contact_email', 'your_email@example.com', '联系邮箱'),
('site_description', '基于 FastAPI + Vue3 的轻量级文件管理系统', '网站描述'),
('allow_register', 'true', '是否允许注册'),
('register_audit', 'false', '注册是否需要审核'),
('default_role', 'user', '新用户默认角色');

SET FOREIGN_KEY_CHECKS = 1;
