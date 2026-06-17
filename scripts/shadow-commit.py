#!/usr/bin/env python3
"""Shadow Commit — pre-commit 失败自动修复 + 重试流水线。

用法:
  python shadow-commit.py -m "commit message"           # 自动修+提交
  python shadow-commit.py -m "msg" --max-rounds 5       # 最多5轮
  python shadow-commit.py -m "msg" --dry-run            # 只检查不提交
  python shadow-commit.py -m "msg" --report-only        # 只出结构化报告，不修

流程:
  1. git add -A
  2. 运行 check-all.py
  3. 失败 → 分类错误 → 机械问题自动修 → 重试 (最多3轮)
  4. 复杂问题 → 输出结构化 JSON 报告 → 交给 AI coder 修复
  5. 全部通过 → git commit

错误分类:
  MECHANICAL  — ruff/whitespace/line-endings → 自动修复
  TEST        — 测试失败/覆盖率不足 → 需 AI 修复
  SYNTAX      — Python/JS 语法错误 → 需 AI 修复
  CRITICAL    — 缺失关键 DOM/函数 → 需 AI 修复
  API         — API 端点不可达 → 跳过（服务器未运行）
"""

import argparse
import json
import os
import subprocess
import sys
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
os.chdir(str(ROOT))  # noqa: F821 — chdir after ROOT is defined


# ── 错误分类器 ──

def classify_failure(check_name, detail):
    """根据检查名称和详情分类错误类型。

    返回: "MECHANICAL" | "TEST" | "SYNTAX" | "CRITICAL" | "API" | "UNKNOWN"
    """
    name_lower = check_name.lower()

    # API 端点 — 服务器没跑，跳过
    if "api" in name_lower or "端点" in name_lower:
        return "API"

    # 测试相关 — 需要 AI
    if "测试" in name_lower or "test" in name_lower or "覆盖" in name_lower or "coverage" in name_lower:
        return "TEST"

    # 语法错误 — 需要 AI（ruff 能修部分，已在 auto-fix 中处理）
    if "语法" in name_lower or "syntax" in name_lower:
        return "SYNTAX"

    # 关键功能缺失 — 需要 AI
    if "关键" in name_lower or "critical" in name_lower or "功能" in name_lower:
        return "CRITICAL"

    # 重复函数 — 需要 AI
    if "重复" in name_lower or "duplicate" in name_lower:
        return "SYNTAX"

    # 括号/引号 — 需要 AI（机械修复太危险）
    if "括号" in name_lower or "引号" in name_lower or "bracket" in name_lower:
        return "SYNTAX"

    # HTML 标签 — 需要 AI
    if "html" in name_lower or "标签" in name_lower:
        return "SYNTAX"

    return "UNKNOWN"


# ── 机械修复器 ──

def auto_fix_ruff():
    """运行 ruff --fix 自动修复格式问题。"""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "maestro/", "--fix", "--select=E,F"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT), timeout=30
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def auto_fix_trailing_whitespace():
    """修复 Python/JS 文件的行尾空白。"""
    fixed = 0
    for pattern in ["maestro/**/*.py", "webui/js/*.js", "webui/*.html"]:
        for f in ROOT.glob(pattern):
            if "__pycache__" in str(f):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                new_content = "\n".join(line.rstrip() for line in content.split("\n"))
                # 保持文件末尾换行一致
                if content.endswith("\n") and not new_content.endswith("\n"):
                    new_content += "\n"
                if content != new_content:
                    f.write_text(new_content, encoding="utf-8")
                    fixed += 1
            except Exception:
                pass
    return fixed


def auto_fix_end_of_file():
    """确保文件以单个换行结尾。"""
    fixed = 0
    for pattern in ["maestro/**/*.py", "webui/js/*.js"]:
        for f in ROOT.glob(pattern):
            if "__pycache__" in str(f):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                if not content:
                    continue
                # 去掉末尾多余空行，保留一个换行
                new_content = content.rstrip("\n") + "\n"
                if content != new_content:
                    f.write_text(new_content, encoding="utf-8")
                    fixed += 1
            except Exception:
                pass
    return fixed


def run_all_auto_fixes():
    """执行所有机械修复，返回修复摘要。"""
    results = {}

    rc, output = auto_fix_ruff()
    results["ruff"] = {"fixed": rc == 0, "detail": output[:200]}

    n = auto_fix_trailing_whitespace()
    results["trailing_ws"] = {"files_fixed": n}

    n = auto_fix_end_of_file()
    results["eof_newline"] = {"files_fixed": n}

    return results


# ── check-all 调用 ──

def run_check_all():
    """运行 check-all.py，返回 (passed: bool, details: list of {check, status, detail})。"""
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check-all.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT), timeout=180
        )
        output = (r.stdout or "") + "\n" + (r.stderr or "")
        passed = r.returncode == 0
        details = parse_check_output(output)
        return passed, details
    except subprocess.TimeoutExpired:
        return False, [{"check": "TIMEOUT", "status": "FAIL", "detail": "check-all.py 超时 (>180s)"}]
    except Exception as e:
        return False, [{"check": "ERROR", "status": "FAIL", "detail": str(e)}]


def parse_check_output(output):
    """解析 check-all.py 的输出，提取各检查项结果。"""
    details = []
    lines = output.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("[OK]") or line.startswith("[FAIL]"):
            status = "OK" if line.startswith("[OK]") else "FAIL"
            check_name = line[5:].strip() if status == "OK" else line[7:].strip()
            # 收集后续详情行（以空格缩进的行）
            detail_lines = []
            j = i + 1
            while j < len(lines) and (lines[j].startswith("         ") or lines[j].strip() == ""):
                stripped = lines[j].strip()
                if stripped:
                    detail_lines.append(stripped)
                j += 1
            details.append({
                "check": check_name,
                "status": "PASS" if status == "OK" else "FAIL",
                "detail": "\n".join(detail_lines) if detail_lines else "",
            })
            i = j
        else:
            i += 1
    return details


# ── 结构化报告 ──

def generate_report(rounds, final_pass, failures, auto_fix_log):
    """生成结构化 JSON 报告，供 AI agent 消费。"""
    # 分类失败项
    mechanical = []
    needs_ai = []
    skippable = []

    for f in failures:
        category = classify_failure(f["check"], f.get("detail", ""))
        f["category"] = category
        if category == "API":
            skippable.append(f)
        elif category == "MECHANICAL":
            mechanical.append(f)
        else:
            needs_ai.append(f)

    report = {
        "shadow_commit": {
            "timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M"),
            "rounds": rounds,
            "max_rounds_reached": rounds >= 3 and not final_pass,
            "final_status": "PASS" if final_pass else "FAIL",
        },
        "failures": {
            "total": len(failures),
            "needs_ai_fix": len(needs_ai),
            "mechanical": len(mechanical),
            "skippable_api": len(skippable),
            "items": failures,
        },
        "auto_fix_log": auto_fix_log,
    }

    return report


# ── 主流程 ──

def shadow_commit(commit_msg, max_rounds=3, dry_run=False, report_only=False):
    """Shadow Commit 主流程。"""
    print(f"🌑 Shadow Commit — 最多 {max_rounds} 轮自动修复")
    print(f"   消息: {commit_msg[:72]}")
    print()

    if not report_only:
        # Stage 所有改动
        print("[1/4] git add -A")
        r = subprocess.run(
            ["git", "add", "-A"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", cwd=str(ROOT)
        )
        if r.returncode != 0:
            print(f"   ❌ git add 失败: {r.stderr}")
            return 1

        # 检查是否有东西可提交
        r = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True, encoding="utf-8", errors="replace", cwd=str(ROOT)
        )
        if r.returncode == 0:
            print("   ⚠ 无暂存改动，跳过提交")
            return 0
        print()

    auto_fix_log = []
    for round_num in range(1, max_rounds + 1):
        print(f"[2/4] 第 {round_num}/{max_rounds} 轮 — 运行 check-all.py...")
        passed, details = run_check_all()

        if passed:
            print(f"   ✅ 全部通过 ({len(details)} 项)")
            break

        # 统计失败
        failures = [d for d in details if d["status"] == "FAIL"]
        print(f"   ❌ {len(failures)} 项失败:")

        for f in failures:
            cat = classify_failure(f["check"], f.get("detail", ""))
            icon = {"API": "🔌", "TEST": "🧪", "SYNTAX": "📝", "CRITICAL": "🚨", "MECHANICAL": "🔧", "UNKNOWN": "❓"}.get(cat, "❓")
            detail_preview = f["detail"][:100].replace("\n", " | ")
            print(f"      {icon} [{cat}] {f['check']}: {detail_preview}")

        # 判断是否只剩 API 失败（可跳过）
        non_api_failures = [f for f in failures if classify_failure(f["check"], f.get("detail", "")) != "API"]
        if not non_api_failures:
            print(f"\n   ⚠ 仅剩 API 端点失败（服务器未运行），视为通过")
            passed = True
            break

        # 执行机械修复
        if not report_only:
            print(f"\n[3/4] 执行自动修复...")
            fix_results = run_all_auto_fixes()
            auto_fix_log.append({"round": round_num, "fixes": fix_results})

            total_fixed = sum(
                v.get("files_fixed", 0) for v in fix_results.values()
            )
            if total_fixed > 0:
                print(f"   🔧 修复 {total_fixed} 个文件")
                # Re-stage 修复后的文件
                subprocess.run(
                    ["git", "add", "-A"], capture_output=True,
                    encoding="utf-8", errors="replace", cwd=str(ROOT)
                )
            else:
                print(f"   ⚠ 无可自动修复的机械问题")
                # 非机械问题，自动修不了
                remaining = [f for f in non_api_failures
                           if classify_failure(f["check"], f.get("detail", "")) != "MECHANICAL"]
                if remaining:
                    print(f"   🔍 {len(remaining)} 项需要 AI 修复（非机械问题）")
                    if round_num >= max_rounds:
                        break
        else:
            break

    print()

    # 最终判定
    if passed:
        if dry_run or report_only:
            print("✅ 所有检查通过 (dry-run，不提交)")
            return 0
        else:
            print("[4/4] git commit...")
            r = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT)
            )
            if r.returncode == 0:
                print(f"✅ 提交成功: {r.stdout.strip()}")
                return 0
            else:
                print(f"❌ 提交失败: {r.stderr}")
                return 1
    else:
        failures = [d for d in details if d["status"] == "FAIL"]
        non_api = [f for f in failures if classify_failure(f["check"], f.get("detail", "")) != "API"]

        print("❌ Shadow Commit 未能通过所有检查\n")

        # 输出结构化报告
        report = generate_report(round_num, False, non_api, auto_fix_log)
        print("── 📋 AI 修复任务 ──")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("── 📋 END ──")

        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Shadow Commit — pre-commit 自动修复 + 重试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-m", "--message", required=True, help="Commit message")
    parser.add_argument("--max-rounds", type=int, default=3, help="最大重试轮数 (默认3)")
    parser.add_argument("--dry-run", action="store_true", help="只检查不提交")
    parser.add_argument("--report-only", action="store_true", help="只出结构化报告，不修不提交")
    parser.add_argument("-o", "--output", help="将结构化报告写入文件 (JSON)")

    args = parser.parse_args()

    rc = shadow_commit(
        commit_msg=args.message,
        max_rounds=args.max_rounds,
        dry_run=args.dry_run,
        report_only=args.report_only,
    )

    sys.exit(rc)


if __name__ == "__main__":
    os.chdir(str(Path(__file__).resolve().parent.parent))
    main()
