"""
SQLAlchemy 数据模型定义
所有模型字段与 MySQL 表结构完全对齐，优化版：
- 添加外键约束
- 添加 CHECK 约束（role, status, is_delete）
- 添加联合索引
- 添加扩展字段（remark）
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, Text, Boolean,
    ForeignKey, Index, CheckConstraint
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship, foreign
from app.database import Base


class Folder(Base):
    """文件夹表"""
    __tablename__ = "folder"
    __table_args__ = (
        CheckConstraint("is_delete IN (0, 1)", name="ck_folder_is_delete"),
        Index("idx_folder_user_parent", "user_id", "parent_id"),
        Index("idx_folder_user", "user_id"),
        Index("idx_folder_user_delete", "user_id", "is_delete"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="文件夹主键")
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属用户ID")
    parent_id = Column(Integer, default=0, index=True, comment="父文件夹ID, 0为根目录")
    folder_name = Column(String(200), nullable=False, comment="文件夹名称")
    folder_path = Column(String(500), nullable=False, comment="逻辑路径 /项目文档")
    file_count = Column(Integer, default=0, comment="文件总数")
    total_size = Column(BigInteger, default=0, comment="总占用字节")
    is_delete = Column(TINYINT, default=0, comment="0正常 1回收站软删除")
    delete_time = Column(DateTime, nullable=True, comment="删除时间")
    remark = Column(String(255), nullable=True, comment="备注（扩展字段）")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系映射
    user = relationship("User", back_populates="folders")
    files = relationship("FileDB", back_populates="folder", primaryjoin="foreign(FileDB.folder_id) == Folder.id")


class User(Base):
    """用户表"""
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user')", name="ck_user_role"),
        CheckConstraint("status IN (0, 1, 2)", name="ck_user_status"),
        Index("idx_user_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户主键")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password = Column(String(255), nullable=False, comment="SHA256 加密后的密码")
    email = Column(String(100), nullable=True, comment="邮箱")
    role = Column(String(20), default="user", comment="角色: admin/user")
    status = Column(TINYINT, default=1, comment="状态: 0待审核 1正常 2禁用")
    storage_quota = Column(BigInteger, default=1073741824, comment="存储配额（字节），默认1GB")
    remark = Column(String(255), nullable=True, comment="备注（扩展字段）")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系映射
    folders = relationship("Folder", back_populates="user", cascade="all, delete-orphan")
    files = relationship("FileDB", back_populates="user", cascade="all, delete-orphan")


class FileDB(Base):
    """文件表"""
    __tablename__ = "file"
    __table_args__ = (
        CheckConstraint("is_delete IN (0, 1)", name="ck_file_is_delete"),
        Index("idx_file_user_folder", "user_id", "folder_id", "is_delete"),
        Index("idx_file_user_delete", "user_id", "is_delete"),
        Index("idx_file_upload_time", "upload_time"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="文件主键")
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True, comment="上传用户ID")
    folder_id = Column(Integer, default=0, index=True, comment="所属文件夹ID, 0为根目录")
    original_name = Column(String(255), nullable=False, comment="原始文件名")
    save_name = Column(String(255), nullable=False, comment="UUID 存储文件名")
    file_path = Column(String(500), nullable=False, comment="磁盘完整路径")
    file_size = Column(BigInteger, nullable=False, comment="文件字节大小")
    file_suffix = Column(String(50), nullable=True, comment="文件后缀 png/xlsx/docx")
    upload_time = Column(DateTime, default=datetime.now, comment="上传时间")
    is_delete = Column(TINYINT, default=0, comment="0正常 1回收站软删除")
    delete_time = Column(DateTime, nullable=True, comment="删除时间")
    remark = Column(String(255), nullable=True, comment="备注（扩展字段）")

    # 关系映射
    user = relationship("User", back_populates="files")
    folder = relationship("Folder", back_populates="files", primaryjoin="foreign(FileDB.folder_id) == Folder.id")


class SystemSetting(Base):
    """系统设置表"""
    __tablename__ = "system_setting"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(50), unique=True, nullable=False, index=True, comment="配置键")
    setting_value = Column(Text, nullable=True, comment="配置值")
    description = Column(String(255), nullable=True, comment="配置描述")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class KnowledgeBase(Base):
    """知识库表（顶层实体，每个用户可以拥有多个独立知识库）"""
    __tablename__ = "knowledge_base"
    __table_args__ = (
        Index("idx_kb_user", "user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="知识库主键")
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属用户ID")
    name = Column(String(200), nullable=False, comment="知识库名称")
    description = Column(String(500), nullable=True, comment="知识库描述")
    doc_count = Column(Integer, default=0, comment="文档总数")
    chunk_count = Column(Integer, default=0, comment="向量化片段总数")
    remark = Column(String(255), nullable=True, comment="备注")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class KbDocument(Base):
    """知识库文档表（每个上传的 doc/docx/pdf/excel 对应一条记录）"""
    __tablename__ = "kb_document"
    __table_args__ = (
        Index("idx_doc_kb", "kb_id"),
        Index("idx_doc_user", "user_id"),
        Index("idx_doc_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="文档主键")
    kb_id = Column(Integer, ForeignKey("knowledge_base.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属知识库ID")
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属用户ID")
    original_name = Column(String(255), nullable=False, comment="原始文件名")
    save_name = Column(String(255), nullable=False, comment="存储文件名（UUID）")
    file_path = Column(String(500), nullable=False, comment="磁盘完整路径")
    file_size = Column(BigInteger, nullable=False, default=0, comment="文件字节大小")
    file_type = Column(String(20), nullable=False, comment="文件类型 doc/docx/pdf/xls/xlsx/csv/txt")
    status = Column(String(20), default="pending", comment="pending/processing/ready/failed")
    status_msg = Column(String(500), nullable=True, comment="处理状态说明/错误信息")
    chunk_count = Column(Integer, default=0, comment="向量化片段数量")
    remark = Column(String(255), nullable=True, comment="备注")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class KbChunk(Base):
    """知识库向量片段表（每条记录是一段文本 + 对应向量 JSON）"""
    __tablename__ = "kb_chunk"
    __table_args__ = (
        Index("idx_chunk_doc", "doc_id"),
        Index("idx_chunk_kb", "kb_id"),
        Index("idx_chunk_user", "user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="片段主键")
    kb_id = Column(Integer, ForeignKey("knowledge_base.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属知识库ID")
    doc_id = Column(Integer, ForeignKey("kb_document.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属文档ID")
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属用户ID")
    content = Column(Text, nullable=False, comment="片段原文文本（供引用/显示）")
    vector_json = Column(Text, nullable=False, comment="向量 JSON 数组（float list，如 [0.1,0.2,...]）")
    vector_dim = Column(Integer, nullable=False, default=0, comment="向量维度")
    char_count = Column(Integer, default=0, comment="片段字符数")
    page_info = Column(String(200), nullable=True, comment="来源页/行信息（如 Page 1 或 Row 12）")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")


class ChatMessage(Base):
    """对话消息表：持久化通用助手和知识库问答的历史记录
    - 每个用户两条独立会话：mode='general' / mode='kb'
    - 退出登录、重新登录、刷新页面、关闭项目都不会清除
    - 仅在用户手动点击"清除对话"或删除数据库记录时清除
    """
    __tablename__ = "chat_message"
    __table_args__ = (
        Index("idx_chat_user_mode", "user_id", "mode"),
        Index("idx_chat_create_time", "create_time"),
        CheckConstraint("mode IN ('general', 'kb')", name="ck_chat_mode"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_role"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="消息主键")
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属用户ID")
    mode = Column(String(20), nullable=False, default="general", comment="对话模式：general=通用助手，kb=知识库问答")
    role = Column(String(20), nullable=False, comment="角色：user=用户，assistant=AI助手")
    content = Column(Text, nullable=False, comment="消息文本内容")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
