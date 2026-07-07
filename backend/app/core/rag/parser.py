from __future__ import annotations

import docx


def load_docx(path: str) -> str:
    """读取 .docx，返回其中的文本（各段落用换行连接）。

    你的文档本身是 Markdown 排版（# / ## / #### 标题），
    这里只负责把 Word 里的文字原样取出，切片交给 splitter。
    """
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)
