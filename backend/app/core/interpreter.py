from __future__ import annotations

import json
import re

from app.utils.client import get_fast_client
from app.utils.logger import logger

# 一次快模型调用同时完成：判定意图(predict/chat) + 抽取对阵球队。
# 结合对话历史理解指代，替代原先「router 分类」+「predictor 抽队名」两次慢调用。
_SYSTEM = """你是请求理解器。判断用户意图并抽取比赛对阵，只输出一个 JSON，不要解释：
{"route":"predict"或"chat","teams":{"home_en":"England","away_en":"Brazil","home_cn":"英格兰","away_cn":"巴西"} 或 null}
规则：
- route="predict"：用户想预测某一场【具体比赛】的胜负/比分（明确写出、或结合历史能确定两支球队）
- route="chat"：闲聊、打招呼、开放性问题、对上一条预测的追问、或无法确定要预测的具体两队
- teams：能明确两支对阵球队时给出（*_en 用国际通用英文队名），否则为 null
- 结合对话历史理解指代（如"那如果梅西没上"通常指上一条预测的那场比赛）"""


async def interpret(question: str, history: list[dict] | None = None) -> dict:
    """返回 {"route": "predict"|"chat", "teams": dict|None}。解析失败安全兜底为 chat。"""
    client = get_fast_client()
    messages = list(history or []) + [{"role": "user", "content": question}]
    resp = await client.complete(messages=messages, system=_SYSTEM, max_tokens=512)

    route, teams = _parse(resp.text)
    logger.info(f"意图理解：route={route}，teams={'有' if teams else '无'}")
    return {"route": route, "teams": teams}


def _parse(text: str) -> tuple[str, dict | None]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return "chat", None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return "chat", None

    route = "predict" if d.get("route") == "predict" else "chat"
    teams = d.get("teams")
    if isinstance(teams, dict) and teams.get("home_en") and teams.get("away_en"):
        teams.setdefault("home_cn", teams["home_en"])
        teams.setdefault("away_cn", teams["away_en"])
    else:
        teams = None
    # 说是 predict 却没抽到两队 → 当作追问，交给 ReAct（teams=None）
    return route, teams
