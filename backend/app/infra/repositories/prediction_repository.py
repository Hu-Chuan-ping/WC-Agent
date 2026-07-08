from __future__ import annotations

import aiomysql

from app.infra.db.mysql_client import get_pool

# 预测记录仓库（MySQL predictions 表）。评估数据要长期累积，故用关系库而非 Redis。
# 本文件是唯一直接操作 predictions 表 SQL 的地方；领域层(core)只调这里的方法。

_DDL = """
CREATE TABLE IF NOT EXISTS predictions (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       VARCHAR(64),
    session_id    VARCHAR(64),
    home_team     VARCHAR(64),   -- 英文名（用于赛果匹配）
    away_team     VARCHAR(64),
    home_cn       VARCHAR(64),
    away_cn       VARCHAR(64),
    kickoff_time  VARCHAR(40),
    agent_p_home  DOUBLE, agent_p_draw DOUBLE, agent_p_away DOUBLE,
    agent_score   VARCHAR(16),
    odds_p_home   DOUBLE, odds_p_draw DOUBLE, odds_p_away DOUBLE,
    extra_json    TEXT,
    actual_home   INT, actual_away INT, actual_outcome VARCHAR(8),
    brier_agent   DOUBLE, brier_odds DOUBLE, logloss_agent DOUBLE,
    status        VARCHAR(16) DEFAULT 'pending',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at   TIMESTAMP NULL
)
"""


async def ensure_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_DDL)


async def insert_prediction(rec: dict) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 去重：同一对阵已有 pending 预测先删掉，一场只保留最新一条待评估
            await cur.execute(
                "DELETE FROM predictions WHERE status='pending' AND "
                "((home_team=%s AND away_team=%s) OR (home_team=%s AND away_team=%s))",
                (rec.get("home_team"), rec.get("away_team"),
                 rec.get("away_team"), rec.get("home_team")),
            )
            await cur.execute(
                """
                INSERT INTO predictions
                  (user_id, session_id, home_team, away_team, home_cn, away_cn,
                   kickoff_time, agent_p_home, agent_p_draw, agent_p_away, agent_score,
                   odds_p_home, odds_p_draw, odds_p_away, extra_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    rec.get("user_id"), rec.get("session_id"),
                    rec.get("home_team"), rec.get("away_team"),
                    rec.get("home_cn"), rec.get("away_cn"), rec.get("kickoff_time"),
                    rec.get("agent_p_home"), rec.get("agent_p_draw"), rec.get("agent_p_away"),
                    rec.get("agent_score"),
                    rec.get("odds_p_home"), rec.get("odds_p_draw"), rec.get("odds_p_away"),
                    rec.get("extra_json"),
                ),
            )
            return cur.lastrowid


async def list_pending() -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM predictions WHERE status = 'pending'")
            return list(await cur.fetchall())


async def mark_resolved(
    pred_id: int, actual_home: int, actual_away: int, outcome: str,
    brier_agent: float, brier_odds: float | None, logloss_agent: float,
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE predictions SET
                  actual_home=%s, actual_away=%s, actual_outcome=%s,
                  brier_agent=%s, brier_odds=%s, logloss_agent=%s,
                  status='resolved', resolved_at=CURRENT_TIMESTAMP
                WHERE id=%s
                """,
                (actual_home, actual_away, outcome, brier_agent, brier_odds,
                 logloss_agent, pred_id),
            )


async def list_resolved() -> list[dict]:
    """已结算预测的每场明细（最新在前）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT home_cn, away_cn, agent_score, actual_home, actual_away, "
                "actual_outcome, agent_p_home, agent_p_draw, agent_p_away, "
                "brier_agent, brier_odds FROM predictions "
                "WHERE status='resolved' ORDER BY resolved_at DESC"
            )
            return list(await cur.fetchall())


async def list_by_user(user_id: str) -> list[dict]:
    """某用户的全部预测（最新在前），供“已预测比赛”页展示与汇总。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT id, home_cn, away_cn, kickoff_time, agent_score,
                       agent_p_home, agent_p_draw, agent_p_away,
                       actual_home, actual_away, actual_outcome,
                       brier_agent, brier_odds, status, session_id, created_at
                FROM predictions WHERE user_id = %s ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return list(await cur.fetchall())


async def aggregate() -> dict:
    """已结算预测的汇总：你 vs 赔率的平均 Brier、log-loss、击败赔率次数。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT COUNT(*) AS total FROM predictions")
            total = (await cur.fetchone())["total"]
            await cur.execute(
                """
                SELECT
                  COUNT(*)                              AS resolved,
                  AVG(brier_agent)                      AS avg_brier_agent,
                  AVG(brier_odds)                       AS avg_brier_odds,
                  AVG(logloss_agent)                    AS avg_logloss_agent,
                  SUM(brier_odds IS NOT NULL AND brier_agent < brier_odds) AS agent_beats_odds
                FROM predictions WHERE status='resolved'
                """
            )
            row = await cur.fetchone()
    return {"total": total, **row}
