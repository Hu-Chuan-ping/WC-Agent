from __future__ import annotations

from app.config.settings import settings
from app.infra.repositories import session_repository

# 短期会话记忆（领域服务）：定义“一轮=用户+助手两条消息”、滑动窗口与 TTL 等策略，
# 具体的 Redis 存取交给 session_repository。


async def load_history(session_id: str) -> list[dict]:
    """按时间顺序返回该会话的消息列表：[{"role","content"}, ...]。"""
    return await session_repository.load(session_id)


async def append_turn(session_id: str, user_msg: str, assistant_msg: str) -> None:
    """追加一轮（用户+助手）；按策略裁剪窗口并续期。"""
    messages = [
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": assistant_msg},
    ]
    await session_repository.append(
        session_id,
        messages,
        max_messages=settings.session_max_messages,
        ttl_seconds=settings.session_ttl_seconds,
    )


async def clear(session_id: str) -> None:
    await session_repository.delete(session_id)
