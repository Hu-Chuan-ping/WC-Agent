from __future__ import annotations

import json

import aiomysql

from app.infra.db.mysql_client import get_pool

# 会话与消息的持久化仓库（MySQL）。
#  sessions：一个用户开的多个对话（列表用）。
#  messages：单个对话里的每条消息（查看完整历史用）。
# Redis 里的 session:{id} 仍是 agent 的“热窗口”（拼 LLM 上下文），与这里各司其职。

_SESSIONS_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id         VARCHAR(64) PRIMARY KEY,
    user_id    VARCHAR(64) NOT NULL,
    title      VARCHAR(255) DEFAULT '新对话',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
)
"""

_MESSAGES_DDL = """
CREATE TABLE IF NOT EXISTS messages (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    role       VARCHAR(16) NOT NULL,
    content    MEDIUMTEXT,
    meta       JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id)
)
"""


async def ensure_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SESSIONS_DDL)
            await cur.execute(_MESSAGES_DDL)
            await _ensure_meta_column(cur)


async def _ensure_meta_column(cur) -> None:
    """给老库补 messages.meta 列（存专家会诊等消息级结构化附件）。幂等。"""
    await cur.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'messages' "
        "AND COLUMN_NAME = 'meta'"
    )
    (exists,) = await cur.fetchone()
    if not exists:
        await cur.execute("ALTER TABLE messages ADD COLUMN meta JSON NULL AFTER content")


# ── sessions ────────────────────────────────────────────────

async def create_session(session_id: str, user_id: str, title: str = "新对话") -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO sessions (id, user_id, title) VALUES (%s, %s, %s)",
                (session_id, user_id, title),
            )


async def get_session(session_id: str) -> dict | None:
    """取会话一行（含 user_id，供归属校验）。不存在返回 None。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, user_id, title FROM sessions WHERE id = %s", (session_id,)
            )
            return await cur.fetchone()


async def list_sessions(user_id: str) -> list[dict]:
    """列出某用户的会话，附带最后一条消息预览，按最近活跃倒序。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT s.id AS session_id, s.title, s.updated_at,
                  (SELECT m.content FROM messages m
                     WHERE m.session_id = s.id ORDER BY m.id DESC LIMIT 1) AS last_message
                FROM sessions s
                WHERE s.user_id = %s
                ORDER BY s.updated_at DESC
                """,
                (user_id,),
            )
            return list(await cur.fetchall())


async def rename_session(session_id: str, title: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE sessions SET title = %s WHERE id = %s", (title, session_id)
            )


async def touch_session(session_id: str) -> None:
    """刷新最近活跃时间（用于列表排序）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (session_id,),
            )


async def delete_session(session_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))


# ── messages ────────────────────────────────────────────────

async def add_message(
    session_id: str, role: str, content: str, meta: dict | None = None
) -> None:
    meta_json = json.dumps(meta, ensure_ascii=False) if meta is not None else None
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO messages (session_id, role, content, meta) "
                "VALUES (%s, %s, %s, %s)",
                (session_id, role, content, meta_json),
            )


async def list_messages(session_id: str) -> list[dict]:
    """按时间顺序返回某会话的全部消息（meta 反序列化为 dict）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT role, content, meta, created_at FROM messages "
                "WHERE session_id = %s ORDER BY id",
                (session_id,),
            )
            rows = list(await cur.fetchall())
    for r in rows:
        # JSON 列可能被驱动返回为 str，也可能已是 dict；统一成 dict|None
        m = r.get("meta")
        if isinstance(m, str):
            try:
                r["meta"] = json.loads(m)
            except json.JSONDecodeError:
                r["meta"] = None
    return rows


async def delete_messages(session_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
