from __future__ import annotations

from app.infra.db.mysql_client import get_pool

# 用户长期画像仓库（MySQL user_profile 表）。
# 只负责存取，不含业务判断——领域层 core/memory/long_term 决定“存什么/何时存”。

_DDL = """
CREATE TABLE IF NOT EXISTS user_profile (
    user_id    VARCHAR(64) PRIMARY KEY,
    profile    TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 ON UPDATE CURRENT_TIMESTAMP
)
"""


async def ensure_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_DDL)


async def get(user_id: str) -> str:
    """取用户画像文本；无则返回空串。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT profile FROM user_profile WHERE user_id = %s", (user_id,)
            )
            row = await cur.fetchone()
    return row[0] if row and row[0] else ""


async def upsert(user_id: str, profile: str) -> None:
    """写入/更新用户画像。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO user_profile (user_id, profile) VALUES (%s, %s) AS new "
                "ON DUPLICATE KEY UPDATE profile = new.profile",
                (user_id, profile),
            )
