from __future__ import annotations

from app.core.eval import metrics, resolver
from app.infra.repositories import prediction_repository as repo

# 预测记录应用服务：编排“列出我的预测 / 我的汇总 / 全局总偏差 / 刷新赛果”。
# 命中判定等领域逻辑调用 core/eval.metrics；存取走 repo。


def _fmt_probs(row: dict) -> str:
    ph, pd, pa = row.get("agent_p_home"), row.get("agent_p_draw"), row.get("agent_p_away")
    if ph is None:
        return "-"
    return f"{ph:.2f}/{pd:.2f}/{pa:.2f}"


def _row_status(row: dict) -> str:
    """未结算 → pending；已结算 → 全中/半中/未中。"""
    if row["status"] != "resolved" or row["actual_home"] is None:
        return "pending"
    return metrics.hit_status(row["agent_score"], row["actual_home"], row["actual_away"])


async def list_predictions(user_id: str) -> list[dict]:
    out = []
    for r in await repo.list_by_user(user_id):
        actual = (
            f"{r['actual_home']}-{r['actual_away']}"
            if r["actual_home"] is not None else None
        )
        out.append({
            "id": r["id"],
            "match": f"{r['home_cn']} vs {r['away_cn']}",
            "kickoff_time": r["kickoff_time"],
            "predicted_score": r["agent_score"],
            "predicted_probs": _fmt_probs(r),
            "actual_score": actual,
            "status": _row_status(r),
            "session_id": r["session_id"],
        })
    return out


async def summary(user_id: str) -> dict:
    rows = await repo.list_by_user(user_id)
    resolved = [r for r in rows if r["status"] == "resolved" and r["actual_home"] is not None]

    counts = {"hit": 0, "half": 0, "miss": 0}
    briers_a, briers_o, beats = [], [], 0
    for r in resolved:
        counts[metrics.hit_status(r["agent_score"], r["actual_home"], r["actual_away"])] += 1
        if r["brier_agent"] is not None:
            briers_a.append(r["brier_agent"])
        if r["brier_odds"] is not None:
            briers_o.append(r["brier_odds"])
            if r["brier_agent"] is not None and r["brier_agent"] < r["brier_odds"]:
                beats += 1

    n = len(resolved)
    avg = lambda xs: round(sum(xs) / len(xs), 4) if xs else None  # noqa: E731
    return {
        "total": len(rows),
        "resolved": n,
        "hit": counts["hit"],
        "half": counts["half"],
        "miss": counts["miss"],
        "hit_rate": round(counts["hit"] / n, 4) if n else None,
        "avg_brier_agent": avg(briers_a),
        "avg_brier_odds": avg(briers_o),
        "beats_odds": beats,
    }


async def overview() -> dict:
    """全局总预测偏差（所有用户所有比赛）。"""
    agg = await repo.aggregate()
    resolved = agg.get("resolved") or 0
    ba, bo = agg.get("avg_brier_agent"), agg.get("avg_brier_odds")
    verdict = "样本不足"
    if resolved and ba is not None and bo is not None:
        verdict = "✅ 整体打赢了赔率" if ba < bo else "❌ 整体没打赢赔率"
    return {
        "total": agg.get("total") or 0,
        "resolved": resolved,
        "avg_brier_agent": round(ba, 4) if ba is not None else None,
        "avg_brier_odds": round(bo, 4) if bo is not None else None,
        "verdict": verdict,
    }


async def resolve() -> int:
    """手动触发赛后结算，返回本次结算场次数。"""
    return await resolver.resolve_pending()
