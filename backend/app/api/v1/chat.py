import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.models.schemas.chat import ChatRequest, ChatResponse
from app.models.schemas.conversation import (
    ContextStatsResponse,
    CreateSessionResponse,
    MessageItem,
    OkResponse,
    RenameSessionRequest,
    SessionIdRequest,
    SessionItem,
)
from app.services import conversation_service
from app.services.dispatch_service import DispatchService, get_dispatch_service

# 对话相关接口：会话管理 + 发消息。全部需登录，user_id 从 JWT 解出。
router = APIRouter()


# ── 会话管理 ────────────────────────────────────────────────

@router.post("/sessions/create", response_model=CreateSessionResponse)
async def create_session(user_id: str = Depends(get_current_user)):
    """新建一个空对话。"""
    return await conversation_service.create_session(user_id)


@router.post("/sessions/list", response_model=list[SessionItem])
async def list_sessions(user_id: str = Depends(get_current_user)):
    """列出我的所有对话（最近活跃在前）。"""
    return await conversation_service.list_sessions(user_id)


@router.post("/sessions/messages", response_model=list[MessageItem])
async def session_messages(
    req: SessionIdRequest, user_id: str = Depends(get_current_user)
):
    """查看某个对话的完整消息。"""
    return await conversation_service.get_messages(user_id, req.session_id)


@router.post("/sessions/rename", response_model=OkResponse)
async def rename_session(
    req: RenameSessionRequest, user_id: str = Depends(get_current_user)
):
    """重命名对话。"""
    await conversation_service.rename_session(user_id, req.session_id, req.title)
    return OkResponse()


@router.post("/sessions/delete", response_model=OkResponse)
async def delete_session(
    req: SessionIdRequest, user_id: str = Depends(get_current_user)
):
    """删除对话（连带清空消息与 Redis 热窗口）。"""
    await conversation_service.delete_session(user_id, req.session_id)
    return OkResponse()


@router.post("/sessions/context", response_model=ContextStatsResponse)
async def session_context(
    req: SessionIdRequest, user_id: str = Depends(get_current_user)
):
    """当前会话的上下文占用（token 圆环用）。"""
    return await conversation_service.context_stats(user_id, req.session_id)


# ── 发消息 ──────────────────────────────────────────────────

@router.post("/dispatch", response_model=ChatResponse)
async def dispatch(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
    service: DispatchService = Depends(get_dispatch_service),
) -> ChatResponse:
    """非流式入口：一次性返回完整回答。"""
    result, session_id = await service.dispatch(
        request.question, request.session_id, user_id
    )
    return ChatResponse(result=result, session_id=session_id)


@router.post("/dispatch/stream")
async def dispatch_stream(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
    service: DispatchService = Depends(get_dispatch_service),
) -> StreamingResponse:
    """流式入口（SSE）：逐段推送 status / token / done 事件。"""

    async def event_gen():
        async for ev in service.dispatch_stream(
            request.question, request.session_id, user_id
        ):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
