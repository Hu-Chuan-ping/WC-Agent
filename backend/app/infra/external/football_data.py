from __future__ import annotations

import httpx

from app.config.settings import settings
from app.utils.logger import logger

# football-data.org 网关：唯一直接 HTTP 访问该数据源的地方。
# 负责“发请求 + 把外部 JSON 归一化成稳定的内部结构”；
# 队名匹配、比分对齐、算分等领域逻辑留在 core（fixtures / resolver）。

_TIMEOUT = 20.0


async def fetch_wc_matches(status: str | None = None) -> list[dict]:
    """拉世界杯赛程/赛果，归一化为内部结构。

    status: 传 "FINISHED" 只要已结束的；None 拉全部。
    返回每场：{"home","away","status","home_goals","away_goals"}
    （home_goals/away_goals 在未开赛时为 None）。
    """
    headers = {"X-Auth-Token": settings.football_data_api_key}
    url = f"{settings.football_data_base_url}/competitions/WC/matches"
    if status:
        url += f"?status={status}"
    async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as c:
        r = await c.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()

    out: list[dict] = []
    for m in data.get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        out.append({
            "home": m["homeTeam"]["name"],
            "away": m["awayTeam"]["name"],
            "status": m["status"],
            "home_goals": ft.get("home"),
            "away_goals": ft.get("away"),
        })
    return out


async def fetch_wc_matches_safe(status: str | None = None) -> list[dict] | None:
    """同 fetch_wc_matches，但网络出错时返回 None（供“查不到当未开赛”的场景用）。"""
    try:
        return await fetch_wc_matches(status)
    except httpx.HTTPError as exc:
        logger.warning(f"查 football-data 赛程失败：{exc}")
        return None
