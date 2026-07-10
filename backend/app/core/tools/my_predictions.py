from __future__ import annotations

from app.core import request_context
from app.core.eval import metrics
from app.core.tools.base_tool import BaseTool
from app.infra.repositories import prediction_repository

_STATUS_CN = {"hit": "全中", "half": "半中（胜负对、比分错）", "miss": "未中"}


def _mentions(query: str, row: dict) -> bool:
    """这条预测是否与查询提到的球队相关（中/英名互查子串）。"""
    names = [row.get("home_cn"), row.get("away_cn"), row.get("home_team"), row.get("away_team")]
    for n in names:
        if n and n in query:
            return True
    # 反向：查询里的词是否命中队名
    for tok in query.split():
        for n in names:
            if n and tok and tok in n:
                return True
    return False


def _one(row: dict) -> str:
    head = (
        f"你对「{row.get('home_cn')} vs {row.get('away_cn')}」的预测："
        f"比分 {row.get('agent_score')}，"
        f"胜/平/负概率 "
        f"{row.get('agent_p_home'):.2f}/{row.get('agent_p_draw'):.2f}/{row.get('agent_p_away'):.2f}"
    )
    if row.get("status") == "resolved" and row.get("actual_home") is not None:
        ah, aw = row["actual_home"], row["actual_away"]
        status = metrics.hit_status(row.get("agent_score"), ah, aw)
        return head + f"。赛后真实比分 {ah}-{aw}，判定：{_STATUS_CN.get(status, status)}。"
    return head + "。该场尚未结算。"


class MyPredictionsTool(BaseTool):
    """查当前用户自己的历史预测 + 赛后结果（读 MySQL predictions 表）。

    追问"你之前对某场的预测/那场结果如何"时用它——数据是自己存过的，不必外部检索。
    """

    name = "get_my_predictions"
    description = (
        "查『当前用户自己』之前对某场比赛的预测（预测比分、胜平负概率）以及赛后真实比分与命中情况。"
        "当用户追问自己预测过的某场比赛、或问某场结果/命中如何时使用。query 传球队名关键词，如：阿根廷 埃及。"
    )

    async def run(self, query: str) -> str:
        user_id = request_context.get_current_user_id()
        if not user_id:
            return "无法确定当前用户身份，暂时查不了你的预测记录。"
        rows = await prediction_repository.list_by_user(user_id)
        if not rows:
            return "你还没有任何预测记录。"
        matched = [r for r in rows if _mentions(query, r)]
        if not matched:
            recent = "；".join(f"{r.get('home_cn')} vs {r.get('away_cn')}" for r in rows[:5])
            return f"没找到与「{query}」匹配的预测。你最近预测过：{recent}。"
        return "\n".join(_one(r) for r in matched)

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "球队名关键词，如：阿根廷 埃及 / 巴西",
                },
            },
            "required": ["query"],
        }
