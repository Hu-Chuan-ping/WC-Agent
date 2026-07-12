from __future__ import annotations

from app.core import request_context
from app.core.eval import metrics
from app.core.tools.base_tool import BaseTool
from app.infra.repositories import user_match_repository

_STATUS_CN = {"hit": "全中", "half": "半中（胜负对、比分错）", "miss": "未中"}


def _mentions(query: str, row: dict) -> bool:
    """这条预测是否与查询提到的球队相关。"""
    names = [row.get("home_cn"), row.get("away_cn")]
    if any(n and n in query for n in names):
        return True
    return any(n and tok and tok in n for tok in query.split() for n in names)


def _one(row: dict) -> str:
    if row.get("p_home") is None:
        return f"你问过「{row.get('home_cn')} vs {row.get('away_cn')}」，但暂无权威预测记录。"
    head = (
        f"你对「{row.get('home_cn')} vs {row.get('away_cn')}」的预测："
        f"最可能比分 {row.get('top_score')}，"
        f"胜/平/负概率 {row['p_home']:.2f}/{row['p_draw']:.2f}/{row['p_away']:.2f}"
    )
    if row.get("outcome") is not None and row.get("home_goals") is not None:
        actual = f"{row['home_goals']}-{row['away_goals']}"
        if row.get("pen_home") is not None:
            actual += f"（点球{row['pen_home']}-{row['pen_away']}）"
        status = metrics.hit_status(row.get("top_score"), row["home_goals"], row["away_goals"])
        return head + f"。赛后真实比分 {actual}，判定：{_STATUS_CN.get(status, status)}。"
    return head + "。该场尚未结算。"


class MyPredictionsTool(BaseTool):
    """查当前用户问过的比赛的权威预测 + 赛后结果（读 matches/match_predictions）。"""

    name = "get_my_predictions"
    description = (
        "查『当前用户』问过的某场比赛的预测（最可能比分、胜平负概率）以及赛后真实比分与命中情况。"
        "当用户追问自己问过的某场比赛、或问某场结果/命中如何时使用。query 传球队名关键词，如：阿根廷 埃及。"
    )

    async def run(self, query: str) -> str:
        user_id = request_context.get_current_user_id()
        if not user_id:
            return "无法确定当前用户身份，暂时查不了你的预测记录。"
        rows = await user_match_repository.list_by_user(user_id)
        if not rows:
            return "你还没有任何预测记录。"
        matched = [r for r in rows if _mentions(query, r)]
        if not matched:
            recent = "；".join(f"{r.get('home_cn')} vs {r.get('away_cn')}" for r in rows[:5])
            return f"没找到与「{query}」匹配的预测。你最近问过：{recent}。"
        return "\n".join(_one(r) for r in matched)

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "球队名关键词，如：阿根廷 埃及 / 巴西"},
            },
            "required": ["query"],
        }
