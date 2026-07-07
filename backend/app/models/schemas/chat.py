from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """前端发往后端的请求体。"""

    question: str
    session_id: str | None = None  # 会话窗口标识；不传则后端新开一个
    user_id: str | None = None     # 用户标识；用于跨会话的长期记忆（画像）


class ChatResponse(BaseModel):
    """后端返回给前端的响应体。"""

    result: str
    session_id: str | None = None
