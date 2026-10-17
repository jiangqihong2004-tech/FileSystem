"""
文件夹管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Folder, FileDB
from app.schemas import FolderCreate, FolderRename
from app.dependencies import get_current_user
from app.utils import resp, to_dict
from datetime import datetime

router = APIRouter(prefix="/folder", tags=["文件夹"])


@router.post("/create")
def folder_create(
    data: FolderCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建文件夹"""
    if not data.folder_name.strip():
        raise HTTPException(status_code=400, detail="文件夹名称不能为空")

    if data.parent_id == 0:
        folder_path = "/" + data.folder_name
    else:
        parent = db.query(Folder).filter(
            Folder.id == data.parent_id,
            Folder.user_id == current.id,
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="父文件夹不存在")
        folder_path = parent.folder_path + "/" + data.folder_name

    folder = Folder(
        user_id=current.id,
        parent_id=data.parent_id,
        folder_name=data.folder_name,
        folder_path=folder_path,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return resp(200, "创建成功", to_dict(folder))


@router.get("/list")
def folder_list(
    parent_id: int = None,
    keyword: str = "",
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取文件夹列表"""
    q = db.query(Folder).filter(
        Folder.user_id == current.id,
        Folder.is_delete == 0,
    )
    if parent_id is not None:
        q = q.filter(Folder.parent_id == parent_id)
    if keyword:
        q = q.filter(Folder.folder_name.like(f"%{keyword}%"))
    folders = q.order_by(Folder.create_time.desc()).all()
    return resp(200, "成功", [to_dict(f) for f in folders])


@router.get("/breadcrumb")
def folder_breadcrumb(
    folder_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取文件夹面包屑路径"""
    breadcrumb = []
    current_id = folder_id
    while current_id and current_id != 0:
        folder = db.query(Folder).filter(
            Folder.id == current_id,
            Folder.user_id == current.id,
            Folder.is_delete == 0,
        ).first()
        if not folder:
            break
        breadcrumb.insert(0, {"id": folder.id, "name": folder.folder_name})
        current_id = folder.parent_id
    return resp(200, "成功", breadcrumb)


@router.put("/rename/{folder_id}")
def folder_rename(
    folder_id: int,
    data: FolderRename,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重命名文件夹"""
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current.id,
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    if not data.new_name.strip():
        raise HTTPException(status_code=400, detail="名称不能为空")

    old_path = folder.folder_path
    if folder.parent_id == 0:
        new_path = "/" + data.new_name
    else:
        parent = db.query(Folder).filter(Folder.id == folder.parent_id).first()
        new_path = parent.folder_path + "/" + data.new_name

    folder.folder_name = data.new_name
    folder.folder_path = new_path

    # 递归更新所有后代文件夹路径
    def update_children_paths(pid, old_prefix, new_prefix):
        children = db.query(Folder).filter(
            Folder.parent_id == pid,
            Folder.user_id == current.id,
        ).all()
        for d in children:
            d.folder_path = new_prefix + d.folder_path[len(old_prefix):]
            update_children_paths(d.id, old_prefix, new_prefix)

    update_children_paths(folder_id, old_path, new_path)

    db.commit()
    return resp(200, "重命名成功", None)


@router.delete("/{folder_id}")
def folder_delete(
    folder_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除文件夹（软删除，将内部文件移入回收站）"""
    from datetime import datetime
    
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current.id,
        Folder.is_delete == 0,
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    def collect_ids(pid):
        ids = [pid]
        children = db.query(Folder).filter(
            Folder.parent_id == pid,
            Folder.user_id == current.id,
            Folder.is_delete == 0,
        ).all()
        for c in children:
            ids.extend(collect_ids(c.id))
        return ids

    all_folder_ids = collect_ids(folder_id)
    now = datetime.now()
    
    files = db.query(FileDB).filter(
        FileDB.folder_id.in_(all_folder_ids),
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
    ).all()
    for f in files:
        f.is_delete = 1
        f.delete_time = now

    folders = db.query(Folder).filter(Folder.id.in_(all_folder_ids)).all()
    for folder_obj in folders:
        folder_obj.is_delete = 1
        folder_obj.delete_time = now

    db.commit()
    return resp(200, f"已删除文件夹，{len(files)} 个文件移入回收站", None)


@router.get("/recycle/list")
def folder_recycle_list(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取回收站中的文件夹列表"""
    q = db.query(Folder).filter(
        Folder.user_id == current.id,
        Folder.is_delete == 1,
    )
    folders = q.order_by(Folder.delete_time.desc()).all()
    return resp(200, "成功", [to_dict(f) for f in folders])


@router.post("/recycle/restore/{folder_id}")
def folder_restore(
    folder_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """恢复文件夹"""
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current.id,
        Folder.is_delete == 1,
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    def collect_ids(pid):
        ids = [pid]
        children = db.query(Folder).filter(
            Folder.parent_id == pid,
            Folder.user_id == current.id,
        ).all()
        for c in children:
            ids.extend(collect_ids(c.id))
        return ids

    all_folder_ids = collect_ids(folder_id)
    
    folders = db.query(Folder).filter(Folder.id.in_(all_folder_ids)).all()
    for folder_obj in folders:
        folder_obj.is_delete = 0
        folder_obj.delete_time = None

    files = db.query(FileDB).filter(
        FileDB.folder_id.in_(all_folder_ids),
        FileDB.user_id == current.id,
        FileDB.is_delete == 1,
    ).all()
    for f in files:
        f.is_delete = 0
        f.delete_time = None

    db.commit()
    return resp(200, "恢复成功", None)


@router.delete("/recycle/permanent/{folder_id}")
def folder_permanent_delete(
    folder_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """彻底删除文件夹"""
    folder = db.query(Folder).filter(
        Folder.id == folder_id,
        Folder.user_id == current.id,
        Folder.is_delete == 1,
    ).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    def collect_ids(pid):
        ids = [pid]
        children = db.query(Folder).filter(
            Folder.parent_id == pid,
            Folder.user_id == current.id,
        ).all()
        for c in children:
            ids.extend(collect_ids(c.id))
        return ids

    all_folder_ids = collect_ids(folder_id)
    
    files = db.query(FileDB).filter(
        FileDB.folder_id.in_(all_folder_ids),
        FileDB.user_id == current.id,
    ).all()
    for f in files:
        try:
            import os
            if os.path.exists(f.file_path):
                os.remove(f.file_path)
        except Exception:
            pass

    db.query(FileDB).filter(FileDB.folder_id.in_(all_folder_ids)).delete(synchronize_session=False)
    db.query(Folder).filter(Folder.id.in_(all_folder_ids)).delete(synchronize_session=False)
    
    db.commit()
    return resp(200, "彻底删除成功", None)
