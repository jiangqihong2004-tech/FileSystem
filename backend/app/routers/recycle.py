"""
回收站路由
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Folder, FileDB
from app.dependencies import get_current_user
from app.utils import resp, to_dict, get_file_category, get_file_icon

router = APIRouter(prefix="/file", tags=["回收站"])


@router.get("/recycle")
def file_recycle_list(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取回收站文件列表"""
    files = db.query(FileDB).filter(
        FileDB.user_id == current.id,
        FileDB.is_delete == 1,
    ).order_by(FileDB.delete_time.desc()).all()

    result = []
    for f in files:
        d = to_dict(f)
        d["category"] = get_file_category(f.file_suffix)
        d["icon"] = get_file_icon(f.file_suffix)
        if f.folder_id == 0:
            d["folder_name"] = "根目录"
        else:
            folder = db.query(Folder).filter(Folder.id == f.folder_id).first()
            d["folder_name"] = folder.folder_path if folder else "已删除"
        result.append(d)
    return resp(200, "成功", result)


@router.put("/restore/{file_id}")
def file_restore(
    file_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从回收站恢复文件"""
    f = db.query(FileDB).filter(
        FileDB.id == file_id,
        FileDB.user_id == current.id,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    if f.is_delete == 0:
        raise HTTPException(status_code=400, detail="文件不在回收站")

    if f.folder_id != 0:
        folder = db.query(Folder).filter(Folder.id == f.folder_id).first()
        if not folder:
            f.folder_id = 0

    f.is_delete = 0
    f.delete_time = None

    if f.folder_id != 0:
        folder = db.query(Folder).filter(Folder.id == f.folder_id).first()
        if folder:
            folder.file_count += 1
            folder.total_size += f.file_size

    db.commit()
    return resp(200, "已恢复", None)


@router.delete("/recycle/clear")
def clear_recycle(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清空回收站"""
    files = db.query(FileDB).filter(
        FileDB.user_id == current.id,
        FileDB.is_delete == 1,
    ).all()
    affected_folder_ids = set()
    for f in files:
        if os.path.exists(f.file_path):
            try:
                os.remove(f.file_path)
            except Exception as e:
                print(f"[删除文件失败] {f.file_path}: {e}")
        if f.folder_id != 0:
            affected_folder_ids.add(f.folder_id)
        db.delete(f)

    for fid in affected_folder_ids:
        folder = db.query(Folder).filter(Folder.id == fid).first()
        if folder:
            folder.file_count = db.query(FileDB).filter(
                FileDB.folder_id == fid,
                FileDB.is_delete == 0,
            ).count()
            folder.total_size = db.query(func.sum(FileDB.file_size)).filter(
                FileDB.folder_id == fid,
                FileDB.is_delete == 0,
            ).scalar() or 0

    db.commit()
    return resp(200, f"已清空回收站，共 {len(files)} 个文件", None)
