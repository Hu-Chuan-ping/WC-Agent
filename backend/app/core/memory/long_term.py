from __future__ import annotations

from app.infra.repositories import profile_repository

# 长期用户记忆（领域服务）：决定“存什么/何时存”的业务判断留在这一层，
# 具体的 MySQL 存取交给 profile_repository。
# 未来“短期→长期”的画像抽取/摘要逻辑也落在这里。


async def get_profile(user_id: str) -> str:
    """取用户画像；无 user_id 或无记录时返回空串。"""
    if not user_id:
        return ""
    return await profile_repository.get(user_id)


async def upsert_profile(user_id: str, profile: str) -> None:
    """写入/更新用户画像。"""
    if not user_id:
        return
    await profile_repository.upsert(user_id, profile)
