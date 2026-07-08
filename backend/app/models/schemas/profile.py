from __future__ import annotations

from pydantic import BaseModel

# 用户资料接口的请求/响应模型。头像上传暂缓（后续接对象存储），故这里不含上传字段。


class UpdateProfileRequest(BaseModel):
    nickname: str | None = None
    signature: str | None = None
    favorite_teams: str | None = None
    favorite_players: str | None = None


class ProfileResponse(BaseModel):
    username: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    signature: str | None = None
    favorite_teams: str | None = None
    favorite_players: str | None = None
