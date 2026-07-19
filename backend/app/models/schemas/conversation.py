from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# 会话相关接口的请求/响应模型。全部走 POST，id 放 body。


class SessionIdRequest(BaseModel):
    session_id: str


class RenameSessionRequest(BaseModel):
    session_id: str
    title: str


class CreateSessionResponse(BaseModel):
    session_id: str
    title: str


class SessionItem(BaseModel):
    session_id: str
    title: str
    last_message: str | None = None
    updated_at: datetime


class MessageItem(BaseModel):
    role: str
    content: str
    meta: dict | None = None   # 结构化附件（如专家会诊 {"experts":[...]}）
    created_at: datetime


class OkResponse(BaseModel):
    ok: bool = True
