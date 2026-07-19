from __future__ import annotations

from app.core.tools.base_tool import BaseTool
from app.core.tools.odds import OddsTool
from app.infra.mcp.client import get_odds_mcp_client

# ── OddsTool 的 MCP 版本 ────────────────────────────────────────────
#
# 接口和 OddsTool 完全一致（name / description / run / probabilities / format_text），
# 是它的【透明替身】：pipeline 里 self._tools["get_match_odds"].run(...) / .probabilities(...)
# 照旧调用，感知不到底层从"进程内直接算"换成了"走 MCP 协议问 odds_server"。
#
# 分工：取数(有 IO)走 MCP → odds_server；格式化(纯逻辑，无 IO)本地复用 OddsTool。
# 这正是项目铁律的体现——IO 出去、纯逻辑留下。

# 复用 OddsTool 的纯格式化逻辑（format_text 只吃一个 dict，不含任何 IO）。
_fmt = OddsTool()


class McpOddsTool(BaseTool):
    name = "get_match_odds"
    description = OddsTool.description   # 同一段描述，单一来源

    async def run(self, team_a: str, team_b: str) -> str:
        """文本版：直接调 server 的文本工具，结果喂 LLM。"""
        return await get_odds_mcp_client().call_text(
            "get_match_odds", {"team_a": team_a, "team_b": team_b}
        )

    async def probabilities(self, team_a: str, team_b: str) -> dict | None:
        """结构化版：调 server 的结构化工具，拿回 dict 供入库；找不到返回 None。"""
        return await get_odds_mcp_client().call_struct(
            "get_match_odds_probs", {"team_a": team_a, "team_b": team_b}
        )

    def format_text(self, d: dict) -> str:
        """纯格式化，复用 OddsTool 实现（无 IO，不必走 MCP）。"""
        return _fmt.format_text(d)

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "team_a": {"type": "string", "description": "一方英文队名，如 England"},
                "team_b": {"type": "string", "description": "另一方英文队名，如 Brazil"},
            },
            "required": ["team_a", "team_b"],
        }
