from __future__ import annotations

import asyncio

from app.core.rag.retriever import retrieve
from app.core.tools.base_tool import BaseTool


class RagSearchTool(BaseTool):
    """检索历届世界杯（2006-2022）历史比赛的 RAG 工具。

    数据来自本地向量库（doc_rag 的 5 届世界杯战报），
    用于查两队历史交锋、某队历史战绩与打法。
    """

    name = "search_history"
    description = (
        "检索历届世界杯（2006-2022）的历史比赛资料：两队历史交锋、"
        "某支球队的历史战绩与打法风格。分析历史交锋、历史表现时用它。"
        "query 用自然语言，例如：英格兰 法国 历史交锋。"
    )

    async def run(self, query: str, team_a: str = "", team_b: str = "") -> str:
        # 向量化 + 向量库检索是同步 CPU 操作，丢线程池避免阻塞事件循环。
        # 给了 team_a/team_b（预测场景）→ 元数据过滤精准召回两队交锋。
        return await asyncio.to_thread(
            retrieve, query, team_a or None, team_b or None
        )

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索关键词，自然语言，如：英格兰 法国 历史交锋 / 巴西 历史战绩",
                },
                "team_a": {"type": "string", "description": "对阵一方队名（查两队交锋时给，可选）"},
                "team_b": {"type": "string", "description": "对阵另一方队名（查两队交锋时给，可选）"},
            },
            "required": ["query"],
        }
