from __future__ import annotations

from app.infra.repositories import profile_repository, user_repository

# 用户资料应用服务：编排“取资料 / 存资料”，并把资料合成为喂给 agent 的记忆文本。


def _compose_memory(
    nickname: str | None,
    signature: str | None,
    favorite_teams: str | None,
    favorite_players: str | None,
) -> str:
    """把结构化资料合成一句自然语言画像，写进 profile 列供 agent 读取。"""
    parts: list[str] = []
    if nickname:
        parts.append(f"昵称：{nickname}")
    if favorite_teams:
        parts.append(f"喜欢的球队：{favorite_teams}")
    if favorite_players:
        parts.append(f"喜欢的球星：{favorite_players}")
    if signature:
        parts.append(f"个性签名：{signature}")
    return "。".join(parts) + ("。" if parts else "")


async def get_profile(user_id: str) -> dict:
    fields = await profile_repository.get_fields(user_id) or {}
    user = await user_repository.get_by_id(user_id)
    return {
        "username": user["username"] if user else None,
        "nickname": fields.get("nickname"),
        "avatar_url": fields.get("avatar_url"),
        "signature": fields.get("signature"),
        "favorite_teams": fields.get("favorite_teams"),
        "favorite_players": fields.get("favorite_players"),
    }


async def update_profile(
    user_id: str,
    nickname: str | None,
    signature: str | None,
    favorite_teams: str | None,
    favorite_players: str | None,
) -> dict:
    memory = _compose_memory(nickname, signature, favorite_teams, favorite_players)
    await profile_repository.upsert_fields(
        user_id, memory, nickname, signature, favorite_teams, favorite_players
    )
    return await get_profile(user_id)
