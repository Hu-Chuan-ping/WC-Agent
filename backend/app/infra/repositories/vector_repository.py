from __future__ import annotations

import chromadb

from app.config.settings import settings

# 向量库仓库（Chroma 持久化 collection），懒加载单例。
# 只负责“原文+向量+元数据”的增删查，检索策略(阈值/两阶段)在 core/rag/retriever。
_client: chromadb.ClientAPI | None = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = _client.get_or_create_collection(
            name=settings.rag_collection,
            metadata={"hnsw:space": "cosine"},  # 配合归一化向量用 cosine
        )
    return _collection


def add(ids: list[str], documents: list[str],
        embeddings: list[list[float]], metadatas: list[dict]) -> None:
    """写入一批「原文 + 向量 + 元数据」。"""
    _get_collection().add(
        ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
    )


def query(query_embedding: list[float], top_k: int = 5) -> list[tuple]:
    """按向量相似度召回 top_k，返回 (文档, 元数据, 距离) 列表。"""
    r = _get_collection().query(query_embeddings=[query_embedding], n_results=top_k)
    return list(zip(r["documents"][0], r["metadatas"][0], r["distances"][0]))


def count() -> int:
    return _get_collection().count()


def reset() -> None:
    """删除并重建 collection（重新建库前调用，避免 id 重复）。"""
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    try:
        _client.delete_collection(settings.rag_collection)
    except Exception:
        pass
    _collection = _client.get_or_create_collection(
        name=settings.rag_collection,
        metadata={"hnsw:space": "cosine"},
    )
