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


def hit_status(agent_score: str | None, actual_home: int, actual_away: int) -> str:
    """命中判定：全中(比分全对) / 半中(胜负对、比分错) / 未中(胜负都错)。"""
    try:
        ph, pa = (int(x) for x in str(agent_score).split("-"))
    except (ValueError, AttributeError):
        return "miss"  # 预测比分无法解析，按未中处理
    if ph == actual_home and pa == actual_away:
        return "hit"
    same_outcome = outcome_from_score(ph, pa) == outcome_from_score(actual_home, actual_away)
    return "half" if same_outcome else "miss"


def brier(p_home: float, p_draw: float, p_away: float, outcome: str) -> float:
    """多分类 Brier：越低越准，范围 0~2。"""
    o = _ONEHOT[outcome]
    return (p_home - o[0]) ** 2 + (p_draw - o[1]) ** 2 + (p_away - o[2]) ** 2


def log_loss(p_home: float, p_draw: float, p_away: float, outcome: str) -> float:
    """交叉熵：对"自信地错"惩罚更重。"""
    p = {"home": p_home, "draw": p_draw, "away": p_away}[outcome]
    return -math.log(min(max(p, 1e-9), 1.0))


def rps(p_home: float, p_draw: float, p_away: float, outcome: str) -> float:
    """排序概率得分（Ranked Probability Score），足球 1x2 的标准指标。

    主/平/客是【有序】的：预测客胜却主胜，比预测平局更离谱，RPS 会按"错多远"惩罚，
    Brier 则不区分。用累积概率与累积实际的均方差衡量。范围 0~1，越低越准。
    """
    o = _ONEHOT[outcome]
    # 累积到前 1、前 2 项（第 3 项累积恒为 1，无需算）
    cp1, cp2 = p_home, p_home + p_draw
    co1, co2 = o[0], o[0] + o[1]
    return 0.5 * ((cp1 - co1) ** 2 + (cp2 - co2) ** 2)
