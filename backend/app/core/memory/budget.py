from __future__ import annotations

# 轻量 token 估算：用于"上下文占用"仪表 + 滚动摘要的预算判断。
#
# 非精确——DeepSeek 有自己的分词器，这里用启发式近似：
#   中文/CJK 字符 ≈ 0.6 token，其它字符（英文/数字/符号）≈ 0.3 token。
# 做"仪表显示"和"是否超预算"的判断足够，不追求逐 token 精确。


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    other = len(text) - cjk
    return int(cjk * 0.6 + other * 0.3) + 1


def messages_tokens(messages: list[dict]) -> int:
    return sum(estimate_tokens(m.get("content", "")) for m in messages)


def context_tokens(history: list[dict], profile: str = "") -> int:
    """会话上下文占用 ≈ 历史窗口 + 用户画像。

    （system prompt / 工具 schema / 预测时的瞬时数据是每轮临时拼的，
     不计入这个"会话累积"口径——仪表要反映的是随对话增长的那部分。）
    """
    return messages_tokens(history) + estimate_tokens(profile)
