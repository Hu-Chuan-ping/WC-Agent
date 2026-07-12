from __future__ import annotations

import aiomysql

from app.infra.db.mysql_client import get_pool

# 用户↔问过的比赛。predictions 是全局共享的，这张表只记“谁问过哪一场”，
# “我的预测记录”由它 join matches + match_predictions 得到。

_DDL = """
CREATE TABLE IF NOT EXISTS user_match (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id    VARCHAR(64) NOT NULL,
    match_id   VARCHAR(32) NOT NULL,
    session_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_match (user_id, match_id)
)
"""


async def ensure_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_DDL)


async def link(user_id: str, match_id: str, session_id: str | None) -> None:
    """记录该用户问过这场（同一用户同一场只保留一条，更新来源会话）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO user_match (user_id, match_id, session_id) VALUES (%s,%s,%s) AS new "
                "ON DUPLICATE KEY UPDATE session_id=new.session_id",
                (user_id, match_id, session_id),
            )


async def list_by_user(user_id: str) -> list[dict]:
    """某用户问过的所有比赛（含权威预测 + 赛果），最新在前。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT m.match_id, m.home_cn, m.away_cn, m.kickoff_time, m.status,
                       m.home_goals, m.away_goals, m.pen_home, m.pen_away, m.outcome,
                       p.p_home, p.p_draw, p.p_away, p.top_score, p.score_dist,
                       p.brier_agent, p.rps_agent, p.brier_odds, p.rps_odds,
                       um.session_id
                FROM user_match um
                JOIN matches m           ON um.match_id = m.match_id
                LEFT JOIN match_predictions p ON um.match_id = p.match_id
                WHERE um.user_id = %s
                ORDER BY m.kickoff_time DESC
                """,
                (user_id,),
            )
            return list(await cur.fetchall())
