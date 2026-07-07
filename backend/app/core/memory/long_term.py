from __future__ import annotations

from app.db.mysql_client import get_pool

# 长期用户记忆：MySQL user_profile 表，按 user_id 存一段画像文本。


async def ensure_tables() -> None:
    """建好长期记忆表（应用启动时调用一次）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
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


async def get_profile(user_id: str) -> str:
    """取用户画像；无则返回空串。"""
    if not user_id:
        return ""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT profile FROM user_profile WHERE user_id = %s", (user_id,)
            )
            row = await cur.fetchone()
    return row[0] if row and row[0] else ""


async def upsert_profile(user_id: str, profile: str) -> None:
    """写入/更新用户画像。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO user_profile (user_id, profile) VALUES (%s, %s) AS new "
                "ON DUPLICATE KEY UPDATE profile = new.profile",
                (user_id, profile),
            )
