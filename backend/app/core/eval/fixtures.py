from __future__ import annotations

import httpx

from app.config.settings import settings
from app.utils.logger import logger
from app.utils.teammatch import same_team

_TIMEOUT = 20.0


async def match_state(home: str, away: str) -> dict | None:
    """查 football-data 世界杯赛程，返回该对阵的状态与（若有）比分。

    返回 {"status": SCHEDULED|TIMED|IN_PLAY|PAUSED|FINISHED..., "home_goals", "away_goals"}
    —— home_goals/away_goals 已按传入的 home/away 顺序对齐。查不到或出错返回 None。
    """
    headers = {"X-Auth-Token": settings.football_data_api_key}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as c:
            r = await c.get(
                f"{settings.football_data_base_url}/competitions/WC/matches",
                headers=headers,
            )
            r.raise_for_status()
            matches = r.json().get("matches", [])
    except httpx.HTTPError as exc:
        logger.warning(f"查赛程状态失败（当作未开赛处理）：{exc}")
        return None

    for m in matches:
        mh, ma = m["homeTeam"]["name"], m["awayTeam"]["name"]
        ft = (m.get("score") or {}).get("fullTime") or {}
        if same_team(mh, home) and same_team(ma, away):
            return {"status": m["status"],
                    "home_goals": ft.get("home"), "away_goals": ft.get("away")}
        if same_team(mh, away) and same_team(ma, home):  # 赛程里主客顺序相反 → 比分对调
            return {"status": m["status"],
                    "home_goals": ft.get("away"), "away_goals": ft.get("home")}
    return None
