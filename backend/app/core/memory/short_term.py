from __future__ import annotations

import json

from app.config.settings import settings
from app.db.redis_client import get_redis

# 短期会话记忆：Redis LIST，key = session:{session_id}，
# 每个元素是一条消息的 JSON 串（append-only + 滑动窗口 + TTL）。


def _key(session_id: str) -> str:
    return f"session:{session_id}"


async def load_history(session_id: str) -> list[dict]:
    """按时间顺序返回该会话的消息列表：[{"role","content"}, ...]。"""
    raw = await get_redis().lrange(_key(session_id), 0, -1)
    return [json.loads(x) for x in raw]


async def append_turn(session_id: str, user_msg: str, assistant_msg: str) -> None:
    """追加一轮（用户+助手）；滑动窗口只留最近 N 条；刷新过期时间。"""
    r = get_redis()
    key = _key(session_id)
    await r.rpush(
        key,
        json.dumps({"role": "user", "content": user_msg}, ensure_ascii=False),
        json.dumps({"role": "assistant", "content": assistant_msg}, ensure_ascii=False),
    )
    await r.ltrim(key, -settings.session_max_messages, -1)  # 砍掉过旧的，保留最近 N 条
    await r.expire(key, settings.session_ttl_seconds)       # 每次访问续期 → 滑动过期


async def clear(session_id: str) -> None:
    await get_redis().delete(_key(session_id))
