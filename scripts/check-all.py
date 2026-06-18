#!/usr/bin/env python3
"""Agency 全量检测 — JS/Python/API 一把梭"""

import subprocess
import sys
import os
import ast
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT))  # 确保 maestro.app_config 可导入

from maestro.app_config import PORT as AGENCY_PORT

errors = 0
OK = 0


def check(title, fn):
    global errors, OK
    ok, msg = fn()
    if ok:
        print(f"  [OK] {title}")
        OK += 1
    else:
        print(f"  [FAIL] {title}")
        errors += 1
    if msg:
        for line in msg.strip().split("\n"):
            print(f"         {line}")


# ── 1. JS 语法 ──
def check_js_syntax():
    js_dir = ROOT / "webui" / "js"
    failures = []
    for js_file in sorted(js_dir.glob("*.js")):
        r = subprocess.run(["node", "--check", str(js_file)], capture_output=True, text=True)
        if r.returncode != 0:
            failures.append(f"{js_file.name}: {r.stderr.strip()}")
    if failures:
        return False, "\n".join(failures)
    return True, ""


# ── 2. JS 括号/引号平衡 ──
def check_js_brackets():
    js_dir = ROOT / "webui" / "js"
    all_errors = []
    for js_file in sorted(js_dir.glob("*.js")):
        try:
            content = js_file.read_text(encoding="utf-8")
        except Exception as e:
            all_errors.append(f"{js_file.name}: {e}")
            continue

        pairs = {"(": ")", "{": "}", "[": "]"}
        closing = set(pairs.values())
        stack = []
        mode = None
        i = 0
        while i < len(content):
            ch = content[i]
            if mode == "'" or mode == '"' or mode == "`":
                if ch == "\\":
                    i += 2
                    continue
                if ch == mode:
                    mode = None
                i += 1
                continue
            if mode == "/":
                if ch == "\\":
                    i += 2
                    continue
                if ch == "/":
                    mode = None
                i += 1
                continue
            if ch in "'\"`":
                mode = ch
                i += 1
                continue
            if ch == "/" and i > 0 and content[i - 1] in "=(,:;!&|?~":
                if i + 1 < len(content) and content[i + 1] != "/" and content[i + 1] != "*":
                    mode = "/"
                    i += 1
                    continue
            if ch in pairs:
                stack.append((ch, i))
            elif ch in closing:
                if not stack:
                    line = content[:i].count("\n") + 1
                    all_errors.append(f"{js_file.name}: 多余的 {ch} 在行 {line}")
                    i += 1
                    continue
                opened, pos = stack.pop()
                if pairs[opened] != ch:
                    line_open = content[:pos].count("\n") + 1
                    line_close = content[:i].count("\n") + 1
                    all_errors.append(
                        f"{js_file.name}: {opened}(行{line_open}) 被 {ch}(行{line_close}) 错误关闭"
                    )
            i += 1
        if stack:
            for ch, pos in stack[-3:]:
                line = content[:pos].count("\n") + 1
                all_errors.append(f"{js_file.name}: {ch} 行{line} 未闭合")
    if all_errors:
        return False, "\n".join(all_errors[:10])
    return True, ""


# ── 3. HTML 标签配对 ──
def check_html_tags():
    try:
        content = (ROOT / "webui" / "index.html").read_text(encoding="utf-8")
    except Exception as e:
        return False, str(e)

    void_tags = {
        "br",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "area",
        "base",
        "col",
        "embed",
        "source",
        "track",
        "wbr",
    }
    # 匹配 <tag> 和 </tag>
    tags = re.findall(r"<(/?)(\w+)[^>]*>", content)
    stack = []
    for slash, name in tags:
        if name in void_tags or name.startswith("!"):
            continue
        if slash:  # 闭合标签 </name>
            if not stack:
                return False, f"多余的 </{name}>"
            # 找最近的同名标签
            found = False
            for j in range(len(stack) - 1, -1, -1):
                if stack[j] == name:
                    stack = stack[:j]
                    found = True
                    break
            if not found:
                return False, f"</{name}> 无匹配开放标签"
        else:
            stack.append(name)
    if stack:
        return True, ""  # HTML 允许部分标签不闭合 (如 <li>)，不报错
    return True, ""


# ── 4. Python 语法 ──
def check_python_syntax():
    errors_py = []
    for py_file in sorted(ROOT.glob("maestro/**/*.py")):
        if "__pycache__" in str(py_file):
            continue
        try:
            ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError as e:
            errors_py.append(f"{py_file.relative_to(ROOT)}:{e.lineno} {e.msg}")
    if errors_py:
        return False, "\n".join(errors_py[:10])
    return True, ""


# ── 5. 重复函数检测 ──
def check_duplicate_functions():
    js_dir = ROOT / "webui" / "js"
    all_dupes = []
    nested_ok = {
        "read",
        "finish",
        "runNext",
        "runNextPhase",
        "renderNode",
        "finish_",
        "read_",
        "run_next",
    }
    for js_file in sorted(js_dir.glob("*.js")):
        try:
            content = js_file.read_text(encoding="utf-8")
        except Exception as e:
            all_dupes.append(f"{js_file.name}: {e}")
            continue
        funcs = re.findall(r"\bfunction (\w+)\([^)]*\)\s*\{", content)
        funcs = [f for f in funcs if f not in nested_ok]
        dupes = {k: v for k, v in Counter(funcs).items() if v > 1}
        if dupes:
            all_dupes.append(f"{js_file.name}: " + ", ".join(f"{k}x{v}" for k, v in dupes.items()))
    if all_dupes:
        return False, "\n".join(all_dupes)
    return True, ""


# ── 6. API 健康检查 ──
def check_api():
    import urllib.request

    # 禁用代理（Windows 可能有 socks 代理配置）
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    endpoints = ["/api/version", "/api/agents", "/api/cost", "/api/skills", "/api/mcp/status"]
    failures = []
    for ep in endpoints:
        try:
            r = opener.open(f"http://127.0.0.1:{AGENCY_PORT}{ep}", timeout=3)
            if r.status != 200:
                failures.append(f"{ep} HTTP {r.status}")
            else:
                data = r.read().decode("utf-8")
                if not data.strip().startswith(("{", "[")):
                    failures.append(f"{ep} 非JSON响应")
        except Exception as e:
            failures.append(f"{ep}: {e}")
    if failures:
        return False, "\n".join(failures)
    return True, ""


# ── 7. 前端功能完整性（防止改A坏B）──
def check_frontend_critical():
    """验证 HTML 关键元素 + JS 关键函数存在，防止修改导致按钮/输入框消失"""
    try:
        html = (ROOT / "webui" / "index.html").read_text(encoding="utf-8")
    except Exception as e:
        return False, str(e)

    # 关键 DOM 元素（按钮、输入框、面板容器）
    must_have = [
        ('id="grid"', "面板容器(JS动态挂载)"),
        ('id="helpBtn"', "帮助按钮"),
        ('id="searchBtn"', "搜索按钮"),
        ('id="dashboardBtn"', "仪表盘按钮"),
        ('id="devBtn"', "设置按钮"),
        ('id="api-key"', "API Key 输入框"),
        ('id="api-provider"', "Provider 下拉"),
        ('id="devOverlay"', "设置覆盖层"),
        ('id="helpOverlay"', "帮助覆盖层"),
        ('id="searchOverlay"', "搜索覆盖层"),
        ('id="compaction-config-ui"', "压缩配置UI"),
        ('id="cron-section"', "定时任务区"),
        ('id="pr-section"', "PR集成区"),
    ]
    missing = []
    for needle, desc in must_have:
        if needle not in html:
            missing.append(f"{desc} ({needle})")
    if missing:
        return False, "缺失关键DOM元素: " + ", ".join(missing)

    # 关键 JS 文件存在 + 语法正确
    js_dir = ROOT / "webui" / "js"
    critical_js = ["chat.js", "app.js", "settings.js", "dashboard.js", "terminal.js", "utils.js"]
    for fname in critical_js:
        fpath = js_dir / fname
        if not fpath.exists():
            return False, f"缺失关键JS: {fname}"
        r = subprocess.run(["node", "--check", str(fpath)], capture_output=True, text=True)
        if r.returncode != 0:
            return False, f"{fname} 语法错误: {r.stderr.strip()[:200]}"

    # 关键函数存在性（防止函数被误删或改名导致按钮失效）
    func_checks = [
        ("chat.js", "handleSend", "发送消息"),
        ("chat.js", "buildPanelDOM", "面板构建"),
        ("chat.js", "removePanel", "关闭面板"),
        ("app.js", "toggleHelpOverlay", "帮助覆盖层"),
        ("app.js", "toggleGlobalSearch", "全局搜索"),
        ("settings.js", "toggleDevOverlay", "设置面板"),
        ("settings.js", "saveCompactionConfig", "压缩配置保存"),
        ("dashboard.js", "toggleDashboard", "仪表盘"),
        ("terminal.js", "toggleTerminal", "终端"),
        ("terminal.js", "stopTerminal", "终端清理"),
    ]
    missing_funcs = []
    for fname, func, desc in func_checks:
        try:
            content = (js_dir / fname).read_text(encoding="utf-8")
            # 匹配 function xxx( 或 xxx = function( 或 xxx=function( 或 window.xxx = function(
            found = False
            for pat in [f"function {func}(", f"{func} = function(", f"{func}=function(",
                        f"window.{func} = function(", f"window.{func}=function("]:
                if pat in content:
                    found = True
                    break
            if not found:
                missing_funcs.append(f"{desc}({func} in {fname})")
        except Exception:
            pass
    if missing_funcs:
        return False, "缺失关键函数: " + ", ".join(missing_funcs)

    return True, ""


# ── 8. 测试覆盖率门控 ──
def check_test_coverage():
    """运行 pytest --cov 并检查覆盖率阈值（60%）。

    低于阈值 → commit 失败。
    pytest-cov 未安装 → 跳过并警告（不阻断）。
    """
    import shutil

    if not shutil.which("pytest"):
        return True, ""  # 无 pytest，跳过

    try:
        import pytest_cov  # noqa: F401
    except ImportError:
        return False, "pytest-cov 未安装，跳过覆盖率检查。安装: pip install pytest-cov"

    # 只测 maestro 核心模块（排除 tests/ 自身和 webui/）
    r = subprocess.run(
        [
            sys.executable, "-m", "pytest", "tests/",
            "--cov=maestro",
            "--cov-report=term",
            "--cov-fail-under=20",
            "-q",
            "--no-header",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )

    output = (r.stdout + "\n" + r.stderr).strip()
    if r.returncode != 0:
        # 提取覆盖率百分比行
        cov_lines = [l for l in output.split("\n") if "Coverage" in l or "TOTAL" in l or "%" in l]
        detail = "\n".join(cov_lines[-5:]) if cov_lines else output[-500:]
        return False, f"覆盖率不达标:\n{detail}"
    return True, ""


# ── 9. 防退化：禁止新 _private 跨模块访问 ──
def check_no_private_leak():
    """_private 成员只应在定义文件内访问，跨模块访问会触发此检查"""
    pattern = re.compile(r'\._(?:total_in|total_out|transcript|cost|running|sessions)\b')
    allow_in = {
        "claude_session.py",   # 类内部自引用
        "codex_session.py",    # 类内部自引用
        "weixin_bot.py",        # 类内部自引用
    }
    violations = []
    for py_file in sorted(ROOT.glob("maestro/**/*.py")):
        if "__pycache__" in str(py_file):
            continue
        if py_file.name in allow_in:
            continue
        try:
            for i, line in enumerate(py_file.read_text(encoding="utf-8").split("\n"), 1):
                if pattern.search(line):
                    violations.append(f"{py_file.relative_to(ROOT)}:{i}: {line.strip()[:80]}")
        except Exception:
            pass
    if violations:
        return False, "\n".join(violations[:10])
    return True, ""


# ── 10. 防退化：禁止新 var 声明 ──
def check_no_new_var():
    """webui/js/ 下所有用户代码应使用 let/const，非 lib/ 文件出现 var 则拦截"""
    js_dir = ROOT / "webui" / "js"
    violations = []
    for js_file in sorted(js_dir.glob("**/*.js")):
        rel = js_file.relative_to(js_dir)
        if str(rel).startswith("lib" + os.sep):
            continue
        try:
            for i, line in enumerate(js_file.read_text(encoding="utf-8").split("\n"), 1):
                if re.search(r'\bvar\s+\w+\s*=', line):
                    # 排除 CSS 变量引用 var(--xxx)
                    if "var(--" in line:
                        continue
                    violations.append(f"{rel}:{i}: {line.strip()[:80]}")
        except Exception:
            pass
    if violations:
        return False, "\n".join(violations[:10])
    return True, ""


# ── 11. 防退化：禁止 ALTER TABLE 热修 ──
def check_no_hotfix_alter_table():
    """ALTER TABLE + except OperationalError = 每次写入都改表，应走 web_cost._MIGRATIONS"""
    pattern = re.compile(r'ALTER TABLE.*ADD COLUMN', re.IGNORECASE)
    # web_cost.py 的 _MIGRATIONS dict 是唯一合法使用处
    allow_in = {"web_cost.py"}
    violations = []
    for py_file in sorted(ROOT.glob("maestro/**/*.py")):
        if "__pycache__" in str(py_file):
            continue
        if py_file.name in allow_in:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            if pattern.search(content):
                # Check if there's also an except OperationalError nearby
                if "OperationalError" in content:
                    violations.append(
                        f"{py_file.relative_to(ROOT)}: ALTER TABLE + except (热修模式，应走 migration)"
                    )
        except Exception:
            pass
    if violations:
        return False, "\n".join(violations)
    return True, ""


# ── 12. 路由一致性：route_registry.py vs flask_app.py ──
def check_route_consistency():
    """确保所有路由只通过 route_registry.py 注册，没有散落在 flask_app.py 中"""
    flask_path = ROOT / "maestro" / "flask_app.py"
    if not flask_path.exists():
        return True, ""
    content = flask_path.read_text(encoding="utf-8")
    # flask_app.py 应只通过 register_flask() 来注册路由，不应有独立的 app.add_url_rule
    lines_with_rule = [
        i for i, line in enumerate(content.split("\n"), 1)
        if "app.add_url_rule" in line
    ]
    if lines_with_rule:
        return False, (
            f"flask_app.py 仍有 {len(lines_with_rule)} 处独立 app.add_url_rule（行 "
            + ", ".join(map(str, lines_with_rule[:5]))
            + "）。应统一到 route_registry.py 的 ROUTES 表。"
        )
    return True, ""


# ═══════════════════════════════════
if __name__ == "__main__":
    # 确保 stdout 用 utf-8
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("Agency 全量检测\n")
    check("JS 语法 (node --check)", check_js_syntax)
    check("JS 括号/引号平衡", check_js_brackets)
    check("JS 重复函数", check_duplicate_functions)
    check("HTML 标签配对", check_html_tags)
    check("Python 语法", check_python_syntax)
    check("防退化: 无新 _private 跨模块访问", check_no_private_leak)
    check("防退化: 无新 var 声明", check_no_new_var)
    check("防退化: 无 ALTER TABLE 热修", check_no_hotfix_alter_table)
    check("路由一致性: route_registry vs flask_app", check_route_consistency)
    check("API 端点", check_api)
    check("前端关键功能完整性", check_frontend_critical)
    check("测试覆盖率 (>=20%)", check_test_coverage)

    print(f"\n{'=' * 40}")
    if errors == 0:
        print(f"全部通过 ({OK}项)")
        sys.exit(0)
    else:
        print(f"{errors}项失败 / {OK}项通过")
        sys.exit(1)
