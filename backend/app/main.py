"""
FileManager 文件管理系统 - 后端主应用
基于 FastAPI + SQLAlchemy + MySQL

优化点：
1. 采用 Controller/Service/DAO 三层架构
2. 路由按功能模块拆分到 routers/ 目录
3. 移除前端页面路由，纯 API 服务
4. 添加 CORS 配置支持前端开发
5. 添加 .gitignore 排除虚拟环境
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine, SessionLocal
from app.models import User, SystemSetting
from app.utils import hash_password
from app.routers import auth, folder, file, recycle, stats, settings, user
from app.routers import ai_router, kb_router

# ============ 全局常量 ============
BASE_STATIC = "static"
FRONTEND_DIST = os.path.join(BASE_STATIC, "dist")
ADMIN_USERNAME = "your_admin_username"
ADMIN_PASSWORD = "your_admin_password"
ADMIN_EMAIL = "your_email@example.com"

os.makedirs(BASE_STATIC, exist_ok=True)


# ============ 启动事件 ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时创建表、初始化管理员账号和默认系统设置"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=ADMIN_USERNAME,
                password=hash_password(ADMIN_PASSWORD),
                email=ADMIN_EMAIL,
                role="admin",
                status=1,
            )
            db.add(admin)
            db.commit()
            print(f"[初始化] 管理员账号已创建: {ADMIN_USERNAME}")

        default_settings = {
            "site_name": ("FileManager 文件管理系统", "网站名称"),
            "site_url": ("http://localhost", "网站地址"),
            "contact_email": (ADMIN_EMAIL, "联系邮箱"),
            "site_description": ("基于 FastAPI + Vue3 的轻量级文件管理系统", "网站描述"),
            "allow_register": ("true", "是否允许注册"),
            "register_audit": ("false", "注册是否需要审核"),
            "default_role": ("user", "新用户默认角色"),
        }
        for key, (value, desc) in default_settings.items():
            existing = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
            if not existing:
                db.add(SystemSetting(setting_key=key, setting_value=value, description=desc))
            elif key == "contact_email":
                existing.setting_value = ADMIN_EMAIL
        db.commit()
    finally:
        db.close()
    yield


# ============ FastAPI 应用 ============
app = FastAPI(title="FileManager 文件管理系统 API", version="3.0.0", lifespan=lifespan)

# CORS 配置 - 支持前端开发服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录（用于文件预览和下载）
app.mount("/static", StaticFiles(directory=BASE_STATIC), name="static")

# 注册路由
app.include_router(auth.router)
app.include_router(folder.router)
app.include_router(file.router)
app.include_router(recycle.router)
app.include_router(stats.router)
app.include_router(settings.router)
app.include_router(user.router)
app.include_router(ai_router.router)
app.include_router(kb_router.router)


# 启动时确保新增的知识库表也被创建（向前兼容）
try:
    from app.models import KnowledgeBase, KbDocument, KbChunk, ChatMessage  # noqa: F401
    Base.metadata.create_all(bind=engine, tables=[
        Base.metadata.tables.get("knowledge_base"),
        Base.metadata.tables.get("kb_document"),
        Base.metadata.tables.get("kb_chunk"),
        Base.metadata.tables.get("chat_message"),
    ])
except Exception as _e:
    print(f"[init] 创建知识库/对话表异常: {_e}")

# 挂载前端构建产物的 assets 目录（确保 JS/CSS 以正确 MIME 类型返回）
FRONTEND_ASSETS = os.path.join(FRONTEND_DIST, "assets")
if os.path.isdir(FRONTEND_ASSETS):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="frontend_assets")

# ============ 前端页面托管（SPA） ============
@app.get("/")
def serve_frontend():
    """提供前端首页"""
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {"status": "ok", "message": "FileManager API 服务运行中", "version": "3.0.0"}


@app.get("/{path:path}")
def serve_frontend_spa(path: str):
    """SPA 路由兜底：所有未匹配的路径返回 index.html"""
    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.isfile(file_path):
        return HTMLResponse(content=open(file_path, encoding="utf-8").read())
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {"status": "ok", "message": "FileManager API 服务运行中", "version": "3.0.0"}
