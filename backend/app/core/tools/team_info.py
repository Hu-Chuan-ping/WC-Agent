from __future__ import annotations

import httpx

from app.config.settings import settings
from app.core.tools.base_tool import BaseTool
from app.utils import request_stats
from app.utils.exceptions import ConfigError, ExternalServiceError
from app.utils.teammatch import same_team

_TIMEOUT = 20.0
_WC_CODE = "WC"  # football-data 里世界杯的赛事代码

# 模块级缓存：世界杯参赛队 name(小写) -> {id, name, coach}
# football-data 的球队列表基本不变，缓存避免每次预测都重拉一次（省 10次/分钟 的限流）
_wc_teams_cache: dict[str, dict] | None = None


class TeamInfoTool(BaseTool):
    """
    获取一支国家队的结构化事实数据（数据源：football-data 免费层）。

    提供：主教练、近期战绩（近几场比分）、接下来的赛程。
    不含首发/伤病——免费层无此结构化数据，这类时效软信息交给 search_web 搜新闻。
    （api-football 免费层仅开放 2022~2024 赛季，对 2026 无效，故未接入；其 key 留作将来历史层使用。）
    """

    name = "get_team_info"
    description = (
        "获取某支国家队的结构化事实数据：主教练、近期战绩（近几场比分）、接下来的赛程。"
        "比赛预测前用它收集硬数据。team_name 必须传英文队名，例如 England、Brazil、France。"
        "注意：本工具不含首发与伤病，这两类信息请改用 search_web 搜索最新新闻。"
    )

    async def run(self, team_name: str) -> str:
        if not settings.football_data_api_key:
            raise ConfigError("结构化数据未配置：缺少 FOOTBALL_DATA_API_KEY")

        team = await self._resolve_wc_team(team_name)
        if team is None:
            return f"在世界杯参赛队中未找到「{team_name}」，请改用英文队名（如 England、Brazil）。"

        matches = await self._recent_matches(team["id"])
        return self._format(team, matches)

    async def _fd_get(self, path: str) -> dict:
        headers = {"X-Auth-Token": settings.football_data_api_key}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as c:
                r = await c.get(f"{settings.football_data_base_url}{path}", headers=headers)
                r.raise_for_status()
                # football-data 给的是「每分钟」剩余额度
                request_stats.record_quota("football-data(分)", r.headers.get("X-Requests-Available-Minute"))
                return r.json()
        except httpx.HTTPError as exc:
            raise ExternalServiceError("football-data 请求失败", detail=str(exc)) from exc

    async def _resolve_wc_team(self, name: str) -> dict | None:
        global _wc_teams_cache
        if _wc_teams_cache is None:
            data = await self._fd_get(f"/competitions/{_WC_CODE}/teams")
            _wc_teams_cache = {
                t["name"].lower(): {
                    "id": t["id"],
                    "name": t["name"],
                    "coach": (t.get("coach") or {}).get("name"),
                }
                for t in data.get("teams", [])
            }
        key = name.strip().lower()
        if key in _wc_teams_cache:
            return _wc_teams_cache[key]
        # 忽略词序 + 容忍子集（DR Congo↔Congo DR、Cape Verde↔Cape Verde Islands）
        for v in _wc_teams_cache.values():
            if same_team(v["name"], name):
                return v
        return None

    async def _recent_matches(self, team_id: int) -> list[dict]:
        # limit=10 返回当前时间前后的一批比赛，含已结束与未开始，后面按状态拆分
        data = await self._fd_get(f"/teams/{team_id}/matches?limit=10")
        return data.get("matches", [])

    def _format(self, team: dict, matches: list[dict]) -> str:
        lines = [f"【{team['name']} 结构化数据】"]
        lines.append(f"主教练：{team.get('coach') or '未知'}")

        finished = [m for m in matches if m.get("status") == "FINISHED"]
        upcoming = [m for m in matches if m.get("status") in ("SCHEDULED", "TIMED")]

        lines.append("\n近期战绩（football-data）：")
        if finished:
            for m in finished[-5:]:
                ft = m.get("score", {}).get("fullTime", {})
                lines.append(
                    f"  {m.get('utcDate', '')[:10]} "
                    f"{m['homeTeam']['name']} {ft.get('home')}-{ft.get('away')} {m['awayTeam']['name']}"
                    f"（{m['competition']['name']}）"
                )
        else:
            lines.append("  暂无已结束的比赛记录")

        lines.append("\n接下来赛程：")
        if upcoming:
            for m in upcoming[:3]:
                lines.append(
                    f"  {m.get('utcDate', '')[:10]} "
                    f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}（{m['competition']['name']}）"
                )
        else:
            lines.append("  暂无")

        return "\n".join(lines)

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "team_name": {
                    "type": "string",
                    "description": "英文国家队名，例如 England、Brazil、France、Argentina",
                }
            },
            "required": ["team_name"],
        }
