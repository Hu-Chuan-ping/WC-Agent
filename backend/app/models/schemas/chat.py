from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """前端发往后端的请求体。user_id 不再由前端传，改从 JWT 解出。"""

    question: str
    session_id: str | None = None  # 会话窗口标识；不传则后端新开一个


class ChatResponse(BaseModel):
    """后端返回给前端的响应体。"""

    result: str
    session_id: str | None = None
