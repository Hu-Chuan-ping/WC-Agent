from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentConfig:
    """
    单个 Agent 的行为参数。

    model 默认为 None，表示使用 settings.deepseek_model 的全局配置。
    只有当某个 Agent 需要用不同模型时才显式指定。
    """

    temperature: float = 0.7
    max_tokens: int = 4096
    max_iterations: int = 10
    model: str | None = None
