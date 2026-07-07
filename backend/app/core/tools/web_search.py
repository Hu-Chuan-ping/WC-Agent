from __future__ import annotations

import httpx

from app.config.settings import settings
from app.core.tools.base_tool import BaseTool
from app.utils.exceptions import ConfigError, ExternalServiceError

# Tavily 单次请求超时（秒）。国际服务 + 可能走代理，给宽松一点。
_TIMEOUT = 20.0


class WebSearchTool(BaseTool):
    """
    基于 Tavily 的网页搜索工具。

    用于获取「本地数据库没有、且需要时效性」的公开信息：
    赛事新闻、伤病动态、首发消息、球队/球员近期状态、教练表态等。
    Tavily 返回的是清洗过的正文，可直接交给 LLM 阅读。
    """

    name = "search_web"
    description = (
        "搜索互联网获取球队或比赛的最新公开信息，例如赛事新闻、伤病情况、"
        "首发阵容、球队近期状态、教练表态等。当需要时效性信息、或本地数据"
        "里查不到时使用。返回若干条带标题、链接和正文摘要的搜索结果。"
    )

    async def run(self, query: str, max_results: int = 5) -> str:
        if not settings.tavily_api_key:
            raise ConfigError("搜索功能未配置：缺少 TAVILY_API_KEY")

        payload = {
            "query": query,
            "search_depth": "basic",   # basic=1额度/次，advanced=2；先用 basic 省额度
            "topic": "general",
            "max_results": max_results,
            "include_answer": True,     # 让 Tavily 先给一段综合摘要，省 LLM 一次推理
        }
        headers = {"Authorization": f"Bearer {settings.tavily_api_key}"}

        # trust_env=False：忽略系统代理。本机 Clash 把 https 代理写成了 https:// 前缀，
        # httpx 会误以为要对本地代理做 TLS 握手而失败；直连即可（与 LLMClient 一致）。
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as client:
                resp = await client.post(
                    f"{settings.tavily_base_url}/search",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            # 把底层 httpx 异常翻译成业务异常；message 给前端，detail 进日志
            raise ExternalServiceError("Tavily 搜索失败", detail=str(exc)) from exc

        return self._format(query, data)

    def _format(self, query: str, data: dict) -> str:
        results = data.get("results") or []
        if not results:
            return f"未搜索到「{query}」的相关结果。"

        lines: list[str] = [f"搜索关键词：{query}"]

        answer = data.get("answer")
        if answer:
            lines.append(f"\n【综合摘要】\n{answer}")

        lines.append("\n【来源结果】")
        for i, item in enumerate(results, start=1):
            title = item.get("title", "（无标题）")
            url = item.get("url", "")
            content = (item.get("content") or "").strip()
            lines.append(f"\n{i}. {title}\n   链接：{url}\n   摘要：{content}")

        return "\n".join(lines)

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，用自然语言描述要查的信息，例如：英格兰队 2026世界杯 最新伤病 首发",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量，默认 5，建议 3~8",
                },
            },
            "required": ["query"],
        }
