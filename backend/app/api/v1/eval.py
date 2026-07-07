from __future__ import annotations

from fastapi import APIRouter

from app.core.eval import repo, resolver

router = APIRouter()


@router.get("/eval")
async def eval_report() -> dict:
    """评估报告：你的预测 vs 赔率基准的平均 Brier / log-loss / 击败次数。"""
    agg = await repo.aggregate()
    resolved = agg.get("resolved") or 0
    ba = agg.get("avg_brier_agent")
    bo = agg.get("avg_brier_odds")
    verdict = "样本不足"
    if resolved and ba is not None and bo is not None:
        verdict = "✅ 你打赢了赔率" if ba < bo else "❌ 没打赢赔率（≈复述市场）"
    return {
        "总预测数": agg.get("total"),
        "已结算": resolved,
        "平均Brier_你": round(ba, 4) if ba is not None else None,
        "平均Brier_赔率": round(bo, 4) if bo is not None else None,
        "平均logloss_你": round(agg["avg_logloss_agent"], 4) if agg.get("avg_logloss_agent") is not None else None,
        "你击败赔率次数": int(agg.get("agent_beats_odds") or 0),
        "结论": verdict,
    }


@router.get("/eval/details")
async def eval_details() -> list[dict]:
    """每场明细：你的预测/概率 vs 实际结果，以及各自 Brier。"""
    out = []
    for r in await repo.list_resolved():
        out.append({
            "对阵": f"{r['home_cn']} vs {r['away_cn']}",
            "预测比分": r["agent_score"],
            "实际比分": f"{r['actual_home']}-{r['actual_away']}",
            "赛果": r["actual_outcome"],
            "你的概率(主/平/客)": (
                f"{r['agent_p_home']:.2f}/{r['agent_p_draw']:.2f}/{r['agent_p_away']:.2f}"
            ),
            "Brier你": round(r["brier_agent"], 3) if r["brier_agent"] is not None else None,
            "Brier赔率": round(r["brier_odds"], 3) if r["brier_odds"] is not None else None,
        })
    return out


@router.post("/eval/resolve")
async def trigger_resolve() -> dict:
    """手动触发一次结算（查赛果、算分）。"""
    n = await resolver.resolve_pending()
    return {"resolved": n}
