from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.tools.odds import OddsTool

# ── 赔率 MCP Server ──────────────────────────────────────────────
#
# 这是一个【独立进程】：对外用 MCP 协议(JSON-RPC over stdio)暴露"查赔率"能力，
# 对内复用已有的 OddsTool 算法(打 The Odds API + 去抽水归一化)。
#
# 为什么放在 infra 而不是 core：它要打 HTTP、走 stdio，全是 IO——按项目铁律
# (core 只推理、不碰 IO)，这类"对外网关"归 infra。它和 infra/external/football_data.py
# 是同一类东西：外部能力的封装，只不过这次是"暴露成一个 MCP 服务"。
#
# 运行方式(从 backend/ 目录)：
#   python -m app.infra.mcp.odds_server        # 以 stdio 启动，等待 client 连接
#   npx @modelcontextprotocol/inspector python -m app.infra.mcp.odds_server   # 用 Inspector 调试

mcp = FastMCP("wc-odds")

# 单例复用：OddsTool 无状态(只依赖 settings 里的 key)，一个实例即可。
_odds = OddsTool()


@mcp.tool()
async def get_match_odds(team_a: str, team_b: str) -> str:
    """获取某场世界杯比赛的市场赔率与隐含概率(主胜/平局/客胜)。

    赔率综合多家博彩商，隐含概率(已去抽水归一化)代表市场共识，是预测的重要参考。

    Args:
        team_a: 一方英文队名，例如 England。
        team_b: 另一方英文队名，例如 Brazil。
    """
    # FastMCP 会把上面的类型注解 + docstring 自动转成 JSON Schema 暴露给 client：
    # 参数名/类型来自函数签名，参数说明来自 Args，工具描述来自首行 docstring。
    # 这里不写任何协议代码，纯业务——协议编解码全由 FastMCP 处理。
    return await _odds.run(team_a=team_a, team_b=team_b)


@mcp.tool()
async def get_match_odds_probs(team_a: str, team_b: str) -> dict:
    """获取某场世界杯比赛的结构化隐含概率（给程序用，非给人读）。

    返回 {home_team, away_team, commence_time, n_books, probs{home,draw,away}, avg{...}}；
    找不到该场比赛时返回空对象 {}。文本版请用 get_match_odds。

    Args:
        team_a: 一方英文队名。
        team_b: 另一方英文队名。
    """
    # 返回 dict → FastMCP 走 structuredContent 通道，client 能拿回原样结构化数据。
    # None 会让输出 schema 报错，故不存在时统一返回 {}。
    data = await _odds.probabilities(team_a, team_b)
    return data or {}


if __name__ == "__main__":
    # transport 默认 stdio：server 作为子进程，靠标准输入输出和 client 通信。
    # 将来跨机/上云再换 transport="streamable-http"，业务代码一行都不用动。
    mcp.run()
