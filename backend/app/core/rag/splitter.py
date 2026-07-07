from __future__ import annotations

import re
from dataclasses import dataclass, field

# 真实标题格式（含 vs 即为一场比赛，级别不定）：
#   小组赛(####)：第1轮 第一场：卡塔尔 vs 厄瓜多尔 常规时间比分：0-2
#   淘汰赛(###) ：阿根廷 vs 法国 常规时间比分：3-3
#   决赛/季军赛(##)：决赛：阿根廷 vs 法国 常规时间比分：3-3（加时…点球4-2）
_TEAMS = re.compile(r"([^\s:：]+)\s*vs\s*([^\s:：]+)")
_SCORE = re.compile(r"比分[:：]\s*(\d+)\s*[-–]\s*(\d+)")  # 取常规时间比分


@dataclass
class MatchChunk:
    """一场比赛 = 一个切片。text 送去向量化，metadata 用于展示/过滤。"""

    text: str
    metadata: dict = field(default_factory=dict)


def split_into_matches(text: str, year: int) -> list[MatchChunk]:
    """按标题切分：凡标题含 'vs' 即为一场比赛，一场一片，并抽出队伍/比分/阶段。"""
    chunks: list[MatchChunk] = []
    cur_stage = ""          # 由最近的「不含 vs 的 ## 标题」决定（小组赛 / 1/8决赛…）
    buf: list[str] = []     # 当前比赛累积的正文行
    cur_meta: dict | None = None

    def flush() -> None:
        if cur_meta and buf:
            chunks.append(MatchChunk("\n".join(buf).strip(), dict(cur_meta)))

    for raw in text.split("\n"):
        s = raw.strip()
        if not s:
            continue

        if s.startswith("#"):
            title = s.lstrip("#").strip()

            if "vs" in title:                       # —— 一场比赛 ——
                flush()
                buf = [title]
                tm = _TEAMS.search(title)
                sm = _SCORE.search(title)
                home, away = (tm.group(1), tm.group(2)) if tm else ("", "")
                score = f"{sm.group(1)}-{sm.group(2)}" if sm else ""
                if s.startswith("## "):             # 决赛/季军赛：阶段在标题里
                    stage = re.split(r"[:：]", title)[0].strip()
                else:                               # 小组赛/淘汰赛：用当前阶段
                    stage = cur_stage
                cur_meta = {
                    "year": year, "stage": stage,
                    "home": home, "away": away, "score": score,
                }
            else:                                   # —— 非比赛标题 ——
                flush()
                buf = []
                cur_meta = None
                if s.startswith("## "):             # 记录阶段
                    cur_stage = title

        elif cur_meta is not None:                  # 比赛正文（首发/进球/换人）
            buf.append(s)

    flush()
    return chunks
