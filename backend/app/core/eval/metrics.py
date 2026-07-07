from __future__ import annotations

import math

# 评估指标：Brier score（=概率向量与实际 one-hot 的均方误差）和 log-loss。
# outcome 取值："home" / "draw" / "away"，均相对【我方主队】。

_ONEHOT = {"home": (1, 0, 0), "draw": (0, 1, 0), "away": (0, 0, 1)}


def outcome_from_score(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def brier(p_home: float, p_draw: float, p_away: float, outcome: str) -> float:
    """多分类 Brier：越低越准，范围 0~2。"""
    o = _ONEHOT[outcome]
    return (p_home - o[0]) ** 2 + (p_draw - o[1]) ** 2 + (p_away - o[2]) ** 2


def log_loss(p_home: float, p_draw: float, p_away: float, outcome: str) -> float:
    """交叉熵：对"自信地错"惩罚更重。"""
    p = {"home": p_home, "draw": p_draw, "away": p_away}[outcome]
    return -math.log(min(max(p, 1e-9), 1.0))
