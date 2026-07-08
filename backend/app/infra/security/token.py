from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.config.settings import settings

# JWT 令牌签发/解析。无状态：服务端不存 session，令牌自带用户身份 + 签名防伪。


def create_access_token(user_id: str) -> str:
    """为某个用户签发访问令牌，sub 存 user_id。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str | None:
    """解析令牌，返回 user_id；无效或过期返回 None。"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
