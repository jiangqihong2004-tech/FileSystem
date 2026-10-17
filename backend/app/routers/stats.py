"""
统计路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Folder, FileDB
from app.dependencies import get_current_user
from app.utils import resp, get_file_category

router = APIRouter(prefix="/stats", tags=["统计"])


@router.get("/overview")
def stats_overview(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户统计概览"""
    base_filter = [
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
    ]

    total_files = db.query(func.count(FileDB.id)).filter(*base_filter).scalar() or 0
    total_size = db.query(func.sum(FileDB.file_size)).filter(*base_filter).scalar() or 0
    total_folders = db.query(Folder).filter(
        Folder.user_id == current.id,
        Folder.is_delete == 0,
    ).count()
    recycle_count = db.query(FileDB).filter(
        FileDB.user_id == current.id, FileDB.is_delete == 1
    ).count()

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_uploads = db.query(FileDB).filter(
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
        FileDB.upload_time >= today_start,
    ).count()

    category_stats = {}
    files = db.query(FileDB).filter(*base_filter).all()
    for f in files:
        cat = get_file_category(f.file_suffix)
        category_stats[cat] = category_stats.get(cat, 0) + 1

    return resp(200, "统计成功", {
        "totalFiles": total_files,
        "totalSize": total_size,
        "totalFolders": total_folders,
        "recycleCount": recycle_count,
        "todayUploads": today_uploads,
        "categoryStats": category_stats,
        "storageQuota": current.storage_quota,
        "storageUsed": total_size,
        "storagePercent": round(total_size / current.storage_quota * 100, 2) if current.storage_quota > 0 else 0,
    })


@router.get("/storage")
def storage_detail(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户存储详情"""
    total_size = db.query(func.sum(FileDB.file_size)).filter(
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
    ).scalar() or 0
    
    category_sizes = {}
    files = db.query(FileDB).filter(
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
    ).all()
    
    for f in files:
        cat = get_file_category(f.file_suffix)
        category_sizes[cat] = category_sizes.get(cat, 0) + f.file_size
    
    return resp(200, "获取成功", {
        "storageQuota": current.storage_quota,
        "storageUsed": total_size,
        "storageFree": current.storage_quota - total_size,
        "storagePercent": round(total_size / current.storage_quota * 100, 2) if current.storage_quota > 0 else 0,
        "categorySizes": category_sizes,
    })
