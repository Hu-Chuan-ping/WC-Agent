from __future__ import annotations

from app.core.eval import metrics
from app.infra.external import football_data
from app.infra.repositories import match_repository
from app.utils.logger import logger

# 赛后结算（领域编排）：拉赛果 → upsert 进 matches → 给未评分的权威预测算 Brier/RPS。
# 不含 HTTP/SQL 细节，只编排网关 + 仓库 + 指标。


async def resolve_pending() -> int:
    """结算所有已结束但未评分的权威预测。返回本次评分场次数。"""
    matches = await football_data.fetch_wc_matches()

    # 1) 把已结束比赛的客观赛果写进 matches（共享事实）
    for m in matches:
        if m["status"] == "FINISHED" and m["home_goals"] is not None:
            m["outcome"] = metrics.outcome_from_score(m["home_goals"], m["away_goals"])
            await match_repository.upsert_match(m)

    # 2) 给"已结束 + 有预测 + 未评分"的场次算分（用常规比分的 outcome）
    resolved = 0
    for r in await match_repository.list_unresolved():
        outcome = r["outcome"]
        ba = metrics.brier(r["p_home"], r["p_draw"], r["p_away"], outcome)
        ra = metrics.rps(r["p_home"], r["p_draw"], r["p_away"], outcome)
        bo = ro = None
        if r["odds_p_home"] is not None:
            bo = metrics.brier(r["odds_p_home"], r["odds_p_draw"], r["odds_p_away"], outcome)
            ro = metrics.rps(r["odds_p_home"], r["odds_p_draw"], r["odds_p_away"], outcome)
        await match_repository.update_scores(r["match_id"], ba, ra, bo, ro)
        resolved += 1
        logger.info(
            f"结算 {r['home_cn']} {r['home_goals']}-{r['away_goals']} {r['away_cn']}："
            f"RPS你={ra:.3f}" + (f" vs 赔率={ro:.3f}" if ro is not None else "")
        )

    logger.info(f"本次结算 {resolved} 场")
    return resolved
