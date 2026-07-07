from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator

from app.config.agent_config import AgentConfig
from app.core.agents.base_agent import BaseAgent
from app.core.agents.predictor.prompts import PIPELINE_SYSTEM_PROMPT, SYSTEM_PROMPT
from app.core.eval import pending
from app.core.eval.fixtures import match_state
from app.core.tools.odds import OddsTool
from app.core.tools.rag_search import RagSearchTool
from app.core.tools.team_info import TeamInfoTool
from app.core.tools.web_search import WebSearchTool
from app.utils import request_stats
from app.utils.logger import logger

PREDICTOR_CONFIG = AgentConfig(
    temperature=0.3,
    # deepseek-v4-pro 是推理模型：max_tokens 要同时容纳「思考(reasoning) + 正文」。
    max_tokens=8192,
    max_iterations=8,   # 仅在回退 ReAct 时用到
)


class PredictorAgent(BaseAgent):
    """世界杯比分预测 Agent。

    用【确定性 pipeline】而非 ReAct：解析队名 → 并行抓全维数据 → 单次预测。
    原因：预测是已知流程，每次都要全套数据。pipeline 只需 2 次 LLM 调用（解析+预测），
    比 ReAct 的 N+1 次快且省，且绝不会漏调工具。
    无法识别出两支球队时，回退到 BaseAgent 的 ReAct 循环。
    """

    name = "predictor"
    description = "2026 世界杯比分预测，根据球队数据、历史交手、赔率给出比分与胜负概率"

    def __init__(self):
        super().__init__(system_prompt=SYSTEM_PROMPT, config=PREDICTOR_CONFIG)
        # 工具照常注册：pipeline 里由代码固定调用，回退 ReAct 时由 LLM 调用
        self.register_tool(TeamInfoTool())
        self.register_tool(WebSearchTool())
        self.register_tool(OddsTool())
        self.register_tool(RagSearchTool())

    async def run(
        self,
        user_input: str,
        history: list[dict] | None = None,
        profile: str = "",
        teams: dict | None = None,
    ) -> str:
        """非流式：收集 run_stream 的 token 事件拼成完整回答。"""
        parts: list[str] = []
        async for ev in self.run_stream(user_input, history, profile, teams):
            if ev["type"] == "token":
                parts.append(ev["text"])
        return "".join(parts)

    async def run_stream(
        self,
        user_input: str,
        history: list[dict] | None = None,
        profile: str = "",
        teams: dict | None = None,
    ) -> AsyncIterator[dict]:
        """流式：全新预测走确定性 pipeline（状态事件 + 流式预测）；否则回退 ReAct。

        teams 由上游 interpreter 抽好传入（已合并原来的 extract 调用）。
        """
        if teams is None:
            # 追问/窄问题/闲聊 → ReAct（带历史/画像），整段作为单个事件
            logger.info("非全新比赛预测 → ReAct（带历史/画像）")
            answer = await super().run(user_input, history, profile)
            yield {"type": "token", "text": answer}
            return

        # 赛前 / 进行中 / 已结束 三态分流（防止给已踢完的比赛做假预测污染评估）
        state = await match_state(teams["home_en"], teams["away_en"])
        if state and state["status"] == "FINISHED":
            hg, ag = state["home_goals"], state["away_goals"]
            logger.info(f"[pipeline] 该场已结束 {teams['home_cn']} {hg}-{ag} {teams['away_cn']}，跳过预测")
            yield {"type": "token", "text": (
                f"这场比赛**已经结束**了：**{teams['home_cn']} {hg} - {ag} {teams['away_cn']}**。\n\n"
                f"所以我不再做赛前预测（也不会计入评估）。想让我复盘这场，或预测别的比赛，随时说。"
            )}
            return
        live = bool(state and state["status"] in ("IN_PLAY", "PAUSED"))

        request_stats.start()
        try:
            logger.info(f"[pipeline] 对阵 {teams['home_cn']} vs {teams['away_cn']}（{'进行中' if live else '赛前'}）")
            if live:
                yield {"type": "status", "text":
                       f"⚠️ 比赛进行中（当前 {state['home_goals']}-{state['away_goals']}），"
                       f"以下为临场分析，不计入评估"}
            yield {"type": "status",
                   "text": f"正在并行收集 {teams['home_cn']} vs {teams['away_cn']} 的数据…"}
            context, odds_data = await self._gather_context(teams)

            yield {"type": "status", "text": "数据就绪，正在分析预测…"}

            # 流式预测：边流边攒完整原文；只输出 ```json 机器块之前的内容
            system = PIPELINE_SYSTEM_PROMPT
            if profile:
                system += f"\n\n<已知用户画像>\n{profile}\n</已知用户画像>"
            user_msg = (
                f"请预测这场比赛：{teams['home_cn']} vs {teams['away_cn']}\n"
                f"（用户原始问题：{user_input}）\n\n"
                f"以下是已为你收集好的多维数据：\n\n{context}"
            )
            full, emitted = "", 0
            async for delta in self.client.stream(
                [{"role": "user", "content": user_msg}], system,
                max_tokens=self._max_tokens,
            ):
                full += delta
                idx = full.find("```json")
                # 没出现 fence 时保留末尾 7 字，防半个 ```json 泄给用户
                visible = full[:idx] if idx >= 0 else (full[:-7] if len(full) > 7 else "")
                if len(visible) > emitted:
                    yield {"type": "token", "text": visible[emitted:]}
                    emitted = len(visible)
            # 收尾：刷出保留的尾巴（真正 json 块之前的剩余内容）
            final_visible = full[: full.find("```json")] if "```json" in full else full
            if len(final_visible) > emitted:
                yield {"type": "token", "text": final_visible[emitted:]}

            structured = self._parse_prediction(full)
            if live:
                logger.info("[pipeline] 比赛进行中，本次分析不入库（避免污染赛前评估）")
            else:
                self._stash_prediction(teams, odds_data, structured)  # 只有赛前才入库
        finally:
            logger.info(request_stats.summary())

    # ② 并行抓全维数据（赔率取结构化，既拼文本又留数字入库）
    async def _gather_context(self, t: dict) -> tuple[str, dict | None]:
        home_en, away_en = t["home_en"], t["away_en"]
        home_cn, away_cn = t["home_cn"], t["away_cn"]

        ti_home, ti_away, web, history, odds_data = await asyncio.gather(
            self._call_tool("get_team_info", team_name=home_en),
            self._call_tool("get_team_info", team_name=away_en),
            self._call_tool(
                "search_web",
                query=f"{home_cn} {away_cn} 2026世界杯 首发 伤病 最新",
                max_results=5,
            ),
            self._call_tool("search_history", query=f"{home_cn} {away_cn} 历史交锋",
                            team_a=home_cn, team_b=away_cn),
            self._fetch_odds_structured(home_en, away_en),
        )
        odds_text = (
            self._tools["get_match_odds"].format_text(odds_data)
            if odds_data else "（未找到该场比赛的市场赔率）"
        )

        context = (
            f"## 主队 {home_cn}（{home_en}）结构化数据\n{ti_home}\n\n"
            f"## 客队 {away_cn}（{away_en}）结构化数据\n{ti_away}\n\n"
            f"## 最新动态（首发/伤病，来自搜索）\n{web}\n\n"
            f"## 历史交锋（来自历史知识库）\n{history}\n\n"
            f"## 市场赔率与隐含概率\n{odds_text}"
        )
        return context, odds_data

    async def _fetch_odds_structured(self, home_en: str, away_en: str) -> dict | None:
        request_stats.record_tool_call("get_match_odds")
        logger.info(f"[pipeline] 调用 get_match_odds(结构化) {home_en} vs {away_en}")
        try:
            return await self._tools["get_match_odds"].probabilities(home_en, away_en)
        except Exception as exc:
            logger.warning(f"[pipeline] get_match_odds 失败：{exc}")
            return None

    async def _call_tool(self, name: str, **kwargs) -> str:
        """固定调用某个工具；记录统计；单个失败降级为提示，不影响其余维度。"""
        request_stats.record_tool_call(name)
        logger.info(f"[pipeline] 调用 {name} {kwargs}")
        try:
            return str(await self._tools[name].run(**kwargs))
        except Exception as exc:
            logger.warning(f"[pipeline] {name} 失败：{exc}")
            return f"（{name} 数据获取失败：{exc}）"

    @staticmethod
    def _parse_prediction(text: str) -> dict | None:
        """从回答里抠出机器 JSON，校验并归一化概率。失败返回 None（不入库）。"""
        blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        raw = blocks[-1] if blocks else None
        if raw is None:  # 容错：模型没套 ```json，就找含 p_home 的裸 JSON
            m = re.search(r"\{[^{}]*p_home[^{}]*\}", text, re.DOTALL)
            raw = m.group(0) if m else None
        if not raw:
            return None
        try:
            d = json.loads(raw)
            ph, pd, pa = float(d["p_home"]), float(d["p_draw"]), float(d["p_away"])
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            return None
        s = ph + pd + pa
        if s <= 0:
            return None
        d["p_home"], d["p_draw"], d["p_away"] = ph / s, pd / s, pa / s  # 归一化
        return d

    def _stash_prediction(
        self, teams: dict, odds_data: dict | None, structured: dict | None
    ) -> None:
        """把结构化预测暂存到 contextvar，交给 dispatch 补 user_id/session_id 后入库。"""
        if structured is None:
            logger.warning("[pipeline] 预测未产出结构化 JSON，跳过入库")
            return
        odds_probs = (odds_data or {}).get("probs") or {}
        extra = {k: structured[k] for k in ("total_goals", "btts") if k in structured}
        pending.stash({
            "home_team": teams["home_en"], "away_team": teams["away_en"],
            "home_cn": teams["home_cn"], "away_cn": teams["away_cn"],
            "kickoff_time": (odds_data or {}).get("commence_time"),
            "agent_p_home": structured["p_home"], "agent_p_draw": structured["p_draw"],
            "agent_p_away": structured["p_away"], "agent_score": structured.get("score"),
            "odds_p_home": odds_probs.get("home"), "odds_p_draw": odds_probs.get("draw"),
            "odds_p_away": odds_probs.get("away"),
            "extra_json": json.dumps(extra, ensure_ascii=False),
        })
        logger.info("[pipeline] 结构化预测已暂存，待入库")
