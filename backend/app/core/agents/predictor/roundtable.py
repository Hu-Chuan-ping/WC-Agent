from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.core.agents.predictor.roundtable_prompts import (
    HISTORY_SPECIALIST,
    MARKET_SPECIALIST,
    MODERATOR_PROMPT,
    STATUS_SPECIALIST,
)
from app.infra.llm.client import LLMClient, get_fast_client
from app.utils.logger import logger

# ── 预测圆桌(sub-agent 编排)────────────────────────────────────────
#
# 三位专家【并行】各自分析一维数据(专业化推理 pass，用快模型)，
# 主持人【流式】综合三份意见给出最终预测(用强模型)。
# 专家是轻量“推理 pass”而非带工具的 BaseAgent——数据已由 pipeline 预抓，无需各自调工具。


class Specialist:
    """圆桌里的一个专家：一次专业化 LLM 调用，只对给定的一维数据出判断。"""

    def __init__(self, name: str, title: str, system_prompt: str):
        self.name = name              # 机器名，对应 slices 的 key，如 "market"
        self.title = title            # 展示名，前端卡片标题，如 "市场专家"
        self.system_prompt = system_prompt

    async def analyze(self, data_slice: str, client: LLMClient) -> str:
        user_msg = f"以下是供你分析的数据：\n\n{data_slice}"
        resp = await client.complete(
            [{"role": "user", "content": user_msg}],
            self.system_prompt,
            max_tokens=1024,
        )
        return resp.text


# 三位专家。name 必须与 pipeline 切片(_gather_context 返回的 slices)的 key 对齐。
SPECIALISTS: list[Specialist] = [
    Specialist("status", "状态/战力专家", STATUS_SPECIALIST),
    Specialist("history", "历史交锋专家", HISTORY_SPECIALIST),
    Specialist("market", "市场专家", MARKET_SPECIALIST),
]


async def run_roundtable(
    slices: dict[str, str],
    moderator_client: LLMClient,
    user_input: str,
    profile: str = "",
    max_tokens: int = 8192,
) -> AsyncIterator[dict]:
    """圆桌主链路。产出事件：
      - status：进度文案
      - expert：某专家的意见(name/title/text)，供前端渲成卡片
      - token：主持人合成的最终回答，逐字流(含末尾机器 JSON，由调用方过滤)

    专家用快模型并行；主持人用传入的强模型(moderator_client)流式。
    """
    fast = get_fast_client()

    yield {"type": "status", "text": "三位专家正在并行会诊…"}

    async def _one(sp: Specialist) -> tuple[Specialist, str]:
        # 单个专家失败降级为提示，不拖垮整桌(与 pipeline 的容错一致)
        try:
            take = await sp.analyze(slices.get(sp.name, "（无相关数据）"), fast)
        except Exception as exc:
            logger.warning(f"[roundtable] 专家 {sp.name} 失败：{exc}")
            take = f"（{sp.title}分析失败，本维度意见缺失：{exc}）"
        return sp, take

    results = await asyncio.gather(*(_one(sp) for sp in SPECIALISTS))

    take_blocks: list[str] = []
    for sp, take in results:
        yield {"type": "expert", "name": sp.name, "title": sp.title, "text": take}
        take_blocks.append(f"## {sp.title}的意见\n{take}")
    takes_joined = "\n\n".join(take_blocks)

    yield {"type": "status", "text": "主持人正在综合三方意见…"}

    system = MODERATOR_PROMPT
    if profile:
        system += f"\n\n<已知用户画像>\n{profile}\n</已知用户画像>"
    user_msg = (
        f"用户原始问题：{user_input}\n\n"
        f"以下是三位专家对本场比赛的独立分析意见：\n\n{takes_joined}\n\n"
        f"请综合这些意见，给出最终预测。"
    )
    async for delta in moderator_client.stream(
        [{"role": "user", "content": user_msg}], system, max_tokens=max_tokens
    ):
        yield {"type": "token", "text": delta}
