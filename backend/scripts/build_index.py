"""离线建库：把 doc_rag 下的世界杯 docx 切片、向量化，灌入 Chroma。

用法（在 backend 目录下）：
    python scripts/build_index.py

只需在数据变化时重跑；平时预测走在线检索，不碰这里。
"""
from __future__ import annotations

import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
# 把 backend 目录加入路径，好 import app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.rag import embedder  # noqa: E402
from app.core.rag.parser import load_docx  # noqa: E402
from app.core.rag.splitter import split_into_matches  # noqa: E402
from app.db import vector_store  # noqa: E402
from app.utils.logger import logger  # noqa: E402

DOC_DIR = "D:/code/WC-agent/doc_rag"


def main() -> None:
    vector_store.reset()  # 清空重建，保证可重复运行
    # 排除 Word 打开文档时产生的 ~$ 临时锁文件
    files = sorted(
        f for f in os.listdir(DOC_DIR)
        if f.endswith(".docx") and not f.startswith("~$")
    )
    total = 0

    for fname in files:
        year_m = re.search(r"(\d{4})", fname)
        year = int(year_m.group(1)) if year_m else 0

        text = load_docx(os.path.join(DOC_DIR, fname))
        chunks = split_into_matches(text, year)
        if not chunks:
            logger.warning(f"{fname} 未切出任何比赛，请检查格式")
            continue

        docs = [c.text for c in chunks]
        metas = [c.metadata for c in chunks]
        ids = [f"{year}-{i}" for i in range(len(chunks))]
        embeddings = embedder.embed_docs(docs)
        vector_store.add(ids, docs, embeddings, metas)

        sample = chunks[0].metadata
        logger.info(
            f"{fname}: {len(chunks)} 场已入库（示例：{sample['home']} "
            f"{sample['score']} {sample['away']} / {sample['stage']}）"
        )
        total += len(chunks)

    logger.info(f"建库完成：共 {total} 场，collection 现有 {vector_store.count()} 条")


if __name__ == "__main__":
    main()
