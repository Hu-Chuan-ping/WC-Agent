from __future__ import annotations

import re


def _wordset(name: str) -> set[str]:
    return set(re.findall(r"\w+", (name or "").lower()))


def same_team(a: str, b: str) -> bool:
    """判断两个队名是否指同一支球队（忽略词序 + 容忍子集）。

    - 忽略词序：'DR Congo' == 'Congo DR'
    - 容忍子集：'Cape Verde' 与 'Cape Verde Islands'（LLM 给短名、API 给全名）
    """
    wa, wb = _wordset(a), _wordset(b)
    if not wa or not wb:
        return False
    return wa == wb or wa <= wb or wb <= wa
