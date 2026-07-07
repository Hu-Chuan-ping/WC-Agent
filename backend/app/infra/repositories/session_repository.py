from __future__ import annotations

import json

from app.infra.db.redis_client import get_redis

# 会话消息仓库（Redis LIST，key = session:{session_id}）。
# 只负责存取原始消息；“留多少条 / 多久过期”等策略由 core/memory/short_term 传入。


def _key(session_id: str) -> str:
    return f"session:{session_id}"


async def load(session_id: str) -> list[dict]:
    """按时间顺序返回该会话的消息列表：[{"role","content"}, ...]。"""
    raw = await get_redis().lrange(_key(session_id), 0, -1)
    return [json.loads(x) for x in raw]


async def append(
    session_id: str, messages: list[dict], max_messages: int, ttl_seconds: int
) -> None:
    """追加若干条消息；滑动窗口只留最近 max_messages 条；刷新过期时间。"""
    r = get_redis()
    key = _key(session_id)
    await r.rpush(key, *[json.dumps(m, ensure_ascii=False) for m in messages])
    await r.ltrim(key, -max_messages, -1)   # 砍掉过旧的，保留最近 N 条
    await r.expire(key, ttl_seconds)         # 每次访问续期 → 滑动过期


async def delete(session_id: str) -> None:
    await get_redis().delete(_key(session_id))
