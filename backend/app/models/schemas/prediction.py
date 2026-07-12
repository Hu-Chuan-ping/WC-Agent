from __future__ import annotations

from pydantic import BaseModel

# 预测记录相关接口的响应模型。


class ScoreProb(BaseModel):
    score: str
    p: float


class PredictionItem(BaseModel):
    match_id: str
    match: str                     # "主队 vs 客队"
    kickoff_time: str | None = None
    predicted_score: str | None = None       # 概率最高比分
    predicted_probs: str           # "主/平/客"，如 "0.50/0.30/0.20"
    score_dist: list[ScoreProb] = []          # 多概率比分分布
    actual_score: str | None = None  # 已结算才有，如 "0-0（4-3）"
    status: str                    # pending / hit / half / miss
    session_id: str | None = None


class PredictionSummary(BaseModel):
    total: int
    resolved: int
    hit: int
    half: int
    miss: int
    hit_rate: float | None = None
    avg_rps_agent: float | None = None
    avg_rps_odds: float | None = None
    avg_brier_agent: float | None = None
    avg_brier_odds: float | None = None
    beats_odds: int = 0            # 你 RPS 低于赔率的场次


class OverviewResponse(BaseModel):
    """全局：所有权威预测的总偏差（agent 整体水平）。"""

    total: int
    resolved: int
    avg_rps_agent: float | None = None
    avg_rps_odds: float | None = None
    avg_brier_agent: float | None = None
    avg_brier_odds: float | None = None
    verdict: str
