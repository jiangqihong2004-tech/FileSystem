"""
Web 端多轮对话会话管理器（改进版）
===========================================
- 两种模式：general（通用助手） 与 kb（知识库问答），各自独立，互不干扰
- 持久化到数据库 chat_message 表，退出登录/重启/关闭项目都不会丢失
- 仅在用户点击"清除对话记录"按钮时才会清空
- 按 user_id + mode 严格隔离（不同账号的历史完全分离）

使用方式：
    from app.chat_session import get_session_manager
    manager = get_session_manager()
    reply = manager.send_message(user_id=1, content="你好", mode="general")
    history = manager.load_history(user_id=1, mode="general")
    manager.clear_session(user_id=1, mode="kb")
"""

import os
import threading
from datetime import datetime

from app.base_agent import chat_with_agent, describe_image

# ============ 配置区 ============
# 对话记录存储目录（保留用于向后兼容，实际不再使用）
CHAT_RECORD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "file_mgr",
    "chat_record"
)

# 系统提示词（两种模式区分）
SYSTEM_PROMPT_GENERAL = (
    "你是 FileManager 文件管理系统内置的 AI 智能助手。"
    "你可以回答用户的通用问题、闲聊、协助查询时间和日期。"
    "当用户询问时间相关问题时，请使用提供的 get_current_time 工具获取准确时间，"
    "不要自行推断时间。回答时语言简洁友好，使用中文。"
)

SYSTEM_PROMPT_KB = (
    "你是 FileManager 文件管理系统内置的知识库问答助手。"
    "请根据下方提供的相关片段，准确、简洁地回答用户的问题。"
    "若相关片段中没有给出答案或未检索到相关内容，请明确告知用户，"
    "不要自行编造。回答时使用中文。"
)


class ChatSessionManager:
    """
    多轮对话会话管理器
    - 两种模式：general（通用助手）、kb（知识库问答），各自独立，互不干扰
    - 持久化到数据库 chat_message 表，退出登录/重启都不会丢失
    - 仅在用户点击"清除"按钮时才会清空
    - 按 user_id + mode 严格隔离
    """

    # 类级线程锁（所有实例共享）
    _lock = threading.RLock()

    VALID_MODES = ("general", "kb")

    def __init__(self, db_getter=None, record_dir: str = CHAT_RECORD_DIR):
        """
        Args:
            db_getter: 返回 SQLAlchemy Session 的可调用对象（可选）
            record_dir: 对话记录存档目录（仅保留向后兼容）
        """
        self.record_dir = record_dir
        os.makedirs(self.record_dir, exist_ok=True)

        # 内存存储：{(user_id, mode): [message, message, ...]}
        self._sessions: dict = {}

        # 数据库会话获取器
        self._db_getter = db_getter

    # ============================================================
    #  辅助：session key & DB 会话
    # ============================================================
    @staticmethod
    def _session_key(user_id: int, mode: str) -> tuple:
        return (int(user_id), str(mode))

    def _get_db(self):
        """获取数据库会话"""
        if self._db_getter:
            try:
                return self._db_getter()
            except Exception:
                pass
        # 懒加载默认数据库
        try:
            from app.database import SessionLocal
            return SessionLocal()
        except Exception:
            return None

    # ============================================================
    #  数据库持久化相关
    # ============================================================
    def _append_to_db(self, user_id: int, mode: str, role: str, content: str):
        """将一条消息追加到数据库"""
        db = self._get_db()
        if db is None:
            return
        try:
            from app.models import ChatMessage
            msg = ChatMessage(
                user_id=user_id,
                mode=mode,
                role=role,
                content=content,
                create_time=datetime.now(),
            )
            db.add(msg)
            db.commit()
        except Exception as e:
            print(f"[chat_session] 写入对话失败: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _load_from_db(self, user_id: int, mode: str) -> list:
        """从数据库加载该用户指定模式的历史消息"""
        messages = []
        db = self._get_db()
        if db is None:
            return messages
        try:
            from app.models import ChatMessage
            rows = (
                db.query(ChatMessage)
                .filter(ChatMessage.user_id == user_id, ChatMessage.mode == mode)
                .order_by(ChatMessage.id.asc())
                .all()
            )
            for row in rows:
                messages.append({"role": row.role, "content": row.content})
        except Exception as e:
            print(f"[chat_session] 读取对话历史失败: {e}")
        finally:
            try:
                db.close()
            except Exception:
                pass
        return messages

    def _clear_in_db(self, user_id: int, mode: str) -> bool:
        """从数据库删除该用户指定模式的所有消息"""
        db = self._get_db()
        if db is None:
            return False
        try:
            from app.models import ChatMessage
            db.query(ChatMessage).filter(
                ChatMessage.user_id == user_id,
                ChatMessage.mode == mode,
            ).delete(synchronize_session=False)
            db.commit()
            return True
        except Exception as e:
            print(f"[chat_session] 清空对话失败: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return False
        finally:
            try:
                db.close()
            except Exception:
                pass

    # ============================================================
    #  系统提示词 & 消息初始化
    # ============================================================
    def _system_prompt_for(self, mode: str) -> str:
        return SYSTEM_PROMPT_KB if mode == "kb" else SYSTEM_PROMPT_GENERAL

    def _new_session_messages(self, mode: str = "general") -> list:
        """构造新的 messages 列表（含 system 提示词）"""
        return [{"role": "system", "content": self._system_prompt_for(mode)}]

    def _ensure_session(self, user_id: int, mode: str) -> list:
        """确保内存中有该会话，首次加载时从数据库恢复"""
        key = self._session_key(user_id, mode)
        if key not in self._sessions:
            db_messages = self._load_from_db(user_id, mode)
            if db_messages:
                self._sessions[key] = self._new_session_messages(mode) + db_messages
            else:
                self._sessions[key] = self._new_session_messages(mode)
        return self._sessions[key]

    # ============================================================
    #  对外 API
    # ============================================================
    # ------------------------------------------------------------
    #  生成"思考过程（reasoning）"文本：向用户展示 AI 的思考路径
    # ------------------------------------------------------------
    @staticmethod
    def _build_reasoning(content: str, mode: str, context_len: int = 0) -> str:
        """
        基于用户输入生成一段"思考过程"文本，用于前端以可折叠方式展示。
        该文本不影响实际 AI 回复，仅用于让用户感知 AI 的分析过程。
        """
        content = (content or "").strip()
        if not content:
            return "收到用户输入为空，将提示用户提供有效内容。"

        lines = []
        lines.append(f"① 理解问题：用户说「{content[:80]}{'…' if len(content) > 80 else ''}」。")

        # 模式差异
        if mode == "kb":
            lines.append("② 识别场景：这是知识库问答，需要先做向量化检索。")
            lines.append("③ 准备工作：将用户问题编码为向量，再与知识库中的文档片段做余弦相似度匹配。")
            lines.append("④ 检索策略：按分数降序，取 TOP N 最高相关片段作为上下文。")
            lines.append("⑤ 答案生成：将检索到的片段拼接后交给 LLM，基于片段内容组织答案；无相关片段则直接告知未找到。")
        else:
            lines.append("② 识别意图：判断用户是在提问、闲聊、请求工具（时间/日期）还是上传图片查询。")
            lines.append("③ 上下文：已有 {} 条历史对话，将把最新问题与上下文一起提交给模型。".format(context_len))
            lines.append("④ 工具使用：如果涉及时间、日期，则优先调用 get_current_time 获取真实时间；否则直接让模型生成文本回复。")

        # 关键词提示
        kws = [c for c in ["时间", "日期", "几点", "今天", "图片", "天气", "文件", "目录"] if c in content]
        if kws:
            lines.append("⑥ 关键词命中：{}，将重点处理这些内容。".format("、".join(kws)))
        else:
            lines.append("⑥ 关键词命中：无强关键词，使用常规文本生成方式回复。")

        lines.append("⑦ 最终：组织语言，以简洁、友好的中文回答。")
        return "\n".join(lines)

    def send_message(self, user_id: int, content: str, mode: str = "general", user_question: str = None) -> dict:
        """
        用户发送一条消息，返回 AI 助手的回复（含思考过程）。
        - content：发送给 AI 的完整文本（可能含上下文 / 提示词前缀）
        - user_question：用户真实输入的问题（用于持久化到数据库，避免把内部上下文
          当作"用户消息"写入并在刷新页面时展示给用户）
        返回：{"reply": str, "reasoning": str}
        """
        content = (content or "").strip()
        if not content:
            return {"reply": "请输入有效内容", "reasoning": self._build_reasoning(content, mode)}
        if mode not in self.VALID_MODES:
            mode = "general"

        # 持久化到数据库的用户消息：若传入 user_question，则只存用户的真实输入
        display_user_msg = (user_question if (user_question is not None and str(user_question).strip()) else content).strip()

        with self._lock:
            messages = self._ensure_session(user_id, mode)
            context_len = max(0, len(messages))
            # 内存中追加真实用户消息（用于后续会话上下文）
            messages.append({"role": "user", "content": content})
            self._append_to_db(user_id, mode, "user", display_user_msg)

            try:
                reply = chat_with_agent(messages)
            except Exception as e:
                reply = f"AI 调用异常：{e}"

            messages.append({"role": "assistant", "content": reply})
            self._append_to_db(user_id, mode, "assistant", reply)

            reasoning = self._build_reasoning(display_user_msg, mode, context_len)
            return {"reply": reply, "reasoning": reasoning}

    def send_image_message(self, user_id: int, image_base64: str, mime_type: str,
                           user_prompt: str = "", mode: str = "general") -> dict:
        """发送图片消息（仅通用助手模式使用），返回 {"reply": str, "reasoning": str}"""
        if mode not in self.VALID_MODES:
            mode = "general"
        with self._lock:
            messages = self._ensure_session(user_id, mode)
            prompt_text = user_prompt or "请描述这张图片"
            user_msg = f"[图片] {prompt_text}"
            messages.append({"role": "user", "content": user_msg})
            self._append_to_db(user_id, mode, "user", user_msg)

            try:
                reply = describe_image(image_base64, mime_type, prompt_text)
            except Exception as e:
                reply = f"图片识别异常：{e}"

            messages.append({"role": "assistant", "content": reply})
            self._append_to_db(user_id, mode, "assistant", reply)

            reasoning = (
                "① 理解请求：用户上传了一张图片，并附文字「{}」。\n"
                "② 识别流程：首先通过多模态视觉模型读取图片内容，提取关键对象、颜色、布局等信息。\n"
                "③ 与文本结合：将视觉识别结果与用户文本提示对齐，组织一段有意义的描述。\n"
                "④ 最终：以简洁友好的中文向用户反馈。"
            ).format(prompt_text[:80])
            return {"reply": reply, "reasoning": reasoning}

    def load_history(self, user_id: int, mode: str = "general") -> list:
        """加载该用户指定模式的历史消息列表（用于前端展示）"""
        if mode not in self.VALID_MODES:
            mode = "general"
        with self._lock:
            # 直接从数据库读取，保证切换用户/页面刷新都能获取最新内容
            return self._load_from_db(user_id, mode)

    def clear_session(self, user_id: int, mode: str = "general") -> bool:
        """清空该用户指定模式的历史记录（内存 + 数据库）"""
        if mode not in self.VALID_MODES:
            mode = "general"
        with self._lock:
            key = self._session_key(user_id, mode)
            self._sessions[key] = self._new_session_messages(mode)
            return self._clear_in_db(user_id, mode)

    def list_sessions(self) -> list:
        """列出内存中当前会话（调试/管理用）"""
        result = []
        for (uid, mode), msgs in list(self._sessions.items()):
            result.append({
                "user_id": uid,
                "mode": mode,
                "message_count": len(msgs),
            })
        return result


# ============================================================
#  全局单例：供 FastAPI 路由直接使用
# ============================================================
_global_manager: ChatSessionManager | None = None
_global_init_lock = threading.Lock()


def get_session_manager() -> ChatSessionManager:
    """获取全局对话管理器单例（延迟初始化）"""
    global _global_manager
    if _global_manager is None:
        with _global_init_lock:
            if _global_manager is None:
                _global_manager = ChatSessionManager()
    return _global_manager
