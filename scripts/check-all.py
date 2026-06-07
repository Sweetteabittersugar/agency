#!/usr/bin/env python3
"""Agency 全量检测 — JS/Python/API 一把梭"""
import subprocess, sys, os, json, ast, re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
os.chdir(str(ROOT))

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
    r = subprocess.run(["node", "--check", "webui/app.js"], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


# ── 2. JS 括号/引号平衡 ──
def check_js_brackets():
    try:
        content = (ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    except Exception as e:
        return False, str(e)

    pairs = {"(": ")", "{": "}", "[": "]"}
    closing = set(pairs.values())
    stack = []
    # 状态: None=代码, "'"=单引号, '"'=双引号, '`'=模板, '/'=正则
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
        if mode == "/":  # 正则字面量内
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
        # 检测正则字面量开头 (跟在 = ( , ; : 后面的 /)
        if ch == "/" and i > 0 and content[i - 1] in "=(,:;!&|?~":
            # 排除注释 //
            if i + 1 < len(content) and content[i + 1] != "/" and content[i + 1] != "*":
                mode = "/"
                i += 1
                continue
        if ch in pairs:
            stack.append((ch, i))
        elif ch in closing:
            if not stack:
                line = content[:i].count("\n") + 1
                return False, f"多余的 {ch} 在行 {line}"
            opened, pos = stack.pop()
            if pairs[opened] != ch:
                line_open = content[:pos].count("\n") + 1
                line_close = content[:i].count("\n") + 1
                return False, f"{opened}(行{line_open}) 被 {ch}(行{line_close}) 错误关闭"
        i += 1

    if stack:
        msgs = []
        for ch, pos in stack[-5:]:
            line = content[:pos].count("\n") + 1
            msgs.append(f"  {ch} 行{line}")
        return False, f"{len(stack)} 个未闭合:\n" + "\n".join(msgs)
    return True, ""


# ── 3. HTML 标签配对 ──
def check_html_tags():
    try:
        content = (ROOT / "webui" / "index.html").read_text(encoding="utf-8")
    except Exception as e:
        return False, str(e)

    void_tags = {"br", "hr", "img", "input", "link", "meta", "area", "base",
                 "col", "embed", "source", "track", "wbr"}
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
    try:
        content = (ROOT / "webui" / "app.js").read_text(encoding="utf-8")
    except Exception as e:
        return False, str(e)
    # 检查函数名重复（嵌套闭包如 read/finish 是正常的，不报）
    funcs = re.findall(r"\bfunction (\w+)\([^)]*\)\s*\{", content)
    # 过滤已知的正常嵌套函数名
    nested_ok = {"read", "finish", "runNext", "runNextPhase", "renderNode"}
    funcs = [f for f in funcs if f not in nested_ok]
    dupes = {k: v for k, v in Counter(funcs).items() if v > 1}
    if dupes:
        return False, "重复的函数声明: " + ", ".join(f"{k}x{v}" for k, v in dupes.items())
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
            r = opener.open(f"http://127.0.0.1:8800{ep}", timeout=3)
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
    check("API 端点", check_api)

    print(f"\n{'='*40}")
    if errors == 0:
        print(f"全部通过 ({OK}项)")
        sys.exit(0)
    else:
        print(f"{errors}项失败 / {OK}项通过")
        sys.exit(1)
