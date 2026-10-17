"""
用户管理路由（管理员）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserStatusUpdate, UserStorageQuotaUpdate
from app.dependencies import get_admin_user
from app.utils import resp

router = APIRouter(prefix="/user", tags=["用户管理"])


@router.get("/list")
def user_list(
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取所有用户列表"""
    users = db.query(User).order_by(User.create_time.desc()).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "storage_quota": u.storage_quota or 1073741824,
            "create_time": u.create_time.strftime("%Y-%m-%d %H:%M:%S") if u.create_time else None,
        })
    return resp(200, "成功", result)


@router.put("/status")
def update_user_status(
    data: UserStatusUpdate,
    current=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """更新用户状态"""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current.id and data.status == 2:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    user.status = data.status
    db.commit()
    return resp(200, "更新成功", None)


@router.put("/storage_quota")
def update_storage_quota(
    data: UserStorageQuotaUpdate,
    current=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """更新用户存储配额"""
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.storage_quota = data.storage_quota
    db.commit()
    return resp(200, "更新存储配额成功", None)
