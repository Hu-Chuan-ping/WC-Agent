from __future__ import annotations

import json

from app.core.eval import metrics, resolver
from app.infra.repositories import match_repository, user_match_repository

# 预测记录应用服务：编排"我的预测 / 我的汇总 / 全局总偏差 / 刷新赛果"。
# 命中判定等领域逻辑调 metrics；存取走仓库。评价对象是每场一条的权威预测。


def _fmt_probs(row: dict) -> str:
    ph = row.get("p_home")
    if ph is None:
        return "-"
    return f"{ph:.2f}/{row['p_draw']:.2f}/{row['p_away']:.2f}"


def _fmt_actual(row: dict) -> str | None:
    if row.get("outcome") is None or row.get("home_goals") is None:
        return None
    s = f"{row['home_goals']}-{row['away_goals']}"
    if row.get("pen_home") is not None:  # 点球赛：常规比分（点球比分）
        s += f"（{row['pen_home']}-{row['pen_away']}）"
    return s


def _row_status(row: dict) -> str:
    if row.get("outcome") is None or row.get("home_goals") is None:
        return "pending"
    return metrics.hit_status(row.get("top_score"), row["home_goals"], row["away_goals"])


def _parse_dist(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        d = json.loads(raw)
        return d if isinstance(d, list) else []
    except json.JSONDecodeError:
        return []


async def list_predictions(user_id: str) -> list[dict]:
    out = []
    for r in await user_match_repository.list_by_user(user_id):
        out.append({
            "match_id": r["match_id"],
            "match": f"{r['home_cn']} vs {r['away_cn']}",
            "kickoff_time": r["kickoff_time"],
            "predicted_score": r.get("top_score"),
            "predicted_probs": _fmt_probs(r),
            "score_dist": _parse_dist(r.get("score_dist")),
            "actual_score": _fmt_actual(r),
            "status": _row_status(r),
            "session_id": r.get("session_id"),
        })
    return out


async def summary(user_id: str) -> dict:
    rows = await user_match_repository.list_by_user(user_id)
    resolved = [r for r in rows if r.get("outcome") is not None and r.get("home_goals") is not None]

    counts = {"hit": 0, "half": 0, "miss": 0}
    rps_a, rps_o, brier_a, brier_o, beats = [], [], [], [], 0
    for r in resolved:
        counts[metrics.hit_status(r.get("top_score"), r["home_goals"], r["away_goals"])] += 1
        if r.get("rps_agent") is not None:
            rps_a.append(r["rps_agent"])
        if r.get("brier_agent") is not None:
            brier_a.append(r["brier_agent"])
        if r.get("rps_odds") is not None:
            rps_o.append(r["rps_odds"])
            if r.get("rps_agent") is not None and r["rps_agent"] < r["rps_odds"]:
                beats += 1
        if r.get("brier_odds") is not None:
            brier_o.append(r["brier_odds"])

    n = len(resolved)
    avg = lambda xs: round(sum(xs) / len(xs), 4) if xs else None  # noqa: E731
    return {
        "total": len(rows), "resolved": n,
        "hit": counts["hit"], "half": counts["half"], "miss": counts["miss"],
        "hit_rate": round(counts["hit"] / n, 4) if n else None,
        "avg_rps_agent": avg(rps_a), "avg_rps_odds": avg(rps_o),
        "avg_brier_agent": avg(brier_a), "avg_brier_odds": avg(brier_o),
        "beats_odds": beats,
    }


async def overview() -> dict:
    """全局总偏差：所有权威预测 vs 赔率。以 RPS 为主判定是否赢过市场。"""
    agg = await match_repository.aggregate()
    resolved = agg.get("resolved") or 0
    ra, ro = agg.get("avg_rps_agent"), agg.get("avg_rps_odds")
    verdict = "样本不足"
    if resolved and ra is not None and ro is not None:
        verdict = "✅ 整体打赢了赔率（RPS 更低）" if ra < ro else "❌ 整体没打赢赔率"
    rnd = lambda v: round(v, 4) if v is not None else None  # noqa: E731
    return {
        "total": agg.get("total") or 0, "resolved": resolved,
        "avg_rps_agent": rnd(ra), "avg_rps_odds": rnd(ro),
        "avg_brier_agent": rnd(agg.get("avg_brier_agent")), "avg_brier_odds": rnd(agg.get("avg_brier_odds")),
        "verdict": verdict,
    }


async def resolve() -> int:
    return await resolver.resolve_pending()
