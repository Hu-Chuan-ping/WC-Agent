from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.schemas.prediction import (
    OverviewResponse,
    PredictionItem,
    PredictionSummary,
)
from app.services import prediction_service

# 已预测比赛 / 评估相关接口（产品接口，需登录、按当前用户）。
router = APIRouter()


@router.post("/predictions/list", response_model=list[PredictionItem])
async def list_predictions(user_id: str = Depends(get_current_user)):
    """列出我问过的所有比赛（含权威预测 + 命中状态）。"""
    return await prediction_service.list_predictions(user_id)


@router.post("/predictions/summary", response_model=PredictionSummary)
async def prediction_summary(user_id: str = Depends(get_current_user)):
    """我的预测汇总：命中分布、命中率、RPS/Brier vs 赔率。"""
    return await prediction_service.summary(user_id)


@router.post("/predictions/overview", response_model=OverviewResponse)
async def prediction_overview(_: str = Depends(get_current_user)):
    """全局总预测偏差（所有权威预测，展示 agent 整体水平）。"""
    return await prediction_service.overview()


@router.post("/predictions/resolve")
async def resolve_predictions(_: str = Depends(get_current_user)) -> dict:
    """手动刷新赛果（触发结算）。"""
    return {"resolved": await prediction_service.resolve()}
