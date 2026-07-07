from __future__ import annotations

import httpx

from app.config.settings import settings
from app.core.eval import metrics, repo
from app.utils.logger import logger
from app.utils.teammatch import same_team

_TIMEOUT = 20.0


async def _fetch_wc_results() -> list[dict]:
    """从 football-data 拉世界杯所有已结束比赛的终场比分。"""
    headers = {"X-Auth-Token": settings.football_data_api_key}
    async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as c:
        r = await c.get(
            f"{settings.football_data_base_url}/competitions/WC/matches?status=FINISHED",
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()
    out = []
    for m in data.get("matches", []):
        ft = (m.get("score") or {}).get("fullTime") or {}
        if ft.get("home") is None:
            continue
        out.append({
            "home": m["homeTeam"]["name"], "away": m["awayTeam"]["name"],
            "h": ft["home"], "a": ft["away"],
        })
    return out


def _find_result(results: list[dict], home: str, away: str) -> tuple[int, int] | None:
    """按队名找赛果，返回 (我方主队进球, 我方客队进球)。"""
    for m in results:
        if same_team(m["home"], home) and same_team(m["away"], away):
            return m["h"], m["a"]
        if same_team(m["home"], away) and same_team(m["away"], home):  # 主客顺序反了 → 比分对调
            return m["a"], m["h"]
    return None


async def resolve_pending() -> int:
    """结算所有已开赛结束的预测：查赛果 → 算 Brier(你)与 Brier(赔率) → 落库。"""
    pend = await repo.list_pending()
    if not pend:
        return 0
    results = await _fetch_wc_results()

    resolved = 0
    for row in pend:
        r = _find_result(results, row["home_team"], row["away_team"])
        if r is None:
            continue  # 还没结束或没匹配到，下次再查
        ah, aw = r
        outcome = metrics.outcome_from_score(ah, aw)

        ba = metrics.brier(
            row["agent_p_home"], row["agent_p_draw"], row["agent_p_away"], outcome
        )
        ll = metrics.log_loss(
            row["agent_p_home"], row["agent_p_draw"], row["agent_p_away"], outcome
        )
        bo = None
        if row["odds_p_home"] is not None:
            bo = metrics.brier(
                row["odds_p_home"], row["odds_p_draw"], row["odds_p_away"], outcome
            )

        await repo.mark_resolved(row["id"], ah, aw, outcome, ba, bo, ll)
        resolved += 1
        logger.info(
            f"结算 {row['home_cn']} {ah}-{aw} {row['away_cn']}："
            f"Brier你={ba:.3f}" + (f" vs 赔率={bo:.3f}" if bo is not None else "")
        )

    logger.info(f"本次结算 {resolved}/{len(pend)} 场")
    return resolved
