from __future__ import annotations

import os

from app.config.settings import settings

# 必须在 import sentence_transformers 之前设好这些环境变量：
# - HF_HOME：模型缓存目录指向 D 盘，不占 C
# - HF_HUB_OFFLINE：模型已缓存，只读本地、不再联网（也就绕开了代理问题）
os.environ.setdefault("HF_HOME", settings.hf_home)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from sentence_transformers import SentenceTransformer  # noqa: E402

from app.utils.logger import logger  # noqa: E402

# bge 中文模型的建议用法：对「查询」加指令前缀能显著提升召回，对「文档」不加。
_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """懒加载 + 单例：模型几百 MB，只加载一次。"""
    global _model
    if _model is None:
        logger.info(f"加载向量模型 {settings.embedding_model} ...")
        _model = SentenceTransformer(settings.embedding_model)
        logger.info("向量模型加载完成")
    return _model


def embed_docs(texts: list[str]) -> list[list[float]]:
    """给文档批量向量化（建库用）。normalize 后配合 cosine 距离。"""
    vecs = _get_model().encode(texts, normalize_embeddings=True)
    return vecs.tolist()


def embed_query(query: str) -> list[float]:
    """给查询向量化（检索用），加 bge 指令前缀。"""
    vec = _get_model().encode(_QUERY_PREFIX + query, normalize_embeddings=True)
    return vec.tolist()
