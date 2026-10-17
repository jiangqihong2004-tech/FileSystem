"""
知识库路由
===========================
提供知识库、文档上传、检索、问答等 API。
全部接口需登录（依赖 get_current_user）。
- 用户 A/B 与管理员彼此隔离（user_id 权限判断）
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, KbChunk
from app.kb_session import KnowledgeSession, ALLOWED_EXTS


router = APIRouter(prefix="/kb", tags=["知识库"])


# ============ 请求模型 ============
class CreateKbRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class AskKbRequest(BaseModel):
    kb_id: int
    question: str


# ============ 辅助 ============
def _session_for(db: Session, user: User) -> KnowledgeSession:
    return KnowledgeSession(db=db, user_id=user.id)


# ============ 知识库 ============
@router.get("/list", summary="列出当前用户的知识库")
def kb_list(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        items = _session_for(db, current_user).list_knowledge_bases()
        return {"code": 200, "message": "ok", "data": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库列表失败: {e}")


@router.post("/create", summary="创建新的知识库")
def kb_create(
    req: CreateKbRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        kb = _session_for(db, current_user).create_knowledge_base(req.name, req.description or "")
        return {"code": 200, "message": "ok", "data": kb}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识库失败: {e}")


@router.delete("/{kb_id}", summary="删除指定知识库（含文档与向量片段）")
def kb_delete(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ok = _session_for(db, current_user).delete_knowledge_base(kb_id)
        if not ok:
            raise HTTPException(status_code=404, detail="知识库不存在或无权限")
        return {"code": 200, "message": "ok", "data": {"kb_id": kb_id, "deleted": True}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除知识库失败: {e}")


# ============ 文档 ============
@router.get("/{kb_id}/documents", summary="获取指定知识库的文档列表")
def kb_documents(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        docs = _session_for(db, current_user).list_documents(kb_id)
        return {"code": 200, "message": "ok", "data": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {e}")


@router.post("/{kb_id}/upload", summary="上传文档并完成向量化入库")
async def kb_upload(
    kb_id: int,
    file: UploadFile = File(..., description="上传 doc/docx/pdf/xls/xlsx/csv/txt 文档"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # 检查扩展名
        fname = file.filename or "untitled"
        ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if ext not in ALLOWED_EXTS:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型：{ext}")
        # 读取字节：限制 20MB
        max_size = 20 * 1024 * 1024
        contents = await file.read()
        if len(contents) > max_size:
            raise HTTPException(status_code=400, detail="文件大小超过 20MB 限制")
        doc = _session_for(db, current_user).upload_document(kb_id, fname, contents)
        return {"code": 200, "message": "ok", "data": doc}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传并向量化失败: {e}")


@router.delete("/document/{doc_id}", summary="删除指定文档（含磁盘文件与对应片段）")
def kb_delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ok = _session_for(db, current_user).delete_document(doc_id)
        if not ok:
            raise HTTPException(status_code=404, detail="文档不存在或无权限")
        return {"code": 200, "message": "ok", "data": {"doc_id": doc_id, "deleted": True}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {e}")


# ---------- 知识库和文档的重命名/移动/下载 ----------
class RenameKbRequest(BaseModel):
    name: str
    description: Optional[str] = None


class RenameDocRequest(BaseModel):
    name: str


class MoveDocRequest(BaseModel):
    target_kb_id: int


@router.put("/{kb_id}", summary="重命名/更新知识库")
def kb_rename(
    kb_id: int,
    req: RenameKbRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        kb = _session_for(db, current_user).rename_knowledge_base(kb_id, req.name, req.description)
        return {"code": 200, "message": "ok", "data": kb}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名知识库失败: {e}")


@router.put("/document/{doc_id}", summary="重命名文档")
def kb_rename_document(
    doc_id: int,
    req: RenameDocRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        doc = _session_for(db, current_user).rename_document(doc_id, req.name)
        return {"code": 200, "message": "ok", "data": doc}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名文档失败: {e}")


@router.post("/document/{doc_id}/move", summary="将文档移动到另一个知识库")
def kb_move_document(
    doc_id: int,
    req: MoveDocRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        doc = _session_for(db, current_user).move_document(doc_id, req.target_kb_id)
        return {"code": 200, "message": "ok", "data": doc}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移动文档失败: {e}")


@router.get("/document/{doc_id}/download", summary="下载单个文档")
def kb_download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        info = _session_for(db, current_user).get_document_path(doc_id)
        from fastapi.responses import FileResponse
        return FileResponse(
            path=info["file_path"],
            filename=info["original_name"],
            media_type="application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载文档失败: {e}")


@router.get("/{kb_id}/download", summary="打包下载知识库中所有文档（ZIP）")
def kb_download_all(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        docs = _session_for(db, current_user).get_knowledge_base_docs(kb_id)
        if not docs:
            raise HTTPException(status_code=400, detail="知识库中无可用文件")
        # 动态生成 ZIP，流式响应
        import zipfile
        import io
        from fastapi.responses import StreamingResponse

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, doc in enumerate(docs):
                # 防止同名文件覆盖，按序号前缀
                safe_name = f"{idx + 1:03d}_{doc['original_name']}"
                try:
                    zf.write(doc["file_path"], arcname=safe_name)
                except Exception:
                    pass
        buf.seek(0)
        kb_name = f"knowledge_base_{kb_id}"
        headers = {"Content-Disposition": f"attachment; filename=\"{kb_name}.zip\""}
        return StreamingResponse(iter([buf.read()]), media_type="application/zip", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打包下载失败: {e}")


# ============ 检索 + 问答 ============
@router.post("/search", summary="在指定知识库中按余弦相似度检索相关片段")
def kb_search(
    req: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        kb_id = int(req.get("kb_id") or 0)
        query = (req.get("question") or "").strip()
        top_k = int(req.get("top_k") or 8)
        if kb_id <= 0 or not query:
            raise HTTPException(status_code=400, detail="缺少必要参数 kb_id 或 question")
        hits = _session_for(db, current_user).search_top_k(kb_id, query, top_k=top_k)
        return {"code": 200, "message": "ok", "data": {"kb_id": kb_id, "question": query, "hits": hits}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")


@router.post("/ask", summary="知识库问答（RAG：检索相关片段 + 调用模型回答）")
def kb_ask(
    req: AskKbRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if not req.kb_id or not req.question or not str(req.question).strip():
            raise HTTPException(status_code=400, detail="缺少必要参数 kb_id 或 question")
        result = _session_for(db, current_user).rag_answer(req.kb_id, req.question.strip())
        return {"code": 200, "message": "ok", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识库问答失败: {e}")


# ============ 跨知识库问答（全局检索） ============
class AskAllRequest(BaseModel):
    question: str


@router.post("/ask-all", summary="跨所有知识库问答（全局 RAG，自动持久化对话历史）")
def kb_ask_all(
    req: AskAllRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    改进版：执行知识库向量检索后，调用 chat_session 生成 AI 回复，
    并自动将问答记录持久化到 chat_message 表（mode="kb"），
    从而支持刷新页面恢复、退出登录后恢复、清除按钮清除等功能。
    """
    try:
        q = (req.question or "").strip()
        if not q:
            raise HTTPException(status_code=400, detail="缺少 question 参数")

        session = _session_for(db, current_user)
        # 1) 先搜索相关片段
        hits = session.search_all_top_k(q, top_k=8)
        # 2) 拼接片段为 AI 可理解的上下文
        parts = []
        for idx, hit in enumerate(hits[:5], 1):
            parts.append(f"[相关片段 {idx}] {hit.get('content', '')}")
        context = "\n".join(parts) or "（未检索到相关内容）"

        # 3) 交给 chat_session 生成回复并持久化（mode="kb"）
        from app.chat_session import get_session_manager
        manager = get_session_manager()
        # 注意：content 是完整上下文（含知识库片段），但 user_question 只存用户真实问题，
        # 避免刷新页面后在"用户消息"气泡中看到 [知识库]/[相关片段] 等内部信息
        result = manager.send_message(
            user_id=current_user.id,
            content=f"[知识库] 用户问题：{q}\n相关内容：\n{context}\n请基于上述相关内容回答用户问题。",
            user_question=q,
            mode="kb",
        )
        # 构造一条专门针对知识库问答的 reasoning（更贴近检索流程）
        kb_reasoning_parts = [
            f"① 解析用户问题：「{q[:80]}{'…' if len(q) > 80 else ''}」。",
            "② 向量化：将用户问题编码为向量。",
            "③ 全库余弦相似度检索：在 {} 个知识库的文档片段中做匹配。".format(
                sum(1 for h in hits)  # 简单展示命中数量
            ),
            "④ 取 TOP 5 片段作为上下文：\n{}".format(
                "\n".join([f"  · 片段 {i+1}（得分 {round(h.get('score', 0), 3)}）" for i, h in enumerate(hits[:5])]) or "  · 未命中任何片段。"
            ),
            "⑤ 将片段与用户问题交给 LLM 生成最终答案。",
        ]
        if isinstance(result, dict):
            reply = result.get("reply")
            # 拼接：保留通用 reasoning 的最后几步，同时展示我们构造的 KB 检索 reasoning
            reasoning = "\n".join(kb_reasoning_parts) + "\n" + (result.get("reasoning") or "").replace("①", "⑥").replace("②", "⑦").replace("③", "⑧").replace("④", "⑨").replace("⑤", "⑩").replace("⑥", "⑪").replace("⑦", "⑫")
        else:
            reply = result
            reasoning = "\n".join(kb_reasoning_parts)

        # 4) 返回给前端（简化版答案 + 命中片段 + 思考过程）
        return {
            "code": 200,
            "message": "ok",
            "data": {
                "question": q,
                "answer": reply,
                "reasoning": reasoning,
                "hits": hits,
                "mode": "kb",
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"跨知识库问答失败: {e}")


@router.post("/search-all", summary="跨所有知识库余弦相似度检索")
def kb_search_all(
    req: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = (req.get("question") or "").strip()
        top_k = int(req.get("top_k") or 8)
        if not query:
            raise HTTPException(status_code=400, detail="缺少 question 参数")
        hits = _session_for(db, current_user).search_all_top_k(query, top_k=top_k)
        return {"code": 200, "message": "ok", "data": {"question": query, "hits": hits}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")
