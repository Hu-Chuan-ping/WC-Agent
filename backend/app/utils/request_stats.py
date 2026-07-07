from __future__ import annotations

import contextvars
from collections import Counter

# 请求级统计：每次 agent.run() 开始时初始化，工具调用次数 / API 剩余额度都写进同一个 dict。
# 用 contextvar 是为了让 asyncio.gather 出的子任务也能写进同一份统计——
# 子任务会复制父上下文，拿到的是同一个 dict 引用，原地修改对父任务可见。
# 注意：只在 start() 里 .set() 新 dict，其余地方只「原地修改」，不要再 .set()，
# 否则子任务里的 .set() 不会回传到父任务。
_stats: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "request_stats", default=None
)


def start() -> None:
    """一次请求/对话开始时调用，重置统计。"""
    _stats.set({"tools": Counter(), "quota": {}})


def record_tool_call(name: str) -> None:
    """记录一次工具调用。"""
    s = _stats.get()
    if s is not None:
        s["tools"][name] += 1


def record_quota(api: str, remaining) -> None:
    """记录某个限额 API 的最新剩余次数（remaining 为 None 时忽略）。"""
    s = _stats.get()
    if s is not None and remaining is not None:
        s["quota"][api] = remaining


def summary() -> str:
    """生成一行汇总文本，供日志输出。"""
    s = _stats.get()
    if not s:
        return "本次无工具调用统计"
    tools = "、".join(f"{k}×{v}" for k, v in s["tools"].items()) or "无"
    quota = "、".join(f"{k}={v}" for k, v in s["quota"].items()) or "无"
    return f"📊 本次工具调用：{tools} | 限额API剩余：{quota}"
