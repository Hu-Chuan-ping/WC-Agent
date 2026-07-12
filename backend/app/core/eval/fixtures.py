from __future__ import annotations

from app.infra.external import football_data
from app.utils.teammatch import same_team

# 赛程定位（领域逻辑）：向 football_data 网关要归一化赛程，在这里做队名匹配、消歧、朝向判断。

_LIVE = ("SCHEDULED", "TIMED", "IN_PLAY", "PAUSED")


async def find_match(home: str, away: str) -> dict | None:
    """按两支球队定位到 football-data 的唯一一场比赛。

    消歧：同两队可能踢多次 → 优先未结束的（预测场景），否则取已结束的。
    返回归一化 match dict（football 原生主客朝向）+ user_is_home（用户的 home 是否即 football 的 home）。
    查不到或出错返回 None。
    """
    matches = await football_data.fetch_wc_matches_safe()
    if matches is None:
        return None

    candidates = [
        m for m in matches
        if (same_team(m["home_team"], home) and same_team(m["away_team"], away))
        or (same_team(m["home_team"], away) and same_team(m["away_team"], home))
    ]
    if not candidates:
        return None

    live = [m for m in candidates if m["status"] in _LIVE]
    chosen = (
        min(live, key=lambda m: m["kickoff_time"] or "")   # 未结束取最近开赛的
        if live
        else max(candidates, key=lambda m: m["kickoff_time"] or "")  # 全结束取最近踢过的
    )
    chosen = dict(chosen)
    chosen["user_is_home"] = same_team(chosen["home_team"], home)
    return chosen
