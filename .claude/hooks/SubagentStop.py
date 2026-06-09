#!/usr/bin/env python3
"""SubagentStop Hook — 子Agent完成时校验输出"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "maestro" / "results"


def get_subagent_input():
    """从 stdin 或环境变量读取 SubAgent 完成信息"""
    # Claude Code 通过 stdin 传入 JSON
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read().strip()
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return {}


def find_output_file(agent_name):
    """查找子Agent的输出文件"""
    if not RESULTS_DIR.exists():
        return None
    for ext in [".json", ".txt", ".md"]:
        candidates = list(RESULTS_DIR.glob(f"*{agent_name}*{ext}"))
        if candidates:
            return candidates[0]
    return None


def validate_output(output_path):
    """校验输出是否包含完成标记"""
    if not output_path or not output_path.exists():
        return False, "输出文件不存在"
    try:
        content = output_path.read_text(encoding="utf-8")
        markers = ["DONE", "COMPLETE", "SUCCESS", "OK"]
        found = [m for m in markers if m in content.upper()]
        if not found:
            return False, f"输出未包含完成标记 (缺失: {', '.join(markers)})"
        return True, f"校验通过，找到标记: {', '.join(found)}"
    except Exception as e:
        return False, f"读取输出文件失败: {e}"


def write_result(agent_name, passed, reason):
    """写入结果记录"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "agent": agent_name,
        "passed": passed,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }
    result_file = RESULTS_DIR / f"subagent_check_{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    data = get_subagent_input()
    agent_name = data.get("agent", data.get("name", data.get("agent_name", "unknown")))
    output_path = data.get("output_path", data.get("output", ""))

    # 尝试自动查找输出文件
    if output_path:
        output_path = Path(output_path)
    else:
        output_path = find_output_file(agent_name)

    passed, reason = validate_output(output_path)
    write_result(agent_name, passed, reason)

    if not passed:
        print(f"RETRY: {reason}")
        sys.exit(1)
    else:
        print(f"OK: {reason}")
        sys.exit(0)


if __name__ == "__main__":
    main()
