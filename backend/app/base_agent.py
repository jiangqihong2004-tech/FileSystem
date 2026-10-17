"""
火山方舟（Ark）Chat Completions + Function Calling 官方API封装
==========================================
- 基于 Python 标准库 urllib + ssl 原生 HTTPS 请求
- 支持 Function Calling 工具调用（内置 get_current_time 时间工具）
- 每次请求携带完整 messages 数组，维护多轮对话上下文记忆
- API_KEY 仅存储在此文件内，不暴露到前端

使用方式：
    from app.base_agent import chat_with_agent
    messages = [{"role": "user", "content": "现在几点了？"}]
    reply = chat_with_agent(messages)
"""

import json
import ssl
import re
import hashlib
import urllib.request
import urllib.error
from datetime import datetime

# ============ 火山方舟 API 配置区 ============
# 官方接入地址（Chat Completions 统一入口）
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# 模型推理接入点（Endpoint ID），在火山方舟控制台「推理接入点」中创建获取
# 格式示例："ep-20240101xxxxxx"
MODEL_ENDPOINT = ""

# 视觉多模态图像识别模型接入点（支持图片理解）
# 推荐使用 Doubao-Vision / 方舟视觉模型，该模型能够理解图片内容并进行解释
# 若控制台中已有视觉模型接入点，请把 ID 填写到下方；如留空则会降级为纯文本模型
VISION_ENDPOINT = ""

# 文本向量化 Embedding 模型接入点（知识库检索核心组件）
# 推荐使用 doubao-embedding-2 / doubao-embedding-vision 等官方模型
# 控制台「推理接入点」中创建，把 ID 填写到下方；如留空则会走本地哈希向量兜底
EMBEDDING_ENDPOINT = ""

# API Key（在火山方舟控制台「API Key 管理」中创建获取）
# ⚠️ 生产环境建议改为从环境变量读取：
#   import os
#   ARK_API_KEY = os.environ.get("ARK_API_KEY", "")
ARK_API_KEY = ""

# 请求超时时间（秒），官方建议设置为 180s
REQUEST_TIMEOUT = 180

# 工具调用最大循环次数（防止无限循环）
MAX_TOOL_CALLS = 6

# Embedding 向量维度（火山方舟 doubao-embedding-2 输出 2048 维）
EMBEDDING_DIM = 2048


# ============ 工具函数：get_current_time ============
def get_current_time(format_type: str = "default") -> str:
    """
    获取当前本地时间的工具函数（Function Calling 调用）

    Args:
        format_type: 时间格式
            - "default" : 默认格式 YYYY-MM-DD HH:MM:SS 星期X
            - "date"    : 仅日期 YYYY-MM-DD
            - "time"    : 仅时间 HH:MM:SS
            - "timestamp": Unix 时间戳

    Returns:
        格式化后的当前时间字符串
    """
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]

    if format_type == "date":
        return now.strftime("%Y-%m-%d")
    elif format_type == "time":
        return now.strftime("%H:%M:%S")
    elif format_type == "timestamp":
        return str(int(now.timestamp()))
    else:
        # default: 完整日期时间 + 星期
        return now.strftime(f"%Y-%m-%d %H:%M:%S {weekday}")


# ============ TOOLS 工具数组（Function Calling 规范） ============
# 严格遵循 OpenAI / 火山方舟 Function Calling 官方格式
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": (
                "获取用户当前所在地的本地日期和时间。"
                "当用户询问时间、日期、现在几点、今天几号、星期几等与时间相关的问题时，"
                "必须调用此工具获取准确时间，而不是凭空回答。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "format_type": {
                        "type": "string",
                        "description": (
                            "返回的时间格式："
                            "'default' 返回完整日期+时间+星期；"
                            "'date' 仅返回日期；"
                            "'time' 仅返回时分秒；"
                            "'timestamp' 返回 Unix 时间戳。"
                        ),
                        "enum": ["default", "date", "time", "timestamp"],
                        "default": "default"
                    }
                },
                "required": []
            }
        }
    }
]


# ============ 工具注册表：根据工具名查找实现函数 ============
TOOL_REGISTRY = {
    "get_current_time": get_current_time,
}


# ============ urllib + ssl 原生 HTTPS 请求函数 ============
def _ark_http_request(payload: dict) -> dict:
    """
    向火山方舟发起原生 HTTPS POST 请求

    Args:
        payload: 请求体字典（含 model、messages、tools 等）

    Returns:
        解析后的 JSON 响应字典

    Raises:
        RuntimeError: 请求失败或 API 返回错误
    """
    url = f"{BASE_URL}/chat/completions"

    # 构造请求头：严格携带 API Key
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_API_KEY}",
    }

    # 序列化请求体
    data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    # 创建 Request 对象
    req = urllib.request.Request(
        url=url,
        data=data_bytes,
        headers=headers,
        method="POST"
    )

    # 创建 SSL 上下文（启用证书校验）
    ssl_context = ssl.create_default_context()

    try:
        # 发起 HTTPS 请求
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ssl_context) as resp:
            resp_body = resp.read().decode("utf-8")
            resp_json = json.loads(resp_body)

            # 正常响应：提取 assistant message
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                return resp_json

            # 错误响应
            error_msg = resp_json.get("error", {}).get("message", str(resp_json))
            raise RuntimeError(f"火山方舟API返回错误: {error_msg}")

    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        try:
            detail_json = json.loads(detail)
            detail = detail_json.get("error", {}).get("message", detail)
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} 请求失败: {detail}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络连接失败: {e.reason}")
    except TimeoutError:
        raise RuntimeError("请求超时（180s）")
    except json.JSONDecodeError:
        raise RuntimeError("响应解析失败，返回内容非合法 JSON")


# ============ 主函数：带 Function Calling 的多轮对话 ============
def chat_with_agent(messages: list, use_tools: bool = True) -> str:
    """
    与火山方舟对话助手交互（支持 Function Calling）

    Args:
        messages: 完整对话历史，形如
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么可以帮您？"},
                {"role": "user", "content": "现在几点了？"}
            ]
        use_tools: 是否启用工具调用（默认 True）

    Returns:
        助手最终回复文本

    使用流程：
        1. 携带完整 messages 发起首次请求
        2. 若模型决定调用工具（finish_reason == "tool_calls"），
           则执行本地工具函数，并将 tool_call 结果作为 role="tool" 消息加入上下文
        3. 再次向模型发起请求（携带包含工具结果的完整上下文）
        4. 循环最多 MAX_TOOL_CALLS 次，直到模型给出文本回复
    """
    if not ARK_API_KEY or ARK_API_KEY == "":
        return (
            "⚠️ 尚未配置火山方舟 API Key。\n"
            "请在 backend/app/base_agent.py 中填写 ARK_API_KEY 和 MODEL_ENDPOINT。\n"
            "获取方式：登录火山方舟控制台 → API Key 管理 → 创建新密钥。"
        )

    if not MODEL_ENDPOINT or MODEL_ENDPOINT == "":
        return (
            "⚠️ 尚未配置模型推理接入点。\n"
            "请在 backend/app/base_agent.py 中填写 MODEL_ENDPOINT。\n"
            "获取方式：登录火山方舟控制台 → 推理接入点 → 创建接入点。"
        )

    # 工作副本：防止修改调用者传入的原始列表（函数内追加 tool messages）
    working_messages = [dict(m) for m in messages]

    for loop_idx in range(MAX_TOOL_CALLS):
        # 构造请求体
        payload = {
            "model": MODEL_ENDPOINT,
            "messages": working_messages,
        }
        if use_tools:
            payload["tools"] = TOOLS
            payload["tool_choice"] = "auto"

        # 发起请求
        resp_json = _ark_http_request(payload)
        choice = resp_json["choices"][0]
        assistant_msg = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "")

        # --- 情况 1：模型直接给出文本回复 ---
        if finish_reason != "tool_calls" or not assistant_msg.get("tool_calls"):
            return assistant_msg.get("content", "") or "(模型未返回有效内容)"

        # --- 情况 2：模型要求调用工具 ---
        # 将 assistant 的 tool_calls 消息加入上下文（必须保留 tool_calls 字段）
        assistant_record = {
            "role": "assistant",
            "content": assistant_msg.get("content") or "",
            "tool_calls": assistant_msg["tool_calls"]
        }
        working_messages.append(assistant_record)

        # 逐个执行工具调用，并将 tool role 消息加入上下文
        tool_calls = assistant_msg["tool_calls"]
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name", "")
            tool_call_id = tc.get("id", "")

            # 解析工具参数
            try:
                args_str = tc.get("function", {}).get("arguments", "{}")
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {}

            # 执行本地工具函数
            try:
                if tool_name in TOOL_REGISTRY:
                    tool_result = TOOL_REGISTRY[tool_name](**args)
                else:
                    tool_result = f"错误：未知工具 '{tool_name}'"
            except Exception as tool_err:
                tool_result = f"工具执行异常: {tool_err}"

            # 将 tool 消息加入上下文（按官方规范）
            working_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": str(tool_result)
            })

        # 循环回到开头：再次让模型基于工具结果生成最终回复

    # 超过最大工具调用循环次数
    return "（助手调用工具次数过多，已终止对话）"


# ============ 视觉多模态：图片理解 ============
def describe_image(
    image_base64: str,
    mime_type: str = "image/jpeg",
    user_prompt: str = "",
) -> str:
    """
    调用火山方舟视觉多模态模型对图片进行识别与描述。

    流程说明：
    1) 优先使用 VISION_ENDPOINT（视觉模型接入点）：按官方多模态格式发送图片 + 提问；
    2) 若未配置 VISION_ENDPOINT：改用普通文本模型，给一段"我收到了一张图片"的友好回复，
       避免把多模态数组 content 发向纯文本模型而导致接口 4xx 报错。

    Args:
        image_base64: 图片的 base64 编码（不包含 data:image/...;base64, 前缀）
        mime_type:    图片 MIME，例如 image/jpeg / image/png
        user_prompt:  用户对图片的提问（可选），留空表示 "描述这张图片"

    Returns:
        AI 助手对图片的描述/回答文本
    """
    if not ARK_API_KEY:
        return "⚠️ 尚未配置火山方舟 API Key，无法进行图片识别。"

    # 用户意图提示
    if not user_prompt or not user_prompt.strip():
        user_prompt = "请详细描述这张图片：图中是什么？图中有哪些物体/人物/场景？它们在做什么？尽量详细，使用中文。"

    vision_endpoint = VISION_ENDPOINT if (VISION_ENDPOINT and VISION_ENDPOINT.strip()) else ""

    # ============ 分支 A：已配置视觉模型接入点 —— 走官方多模态接口 ============
    if vision_endpoint:
        # 构造视觉多模态消息 content（OpenAI / 火山方舟视觉模型标准格式）
        data_url = f"data:{mime_type};base64,{image_base64}"
        messages_for_vision = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url,
                            "detail": "auto",
                        },
                    },
                ],
            }
        ]

        payload = {
            "model": vision_endpoint,
            "messages": messages_for_vision,
            # 视觉模型通常不配合 tools 调用
        }

        try:
            resp_json = _ark_http_request(payload)
        except RuntimeError as err:
            # 如果模型因不支持图片而报错，返回友好提示
            msg = str(err)
            if "不支持" in msg or "not support" in msg.lower() or "image" in msg.lower():
                return (
                    "（当前 VISION_ENDPOINT 不支持图片识别，建议将其替换为视觉多模态模型接入点。"
                    f"原始错误: {msg}）"
                )
            return f"（调用视觉模型失败: {msg}）"
        except Exception as err:
            return f"（系统异常: {err}）"

        try:
            choice = resp_json["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "")
            if content:
                return content
            return "（模型未返回有效描述）"
        except Exception as err:
            return f"（解析视觉模型响应失败: {err}）"

    # ============ 分支 B：未配置视觉模型接入点 —— 走普通文本模型的"降级描述" ============
    # 这里不再把 base64 发到文本模型，而是基于文件名/大小给出一条通用友好回复
    fallback_msg = (
        f"我已收到您上传的图片（{mime_type}）。\n"
        f"当前系统仅配置了普通文本模型（MODEL_ENDPOINT），尚未在 base_agent.py 中配置 VISION_ENDPOINT（视觉多模态接入点），"
        f"因此暂时无法真正「看懂」图片内容。\n"
        f"如果您希望让我识别图片，请联系管理员在火山方舟控制台开通视觉多模态接入点，并把 endpoint 填写到 VISION_ENDPOINT。\n"
        f"您也可以用文字描述这张图片的内容，我会根据描述回答您的问题：\n"
        f"> 用户的问题是：{user_prompt}"
    )
    # 调一次普通文本模型，让它基于上述文本整理出一份友好答复
    try:
        return chat_with_agent(
            [
                {
                    "role": "user",
                    "content": (
                        "下面是一段关于『用户上传了一张图片，但系统暂不支持图片识别』的说明文字。"
                        "请你把它改写为一两句友好、自然的中文回复，并对用户紧跟着的问题给出你能回答的部分。\n\n"
                        + fallback_msg
                    ),
                }
            ],
            use_tools=False,
        )
    except Exception as err:
        # 兜底：直接返回手写说明，保证不会因为模型异常而返回错误字符串
        return (
            "我已收到您的图片，但当前仅配置了普通文本模型（MODEL_ENDPOINT），"
            "没有在 backend/app/base_agent.py 中配置 VISION_ENDPOINT 视觉接入点，暂时无法真正识别图片内容。"
            f"（错误信息: {err}）"
        )


def has_vision_support() -> bool:
    """当前是否已配置视觉多模态支持"""
    return bool(VISION_ENDPOINT and VISION_ENDPOINT.strip())


# ============ 向量/embedding 相关函数 ============
def embeddings_ark_request(texts: list, batch_size: int = 16) -> list:
    """
    调用火山方舟 Embeddings API，为每段文本返回一个 float 向量 list。
    - 支持批量请求（默认每次 16 条，减少网络往返）
    - 若未配置 EMBEDDING_ENDPOINT 或调用失败，返回空列表，让调用方走兜底。
    """
    endpoint = globals().get("EMBEDDING_ENDPOINT") or ""
    if not endpoint.strip():
        return []
    if not ARK_API_KEY:
        return []
    if not texts:
        return []

    url = f"{BASE_URL}/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_API_KEY}",
    }
    ssl_context = ssl.create_default_context()
    results = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        # 火山方舟 embeddings 支持 batch：input 传字符串列表
        payload = {
            "model": endpoint.strip(),
            "input": [t if (t and t.strip()) else " " for t in batch],
        }
        try:
            data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url=url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ssl_context) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                data = body.get("data") or []
                if not data or not isinstance(data, list):
                    return []
                # data 是按 input 顺序返回的 [{index, embedding}, ...]
                # 按 index 排序保证顺序一致
                data_sorted = sorted(data, key=lambda x: int(x.get("index", 0)))
                batch_vecs = []
                for item in data_sorted:
                    emb = item.get("embedding")
                    if isinstance(emb, list) and emb:
                        batch_vecs.append([float(x) for x in emb])
                    else:
                        return []
                if len(batch_vecs) != len(batch):
                    return []
                results.extend(batch_vecs)
        except Exception:
            return []

    return results if len(results) == len(texts) else []


def _chinese_tokenize(text: str) -> list:
    """分词：去除空白与常见符号，按字符/数字/英文单词切分。"""
    if not text:
        return []
    # 去除各类标点/符号（保留中文/英文/数字）
    cleaned = re.sub(
        r"[\s\-\_\.\,\?\!。，？！:：;；\"'、·~\/\\()（）\[\]【】<>《》…—]",
        "",
        text,
    )
    # 按中文字符/数字/英文单词拆分成独立 token
    tokens = re.findall(r"[\u4e00-\u9fa5]|[0-9]+|[A-Za-z]+", cleaned)
    return tokens


def _build_ngrams(tokens: list, n: int = 2) -> list:
    """基于 tokens 生成 1..n-gram 列表，提升局部匹配能力。"""
    ngrams = list(tokens)  # 1-gram
    for k in range(2, n + 1):
        for i in range(len(tokens) - k + 1):
            ngrams.append("".join(tokens[i : i + k]))
    return ngrams


def _hash_to_index(s: str, dim: int, seed: int = 0) -> int:
    """对字符串生成稳定的整型哈希，基于 md5。seed 用于多哈希变化。"""
    raw = (str(seed) + "|" + s).encode("utf-8")
    h = int(hashlib.md5(raw).hexdigest(), 16)
    return h % dim


def _sign_of(s: str, seed: int = 0) -> float:
    """生成稳定的 +1/-1 符号，用于让相似内容在相同维度累加同向。"""
    raw = (str(seed) + "_sign_" + s).encode("utf-8")
    h = int(hashlib.md5(raw).hexdigest(), 16)
    return 1.0 if (h % 2 == 0) else -1.0


def _vector_from_tokens(tokens: list, dim: int = 2048) -> list:
    """
    将 tokens 转成固定维度的 float 向量，基于 1..3-gram + 多种 seed 哈希累加。
    改进：
      - 采用 FNV-1a 哈希（比 md5 更轻量），并做 sign-consistent 累加
      - 对长 token/数字/中文单独加权，使局部关键词在余弦相似度中更容易命中
      - L2 归一化保证可直接用于余弦相似度比较
    """
    vec = [0.0] * dim
    if not tokens:
        vec[0] = 0.1
        return [v / (0.1 ** 2) ** 0.5 for v in vec]  # 简单归一

    def _fnv1a(s: str) -> int:
        h = 0x811c9dc5
        for ch in s.encode("utf-8"):
            h = (h ^ ch) & 0xFFFFFFFF
            h = (h * 0x01000193) & 0xFFFFFFFF
        return h

    def _sign(s: str) -> float:
        return 1.0 if (_fnv1a("s:" + s) & 1) == 0 else -1.0

    def _idx(s: str, seed: int) -> int:
        val = _fnv1a(f"{seed}|{s}")
        return val % dim

    ngrams = _build_ngrams(tokens, n=3)
    for gram in ngrams:
        if not gram:
            continue
        # 对不同长度 token 给予不同权重，短中文 key 权重高
        base_weight = 1.0
        if re.match(r"^[\u4e00-\u9fa5]{2,4}$", gram):
            base_weight = 2.0
        elif re.match(r"^[0-9]{3,}$", gram):
            base_weight = 1.8
        elif re.match(r"^[A-Za-z]{3,}$", gram):
            base_weight = 1.4
        for seed in range(3):
            i = _idx(gram, seed)
            vec[i] += _sign(gram) * base_weight

    # L2 归一化
    norm_sq = sum(v * v for v in vec)
    norm = norm_sq ** 0.5 if norm_sq > 0 else 1.0
    return [v / norm for v in vec]


def keyword_overlap_score(query: str, content: str) -> float:
    """
    基于关键词（token/ngram）交集比例的 0-1 混合打分，
    并对「人名/地名/数字」等关键实体给予额外加分，
    用来和余弦相似度加权混合，提高中文匹配召回率。

    改进：
      - 对 2-4 位中文词给予更高的 ngram 权重
      - 对数字序列单独给予高分（电话号码、价格、年份等精确信息）
      - 加入 IDF 风格惩罚：过于短的 query 惩罚低
    """
    if not query or not content:
        return 0.0

    q_tokens = _chinese_tokenize(query)
    c_tokens = _chinese_tokenize(content)
    if not q_tokens:
        return 0.0

    # 1-3 gram 构造
    q_ngrams = set(_build_ngrams(q_tokens, n=3))
    c_ngrams = set(_build_ngrams(c_tokens, n=3))

    if not q_ngrams or not c_ngrams:
        return 0.0

    common = q_ngrams & c_ngrams
    # 基于 query 的覆盖率（更贴近"有多少 query 的内容出现在 fragment 中"）
    coverage = (len(common) / max(1, len(q_ngrams))) if q_ngrams else 0.0
    # 同时兼顾 intersection/union 作为相似度
    union = len(q_ngrams | c_ngrams)
    jaccard = len(common) / max(1, union)

    base = 0.5 * coverage + 0.5 * jaccard

    # --- 实体增强（对精确信息给予高贡献） ---
    q_ngrams_for_entity = _build_ngrams(q_tokens, n=4)
    entity_bonus = 0.0
    seen = set()
    for tok in q_ngrams_for_entity:
        if not tok or len(tok) > 10:
            continue
        # 2~4 位中文字（人名/地名/公司名/关键字）
        if re.match(r"^[\u4e00-\u9fa5]{2,4}$", tok):
            if tok in seen:
                continue
            seen.add(tok)
            if tok in content:
                entity_bonus += 0.22
        # 4 位以上连续数字（电话/邮编/编号/年份）
        elif re.match(r"^[0-9]{4,}$", tok):
            if tok in seen:
                continue
            seen.add(tok)
            if tok in content:
                entity_bonus += 0.25
        # 3~8 位英文/拼音（名称/缩写）
        elif re.match(r"^[A-Za-z]{3,8}$", tok):
            if tok in seen:
                continue
            seen.add(tok)
            if tok.lower() in content.lower():
                entity_bonus += 0.15

    return max(0.0, min(1.0, base + entity_bonus))


def hybrid_similarity(query_vec: list, content_vec: list, query_text: str, content_text: str) -> float:
    """
    混合评分：余弦相似度 0.3 + 关键词重叠(含实体增强) 0.7，归一到 [0,1]。
    关键词权重更高，使中文 PDF/文档的「精确命中」有更高区分度。
    对「完全没有重叠」的片段，即使向量余弦接近也会得低分，避免噪声干扰。
    """
    cos = max(0.0, float(cosine_similarity(query_vec, content_vec)))
    kw = float(keyword_overlap_score(query_text, content_text))
    # 若关键词一点都没重叠，余弦的贡献也被削弱（减少噪声）
    if kw <= 0.001:
        score = 0.2 * cos + 0.8 * kw
    else:
        score = 0.3 * cos + 0.7 * kw
    return max(0.0, min(1.0, score))


def get_text_embeddings(texts: list) -> list:
    """
    统一入口：为每段文本生成向量。
    优先调用火山方舟 embeddings API，失败/未配置则走本地哈希向量。
    严格保证返回 list 长度 = len(texts)，不会出现长度为 0 的情况。
    """
    # 先试火山方舟 embeddings（如果配置了）
    try:
        ark_vecs = embeddings_ark_request(texts)
        if ark_vecs and len(ark_vecs) == len(texts):
            return ark_vecs
    except Exception:
        pass

    # 失败则使用本地哈希向量（稳定、离线可用）
    dim = globals().get("EMBEDDING_DIM") or 2048
    if not isinstance(dim, int) or dim < 64:
        dim = 2048
    result = []
    for t in texts:
        tokens = _chinese_tokenize(t or "")
        result.append(_vector_from_tokens(tokens, dim=dim))
    # 防御：长度不一致时补到 len(texts)
    while len(result) < len(texts):
        result.append(_vector_from_tokens([], dim=dim))
    return result


def get_single_embedding(text: str) -> list:
    """单条文本的向量（对 get_text_embeddings 的便捷封装）"""
    result = get_text_embeddings([text or ""])
    return result[0] if result else _vector_from_tokens([], dim=(globals().get("EMBEDDING_DIM") or 2048))


def cosine_similarity(a: list, b: list) -> float:
    """计算两个向量的余弦相似度。长度不一致或全零向量时返回 0。"""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = 0.0
    norm_a_sq = 0.0
    norm_b_sq = 0.0
    for i in range(n):
        av = float(a[i]) if a[i] is not None else 0.0
        bv = float(b[i]) if b[i] is not None else 0.0
        dot += av * bv
        norm_a_sq += av * av
        norm_b_sq += bv * bv
    denom = (norm_a_sq ** 0.5) * (norm_b_sq ** 0.5)
    if denom <= 0:
        return 0.0
    return float(dot / denom)
