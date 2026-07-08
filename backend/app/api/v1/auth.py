from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.schemas.auth import (
    CaptchaResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service

# 登录注册鉴权相关接口。
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/captcha", response_model=CaptchaResponse)
async def get_captcha() -> CaptchaResponse:
    """获取一张图形验证码（注册/登录前先拿）。"""
    return await auth_service.new_captcha()


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest) -> TokenResponse:
    """注册新账号，成功后直接返回令牌（自动登录）。"""
    return await auth_service.register(
        req.username, req.password, req.captcha_id, req.captcha_text
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """账号密码登录，返回令牌。"""
    return await auth_service.login(
        req.username, req.password, req.captcha_id, req.captcha_text
    )


@router.get("/me")
async def me(user_id: str = Depends(get_current_user)) -> dict:
    """返回当前登录用户 id（受保护接口示例，用于前端校验登录态）。"""
    return {"user_id": user_id}
