from __future__ import annotations

from app.infra.external import football_data
from app.utils.teammatch import same_team

# 赛程状态查询（领域逻辑）：向 football_data 网关要归一化赛程，
# 在这里做队名匹配与主客对齐，判断某场比赛处于赛前/进行中/已结束。


async def match_state(home: str, away: str) -> dict | None:
    """返回该对阵的状态与（若有）比分。

    返回 {"status": SCHEDULED|TIMED|IN_PLAY|PAUSED|FINISHED..., "home_goals", "away_goals"}
    —— home_goals/away_goals 已按传入的 home/away 顺序对齐。查不到或出错返回 None。
    """
    matches = await football_data.fetch_wc_matches_safe()
    if matches is None:
        return None

    for m in matches:
        mh, ma = m["home"], m["away"]
        if same_team(mh, home) and same_team(ma, away):
            return {"status": m["status"],
                    "home_goals": m["home_goals"], "away_goals": m["away_goals"]}
        if same_team(mh, away) and same_team(ma, home):  # 赛程里主客顺序相反 → 比分对调
            return {"status": m["status"],
                    "home_goals": m["away_goals"], "away_goals": m["home_goals"]}
    return None
