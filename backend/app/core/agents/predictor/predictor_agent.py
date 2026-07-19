from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator

from app.config.agent_config import AgentConfig
from app.core.agents.base_agent import BaseAgent
from app.config.settings import settings
from app.core.agents.predictor.prompts import SYSTEM_PROMPT
from app.core.agents.predictor.roundtable import run_roundtable
from app.core.eval import pending
from app.core.eval.fixtures import find_match
from app.core.tools.odds import OddsTool
from app.core.tools.odds_mcp import McpOddsTool
from app.core.tools.rag_search import RagSearchTool
from app.core.tools.team_info import TeamInfoTool
from app.core.tools.web_search import WebSearchTool
from app.utils import request_stats
from app.utils.logger import logger
from app.utils.teammatch import same_team

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
        # 赔率工具按开关选：MCP 版(走 odds_server) 或 进程内版。两者接口一致，pipeline 无感。
        self.register_tool(McpOddsTool() if settings.use_mcp_odds else OddsTool())
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

        # 定位到 football-data 的这场比赛（拿 match_id + 状态；查不到则无法入库评估）
        match = await find_match(teams["home_en"], teams["away_en"])

        # 赛前 / 进行中 / 已结束 三态分流（防止给已踢完的比赛做假预测污染评估）
        if match and match["status"] == "FINISHED":
            hg, ag, ph, pa = self._orient_result(match)
            pen = f"（点球 {ph}-{pa}）" if ph is not None else ""
            logger.info(f"[pipeline] 该场已结束 {teams['home_cn']} {hg}-{ag} {teams['away_cn']}，跳过预测")
            yield {"type": "token", "text": (
                f"这场比赛**已经结束**了：**{teams['home_cn']} {hg} - {ag} {teams['away_cn']}**{pen}。\n\n"
                f"所以我不再做赛前预测（也不会计入评估）。想让我复盘这场，或预测别的比赛，随时说。"
            )}
            return
        live = bool(match and match["status"] in ("IN_PLAY", "PAUSED"))

        request_stats.start()
        try:
            logger.info(f"[pipeline] 对阵 {teams['home_cn']} vs {teams['away_cn']}（{'进行中' if live else '赛前'}）")
            if live:
                lhg, lag, _, _ = self._orient_result(match)
                yield {"type": "status", "text":
                       f"⚠️ 比赛进行中（当前 {lhg}-{lag}），"
                       f"以下为临场分析，不计入评估"}
            yield {"type": "status",
                   "text": f"正在并行收集 {teams['home_cn']} vs {teams['away_cn']} 的数据…"}
            slices, odds_data = await self._gather_context(teams)

            # 圆桌：三专家并行会诊 → 主持人流式合成。
            # status/expert 事件直接透传；主持人 token 沿用同一套 ```json 过滤后再输出。
            full, emitted = "", 0
            async for ev in run_roundtable(
                slices, self.client, user_input, profile, self._max_tokens
            ):
                if ev["type"] != "token":
                    yield ev                       # status / expert 卡片，原样透传
                    continue
                full += ev["text"]
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
            elif match is None:
                logger.info("[pipeline] football-data 查不到该场赛程（无 match_id），不入库")
            else:
                self._stash_prediction(teams, match, odds_data, structured)  # 赛前才入库
        finally:
            logger.info(request_stats.summary())

    # ② 并行抓全维数据（赔率取结构化，既拼文本又留数字入库）
    async def _gather_context(self, t: dict) -> tuple[dict, dict | None]:
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

        # 按维度切片，分发给对应专家（key 与 roundtable.SPECIALISTS 的 name 对齐）。
        # 不再拼成一个大 context——每个专家只吃自己那一片（上下文隔离）。
        slices = {
            "status": (
                f"## 主队 {home_cn}（{home_en}）结构化数据\n{ti_home}\n\n"
                f"## 客队 {away_cn}（{away_en}）结构化数据\n{ti_away}\n\n"
                f"## 最新动态（首发/伤病，来自搜索）\n{web}"
            ),
            "history": f"## 历史交锋（来自历史知识库）\n{history}",
            "market": f"## 市场赔率与隐含概率\n{odds_text}",
        }
        return slices, odds_data

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
    def _orient_result(match: dict) -> tuple:
        """把 football 原生赛果对齐到【用户的主/客方向】，返回 (home_goals, away_goals, pen_home, pen_away)。"""
        if match.get("user_is_home", True):
            return match["home_goals"], match["away_goals"], match["pen_home"], match["pen_away"]
        return match["away_goals"], match["home_goals"], match["pen_away"], match["pen_home"]

    @staticmethod
    def _flip_score(s: str) -> str:
        """把 "2-1" 翻转成 "1-2"（用户主客与 football 相反时用）。"""
        if isinstance(s, str) and "-" in s:
            a, b = s.split("-", 1)
            return f"{b.strip()}-{a.strip()}"
        return s

    @staticmethod
    def _parse_prediction(text: str) -> dict | None:
        """从回答里抠出机器 JSON，校验并归一化 1x2 概率 + 比分分布。失败返回 None（不入库）。"""
        blocks = re.findall(r"```json\s*(.*?)```", text, re.DOTALL)  # 含嵌套数组，取整块
        raw = blocks[-1].strip() if blocks else None
        if not raw:  # 容错：没套 fence，取第一个 { 到最后一个 }
            i, j = text.find("{"), text.rfind("}")
            raw = text[i:j + 1] if i >= 0 and j > i else None
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

        dist = d.get("score_dist")
        clean: list[dict] = []
        if isinstance(dist, list):
            for x in dist:
                if isinstance(x, dict) and x.get("score"):
                    try:
                        clean.append({"score": str(x["score"]), "p": float(x.get("p", 0))})
                    except (ValueError, TypeError):
                        continue
        clean = [x for x in clean if x["p"] > 0]
        tot = sum(x["p"] for x in clean)
        if tot > 0:
            for x in clean:
                x["p"] = round(x["p"] / tot, 4)
        clean.sort(key=lambda x: x["p"], reverse=True)
        d["score_dist"] = clean
        return d

    def _stash_prediction(
        self, teams: dict, match: dict, odds_data: dict | None, structured: dict | None
    ) -> None:
        """把预测规范化到 football 原生主客方向，暂存交给 dispatch 写 matches/match_predictions/user_match。"""
        if structured is None:
            logger.warning("[pipeline] 预测未产出结构化 JSON，跳过入库")
            return
        uih = match.get("user_is_home", True)

        # agent 概率对齐到 football 主客
        p_home = structured["p_home"] if uih else structured["p_away"]
        p_away = structured["p_away"] if uih else structured["p_home"]
        dist = [
            {"score": s if uih else self._flip_score(s), "p": x["p"]}
            for x in structured["score_dist"] for s in [x["score"]]
        ]
        top_score = dist[0]["score"] if dist else None

        # 赔率概率对齐到 football 主客（OddsTool 按赔率商的 home 给，未必同向）
        oprobs = (odds_data or {}).get("probs") or {}
        if oprobs and (odds_data or {}).get("home_team") \
                and not same_team(odds_data["home_team"], match["home_team"]):
            oprobs = {"home": oprobs.get("away"), "draw": oprobs.get("draw"), "away": oprobs.get("home")}

        extra = {k: structured[k] for k in ("total_goals", "btts") if k in structured}
        match_rec = {
            "match_id": match["match_id"], "competition": match.get("competition", "WC"),
            "home_team": match["home_team"], "away_team": match["away_team"],
            "home_cn": teams["home_cn"] if uih else teams["away_cn"],
            "away_cn": teams["away_cn"] if uih else teams["home_cn"],
            "kickoff_time": match.get("kickoff_time"), "status": match.get("status"),
            "duration": match.get("duration"),
        }
        pred_rec = {
            "p_home": p_home, "p_draw": structured["p_draw"], "p_away": p_away,
            "score_dist": json.dumps(dist, ensure_ascii=False), "top_score": top_score,
            "odds_p_home": oprobs.get("home"), "odds_p_draw": oprobs.get("draw"),
            "odds_p_away": oprobs.get("away"),
            "extra_json": json.dumps(extra, ensure_ascii=False),
        }
        pending.stash({"match": match_rec, "prediction": pred_rec})
        logger.info(f"[pipeline] 权威预测已暂存 match_id={match['match_id']}，待入库")
