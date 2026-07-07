from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """一次工具调用请求，由 LLM 发出。"""

    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    """
    各提供商响应的统一格式，由 LLMClient 负责转换。
    Agent 只依赖这个结构，不感知具体提供商。

    stop_reason:
      "end_turn"  — 模型正常结束，读 text 即可
      "tool_use"  — 模型请求工具，读 tool_calls 并执行
    """

    text: str
    stop_reason: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    assistant_turn: dict | None = None
