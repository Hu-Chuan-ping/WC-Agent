from __future__ import annotations

import httpx

from app.config.settings import settings
from app.utils.logger import logger

# football-data.org 网关：唯一直接 HTTP 访问该数据源的地方。
# 负责“发请求 + 把外部 JSON 归一化成稳定的内部结构”；
# 队名匹配、比分对齐、算分等领域逻辑留在 core（fixtures / resolver）。

_TIMEOUT = 20.0


def _extract_score(score: dict) -> tuple[int | None, int | None, int | None, int | None]:
    """从 football-data 的 score 结构解析出【常规比分】与【点球比分】。

    - 点球赛(PENALTY_SHOOTOUT)：fullTime 含点球，真正结果是 regularTime(如 0-0)；penalties 单列。
    - 加时决出(EXTRA_TIME)：fullTime 就是加时后的胜负比分，直接用。
    - 常规(REGULAR)：fullTime 即结果。
    返回 (home_goals, away_goals, pen_home, pen_away)，无则 None。
    """
    duration = score.get("duration")
    ft = score.get("fullTime") or {}
    if duration == "PENALTY_SHOOTOUT":
        reg = score.get("regularTime") or {}
        pen = score.get("penalties") or {}
        return reg.get("home"), reg.get("away"), pen.get("home"), pen.get("away")
    return ft.get("home"), ft.get("away"), None, None


def _normalize(m: dict) -> dict:
    """把一场 football-data 比赛归一化成内部结构。"""
    score = m.get("score") or {}
    hg, ag, ph, pa = _extract_score(score)
    return {
        "match_id": str(m["id"]),
        "competition": "WC",
        "home_team": m["homeTeam"]["name"],
        "away_team": m["awayTeam"]["name"],
        "kickoff_time": m.get("utcDate"),
        "status": m["status"],
        "duration": score.get("duration"),
        "home_goals": hg,
        "away_goals": ag,
        "pen_home": ph,
        "pen_away": pa,
    }


async def fetch_wc_matches(status: str | None = None) -> list[dict]:
    """拉世界杯赛程/赛果，归一化。status 传 "FINISHED" 只要已结束的；None 拉全部。

    每场：{match_id, competition, home_team, away_team, kickoff_time, status, duration,
           home_goals, away_goals, pen_home, pen_away}（未开赛时比分为 None）。
    """
    headers = {"X-Auth-Token": settings.football_data_api_key}
    url = f"{settings.football_data_base_url}/competitions/WC/matches"
    if status:
        url += f"?status={status}"
    async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as c:
        r = await c.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
    return [_normalize(m) for m in data.get("matches", [])]


async def fetch_wc_matches_safe(status: str | None = None) -> list[dict] | None:
    """同 fetch_wc_matches，但网络出错时返回 None（供“查不到当未开赛”的场景用）。"""
    try:
        return await fetch_wc_matches(status)
    except httpx.HTTPError as exc:
        logger.warning(f"查 football-data 赛程失败：{exc}")
        return None
