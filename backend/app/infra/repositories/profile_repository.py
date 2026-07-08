from __future__ import annotations

import aiomysql

from app.infra.db.mysql_client import get_pool

# 用户长期画像仓库（MySQL user_profile 表）。
#  profile：喂给 agent 的记忆文本（由资料字段合成）。
#  其余为结构化资料字段，供“用户信息”页展示/编辑。

_DDL = """
CREATE TABLE IF NOT EXISTS user_profile (
    user_id          VARCHAR(64) PRIMARY KEY,
    profile          TEXT,
    nickname         VARCHAR(64),
    avatar_url       VARCHAR(255),
    signature        VARCHAR(255),
    favorite_teams   VARCHAR(255),
    favorite_players VARCHAR(255),
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
"""

# 存量表（早期只有 user_id/profile）需要补的结构化列
_MIGRATE_COLUMNS = {
    "nickname": "VARCHAR(64)",
    "avatar_url": "VARCHAR(255)",
    "signature": "VARCHAR(255)",
    "favorite_teams": "VARCHAR(255)",
    "favorite_players": "VARCHAR(255)",
}


async def ensure_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_DDL)
            # 对已存在的旧表补列（MySQL 不支持 ADD COLUMN IF NOT EXISTS，
            # 故先查 information_schema 再补缺失的列）。
            await cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 'user_profile'"
            )
            existing = {r[0] for r in await cur.fetchall()}
            for col, col_type in _MIGRATE_COLUMNS.items():
                if col not in existing:
                    await cur.execute(f"ALTER TABLE user_profile ADD COLUMN {col} {col_type}")


# ── agent 记忆文本（保持原接口，供 long_term 使用）──────────────

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
    """只写 agent 记忆文本列（供 long_term 的“短→长”记忆抽取用）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO user_profile (user_id, profile) VALUES (%s, %s) AS new "
                "ON DUPLICATE KEY UPDATE profile = new.profile",
                (user_id, profile),
            )


# ── 结构化资料（供用户信息页）────────────────────────────────

async def get_fields(user_id: str) -> dict | None:
    """取用户资料的结构化字段；无记录返回 None。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT nickname, avatar_url, signature, favorite_teams, favorite_players "
                "FROM user_profile WHERE user_id = %s",
                (user_id,),
            )
            return await cur.fetchone()


async def upsert_fields(
    user_id: str,
    profile: str,
    nickname: str | None,
    signature: str | None,
    favorite_teams: str | None,
    favorite_players: str | None,
) -> None:
    """写入/更新资料字段 + 合成好的 agent 记忆文本。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO user_profile
                  (user_id, profile, nickname, signature, favorite_teams, favorite_players)
                VALUES (%s, %s, %s, %s, %s, %s) AS new
                ON DUPLICATE KEY UPDATE
                  profile = new.profile, nickname = new.nickname,
                  signature = new.signature, favorite_teams = new.favorite_teams,
                  favorite_players = new.favorite_players
                """,
                (user_id, profile, nickname, signature, favorite_teams, favorite_players),
            )
