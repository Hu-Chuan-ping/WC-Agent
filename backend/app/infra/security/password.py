from __future__ import annotations

import bcrypt

# 密码加盐哈希（bcrypt）。bcrypt 自动生成随机盐并嵌进结果串，故无需自己管盐。
# 注意：bcrypt 只取密码前 72 字节，超长部分被忽略——上层已在校验时限制长度。


def hash_password(plain: str) -> str:
    """把明文密码哈希成可入库的字符串。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文与库里的哈希是否匹配。"""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # 库里哈希串损坏等异常情况，一律视为不匹配
        return False
