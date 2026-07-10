from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
from openai import AsyncOpenAI

from app.config.settings import settings
from app.core.models import LLMResponse, ToolCall
from app.utils.exceptions import LLMError
from app.utils.logger import logger

# 大模型网关：DeepSeek（OpenAI 兼容接口）的封装。属于“对外集成”，归 infra 层。

# 按 (api_key, base_url) 缓存 AsyncOpenAI：同一提供商复用连接池；
# 快模型若用不同 key/base 则各持一个。
_shared_clients: dict[tuple[str, str], AsyncOpenAI] = {}


def _get_openai(api_key: str, base_url: str) -> AsyncOpenAI:
    key = (api_key, base_url)
    if key not in _shared_clients:
        # trust_env=False：忽略系统代理，DeepSeek 是国内服务，走代理反而会 SSL 失败
        _shared_clients[key] = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.AsyncClient(trust_env=False),
        )
    return _shared_clients[key]


class LLMClient:
    """
    DeepSeek（OpenAI 兼容接口）的轻量封装。

    负责三件事：
    1. 将内部工具 schema 转换为 OpenAI function calling 格式
    2. 发送请求
    3. 将响应归一化为 LLMResponse，Agent 不感知具体提供商
    """

    _FALLBACK_TEMPERATURE = 0.7

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self._openai = _get_openai(
            api_key or settings.deepseek_api_key,
            base_url or settings.deepseek_base_url,
        )
        self.model = model or settings.deepseek_model
        self.temperature = temperature if temperature is not None else self._FALLBACK_TEMPERATURE

    async def complete(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        all_messages = [{"role": "system", "content": system}] + messages

        kwargs: dict = {
            "model": self.model,
            "messages": all_messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"

        try:
            response = await self._openai.chat.completions.create(**kwargs)
        except Exception as exc:
            # 超时、限流、鉴权失败等统一翻译为 LLMError；原始细节进日志
            raise LLMError(detail=str(exc)) from exc
        return self._normalize(response)

    async def stream(
        self, messages: list[dict], system: str, max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        """流式生成，逐段 yield 正文 delta（不支持工具调用；推理模型的思考段不输出）。"""
        all_messages = [{"role": "system", "content": system}] + messages
        try:
            stream = await self._openai.chat.completions.create(
                model=self.model,
                messages=all_messages,
                temperature=self.temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            raise LLMError(detail=str(exc)) from exc

    async def stream_events(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[dict]:
        """流式生成，同时支持工具调用（供流式 ReAct 用）。

        产出事件：
          {"type": "token", "text": ...}                     正文逐段
          {"type": "tool_calls", "tool_calls": [...],        本轮模型请求调工具
                                  "assistant_turn": {...}}    （在流结束时一次性给出）
        无工具调用时只有 token 事件；有则最后追加一个 tool_calls 事件。
        """
        all_messages = [{"role": "system", "content": system}] + messages
        kwargs: dict = {
            "model": self.model,
            "messages": all_messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"

        content_parts: list[str] = []
        # 工具调用分片按 index 累积：{index: {"id","name","args"}}
        acc: dict[int, dict] = {}
        try:
            stream = await self._openai.chat.completions.create(**kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                    yield {"type": "token", "text": delta.content}
                for tcd in delta.tool_calls or []:
                    slot = acc.setdefault(tcd.index, {"id": None, "name": None, "args": ""})
                    if tcd.id:
                        slot["id"] = tcd.id
                    if tcd.function and tcd.function.name:
                        slot["name"] = tcd.function.name
                    if tcd.function and tcd.function.arguments:
                        slot["args"] += tcd.function.arguments
        except Exception as exc:
            raise LLMError(detail=str(exc)) from exc

        if acc:
            tool_calls = [
                ToolCall(id=s["id"], name=s["name"], input=json.loads(s["args"] or "{}"))
                for s in acc.values()
            ]
            assistant_turn = {
                "role": "assistant",
                "content": "".join(content_parts) or None,
                "tool_calls": [
                    {
                        "id": s["id"],
                        "type": "function",
                        "function": {"name": s["name"], "arguments": s["args"] or "{}"},
                    }
                    for s in acc.values()
                ],
            }
            yield {"type": "tool_calls", "tool_calls": tool_calls, "assistant_turn": assistant_turn}

    def _to_openai_tools(self, tools: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    def _normalize(self, response) -> LLMResponse:
        choice = response.choices[0]
        msg = choice.message
        content = msg.content or ""

        if choice.finish_reason == "length":
            logger.warning(
                "LLM 输出被 max_tokens 截断（finish_reason=length），回答可能不完整，"
                "建议调大该 Agent 的 max_tokens"
            )

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments),
                )
                for tc in msg.tool_calls
            ]
            assistant_turn = {
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
            return LLMResponse(
                text=content,
                stop_reason="tool_use",
                tool_calls=tool_calls,
                assistant_turn=assistant_turn,
            )

        # 普通结束：若正文为空，记录诊断信息（finish_reason + 思考字段长度）
        if not content:
            reasoning = getattr(msg, "reasoning_content", None)
            logger.warning(
                f"LLM 返回空内容！finish_reason={choice.finish_reason}，"
                f"reasoning_content 长度={len(reasoning) if reasoning else 0}"
            )

        return LLMResponse(
            text=content,
            stop_reason="end_turn",
            assistant_turn={"role": "assistant", "content": content},
        )


def get_fast_client() -> LLMClient:
    """快模型客户端（意图理解/抽取等轻任务）。fast_api_key 留空则复用主 DeepSeek key。"""
    return LLMClient(
        model=settings.fast_model,
        temperature=0.0,
        api_key=settings.fast_api_key or None,
        base_url=settings.fast_base_url or None,
    )
