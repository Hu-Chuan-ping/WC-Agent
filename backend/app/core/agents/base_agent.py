from __future__ import annotations

import asyncio
from abc import ABC
from collections.abc import AsyncIterator

from app.config.agent_config import AgentConfig
from app.core.models import LLMResponse, ToolCall
from app.core.tools.base_tool import BaseTool
from app.infra.llm.client import LLMClient
from app.utils import request_stats
from app.utils.exceptions import AppError, ConfigError
from app.utils.logger import logger


class BaseAgent(ABC):
    """
    所有 Agent 的抽象基类。

    子类需定义类属性 name、description，
    在 __init__ 中传入 system_prompt 和 AgentConfig。
    """

    name: str
    description: str

    def __init__(self, system_prompt: str, config: AgentConfig | None = None):
        cfg = config or AgentConfig()
        self.system_prompt = system_prompt
        self.max_iterations = cfg.max_iterations
        self.client = LLMClient(model=cfg.model, temperature=cfg.temperature)
        self._max_tokens = cfg.max_tokens
        self._tools: dict[str, BaseTool] = {}
        self._tool_schemas: list[dict] = []

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        self._tool_schemas.append(tool.to_schema())

    async def run(
        self,
        user_input: str,
        history: list[dict] | None = None,
        profile: str = "",
    ) -> str:
        """执行一轮对话，内部自动处理 ReAct 工具调用循环。

        history：之前的对话消息（多轮记忆）；profile：用户长期画像。
        """
        request_stats.start()  # 初始化本次对话的统计
        logger.info(f"Agent[{self.name}] 开始处理")
        system_prompt = self._compose_system(profile)
        messages: list[dict] = list(history or [])   # 历史消息在前
        messages.append({"role": "user", "content": user_input})

        try:
            for _ in range(self.max_iterations):
                response: LLMResponse = await self.client.complete(
                    messages=messages,
                    system=system_prompt,
                    tools=self._tool_schemas or None,
                    max_tokens=self._max_tokens,
                )

                if response.stop_reason == "end_turn":
                    # 模型偶发返回空正文（已在 client 记警告），给用户明确提示而非空白
                    return response.text or "（模型本次未返回内容，请重试或调整问法。）"

                if response.stop_reason == "tool_use":
                    if response.assistant_turn:
                        messages.append(response.assistant_turn)
                    messages.extend(await self._execute_tools(response.tool_calls))
                    continue

                return response.text

            return "已达到最大迭代次数，未能得到最终答案。"
        finally:
            # 无论正常返回还是异常，都打一条本次对话的工具/额度汇总
            logger.info(request_stats.summary())

    # 工具调用时给前端看的进度文案
    _TOOL_STATUS = {
        "search_web": "🔎 正在检索最新消息…",
        "search_history": "📚 正在查历史交锋…",
        "get_my_predictions": "🗂 正在查你的历史预测…",
    }

    async def run_stream(
        self,
        user_input: str,
        history: list[dict] | None = None,
        profile: str = "",
    ) -> AsyncIterator[dict]:
        """流式对话。无工具 → 逐 token 流；有工具 → 流式 ReAct（调工具推进度、答案逐字流）。"""
        request_stats.start()
        try:
            system_prompt = self._compose_system(profile)
            messages: list[dict] = list(history or [])
            messages.append({"role": "user", "content": user_input})

            if not self._tool_schemas:
                async for delta in self.client.stream(
                    messages, system_prompt, max_tokens=self._max_tokens
                ):
                    yield {"type": "token", "text": delta}
                return

            for _ in range(self.max_iterations):
                tool_calls = None
                assistant_turn = None
                async for ev in self.client.stream_events(
                    messages, system_prompt, tools=self._tool_schemas, max_tokens=self._max_tokens
                ):
                    if ev["type"] == "token":
                        yield {"type": "token", "text": ev["text"]}
                    elif ev["type"] == "tool_calls":
                        tool_calls = ev["tool_calls"]
                        assistant_turn = ev["assistant_turn"]

                if not tool_calls:
                    return  # 模型给了最终答案，已逐字流出

                for tc in tool_calls:
                    yield {"type": "status", "text": self._TOOL_STATUS.get(tc.name, f"正在调用 {tc.name}…")}
                if assistant_turn:
                    messages.append(assistant_turn)
                messages.extend(await self._execute_tools(tool_calls))

            yield {"type": "token", "text": "（已达到最大迭代次数，未能得到最终答案。）"}
        finally:
            logger.info(request_stats.summary())

    def _compose_system(self, profile: str) -> str:
        """把用户长期画像拼进 system prompt。"""
        if profile:
            return f"{self.system_prompt}\n\n<已知用户画像>\n{profile}\n</已知用户画像>"
        return self.system_prompt

    async def _execute_tools(self, tool_calls: list[ToolCall]) -> list[dict]:
        """并发执行本轮所有工具调用，结果顺序与入参一致。

        模型一次可能请求多个工具，gather 让这些网络/IO 调用并行，
        总耗时取决于最慢的那个，而非逐个相加。
        """
        results = await asyncio.gather(
            *(self._run_one_tool(tc) for tc in tool_calls)
        )
        return list(results)

    async def _run_one_tool(self, tc: ToolCall) -> dict:
        request_stats.record_tool_call(tc.name)
        tool = self._tools.get(tc.name)
        if tool is None:
            logger.warning(f"工具未注册：{tc.name}")
            content = f"错误：工具 '{tc.name}' 未注册。"
        else:
            logger.info(f"调用工具 {tc.name} args={tc.input}")
            try:
                content = str(await tool.run(**tc.input))
                logger.info(f"工具 {tc.name} 执行完成")
            except ConfigError:
                # 配置类错误 LLM 无法重试修复，直接上抛，中断整个请求
                raise
            except AppError as exc:
                # 其余业务异常（如外部服务暂时失败）反馈给 LLM，让它自行调整
                # detail 只进日志（含技术细节），不回传给 LLM/前端
                detail = f" | detail={exc.detail}" if exc.detail else ""
                logger.warning(f"工具 {tc.name} 业务异常：{exc.message}{detail}")
                content = f"工具 '{tc.name}' 执行出错：{exc.message}"
            except Exception as exc:
                logger.exception(f"工具 {tc.name} 未预期异常")
                content = f"工具 '{tc.name}' 执行出错：{exc}"

        return {
            "role": "tool",
            "tool_call_id": tc.id,
            "content": content,
        }
