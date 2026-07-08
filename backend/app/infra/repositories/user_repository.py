from __future__ import annotations

import aiomysql

from app.infra.db.mysql_client import get_pool

# 用户账号仓库（MySQL users 表）。只放“登录凭证”，头像/昵称等资料在 user_profile。
# id 用 uuid 字符串，与 predictions/user_profile 的 user_id(VARCHAR64) 对齐。

_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id            VARCHAR(64) PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


async def ensure_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_DDL)


async def get_by_username(username: str) -> dict | None:
    """按用户名查用户；不存在返回 None。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, username, password_hash, created_at "
                "FROM users WHERE username = %s",
                (username,),
            )
            return await cur.fetchone()


async def create(user_id: str, username: str, password_hash: str) -> None:
    """插入一条新用户。用户名重复会触发 UNIQUE 约束报错，由上层先查重规避。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (%s, %s, %s)",
                (user_id, username, password_hash),
            )
