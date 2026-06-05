#!/usr/bin/env python3
"""Maestro Result Gateway — 结果网关（三道防线兜底保险）

三道防线：
1. 模型自身保证不输出思考过程
2. 网关清洗：去除英文行、工具调用、思考链、系统消息
3. 仅放行含「用户摘要」段的结果，否则全量拦截

用法:
  python gateway.py <task_id>         # 过滤输出
  python gateway.py --file <path>     # 过滤指定文件
  python gateway.py --raw <task_id>   # 原始输出（不过滤）
  python gateway.py --check <task_id> # 检查是否有用户摘要段
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MAESTRO_DIR = Path(PROJECT_ROOT) / "maestro"
TASKS_DIR = MAESTRO_DIR / "tasks"
RESULTS_DIR = MAESTRO_DIR / "results"

# ── 黑名单模式：命中即丢弃 ──────────────────────────────────
BLACKLIST_PATTERNS = [
    # XML 思考/工具标签
    r'<\s*(?:thinking|thought|reasoning|chain.of.thought|tool.calls?|function.calls?|internal|scratchpad)',
    r'<\s*/\s*(?:thinking|thought|reasoning|chain.of.thought|tool.calls?|function.calls?|internal|scratchpad)',
    # 工具调用关键词（行首）
    r'^\s*(?:<function_call>|<tool_call>|Tool|Call|Invoke|Execut(?:e|ing)|Running|Bash|bash)\b',
    # 系统消息泄露标志
    r'(?:system.reminder|system-reminder|internal.instruction|claudeMd|CLAUDE\.md|agent.instruction|task.notification)',
    r'(?:<env>|</env>|<system-reminder>|</system-reminder>)',
    # task-notification 的原始字段名
    r'^\s*(?:STATUS:|RESULT:|SUMMARY:|TASK_ID:|AGENT:)',
    # 思考链引导语
    r'^\s*(?:Let me|I need to|I should|I will|First,|Next,|Then,|Finally,|Now I|I\'ll|I\'m going to)',
    # 代码块标记（裸 ``` 行）
    r'^\s*```',
]
BLACKLIST_RE = [re.compile(p, re.IGNORECASE) for p in BLACKLIST_PATTERNS]


def _has_cjk(text):
    """检查文本是否包含 CJK 字符（中日韩），用于区分实质内容和英文过程。"""
    for ch in text:
        cp = ord(ch)
        if (0x4E00 <= cp <= 0x9FFF or    # CJK 统一汉字
            0x3400 <= cp <= 0x4DBF or    # CJK 扩展 A
            0x20000 <= cp <= 0x2A6DF or  # CJK 扩展 B
            0x3040 <= cp <= 0x309F or    # 平假名
            0x30A0 <= cp <= 0x30FF or    # 片假名
            0xAC00 <= cp <= 0xD7AF):     # 韩文
            return True
    return False


def _is_leak_line(line):
    """判断单行是否为泄露内容。

    命中条件：
    - 匹配黑名单正则
    - 纯 ASCII 且无 CJK 字符（英文/代码/工具输出）
    """
    stripped = line.strip()
    if not stripped:
        return False

    for pattern in BLACKLIST_RE:
        if pattern.search(stripped):
            return True

    if not _has_cjk(stripped):
        return True

    return False


def sanitize_content(raw_text):
    """第一道清洗：逐行移除泄露内容。

    保留空行结构，被过滤行替换为空行以维持段落边界。
    """
    lines = raw_text.split("\n")
    cleaned = []
    for line in lines:
        if not _is_leak_line(line):
            cleaned.append(line)
        else:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
    return "\n".join(cleaned)


def gateway_filter(raw_text):
    """从 agent 结果中提取 boss 可见内容。

    流程：
    1. 清洗全部泄露行（英文、工具调用、思考链）
    2. 取第一非空行为 STATUS
    3. 提取「## 用户摘要」段
    4. 摘要段内二次过滤泄露行
    5. 无摘要段 → 返回空，调用方全量拦截
    """
    if not raw_text:
        return "", ""

    clean_text = sanitize_content(raw_text)
    lines = clean_text.split("\n")

    # 取第一个非空行作为 STATUS
    status_line = ""
    for line in lines:
        if line.strip():
            status_line = line.strip()
            break

    # 提取用户摘要段
    in_summary = False
    summary_lines = []
    for line in lines:
        if re.match(r'^##\s*用户摘要', line.strip()):
            in_summary = True
            continue
        if in_summary:
            # 遇到下一个 ## 段头就停止
            if re.match(r'^##\s', line.strip()) and not re.match(r'^##\s*用户摘要', line.strip()):
                break
            # 摘要内二次过滤
            if line.strip() and _is_leak_line(line):
                continue
            summary_lines.append(line)

    summary = "\n".join(summary_lines).strip() if summary_lines else ""
    return status_line, summary


def has_user_summary(raw_text):
    """检查结果是否包含用户摘要段。"""
    return bool(re.search(r'##\s*用户摘要', raw_text))


def get_agent_name(task_id):
    """从任务文件读取 agent 名称。"""
    task_file = TASKS_DIR / f"{task_id}.json"
    if task_file.exists():
        try:
            with open(task_file, encoding="utf-8") as f:
                t = json.load(f)
                return t.get("agent", "")
        except (json.JSONDecodeError, OSError):
            return ""
    return ""


def filter_result(task_id=None, file_path=None, raw=False, check=False):
    """网关主逻辑。"""
    if file_path:
        result_file = Path(file_path)
        agent_name = ""
    elif task_id:
        result_file = RESULTS_DIR / f"{task_id}.txt"
        agent_name = get_agent_name(task_id)
    else:
        print("错误: 需要 --task-id 或 --file")
        sys.exit(1)

    if not result_file.exists():
        print(f"结果文件不存在: {result_file}")
        sys.exit(1)

    content = result_file.read_text(encoding="utf-8")

    if check:
        if has_user_summary(content):
            leak_count = sum(1 for line in content.split("\n") if _is_leak_line(line))
            if leak_count > 0:
                print(f"WARNING: 含用户摘要段，但检测到 {leak_count} 行疑似泄露内容（英文/工具调用）")
            else:
                print("OK: 含用户摘要段，未检测到泄露内容")
        else:
            print("BLOCKED: 缺少用户摘要段 — 结果已被网关拦截，禁止输出到手机端")
        return

    if raw:
        print(content)
        return

    status_line, summary = gateway_filter(content)

    prefix = f"[{agent_name}] " if agent_name else ""

    if not summary:
        print(f"{prefix}{status_line if _has_cjk(status_line) else '任务完成'}")
        print()
        print("网关拦截：该结果缺少「用户摘要」段，已阻止输出。")
        print("   原因：agent 内部过程（英文、思考链、工具调用）禁止泄露到手机端。")
        if task_id:
            gateway_path = MAESTRO_DIR / "gateway.py"
            print(f"   如需查看原始内容: python {gateway_path} --raw {task_id}")
        return

    # 最终兜底：STATUS 行若不含中文则替换
    if not _has_cjk(status_line):
        status_line = f"[{agent_name or 'Agent'}] 任务完成"

    print(f"{prefix}{status_line}")
    print(summary)


def main():
    parser = argparse.ArgumentParser(
        description="Maestro Result Gateway — 三道防线过滤 agent 结果，防止内部过程泄露"
    )
    parser.add_argument("task_id", nargs="?", help="Task ID to filter")
    parser.add_argument("--file", help="Filter a specific result file (instead of task ID)")
    parser.add_argument("--raw", action="store_true", help="Show raw output (no filter)")
    parser.add_argument("--check", action="store_true", help="Check if result has 用户摘要 section")
    args = parser.parse_args()

    if not args.task_id and not args.file:
        parser.print_help()
        sys.exit(0)

    filter_result(
        task_id=args.task_id,
        file_path=args.file,
        raw=args.raw,
        check=args.check,
    )


if __name__ == "__main__":
    main()
