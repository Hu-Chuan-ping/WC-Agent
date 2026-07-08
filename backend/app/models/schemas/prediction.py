from __future__ import annotations

from pydantic import BaseModel

# 预测记录相关接口的响应模型。


class PredictionItem(BaseModel):
    id: int
    match: str                     # "主队 vs 客队"
    kickoff_time: str | None = None
    predicted_score: str | None = None
    predicted_probs: str           # "主/平/客"，如 "0.50/0.30/0.20"
    actual_score: str | None = None  # 已结算才有，如 "1-2"
    status: str                    # pending / hit / half / miss
    session_id: str | None = None


class PredictionSummary(BaseModel):
    total: int
    resolved: int
    hit: int
    half: int
    miss: int
    hit_rate: float | None = None       # 全中率 = hit / resolved
    avg_brier_agent: float | None = None
    avg_brier_odds: float | None = None
    beats_odds: int = 0                 # 你的 Brier 低于赔率的场次


class OverviewResponse(BaseModel):
    """全局：所有用户、所有比赛的总预测偏差（展示 agent 整体水平）。"""

    total: int
    resolved: int
    avg_brier_agent: float | None = None
    avg_brier_odds: float | None = None
    verdict: str
