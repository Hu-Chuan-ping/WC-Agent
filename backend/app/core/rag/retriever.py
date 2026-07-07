from __future__ import annotations

from app.config.settings import settings
from app.core.rag import embedder
from app.infra.repositories import vector_repository as vector_store
from app.utils.logger import logger
from app.utils.teammatch import same_team


def _both_teams(meta: dict, a: str, b: str) -> bool:
    """这条比赛是否正是 a vs b 的交锋（忽略主客顺序，容忍队名词序/子集）。"""
    home, away = meta.get("home", ""), meta.get("away", "")
    return (
        (same_team(home, a) and same_team(away, b))
        or (same_team(home, b) and same_team(away, a))
    )


def _format(items: list[tuple]) -> str:
    return "\n\n".join(
        f"【{m.get('year')} {m.get('stage')} {m.get('home')} {m.get('score')} {m.get('away')}】\n{doc[:600]}"
        for doc, m, _ in items
    )


def retrieve(
    query: str,
    team_a: str | None = None,
    team_b: str | None = None,
    top_k: int | None = None,
) -> str:
    """两阶段检索：向量搜宽候选 → 若给了两队则先按元数据筛出真正的交锋，否则回退纯向量+阈值。

    给两队时（预测场景），元数据过滤能避免"队名信号被长正文稀释"导致召回错场次。
    """
    k = top_k or settings.rag_top_k
    qvec = embedder.embed_query(query)
    wide = max(k * 4, 20)                       # 搜宽一点，好在候选里筛交锋
    hits = vector_store.query(qvec, wide)       # [(doc, meta, dist), ...]

    # 阶段2：给了两队 → 先按元数据筛"两队都出现"的交锋（元数据命中比相似度更可信，不设阈值）
    if team_a and team_b:
        h2h = [
            (doc, meta, 1 - dist)
            for doc, meta, dist in hits
            if _both_teams(meta, team_a, team_b)
        ][:k]
        if h2h:
            logger.info(f"RAG「{query}」→ 元数据命中 {team_a} vs {team_b} 交锋 {len(h2h)} 条：")
            for _, m, sim in h2h:
                logger.info(f"  [{sim:.3f}]✓交锋 {m.get('year')} {m.get('stage')} "
                            f"{m.get('home')} {m.get('score')} {m.get('away')}")
            return _format(h2h)
        logger.info(f"RAG「{query}」→ {team_a} vs {team_b} 无历史交锋，回退纯向量")

    # 回退：没给两队 或 两队无交锋 → 纯向量 + 阈值
    logger.info(f"RAG「{query}」→ 纯向量（阈值 {settings.rag_min_sim}）：")
    kept: list[tuple] = []
    for doc, meta, dist in hits[:k]:
        sim = 1 - dist
        ok = sim >= settings.rag_min_sim
        logger.info(f"  [{sim:.3f}]{'✓' if ok else '✗低于阈值'} {meta.get('year')} "
                    f"{meta.get('stage')} {meta.get('home')} {meta.get('score')} {meta.get('away')}")
        if ok:
            kept.append((doc, meta, sim))

    if not kept:
        return "未检索到与该查询直接相关的历史比赛（两队可能无历史交锋记录）。"
    return _format(kept)
