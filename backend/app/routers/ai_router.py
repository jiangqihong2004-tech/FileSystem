"""
AI 智能助手 & 知识库问答 FastAPI 路由模块
===========================================
新增改进：
  - 两种模式：general（通用助手）、kb（知识库问答），彼此独立
  - 对话记录持久化到数据库 chat_message 表，刷新页面/退出登录/重启都不会丢失
  - 只有用户点击"清除对话记录"才会清空
  - 按 user_id + mode 严格隔离

接口总览：
  POST  /ai/chat          发送一条文本消息（通用或知识库）
  POST  /ai/image         上传图片并附带文字提问（仅通用助手）
  GET   /ai/history       加载当前登录用户的历史对话（按 mode 区分）
  DELETE /ai/clear        清空当前登录用户的对话（按 mode 区分）
  POST  /kb/ask-all       跨所有知识库问答（与 /ai/chat mode=kb 等价）
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
import base64

from app.database import get_db
from app.chat_session import get_session_manager
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/ai", tags=["AI智能助手"])


# ============ 请求/响应模型 ============
class ChatRequest(BaseModel):
    """发送对话的请求体"""
    mode: str = Field(default="general", description="对话模式：general / kb")
    content: str = Field(..., min_length=1, max_length=4000, description="用户输入的文本")


class HistoryRequest(BaseModel):
    mode: Optional[str] = "general"


class ClearRequest(BaseModel):
    mode: Optional[str] = "general"


def _normalize_mode(mode: str) -> str:
    mode = (mode or "general").lower().strip()
    if mode not in ("general", "kb"):
        mode = "general"
    return mode


# ============ 路由处理函数 ============
@router.post("/chat", summary="发送消息并获取 AI 回复（支持两种模式）")
def ai_chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    发送一条用户消息，调用 AI 生成回复，并写入数据库持久化。
    mode: "general"（通用助手） 或 "kb"（知识库问答）
    """
    try:
        mode = _normalize_mode(req.mode)
        manager = get_session_manager()
        result = manager.send_message(
            user_id=current_user.id,
            content=req.content,
            mode=mode,
        )
        reply_text = result.get("reply") if isinstance(result, dict) else result
        reasoning = result.get("reasoning") if isinstance(result, dict) else None
        return {
            "code": 200,
            "message": "ok",
            "data": {
                "user_id": current_user.id,
                "mode": mode,
                "reply": reply_text,
                "reasoning": reasoning,
                "role": "assistant",
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI助手调用异常: {e}")


@router.get("/history", summary="加载当前登录用户的历史对话（按 mode 区分）")
def ai_history(
    mode: str = "general",
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的历史对话（刷新页面后恢复上下文用）"""
    try:
        m = _normalize_mode(mode)
        manager = get_session_manager()
        messages = manager.load_history(user_id=current_user.id, mode=m)
        return {
            "code": 200,
            "message": "ok",
            "data": {"user_id": current_user.id, "mode": m, "messages": messages}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载历史失败: {e}")


@router.delete("/clear", summary="清空当前登录用户的对话记录（按 mode 区分）")
def ai_clear(
    mode: str = "general",
    current_user: User = Depends(get_current_user),
):
    """清空当前登录用户指定模式的对话记录（内存 + 数据库）"""
    try:
        m = _normalize_mode(mode)
        manager = get_session_manager()
        ok = manager.clear_session(user_id=current_user.id, mode=m)
        return {
            "code": 200 if ok else 500,
            "message": "ok" if ok else "failed",
            "data": {"user_id": current_user.id, "mode": m, "cleared": ok}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空会话失败: {e}")


@router.post("/image", summary="上传图片并获取 AI 识别与解释")
async def ai_image(
    file: UploadFile = File(..., description="上传的图片（jpg/png/webp/gif/bmp）"),
    prompt: Optional[str] = Form(default=None, description="用户对图片的提问文本（可为空）"),
    current_user: User = Depends(get_current_user),
):
    """
    用户上传一张本地图片（可选附带文字提问），AI 助手会识别图片内容，
    解释图中是什么、有哪些物体/场景/人物，并针对用户的提问进行回答。
    图片内容不会保存到磁盘，但会转为文本描述写入数据库作为上下文。
    """
    # 1. 文件基本校验
    if not file:
        raise HTTPException(status_code=400, detail="未提供图片文件")

    allowed_mime = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif", "image/bmp"}
    content_type = (file.content_type or "").lower()
    if content_type not in allowed_mime:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片类型: {content_type}，仅支持 jpg/png/webp/gif/bmp"
        )

    # 2. 读取文件内容并转为 base64（限制 10MB）
    try:
        file_bytes = await file.read()
        max_size = 10 * 1024 * 1024
        if len(file_bytes) > max_size:
            raise HTTPException(status_code=400, detail="图片大小超过 10MB 限制")
        if not file_bytes:
            raise HTTPException(status_code=400, detail="图片文件为空")
        image_base64 = base64.b64encode(file_bytes).decode("utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取图片失败: {e}")

    # 3. 交给会话管理器执行图片识别对话（仅 general 模式）
    try:
        manager = get_session_manager()
        user_prompt = (prompt or "").strip()
        reply_text = manager.send_image_message(
            user_id=current_user.id,
            image_base64=image_base64,
            mime_type=content_type,
            user_prompt=user_prompt,
            mode="general",
        )
        reasoning = None
        if isinstance(reply_text, dict):
            reasoning = reply_text.get("reasoning")
            reply_text = reply_text.get("reply")
        return {
            "code": 200,
            "message": "ok",
            "data": {
                "user_id": current_user.id,
                "mode": "general",
                "reply": reply_text,
                "reasoning": reasoning,
                "role": "assistant",
                "prompt_used": user_prompt or "",
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片识别调用异常: {e}")
