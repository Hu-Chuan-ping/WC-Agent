from __future__ import annotations

from app.infra.repositories import (
    conversation_repository,
    match_repository,
    profile_repository,
    user_match_repository,
    user_repository,
)

# 建表统一入口：应用启动时(main.py lifespan)调一次 ensure_all_tables()。
# 每张表的 DDL 就近放在各自的 repository 里，这里只负责“全部建好”的编排。


async def ensure_all_tables() -> None:
    await user_repository.ensure_table()          # users（账号凭证）
    await profile_repository.ensure_table()       # user_profile（长期画像）
    await conversation_repository.ensure_table()  # sessions + messages（对话）
    await match_repository.ensure_table()         # matches + match_predictions（赛果+权威预测）
    await user_match_repository.ensure_table()    # user_match（用户↔问过的比赛）
