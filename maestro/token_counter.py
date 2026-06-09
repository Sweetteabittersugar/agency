"""token_counter — 轻量 token 估算（无 API usage 数据时的 fallback）

中英文混合场景，用字符数/3 粗略估算。仅用于 cost.db 记录，非精确计费。
"""


def count(text: str) -> int:
    """估算单个文本的 token 数。中文约 1.5 字符/token，英文约 4 字符/token，取 3 折中。"""
    if not text:
        return 0
    return max(1, len(text) // 3)


def count_messages(messages: list[dict]) -> int:
    """估算消息列表的总 token 数。"""
    if not messages:
        return 0
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total += count(str(block.get("text", block.get("thinking", ""))))
                elif isinstance(block, str):
                    total += count(block)
    return max(1, total)
