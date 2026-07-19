from __future__ import annotations

from app.config.settings import settings
from app.core.memory import budget
from app.infra.llm.client import get_fast_client
from app.infra.repositories import session_repository
from app.utils.logger import logger

# 短期会话记忆（领域服务）：定义“一轮=用户+助手两条消息”、滑动窗口、TTL、
# 以及【滚动摘要压缩】策略；具体 Redis 存取交给 session_repository。
#
# 分层记忆的 L1(原文热窗口) + L2(滚动摘要)：
#   历史 token 超预算时，把较旧的几轮摘要成一段梗概（存 :sum 键），只保留最近 N 条原文。
#   load 时把「摘要 + 最近原文」一起喂 LLM——既控住 token，又不丢早期关键信息。

_SUMMARY_SYSTEM = """你是对话摘要助手。请把下面的[已有摘要]和[新增对话]合并、压缩成一段简洁的中文摘要。
保留关键事实：用户问过或预测过哪些比赛及结论、用户偏好、后续追问需要的上下文；去掉寒暄与冗余。
控制在 200 字以内，只输出摘要正文，不要任何前后缀。"""


async def load_history(session_id: str) -> list[dict]:
    """返回喂给 LLM 的历史：若有滚动摘要，则「摘要 + 最近原文」；否则就是原文。"""
    turns = await session_repository.load(session_id)
    summary = await session_repository.get_summary(session_id)
    if summary:
        return [
            {"role": "user", "content": f"【以下是我们此前对话的摘要，供你参考】\n{summary}"},
            {"role": "assistant", "content": "好的，我已了解此前对话的要点。"},
        ] + turns
    return turns


async def append_turn(session_id: str, user_msg: str, assistant_msg: str) -> None:
    """追加一轮（用户+助手）；续期并按 token 预算做滚动摘要压缩。"""
    messages = [
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": assistant_msg},
    ]
    await session_repository.append(
        session_id,
        messages,
        max_messages=settings.session_max_messages,   # 硬上限兜底
        ttl_seconds=settings.session_ttl_seconds,
    )
    await _maybe_compact(session_id)


async def _maybe_compact(session_id: str) -> None:
    """原文窗口 token 超预算 → 摘要最旧的几轮、只留最近 N 条。"""
    turns = await session_repository.load(session_id)
    if budget.messages_tokens(turns) <= settings.context_token_budget:
        return
    keep = settings.context_keep_recent
    if len(turns) <= keep:
        return                       # 条数不够可压
    old = turns[:-keep]              # 待摘要的旧消息
    prev = await session_repository.get_summary(session_id)
    try:
        new_summary = await _summarize(prev, old)
    except Exception:
        logger.warning(f"[context] 会话 {session_id} 滚动摘要失败，本次跳过压缩")
        return
    await session_repository.set_summary(session_id, new_summary, settings.session_ttl_seconds)
    await session_repository.trim_keep_last(session_id, keep, settings.session_ttl_seconds)
    logger.info(f"[context] 压缩会话 {session_id}：{len(old)} 条旧消息 → 摘要，保留最近 {keep} 条")


async def _summarize(prev_summary: str, old_messages: list[dict]) -> str:
    """用快模型把[已有摘要]+[新增旧对话]合并成新摘要。"""
    convo = "\n".join(
        f"{'用户' if m['role'] == 'user' else '助手'}：{m['content']}" for m in old_messages
    )
    user_content = f"[已有摘要]\n{prev_summary or '（无）'}\n\n[新增对话]\n{convo}"
    resp = await get_fast_client().complete(
        [{"role": "user", "content": user_content}], _SUMMARY_SYSTEM, max_tokens=400
    )
    return resp.text.strip()


async def clear(session_id: str) -> None:
    await session_repository.delete(session_id)
