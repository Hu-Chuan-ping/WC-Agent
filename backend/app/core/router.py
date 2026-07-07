from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.agents.base_agent import BaseAgent
from app.utils.logger import logger


class Router:
    """
    意图路由器：把「理解结果」派发到对应 Agent（流式）。

    意图理解由 interpreter 一次快模型调用完成（见 DispatchService），
    Router 只负责根据结果选 agent 并透传 teams。
    """

    def __init__(self):
        self._routes: dict[str, BaseAgent] = {}
        self._descriptions: dict[str, str] = {}
        self._default_agent: BaseAgent | None = None

    def register(
        self,
        intent: str,
        agent: BaseAgent,
        description: str,
        default: bool = False,
    ) -> None:
        self._routes[intent] = agent
        self._descriptions[intent] = description
        if default:
            self._default_agent = agent

    async def route_stream(
        self,
        user_input: str,
        history: list[dict] | None,
        profile: str,
        interp: dict,
    ) -> AsyncIterator[dict]:
        """按理解结果流式派发。interp = {"route","teams"}。"""
        route, teams = interp.get("route"), interp.get("teams")

        if route == "predict" and "predict" in self._routes:
            agent = self._routes["predict"]
            logger.info(f"路由=predict（teams={'有' if teams else '无'}）→ {agent.name}")
            async for ev in agent.run_stream(user_input, history, profile, teams):
                yield ev
            return

        agent = self._default_agent or next(iter(self._routes.values()))
        logger.info(f"路由=chat → {agent.name}")
        async for ev in agent.run_stream(user_input, history, profile):
            yield ev
