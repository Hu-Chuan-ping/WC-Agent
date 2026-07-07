from __future__ import annotations

import aiomysql

from app.config.settings import settings

# 全局 MySQL 连接池（懒加载单例）。
# Web 应用每个请求借一条连接、用完归还，池化避免频繁建连的开销。
_pool: aiomysql.Pool | None = None


async def get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            db=settings.mysql_db,
            autocommit=True,   # 简单读写自动提交，省得手动 commit
            minsize=1,
            maxsize=5,
            charset="utf8mb4",  # 支持中文/emoji
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
