from collections.abc import AsyncIterator

from app.core import request_context
from app.core.agents.general.general_agent import GeneralAgent
from app.core.agents.predictor.predictor_agent import PredictorAgent
from app.core.eval import pending
from app.core.interpreter import interpret
from app.core.memory import long_term, short_term
from app.core.router import Router
from app.infra.repositories import match_repository, user_match_repository
from app.services import conversation_service
from app.utils.logger import logged, logger


class DispatchService:
    """
    业务服务层：所有请求的汇总调度入口，桥接 HTTP 接口层和 Agent 核心层。

    接口层只传字符串进来，结果字符串出去；
    Agent 的初始化、路由注册等细节对接口层透明。
    """

    def __init__(self):
        self._router = self._build_router()

    @logged
    async def dispatch(
        self,
        question: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> tuple[str, str]:
        """非流式：收集流式事件拼成完整回答。"""
        parts: list[str] = []
        sid = session_id or ""
        async for ev in self.dispatch_stream(question, session_id, user_id):
            if ev["type"] == "token":
                parts.append(ev["text"])
            elif ev["type"] == "done":
                sid = ev["session_id"]
        return "".join(parts), sid

    async def dispatch_stream(
        self,
        question: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """流式主链路：加载记忆 → 一次理解(快模型) → 流式路由 → 存回 → done。

        事件类型：status（进度）/ token（回答分段）/ done（带 session_id）。
        """
        request_context.set_current_user(user_id)   # 供工具（get_my_predictions）按当前用户过滤
        # 确保会话存在且属于该用户（没传 session_id 就新建一个），再走后续流程
        session_id = await conversation_service.ensure_session(user_id, session_id)
        history = await short_term.load_history(session_id)
        profile = await long_term.get_profile(user_id) if user_id else ""

        yield {"type": "status", "text": "正在理解你的问题…"}
        interp = await interpret(question, history)         # 合并的意图理解+抽取（一次快模型）

        parts: list[str] = []
        experts: list[dict] = []           # 圆桌专家意见，随消息一起入库供历史回看
        async for ev in self._router.route_stream(question, history, profile, interp):
            if ev["type"] == "token":
                parts.append(ev["text"])
            elif ev["type"] == "expert":
                experts.append({"name": ev["name"], "title": ev["title"], "text": ev["text"]})
            yield ev
        answer = "".join(parts)
        meta = {"experts": experts} if experts else None

        await self._persist_prediction(user_id, session_id)         # 若本轮是预测，入库供赛后评估
        await short_term.append_turn(session_id, question, answer)  # Redis 热窗口（喂 LLM 上下文）
        await conversation_service.record_turn(session_id, question, answer, meta)  # MySQL 持久化（供查看历史）
        # done 带回当前上下文占用（供前端 token 圆环）；在压缩之后测，圆环能反映压缩效果
        stat = await conversation_service.compute_context_stats(session_id, user_id)
        yield {"type": "done", "session_id": session_id, **stat}

    async def _persist_prediction(self, user_id: str | None, session_id: str) -> None:
        """取出 predictor 暂存的权威预测，写 matches + match_predictions + user_match。失败不影响回答。"""
        rec = pending.take()
        if not rec:
            return
        try:
            match_id = rec["match"]["match_id"]
            await match_repository.upsert_match(rec["match"])            # 赛程事实（共享）
            await match_repository.upsert_prediction(match_id, rec["prediction"])  # 权威预测（一场一条）
            if user_id:
                await user_match_repository.link(user_id, match_id, session_id)    # 我问过这场
            m = rec["match"]
            logger.info(f"权威预测已入库 match_id={match_id}（{m.get('home_cn')} vs {m.get('away_cn')}）")
        except Exception:
            logger.exception("预测入库失败（不影响本次回答）")

    def _build_router(self) -> Router:
        router = Router()
        router.register(
            intent="predict",
            agent=PredictorAgent(),
            description="用户询问比赛预测、比分分析、胜负概率",
        )
        # 兜底：意图未命中时由 GeneralAgent 处理普通对话
        router.register(
            intent="general",
            agent=GeneralAgent(),
            description="闲聊、打招呼、开放性问题，或意图不明确的请求",
            default=True,
        )
        # 后续在这里注册更多路由：
        # router.register(
        #     intent="wikipedia",
        #     agent=WikipediaAgent(),
        #     description="用户想查询百科知识、人物、事件等",
        # )
        return router


# 模块级单例：DispatchService 及其下的 Router/Agent/Tool 全部无状态
# （history/profile 都是 run 的参数，统计走 contextvar），全应用共享一个即可，
# 避免每个请求重建整棵 agent 图。
_service: DispatchService | None = None


def get_dispatch_service() -> DispatchService:
    """FastAPI Depends 工厂：返回全局单例（懒加载）。"""
    global _service
    if _service is None:
        _service = DispatchService()
    return _service
