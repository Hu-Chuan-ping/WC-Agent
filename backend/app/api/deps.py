from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infra.security.token import decode_token
from app.utils.exceptions import AuthError

# 鉴权守卫：受保护的接口声明 `user_id: str = Depends(get_current_user)` 即可。
# FastAPI 会在进入 handler 前先跑这里：解 Authorization 头里的 JWT → 得到 user_id，
# 无效则抛 401。这是 FastAPI 版的“横切鉴权”，靠依赖注入而非 AOP 织入。

_bearer = HTTPBearer(auto_error=False)  # 自己抛 AuthError，保证错误响应格式统一


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """从 Bearer 令牌解析出当前用户 id；无令牌/无效/过期一律 401。"""
    if cred is None or not cred.credentials:
        raise AuthError("缺少登录凭证")
    user_id = decode_token(cred.credentials)
    if user_id is None:
        raise AuthError("登录已过期，请重新登录")
    return user_id
