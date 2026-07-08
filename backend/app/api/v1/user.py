from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.schemas.profile import ProfileResponse, UpdateProfileRequest
from app.services import profile_service

# 用户资料相关接口（登录，按当前用户）。
router = APIRouter()


@router.post("/profile/get", response_model=ProfileResponse)
async def get_profile(user_id: str = Depends(get_current_user)):
    """取我的资料（昵称/签名/喜欢的球队球星）。"""
    return await profile_service.get_profile(user_id)


@router.post("/profile/update", response_model=ProfileResponse)
async def update_profile(
    req: UpdateProfileRequest, user_id: str = Depends(get_current_user)
):
    """更新我的资料，并同步合成为长期记忆喂给 agent。"""
    return await profile_service.update_profile(
        user_id, req.nickname, req.signature, req.favorite_teams, req.favorite_players
    )
