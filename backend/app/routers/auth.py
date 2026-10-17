"""
用户认证路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, SystemSetting
from app.schemas import UserRegister, UserLogin, ChangePassword
from app.dependencies import get_current_user
from app.utils import hash_password, verify_password, create_token, resp

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register")
def register(data: UserRegister, db: Session = Depends(get_db)):
    """用户注册"""
    allow_register = db.query(SystemSetting).filter(
        SystemSetting.setting_key == "allow_register"
    ).first()
    if allow_register and allow_register.setting_value == "false":
        raise HTTPException(status_code=403, detail="系统已关闭注册")

    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")

    audit_setting = db.query(SystemSetting).filter(
        SystemSetting.setting_key == "register_audit"
    ).first()
    need_audit = audit_setting and audit_setting.setting_value == "true"

    default_role_setting = db.query(SystemSetting).filter(
        SystemSetting.setting_key == "default_role"
    ).first()
    default_role = default_role_setting.setting_value if default_role_setting else "user"

    user = User(
        username=data.username,
        password=hash_password(data.password),
        email=data.email,
        role=default_role,
        status=0 if need_audit else 1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    msg = "注册成功，请等待管理员审核" if need_audit else "注册成功，请登录"
    return resp(200, msg, {"id": user.id, "username": user.username})


@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 调试日志：打印接收到的用户名和密码长度
    logger.info(f"登录请求 - 用户名: {repr(data.username)}, 密码长度: {len(data.password)}")
    
    user = db.query(User).filter(User.username == data.username).first()
    
    if not user:
        logger.warning(f"用户不存在: {repr(data.username)}")
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    
    logger.info(f"找到用户 - ID: {user.id}, 用户名: {repr(user.username)}, 数据库中密码哈希: {user.password[:20]}...")
    
    expected_hash = hash_password(data.password)
    logger.info(f"计算出的密码哈希: {expected_hash[:20]}...")
    logger.info(f"密码是否匹配: {expected_hash == user.password}")
    
    if not verify_password(data.password, user.password):
        logger.error("密码验证失败")
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    
    if user.status == 0:
        raise HTTPException(status_code=403, detail="账号待审核，请联系管理员")
    if user.status == 2:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_token(user.id, user.username, user.role)
    return resp(200, "登录成功", {
        "token": token,
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "create_time": user.create_time.strftime("%Y-%m-%d %H:%M:%S") if user.create_time else None,
    })


@router.get("/me")
def get_me(current: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return resp(200, "成功", {
        "id": current.id,
        "username": current.username,
        "email": current.email,
        "role": current.role,
        "status": current.status,
        "storage_quota": current.storage_quota,
        "create_time": current.create_time.strftime("%Y-%m-%d %H:%M:%S") if current.create_time else None,
    })


@router.put("/password")
def change_password(
    data: ChangePassword,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码"""
    if not verify_password(data.old_password, current.password):
        raise HTTPException(status_code=400, detail="原密码错误")
    current.password = hash_password(data.new_password)
    db.commit()
    return resp(200, "密码修改成功", None)
