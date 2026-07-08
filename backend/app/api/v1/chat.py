import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.models.schemas.chat import ChatRequest, ChatResponse
from app.services.dispatch_service import DispatchService, get_dispatch_service

# 对话相关接口（后续会话列表 / 历史查询也加在这里）。
router = APIRouter()


@router.post("/dispatch", response_model=ChatResponse)
async def dispatch(
    request: ChatRequest,
    service: DispatchService = Depends(get_dispatch_service),
) -> ChatResponse:
    """非流式入口：一次性返回完整回答。"""
    result, session_id = await service.dispatch(
        request.question, request.session_id, request.user_id
    )
    return ChatResponse(result=result, session_id=session_id)


@router.post("/dispatch/stream")
async def dispatch_stream(
    request: ChatRequest,
    service: DispatchService = Depends(get_dispatch_service),
) -> StreamingResponse:
    """流式入口（SSE）：逐段推送 status / token / done 事件。"""

    async def event_gen():
        async for ev in service.dispatch_stream(
            request.question, request.session_id, request.user_id
        ):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
