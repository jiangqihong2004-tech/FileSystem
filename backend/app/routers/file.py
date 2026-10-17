"""
文件管理路由
"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Folder, FileDB
from app.schemas import FileRename, FileMove, FileBatchDel, FileBatchMove
from app.dependencies import get_current_user
from app.utils import resp, to_dict, get_file_category, get_file_icon, extract_suffix
from typing import Optional

router = APIRouter(prefix="/file", tags=["文件"])

BASE_STATIC = "static"
MAX_FILE_SIZE = 100 * 1024 * 1024


@router.post("/upload/{folder_id}")
async def file_upload(
        folder_id: int,
        files: list[UploadFile] = File(...),
        current: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """上传文件到指定文件夹"""
    from sqlalchemy import func

    if folder_id != 0:
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == current.id,
        ).first()
        if not folder:
            raise HTTPException(status_code=404, detail="目标文件夹不存在")

    user_dir = os.path.join(BASE_STATIC, str(current.id))
    os.makedirs(user_dir, exist_ok=True)

    uploaded = []
    total_upload_size = 0

    for f in files:
        if not f.filename:
            continue
        try:
            content = await f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")

        file_size = len(content)
        total_upload_size += file_size

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件 {f.filename} 超过大小限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）"
            )

    storage_quota = current.storage_quota or 1073741824
    current_usage = db.query(func.sum(FileDB.file_size)).filter(
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
    ).scalar() or 0

    if current_usage + total_upload_size > storage_quota:
        raise HTTPException(
            status_code=400,
            detail=f"总大小将超出存储配额（当前使用: {current_usage / 1024 / 1024:.2f}MB, 配额: {storage_quota / 1024 / 1024:.2f}MB, 本次上传: {total_upload_size / 1024 / 1024:.2f}MB）"
        )

    for f in files:
        if not f.filename:
            continue

        suffix = extract_suffix(f.filename)
        save_name = f"{uuid.uuid4().hex}.{suffix}" if suffix else uuid.uuid4().hex
        file_path = os.path.join(user_dir, save_name)

        try:
            with open(file_path, "wb") as fp:
                fp.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"写入文件失败: {str(e)}")

        record = FileDB(
            user_id=current.id,
            folder_id=folder_id,
            original_name=f.filename,
            save_name=save_name,
            file_path=file_path,
            file_size=file_size,
            file_suffix=suffix,
        )
        db.add(record)
        uploaded.append({"name": f.filename, "size": file_size})

    if folder_id != 0:
        folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == current.id).first()
        if folder:
            folder.file_count = db.query(FileDB).filter(
                FileDB.folder_id == folder_id,
                FileDB.is_delete == 0,
            ).count()
            folder.total_size = db.query(func.sum(FileDB.file_size)).filter(
                FileDB.folder_id == folder_id,
                FileDB.is_delete == 0,
            ).scalar() or 0

    db.commit()

    return resp(200, f"成功上传 {len(uploaded)} 个文件", uploaded)


@router.get("/list")
def file_list(
    folder_id: Optional[int] = None,
    category: str = "",
    keyword: str = "",
    page: int = 1,
    size: int = 100,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取文件列表"""
    q = db.query(FileDB).filter(
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
    )
    if folder_id is not None and category == "":
        q = q.filter(FileDB.folder_id == folder_id)
    if keyword:
        q = q.filter(FileDB.original_name.like(f"%{keyword}%"))

    if category:
        all_files = q.order_by(FileDB.upload_time.desc()).all()
        result = []
        for f in all_files:
            cat = get_file_category(f.file_suffix)
            if cat != category:
                continue
            d = to_dict(f)
            d["category"] = cat
            d["icon"] = get_file_icon(f.file_suffix)
            result.append(d)
        total = len(result)
        start = (page - 1) * size
        result = result[start:start + size]
    else:
        total = q.count()
        files = q.order_by(FileDB.upload_time.desc()).offset((page - 1) * size).limit(size).all()
        result = []
        for f in files:
            d = to_dict(f)
            d["category"] = get_file_category(f.file_suffix)
            d["icon"] = get_file_icon(f.file_suffix)
            result.append(d)

    return resp(200, "成功", {"list": result, "total": total, "page": page, "size": size})


@router.get("/download/{file_id}")
def file_download(
    file_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """下载文件"""
    f = db.query(FileDB).filter(
        FileDB.id == file_id,
        FileDB.user_id == current.id,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not os.path.exists(f.file_path):
        raise HTTPException(status_code=404, detail="文件已被移除")
    return FileResponse(f.file_path, filename=f.original_name)


@router.get("/preview/{file_id}")
def file_preview(
    file_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """文件预览"""
    f = db.query(FileDB).filter(
        FileDB.id == file_id,
        FileDB.user_id == current.id,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not os.path.exists(f.file_path):
        raise HTTPException(status_code=404, detail="文件已被移除")
    return FileResponse(f.file_path)


@router.put("/rename/{file_id}")
def file_rename(
    file_id: int,
    data: FileRename,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重命名文件"""
    f = db.query(FileDB).filter(
        FileDB.id == file_id,
        FileDB.user_id == current.id,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not data.new_name.strip():
        raise HTTPException(status_code=400, detail="名称不能为空")

    if f.file_suffix and not data.new_name.lower().endswith("." + f.file_suffix):
        f.original_name = f"{data.new_name}.{f.file_suffix}"
    else:
        f.original_name = data.new_name
    db.commit()
    return resp(200, "重命名成功", None)


@router.put("/move/{file_id}")
def file_move(
    file_id: int,
    data: FileMove,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移动文件"""
    f = db.query(FileDB).filter(
        FileDB.id == file_id,
        FileDB.user_id == current.id,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")

    if data.target_folder_id != 0:
        target = db.query(Folder).filter(
            Folder.id == data.target_folder_id,
            Folder.user_id == current.id,
        ).first()
        if not target:
            raise HTTPException(status_code=404, detail="目标文件夹不存在")

    old_folder_id = f.folder_id
    f.folder_id = data.target_folder_id

    for fid in {old_folder_id, data.target_folder_id}:
        if fid != 0:
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
    return resp(200, "移动成功", None)


@router.put("/del/{file_id}")
def file_soft_delete(
    file_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """软删除文件（移入回收站）"""
    f = db.query(FileDB).filter(
        FileDB.id == file_id,
        FileDB.user_id == current.id,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")
    if f.is_delete == 1:
        raise HTTPException(status_code=400, detail="文件已在回收站")

    f.is_delete = 1
    f.delete_time = datetime.now()

    if f.folder_id != 0:
        folder = db.query(Folder).filter(Folder.id == f.folder_id).first()
        if folder:
            folder.file_count = max(0, folder.file_count - 1)
            folder.total_size = max(0, folder.total_size - f.file_size)

    db.commit()
    return resp(200, "已移入回收站", None)


@router.delete("/{file_id}")
def file_permanent_delete(
    file_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """彻底删除文件"""
    f = db.query(FileDB).filter(
        FileDB.id == file_id,
        FileDB.user_id == current.id,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")

    folder_id = f.folder_id
    file_size = f.file_size

    if os.path.exists(f.file_path):
        try:
            os.remove(f.file_path)
        except Exception as e:
            print(f"[删除文件失败] {f.file_path}: {e}")
    db.delete(f)

    if folder_id != 0:
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if folder:
            folder.file_count = db.query(FileDB).filter(
                FileDB.folder_id == folder_id,
                FileDB.is_delete == 0,
            ).count()
            folder.total_size = db.query(func.sum(FileDB.file_size)).filter(
                FileDB.folder_id == folder_id,
                FileDB.is_delete == 0,
            ).scalar() or 0

    db.commit()
    return resp(200, "已彻底删除", None)


@router.put("/batch/del")
def file_batch_del(
    data: FileBatchDel,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量软删除文件"""
    files = db.query(FileDB).filter(
        FileDB.id.in_(data.id_list),
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
    ).all()
    now = datetime.now()
    affected_folder_ids = set()
    for f in files:
        f.is_delete = 1
        f.delete_time = now
        if f.folder_id != 0:
            affected_folder_ids.add(f.folder_id)

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
    return resp(200, f"已将 {len(files)} 个文件移入回收站", None)


@router.put("/batch/move")
def file_batch_move(
    data: FileBatchMove,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量移动文件"""
    if data.target_folder_id != 0:
        target = db.query(Folder).filter(
            Folder.id == data.target_folder_id,
            Folder.user_id == current.id,
        ).first()
        if not target:
            raise HTTPException(status_code=404, detail="目标文件夹不存在")

    files = db.query(FileDB).filter(
        FileDB.id.in_(data.id_list),
        FileDB.user_id == current.id,
        FileDB.is_delete == 0,
    ).all()

    affected_folder_ids = set()
    for f in files:
        affected_folder_ids.add(f.folder_id)
        f.folder_id = data.target_folder_id
    affected_folder_ids.add(data.target_folder_id)

    for fid in affected_folder_ids:
        if fid != 0:
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
    return resp(200, "批量移动成功", None)
