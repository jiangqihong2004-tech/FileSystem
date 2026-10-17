"""
鉴权依赖模块
提供 get_current_user 和 get_admin_user 依赖
"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.utils import parse_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """从 Authorization Header 或 query 参数解析 JWT Token，返回当前用户"""
    auth = request.headers.get("Authorization", "")
    token = ""
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        token = request.query_params.get("token", "")
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    payload = parse_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.status == 2:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """要求当前用户是管理员"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
