"""
系统设置路由（管理员）
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SystemSetting
from app.schemas import SystemSettingUpdate
from app.dependencies import get_admin_user
from app.utils import resp

router = APIRouter(prefix="/settings", tags=["系统设置"])


@router.get("")
def get_settings(
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """获取系统设置"""
    settings = db.query(SystemSetting).all()
    result = {}
    for s in settings:
        result[s.setting_key] = s.setting_value
    
    settings_detail = []
    for s in settings:
        settings_detail.append({
            "setting_key": s.setting_key,
            "setting_value": s.setting_value,
            "description": s.description,
            "create_time": s.create_time.strftime("%Y-%m-%d %H:%M:%S") if s.create_time else None,
            "update_time": s.update_time.strftime("%Y-%m-%d %H:%M:%S") if s.update_time else None,
        })
    
    return resp(200, "成功", {"values": result, "details": settings_detail})


@router.put("")
def update_settings(
    data: SystemSettingUpdate,
    admin=Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """更新系统设置"""
    updates = data.dict(exclude_none=True)
    for key, value in updates.items():
        s = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        if s:
            s.setting_value = str(value).lower() if isinstance(value, bool) else str(value)
        else:
            db.add(SystemSetting(setting_key=key, setting_value=str(value)))
    db.commit()
    return resp(200, "保存成功", None)
