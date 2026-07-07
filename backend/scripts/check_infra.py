"""连通性自检：验证 Python 能连上 Docker 里的 Redis 和 MySQL。

用法（在 backend 目录、激活 venv 下）：
    python scripts/check_infra.py
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.mysql_client import close_pool, get_pool  # noqa: E402
from app.db.redis_client import close_redis, get_redis  # noqa: E402


async def check_redis() -> None:
    r = get_redis()
    await r.set("wc:ping", "hello-redis", ex=60)   # 存一个键，60秒后过期
    val = await r.get("wc:ping")                    # 读回来
    print(f"[Redis] {'✅ OK' if val == 'hello-redis' else '❌ FAIL'} → 读到: {val}")
    await close_redis()


async def check_mysql() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:              # 从池借一条连接
        async with conn.cursor() as cur:
            # 顺便建好长期记忆要用的表
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profile (
                    user_id    VARCHAR(64) PRIMARY KEY,
                    profile    TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP
                )
                """
            )
            # 写一条测试数据（存在则更新）。MySQL 8.0.20+ 推荐用别名而非 VALUES()
            await cur.execute(
                "INSERT INTO user_profile (user_id, profile) VALUES (%s, %s) AS new "
                "ON DUPLICATE KEY UPDATE profile = new.profile",
                ("test-user", "英格兰球迷，偏好进攻型球队"),
            )
            # 读回来
            await cur.execute(
                "SELECT user_id, profile FROM user_profile WHERE user_id = %s",
                ("test-user",),
            )
            row = await cur.fetchone()
    print(f"[MySQL] {'✅ OK' if row else '❌ FAIL'} → 读到: {row}")
    await close_pool()


async def main() -> None:
    await check_redis()
    await check_mysql()
    print("连通性自检完成。")


if __name__ == "__main__":
    asyncio.run(main())
