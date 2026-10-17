"""
Pydantic 请求参数模型
统一接口入参校验
"""
from typing import Optional
from pydantic import BaseModel, Field


# ============ 用户认证 ============
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


# ============ 文件夹 ============
class FolderCreate(BaseModel):
    folder_name: str
    parent_id: int = 0


class FolderRename(BaseModel):
    new_name: str


# ============ 文件 ============
class FileRename(BaseModel):
    new_name: str


class FileMove(BaseModel):
    target_folder_id: int


class FileBatchDel(BaseModel):
    id_list: list[int]


class FileBatchMove(BaseModel):
    id_list: list[int]
    target_folder_id: int


# ============ 系统设置 ============
class SystemSettingUpdate(BaseModel):
    site_name: Optional[str] = None
    site_url: Optional[str] = None
    contact_email: Optional[str] = None
    site_description: Optional[str] = None
    allow_register: Optional[bool] = None
    register_audit: Optional[bool] = None
    default_role: Optional[str] = None


# ============ 用户管理 ============
class UserStatusUpdate(BaseModel):
    user_id: int
    status: int


class UserStorageQuotaUpdate(BaseModel):
    user_id: int
    storage_quota: int = Field(..., gt=0, description="存储配额（字节）")
