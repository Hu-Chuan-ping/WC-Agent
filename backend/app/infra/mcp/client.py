from __future__ import annotations

import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.utils.logger import logger

# ── MCP Client（消费方）────────────────────────────────────────────
#
# 管理与一个 MCP server 的长连接：stdio 子进程 + 一个 ClientSession。
# 单例、在 app 启动(lifespan)时 connect()、关闭时 close()——和 redis_client /
# mysql_client 的连接池是同一套"IO 资源单例"思路，所以放 infra。
#
# 为什么用 AsyncExitStack：stdio_client 和 ClientSession 都是异步上下文管理器
# (async with)。我们要跨请求复用同一条连接，就不能写在某个 async with 块里用完即走，
# 于是用 AsyncExitStack 手动 enter（连上并保持），close() 时统一 aclose 释放。

# backend/ 目录：server 子进程要从这里启动，app 包才可导入。
_BACKEND_DIR = str(Path(__file__).resolve().parents[3])


class McpClient:
    def __init__(self, module: str, name: str = "mcp") -> None:
        self._module = module          # 以 python -m <module> 方式启动 server
        self._name = name
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    async def connect(self) -> None:
        """启动 server 子进程、建立 session、完成 initialize 握手。幂等。"""
        if self._session is not None:
            return
        stack = AsyncExitStack()
        params = StdioServerParameters(
            command=sys.executable,                      # 用当前 venv 的 python
            args=["-m", self._module],
            cwd=_BACKEND_DIR,
        )
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._stack, self._session = stack, session
        logger.info(f"MCP client 已连接：server={self._name} module={self._module}")

    async def call_text(self, tool: str, args: dict) -> str:
        """调用一个返回文本的工具，拼接所有文本内容块返回。"""
        result = await self._require_session().call_tool(tool, args)
        texts = [getattr(b, "text", "") for b in result.content]
        return "\n".join(t for t in texts if t)

    async def call_struct(self, tool: str, args: dict) -> dict[str, Any] | None:
        """调用一个返回结构化数据的工具，返回 dict；空对象视为 None。"""
        result = await self._require_session().call_tool(tool, args)
        data = result.structuredContent
        # FastMCP 对返回 dict 的工具走 structuredContent；空 {} 表示"没找到"
        return data or None

    async def close(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = self._session = None
            logger.info(f"MCP client 已关闭：server={self._name}")

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError(f"MCP client 未连接(server={self._name})，请先 connect()")
        return self._session


# 赔率 server 的单例 client。全应用共享一条连接。
_odds_client = McpClient("app.infra.mcp.odds_server", name="wc-odds")


def get_odds_mcp_client() -> McpClient:
    return _odds_client
