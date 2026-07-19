from __future__ import annotations

import uuid

from app.config.settings import settings
from app.core.memory import budget, long_term, short_term
from app.infra.repositories import conversation_repository as repo
from app.utils.exceptions import NotFoundError

# 会话应用服务：编排“新建/列出/查看/重命名/删除”用例，并做归属校验。
# 归属校验是真正的安全防线：任何按 session_id 的操作都先确认它属于当前用户。

_TITLE_MAX = 20


def _make_title(text: str) -> str:
    t = text.strip().replace("\n", " ")
    return t[:_TITLE_MAX] or "新对话"


async def _assert_owner(user_id: str, session_id: str) -> dict:
    """确认会话存在且属于该用户，返回会话行；否则 404（不泄露是否存在）。"""
    s = await repo.get_session(session_id)
    if s is None or s["user_id"] != user_id:
        raise NotFoundError("会话不存在")
    return s


async def create_session(user_id: str) -> dict:
    """新建一个空会话。"""
    session_id = uuid.uuid4().hex
    await repo.create_session(session_id, user_id)
    return {"session_id": session_id, "title": "新对话"}


async def list_sessions(user_id: str) -> list[dict]:
    return await repo.list_sessions(user_id)


async def get_messages(user_id: str, session_id: str) -> list[dict]:
    await _assert_owner(user_id, session_id)
    return await repo.list_messages(session_id)


async def rename_session(user_id: str, session_id: str, title: str) -> None:
    await _assert_owner(user_id, session_id)
    await repo.rename_session(session_id, title.strip() or "新对话")


async def delete_session(user_id: str, session_id: str) -> None:
    await _assert_owner(user_id, session_id)
    await repo.delete_messages(session_id)
    await repo.delete_session(session_id)
    await short_term.clear(session_id)  # 一并清掉 Redis 热窗口


# ── 供 dispatch 复用的两个方法 ──────────────────────────────

async def ensure_session(user_id: str, session_id: str | None) -> str:
    """发消息前确保有一个属于该用户的会话：传了就校验归属，没传就新建。"""
    if session_id:
        await _assert_owner(user_id, session_id)
        return session_id
    new_id = uuid.uuid4().hex
    await repo.create_session(new_id, user_id)
    return new_id


async def compute_context_stats(session_id: str, user_id: str | None) -> dict:
    """当前会话上下文占用（历史窗口 + 画像的 token）/ 模型窗口。供 done 事件与圆环接口。"""
    history = await short_term.load_history(session_id)
    profile = await long_term.get_profile(user_id) if user_id else ""
    return {
        "context_tokens": budget.context_tokens(history, profile),
        "max_context": settings.model_context_window,
        "model": settings.deepseek_model,
    }


async def context_stats(user_id: str, session_id: str) -> dict:
    """带归属校验的版本，供 /sessions/context 接口。"""
    await _assert_owner(user_id, session_id)
    return await compute_context_stats(session_id, user_id)


async def record_turn(
    session_id: str,
    user_msg: str,
    assistant_msg: str,
    assistant_meta: dict | None = None,
) -> None:
    """把一轮对话持久化进 messages；首轮用问题生成标题；刷新活跃时间。

    assistant_meta：助手消息的结构化附件（如专家会诊 {"experts":[...]}），可空。
    """
    await repo.add_message(session_id, "user", user_msg)
    await repo.add_message(session_id, "assistant", assistant_msg, assistant_meta)
    s = await repo.get_session(session_id)
    if s and (not s["title"] or s["title"] == "新对话"):
        await repo.rename_session(session_id, _make_title(user_msg))
    await repo.touch_session(session_id)
