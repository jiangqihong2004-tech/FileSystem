"""
数据库连接配置模块
统一管理 SQLAlchemy 引擎、会话工厂和 Base 声明基类
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ============ 数据库连接参数（支持环境变量） ============
DB_USER = os.environ.get("DB_USER", "your_db_user")
DB_PWD = os.environ.get("DB_PWD", "your_db_password")
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "file_manager")

SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PWD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

# 创建引擎，开启预填充、自动回收连接
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明式基类，所有模型继承自它
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每个请求获取独立数据库会话，请求结束自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
