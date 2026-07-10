from __future__ import annotations

import contextvars

# 请求级上下文：把"当前是哪个用户"放进 contextvar，供工具（如 get_my_predictions）读取。
# 工具的参数由 LLM 填、不含 user_id，故用 contextvar 从请求链路透传，避免串号。
# 在 dispatch 入口 set，agent/工具（含 gather 子任务，创建时复制上下文）都能读到。
_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_user_id", default=None
)


def set_current_user(user_id: str | None) -> None:
    _user_id.set(user_id)


def get_current_user_id() -> str | None:
    return _user_id.get()
