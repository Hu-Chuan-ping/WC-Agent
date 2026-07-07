from __future__ import annotations

import redis.asyncio as aioredis

from app.config.settings import settings

# 全局共享的异步 Redis 客户端（懒加载单例）。
# redis-py 内部自带连接池，一个客户端对象即可全应用复用。
_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,  # 存取都用 str，而非 bytes
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
