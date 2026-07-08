from __future__ import annotations

import uuid

from app.infra.repositories import user_repository
from app.infra.security import captcha, password, token
from app.models.schemas.auth import CaptchaResponse, TokenResponse
from app.utils.exceptions import AuthError, ValidationError
from app.utils.logger import logger

# 鉴权应用服务：编排“注册/登录”用例。只做装配——
# 校验/存取/加密/签发的具体实现都在 infra，这里不含 SQL、不含加密细节。


async def new_captcha() -> CaptchaResponse:
    """签发一张新验证码。"""
    captcha_id, image = await captcha.generate()
    return CaptchaResponse(captcha_id=captcha_id, image=image)


async def register(
    username: str, password_plain: str, captcha_id: str, captcha_text: str
) -> TokenResponse:
    """注册：校验验证码 → 查重名 → 加盐哈希 → 存库 → 直接签发令牌（自动登录）。"""
    if not await captcha.verify(captcha_id, captcha_text):
        raise ValidationError("验证码错误或已过期")

    if await user_repository.get_by_username(username):
        raise ValidationError("用户名已存在")

    user_id = uuid.uuid4().hex
    await user_repository.create(user_id, username, password.hash_password(password_plain))
    logger.info(f"新用户注册：{username}（id={user_id}）")

    return TokenResponse(
        access_token=token.create_access_token(user_id),
        user_id=user_id,
        username=username,
    )


async def login(
    username: str, password_plain: str, captcha_id: str, captcha_text: str
) -> TokenResponse:
    """登录：校验验证码 → 查用户 → 校验密码 → 签发令牌。"""
    if not await captcha.verify(captcha_id, captcha_text):
        raise ValidationError("验证码错误或已过期")

    user = await user_repository.get_by_username(username)
    # 用户不存在与密码错误返回同一句话，避免泄露“哪个用户名存在”
    if user is None or not password.verify_password(password_plain, user["password_hash"]):
        raise AuthError("用户名或密码错误")

    logger.info(f"用户登录：{username}（id={user['id']}）")
    return TokenResponse(
        access_token=token.create_access_token(user["id"]),
        user_id=user["id"],
        username=user["username"],
    )
