from __future__ import annotations

from pydantic import BaseModel, Field


class CaptchaResponse(BaseModel):
    """验证码：id 回传给后端做校验，image 是可直接放进 <img src> 的 data URI。"""

    captcha_id: str
    image: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=64)  # 上限 64 避开 bcrypt 72 字节限制
    captcha_id: str
    captcha_text: str


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: str
    captcha_text: str


class TokenResponse(BaseModel):
    """登录/注册成功后返回的令牌。前端存 token，后续请求带在 Authorization 头。"""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
