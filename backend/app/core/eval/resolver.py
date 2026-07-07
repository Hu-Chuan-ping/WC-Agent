from __future__ import annotations

from app.core.eval import metrics
from app.infra.external import football_data
from app.infra.repositories import prediction_repository as repo
from app.utils.logger import logger
from app.utils.teammatch import same_team

# 赛后结算（领域编排）：查赛果(网关) → 匹配对阵 → 算 Brier/log-loss(metrics) → 落库(repo)。
# 本文件不含任何 HTTP/SQL 细节，只编排三方。


def _find_result(results: list[dict], home: str, away: str) -> tuple[int, int] | None:
    """按队名找赛果，返回 (我方主队进球, 我方客队进球)。"""
    for m in results:
        if same_team(m["home"], home) and same_team(m["away"], away):
            return m["home_goals"], m["away_goals"]
        if same_team(m["home"], away) and same_team(m["away"], home):  # 主客反了 → 比分对调
            return m["away_goals"], m["home_goals"]
    return None


async def resolve_pending() -> int:
    """结算所有已开赛结束的预测：查赛果 → 算 Brier(你)与 Brier(赔率) → 落库。"""
    pend = await repo.list_pending()
    if not pend:
        return 0
    # 只要已结束、且有比分的场次
    results = [
        m for m in await football_data.fetch_wc_matches(status="FINISHED")
        if m["home_goals"] is not None
    ]

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
