"""冒烟测试 — 提交前自动验证核心功能未退化
不可移除——每次 commit 前自动运行，防止改 A 坏 B"""
import urllib.request, json, sys, os

BASE = "http://127.0.0.1:8800"
FAIL = 0
TOTAL = 0

def check(name, fn):
    global TOTAL, FAIL
    TOTAL += 1
    try:
        fn()
        print(f"  [PASS] {name}")
    except Exception as e:
        FAIL += 1
        print(f"  [FAIL] {name}: {e}")

# 1. 服务可达
check("health", lambda: None if json.loads(
    urllib.request.urlopen(f"{BASE}/api/health", timeout=5).read()
).get("status") else (_ for _ in ()).throw(Exception("no status")))

# 2. 首页 200
check("index", lambda: None if urllib.request.urlopen(
    f"{BASE}/", timeout=5
).status == 200 else (_ for _ in ()).throw(Exception("index not 200")))

# 3. 关键 JS 文件全 200（前端加载链不断）
for f in ["js/chat.js", "js/app.js", "js/settings.js", "js/dashboard.js",
          "js/terminal.js", "js/utils.js", "style.css", "css/panels.css"]:
    check(f"static:{f}", lambda u=f"/{f}": None if urllib.request.urlopen(
        f"{BASE}{u}", timeout=5
    ).status == 200 else (_ for _ in ()).throw(Exception(f"{u} not 200")))

# 4. API 关键端点
for ep in ["/api/agents", "/api/settings", "/api/cost/summary",
           "/api/sessions/processes", "/api/cron", "/api/search?q=test",
           "/api/worktrees", "/api/sessions/timeline"]:
    check(f"api:{ep}", lambda u=ep: json.loads(
        urllib.request.urlopen(f"{BASE}{u}", timeout=5).read()
    ))

# 5. Python import 核心模块
mods = ["maestro.flask_app", "maestro.terminal", "maestro.models",
        "maestro.shared", "maestro.ws_chat", "maestro.cron_scheduler",
        "maestro.routes.chat", "maestro.routes.search", "maestro.routes.pr",
        "maestro.routes.session_replay"]
for m in mods:
    check(f"import:{m}", lambda x=m: __import__(x))

# 6. Provider 完整性
check("providers", lambda: None if all(
    __import__("maestro.shared").build_isolated_env("t", p).get("ANTHROPIC_MODEL")
    for p in ["deepseek","anthropic","openai","google","xai","qwen","zhipu"]
) else (_ for _ in ()).throw(Exception("provider missing")))

print(f"\n{TOTAL-FAIL}/{TOTAL} 通过" + (" ✅" if FAIL==0 else f" ❌ {FAIL} FAIL"))
sys.exit(FAIL)
