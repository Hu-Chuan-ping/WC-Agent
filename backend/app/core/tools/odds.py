from __future__ import annotations

import httpx

from app.config.settings import settings
from app.core.tools.base_tool import BaseTool
from app.utils import request_stats
from app.utils.exceptions import ConfigError, ExternalServiceError

_TIMEOUT = 20.0
_SPORT = "soccer_fifa_world_cup"  # The Odds API 里世界杯的赛事 key


class OddsTool(BaseTool):
    """
    获取某场世界杯比赛的市场赔率与隐含概率（数据源：The Odds API）。

    把多家博彩商的 h2h（主胜/平/客胜）十进制赔率取平均，
    再换算成去除抽水、归一化后的隐含概率——可视为市场对赛果的共识判断。
    """

    name = "get_match_odds"
    description = (
        "获取某场世界杯比赛的市场赔率与隐含概率（主胜/平局/客胜）。"
        "赔率综合多家博彩商，隐含概率代表市场共识，是预测的重要参考。"
        "team_a、team_b 传英文队名，例如 England、Brazil。"
    )

    async def run(self, team_a: str, team_b: str) -> str:
        data = await self.probabilities(team_a, team_b)
        if data is None:
            return f"未找到「{team_a} vs {team_b}」的赔率（可能尚未开盘或比赛已结束）。"
        return self.format_text(data)

    async def probabilities(self, team_a: str, team_b: str) -> dict | None:
        """结构化赔率：{home_team, away_team, commence_time, probs{home,draw,away 为0~1分数}, avg, n_books}。
        找不到返回 None。pipeline 用它拿数字入库，run() 用它拿文本喂 LLM。"""
        if not settings.the_odds_api_key:
            raise ConfigError("赔率功能未配置：缺少 THE_ODDS_API_KEY")
        events = await self._fetch_odds()
        event = self._find_event(events, team_a, team_b)
        if event is None:
            return None
        return self._compute(event)

    async def _fetch_odds(self) -> list:
        params = {
            "apiKey": settings.the_odds_api_key,
            "regions": "eu",          # 欧洲盘口
            "markets": "h2h",         # 胜平负
            "oddsFormat": "decimal",  # 十进制（欧赔）
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as c:
                r = await c.get(
                    f"{settings.the_odds_base_url}/v4/sports/{_SPORT}/odds",
                    params=params,
                )
                r.raise_for_status()
                # 月剩余额度在响应头里
                request_stats.record_quota("TheOddsAPI(月)", r.headers.get("x-requests-remaining"))
                return r.json()
        except httpx.HTTPError as exc:
            raise ExternalServiceError("The Odds API 请求失败", detail=str(exc)) from exc

    @staticmethod
    def _match(name: str, query: str) -> bool:
        return query in name or name in query

    def _find_event(self, events: list, a: str, b: str) -> dict | None:
        a, b = a.strip().lower(), b.strip().lower()
        for ev in events:
            home, away = ev.get("home_team", "").lower(), ev.get("away_team", "").lower()
            if (self._match(home, a) and self._match(away, b)) or (
                self._match(home, b) and self._match(away, a)
            ):
                return ev
        return None

    def _compute(self, ev: dict) -> dict | None:
        """从赛事数据算出结构化隐含概率（0~1 分数），映射到 home/draw/away。"""
        home, away = ev["home_team"], ev["away_team"]
        sums: dict[str, list] = {}
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                if mk.get("key") != "h2h":
                    continue
                for o in mk.get("outcomes", []):
                    acc = sums.setdefault(o["name"], [0.0, 0])
                    acc[0] += o["price"]
                    acc[1] += 1
        if not sums:
            return None

        avg = {name: total / count for name, (total, count) in sums.items()}
        implied = {name: 1 / v for name, v in avg.items()}
        total_p = sum(implied.values())              # >1，含抽水
        frac = {name: implied[name] / total_p for name in implied}  # 归一化去抽水

        return {
            "home_team": home,
            "away_team": away,
            "commence_time": ev.get("commence_time"),
            "n_books": max(count for _, count in sums.values()),
            "probs": {                                # 0~1 分数
                "home": frac.get(home, 0.0),
                "draw": frac.get("Draw", 0.0),
                "away": frac.get(away, 0.0),
            },
            "avg": {
                "home": avg.get(home),
                "draw": avg.get("Draw"),
                "away": avg.get(away),
            },
        }

    def format_text(self, d: dict) -> str:
        """把结构化赔率格式化成给 LLM 阅读的文本。"""
        p, a = d["probs"], d["avg"]
        lines = [
            f"【{d['home_team']} vs {d['away_team']} 市场赔率】（综合 {d['n_books']} 家博彩商）",
            f"开赛时间：{d.get('commence_time') or '未知'}",
            "\n平均赔率 → 隐含概率（已去抽水归一化）：",
        ]
        for key, label in [
            ("home", f"{d['home_team']}(主胜)"), ("draw", "平局"),
            ("away", f"{d['away_team']}(客胜)"),
        ]:
            if a.get(key):
                lines.append(f"  {label}: {a[key]:.2f} → {p[key] * 100:.1f}%")
        lines.append("\n提示：隐含概率代表市场共识，通常很难被打败；可作为预测的基准锚。")
        return "\n".join(lines)

    def _input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "team_a": {"type": "string", "description": "一方英文队名，如 England"},
                "team_b": {"type": "string", "description": "另一方英文队名，如 Brazil"},
            },
            "required": ["team_a", "team_b"],
        }
