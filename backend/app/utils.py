"""
工具函数模块
包含密码加密、JWT 令牌、统一响应、文件类型识别等
"""
import hashlib
import time
import json
import base64
from datetime import datetime
from typing import Any, Optional

# ============ JWT 配置 ============
JWT_SECRET = "your_jwt_secret_key_here"
JWT_EXPIRE_HOURS = 24


# ============ 密码加密 ============
def hash_password(password: str) -> str:
    """SHA256 加密密码"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hash_password(plain_password) == hashed_password


# ============ JWT Token（轻量实现，无需第三方库） ============
def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding == 4:
        padding = 0
    if padding:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_token(user_id: int, username: str, role: str) -> str:
    """生成 JWT token"""
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_data = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + JWT_EXPIRE_HOURS * 3600,
    }
    payload = _b64encode(json.dumps(payload_data).encode())
    signature = _b64encode(
        hashlib.sha256(f"{header}.{payload}.{JWT_SECRET}".encode()).digest()
    )
    return f"{header}.{payload}.{signature}"


def parse_token(token: str) -> Optional[dict]:
    """解析并校验 JWT token，返回 payload 或 None"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, signature = parts
        expected_sig = _b64encode(
            hashlib.sha256(f"{header}.{payload}.{JWT_SECRET}".encode()).digest()
        )
        if signature != expected_sig:
            return None
        data = json.loads(_b64decode(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


# ============ 统一响应 ============
def to_dict(obj) -> dict:
    """将 SQLAlchemy 模型对象转为字典"""
    if obj is None:
        return None
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, datetime):
            val = val.strftime("%Y-%m-%d %H:%M:%S")
        result[col.name] = val
    return result


def resp(code: int, msg: str, data: Any = None) -> dict:
    """统一响应格式"""
    return {"code": code, "msg": msg, "data": to_dict(data) if data is not None and not isinstance(data, (dict, list, str, int, float, bool)) else data}


# ============ 文件类型识别 ============
IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "bmp", "svg", "webp", "ico"}
VIDEO_EXTS = {"mp4", "avi", "mov", "wmv", "flv", "mkv", "webm", "m4v"}
AUDIO_EXTS = {"mp3", "wav", "flac", "aac", "ogg", "wma", "m4a"}
DOC_EXTS = {"doc", "docx", "txt", "pdf", "rtf", "odt", "md"}
SHEET_EXTS = {"xls", "xlsx", "csv", "ods"}
SLIDE_EXTS = {"ppt", "pptx", "odp"}
ARCHIVE_EXTS = {"zip", "rar", "7z", "tar", "gz", "bz2", "xz"}


def get_file_category(suffix: str) -> str:
    """根据后缀返回文件分类: image/video/audio/doc/sheet/slide/archive/other"""
    if not suffix:
        return "other"
    s = suffix.lower().lstrip(".")
    if s in IMAGE_EXTS:
        return "image"
    if s in VIDEO_EXTS:
        return "video"
    if s in AUDIO_EXTS:
        return "audio"
    if s in DOC_EXTS:
        return "doc"
    if s in SHEET_EXTS:
        return "sheet"
    if s in SLIDE_EXTS:
        return "slide"
    if s in ARCHIVE_EXTS:
        return "archive"
    return "other"


def get_file_icon(suffix: str) -> str:
    """根据后缀返回 emoji 图标"""
    category = get_file_category(suffix)
    icon_map = {
        "image": "🖼️",
        "video": "🎬",
        "audio": "🎵",
        "doc": "📄",
        "sheet": "📊",
        "slide": "📈",
        "archive": "🗜️",
        "other": "📦",
    }
    return icon_map.get(category, "📦")


def format_size(bytes_size: int) -> str:
    """字节大小格式化"""
    if not bytes_size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(bytes_size)
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    if idx == 0:
        return f"{int(size)} {units[idx]}"
    return f"{size:.1f} {units[idx]}"


def extract_suffix(filename: str) -> str:
    """提取文件后缀（小写，不含点）"""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()
