#!/usr/bin/env python3
"""Agency 前端语法检查 —— 每次改完 index.html 跑"""

import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

html_path = Path(__file__).resolve().parent.parent / "webui" / "index.html"
html = html_path.read_text(encoding="utf-8")

errors = 0
for i, m in enumerate(re.finditer(r"<script>(.*?)</script>", html, re.DOTALL)):
    js = m.group(1)
    b = js.count("{") - js.count("}")
    p = js.count("(") - js.count(")")
    br = js.count("[") - js.count("]")
    if b or p or br:
        print(f"❌ Script block {i + 1}: braces={b:+d} parens={p:+d} brackets={br:+d}")
        errors += 1
    else:
        print(f"✅ Script block {i + 1}: balanced")

# Check paired HTML tags
for tag in ["div", "nav", "span", "button", "details", "summary"]:
    opens = len(re.findall(f"<{tag}[\\s>]", html))
    closes = len(re.findall(f"</{tag}>", html))
    if opens != closes:
        print(f"❌ HTML tag <{tag}>: opens={opens} closes={closes}")
        errors += 1

if errors:
    print(f"\n{errors} error(s) found!")
    sys.exit(1)
print("\nAll checks passed ✅")
sys.exit(0)
