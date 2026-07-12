from __future__ import annotations

import aiomysql

from app.infra.db.mysql_client import get_pool

# 比赛仓库：两张 1:1（同 match_id）表。
#  matches           客观赛果（公共，全用户共享）。
#  match_predictions 每场一条 agent 权威预测 + 评分（评价的唯一对象）。

_MATCHES_DDL = """
CREATE TABLE IF NOT EXISTS matches (
    match_id    VARCHAR(32) PRIMARY KEY,
    competition VARCHAR(16) DEFAULT 'WC',
    home_team   VARCHAR(64),
    away_team   VARCHAR(64),
    home_cn     VARCHAR(64),
    away_cn     VARCHAR(64),
    kickoff_time    VARCHAR(40),
    status      VARCHAR(16),
    duration    VARCHAR(20),
    home_goals  INT, away_goals INT,     -- 常规结果（点球赛=regularTime）
    pen_home    INT, pen_away  INT,       -- 点球比分（无则 NULL）
    outcome     VARCHAR(8),               -- home/draw/away（点球赛=draw）
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
"""

_PREDICTIONS_DDL = """
CREATE TABLE IF NOT EXISTS match_predictions (
    match_id    VARCHAR(32) PRIMARY KEY,
    p_home DOUBLE, p_draw DOUBLE, p_away DOUBLE,
    score_dist  TEXT,                     -- JSON: [{"score":"1-0","p":0.22},...]
    top_score   VARCHAR(16),
    odds_p_home DOUBLE, odds_p_draw DOUBLE, odds_p_away DOUBLE,
    brier_agent DOUBLE, rps_agent DOUBLE,
    brier_odds  DOUBLE, rps_odds  DOUBLE,
    extra_json  TEXT,                     -- total_goals / btts 等
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
"""


async def ensure_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_MATCHES_DDL)
            await cur.execute(_PREDICTIONS_DDL)


# ── matches ─────────────────────────────────────────────────

async def upsert_match(m: dict) -> None:
    """写入/更新一场比赛的事实（赛程或赛果）。只覆盖非 None 字段以免赛程覆盖掉已有赛果。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO matches
                  (match_id, competition, home_team, away_team, home_cn, away_cn,
                   kickoff_time, status, duration, home_goals, away_goals, pen_home, pen_away, outcome)
                VALUES (%(match_id)s,%(competition)s,%(home_team)s,%(away_team)s,%(home_cn)s,%(away_cn)s,
                        %(kickoff_time)s,%(status)s,%(duration)s,%(home_goals)s,%(away_goals)s,
                        %(pen_home)s,%(pen_away)s,%(outcome)s) AS new
                ON DUPLICATE KEY UPDATE
                  status=new.status, duration=new.duration,
                  home_goals=COALESCE(new.home_goals, matches.home_goals),
                  away_goals=COALESCE(new.away_goals, matches.away_goals),
                  pen_home=COALESCE(new.pen_home, matches.pen_home),
                  pen_away=COALESCE(new.pen_away, matches.pen_away),
                  outcome=COALESCE(new.outcome, matches.outcome),
                  home_cn=COALESCE(new.home_cn, matches.home_cn),
                  away_cn=COALESCE(new.away_cn, matches.away_cn)
                """,
                {k: m.get(k) for k in (
                    "match_id", "competition", "home_team", "away_team", "home_cn", "away_cn",
                    "kickoff_time", "status", "duration", "home_goals", "away_goals",
                    "pen_home", "pen_away", "outcome")},
            )


async def get_match(match_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM matches WHERE match_id=%s", (match_id,))
            return await cur.fetchone()


# ── match_predictions ───────────────────────────────────────

async def upsert_prediction(match_id: str, p: dict) -> None:
    """写入/更新某场的权威预测（覆盖旧的，保证一场一条）。评分列不动（结算时填）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO match_predictions
                  (match_id, p_home, p_draw, p_away, score_dist, top_score,
                   odds_p_home, odds_p_draw, odds_p_away, extra_json)
                VALUES (%(match_id)s,%(p_home)s,%(p_draw)s,%(p_away)s,%(score_dist)s,%(top_score)s,
                        %(odds_p_home)s,%(odds_p_draw)s,%(odds_p_away)s,%(extra_json)s) AS new
                ON DUPLICATE KEY UPDATE
                  p_home=new.p_home, p_draw=new.p_draw, p_away=new.p_away,
                  score_dist=new.score_dist, top_score=new.top_score,
                  odds_p_home=new.odds_p_home, odds_p_draw=new.odds_p_draw, odds_p_away=new.odds_p_away,
                  extra_json=new.extra_json,
                  brier_agent=NULL, rps_agent=NULL, brier_odds=NULL, rps_odds=NULL
                """,
                {"match_id": match_id, **{k: p.get(k) for k in (
                    "p_home", "p_draw", "p_away", "score_dist", "top_score",
                    "odds_p_home", "odds_p_draw", "odds_p_away", "extra_json")}},
            )


async def list_unresolved() -> list[dict]:
    """已结束但还没评分的预测（join 赛果），供 resolver 结算。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT p.match_id, p.p_home, p.p_draw, p.p_away,
                       p.odds_p_home, p.odds_p_draw, p.odds_p_away,
                       m.home_cn, m.away_cn, m.home_goals, m.away_goals, m.outcome
                FROM match_predictions p JOIN matches m ON p.match_id=m.match_id
                WHERE m.status='FINISHED' AND m.outcome IS NOT NULL AND p.brier_agent IS NULL
                """
            )
            return list(await cur.fetchall())


async def update_scores(
    match_id: str, brier_agent: float, rps_agent: float,
    brier_odds: float | None, rps_odds: float | None,
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE match_predictions SET brier_agent=%s, rps_agent=%s, "
                "brier_odds=%s, rps_odds=%s WHERE match_id=%s",
                (brier_agent, rps_agent, brier_odds, rps_odds, match_id),
            )


async def aggregate() -> dict:
    """全局汇总：所有权威预测 vs 赔率的平均 Brier/RPS、击败赔率次数（按 RPS）。"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT COUNT(*) AS total FROM match_predictions")
            total = (await cur.fetchone())["total"]
            await cur.execute(
                """
                SELECT COUNT(*) AS resolved,
                       AVG(brier_agent) AS avg_brier_agent, AVG(rps_agent) AS avg_rps_agent,
                       AVG(brier_odds)  AS avg_brier_odds,  AVG(rps_odds)  AS avg_rps_odds,
                       SUM(rps_odds IS NOT NULL AND rps_agent < rps_odds) AS agent_beats_odds
                FROM match_predictions WHERE brier_agent IS NOT NULL
                """
            )
            row = await cur.fetchone()
    return {"total": total, **row}
