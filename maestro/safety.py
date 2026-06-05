#!/usr/bin/env python3
"""
Safety Guard — 独立模式的安全护栏
防止：提示注入、危险代码执行、敏感信息泄露
"""

import re

# === 输入安全（用户输入 → API 之前） ===

FORBIDDEN_PATTERNS = [
    # 提示注入
    r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions",
    r"forget\s+(all\s+)?(your|the)\s+(rules|instructions|prompt)",
    r"you\s+are\s+now\s+(DAN|jailbreak)",
    r"pretend\s+to\s+be",
    r"act\s+as\s+if\s+you\s+are",
    # 危险代码
    r"rm\s+-rf\s+/",
    r"del\s+/[fs]",
    r"DROP\s+TABLE",
    r"eval\s*\(.*\)",
    r"exec\s*\(.*\)",
    r"os\.system\s*\(.*rm",
    r"subprocess\.call\s*\(.*rm",
    # 恶意内容
    r"(hack|steal|exploit|malware|ransomware|phishing)",
]

MAX_INPUT_LENGTH = 32000  # 最大输入字符数

# === 输出安全（API 响应 → 用户之前） ===

DANGEROUS_OUTPUT_PATTERNS = [
    # API key 泄露模式
    r"(sk|api_key|token|secret|password)\s*[=:]\s*[\'\"]?[a-zA-Z0-9\-_]{20,}",
    # 系统指令泄露
    r"system\s*prompt\s*(is|was|:|：)",
    r"your\s*instructions\s*(are|were|include)",
]


def check_input(text):
    """
    检查用户输入是否安全。
    返回 (is_safe: bool, reason: str)
    """
    if not text or not text.strip():
        return True, ""

    if len(text) > MAX_INPUT_LENGTH:
        return False, f"输入过长（{len(text)} > {MAX_INPUT_LENGTH} 字符）"

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"检测到不安全内容（匹配规则: {pattern[:40]}...）"

    return True, ""


def check_output(text):
    """
    检查 API 输出是否包含危险内容。
    返回 (is_safe: bool, issues: list)
    """
    issues = []
    for pattern in DANGEROUS_OUTPUT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            issues.append(f"潜在泄露: {pattern[:40]}...")
    return len(issues) == 0, issues


def sanitize_output(text):
    """
    清理输出中的敏感信息。
    用 ***REDACTED*** 替换疑似密钥。
    """
    text = re.sub(
        r'(sk-[a-zA-Z0-9\-_]{20,})',
        '***REDACTED***',
        text
    )
    text = re.sub(
        r'(api_key|token|secret|password)\s*[=:]\s*[\'\"][^\'\"]+[\'\"]',
        r'\1=***REDACTED***',
        text,
        flags=re.IGNORECASE
    )
    return text


# === 速率限制 ===
import time
from collections import defaultdict

_request_counts = defaultdict(list)
RATE_LIMIT = 60  # 每分钟最多 60 次请求


def check_rate_limit(user_id="default"):
    """简单的滑动窗口速率限制"""
    now = time.time()
    window = now - 60  # 1 分钟窗口

    # 清理过期记录
    _request_counts[user_id] = [t for t in _request_counts[user_id] if t > window]

    if len(_request_counts[user_id]) >= RATE_LIMIT:
        return False

    _request_counts[user_id].append(now)
    return True
