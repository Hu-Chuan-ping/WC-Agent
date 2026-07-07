from __future__ import annotations

import contextvars

# 请求级"待入库预测"暂存：PredictorAgent 产出结构化预测后 stash 进来，
# DispatchService 在 route 返回后 take 出来、补上 user_id/session_id 再入库。
# 用 contextvar：agent.run 与 dispatch 在同一 async 任务链里，set 后父级可见。
_pending: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "pending_prediction", default=None
)


def stash(record: dict) -> None:
    _pending.set(record)


def take() -> dict | None:
    """取出并清空。"""
    rec = _pending.get()
    if rec is not None:
        _pending.set(None)
    return rec
