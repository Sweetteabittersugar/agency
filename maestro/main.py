#!/usr/bin/env python3
"""
Agency — 主入口
你说任务，系统自动选 Agent、调 API、返回结果。

用法:
  python maestro/main.py "帮我写一个排序函数"
  python maestro/main.py "审查这段代码的安全性"
  python maestro/main.py "找到所有 TODO 注释"
  python maestro/main.py --model deepseek-reasoner "设计用户系统架构"
  python maestro/main.py --list-routes    # 查看路由表
"""

import os
import sys
import json
import yaml
import time
import sqlite3
import requests
from pathlib import Path
from datetime import datetime

# ── 项目根目录 ──────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── 加载 .env ──────────────────────────────────
def load_env():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = val

load_env()

DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "deepseek-chat")

MODEL_MAP = {
    "haiku": os.environ.get("LIGHT_MODEL", "deepseek-chat"),
    "sonnet": os.environ.get("STANDARD_MODEL", "deepseek-chat"),
    "opus": os.environ.get("HEAVY_MODEL", "deepseek-reasoner"),
}


def get_provider_config():
    """解析 API 配置，返回 (base_url, api_key, headers)"""
    base_url = ""
    api_key = ""

    # DeepSeek
    if os.environ.get("DEEPSEEK_API_KEY"):
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        api_key = os.environ["DEEPSEEK_API_KEY"]
    # OpenAI 兼容
    elif os.environ.get("OPENAI_API_KEY"):
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.environ["OPENAI_API_KEY"]
    # Ollama
    elif os.environ.get("OLLAMA_BASE_URL"):
        base_url = os.environ["OLLAMA_BASE_URL"]
        api_key = "ollama"
    else:
        return None, None, None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if api_key == "ollama":
        headers = {"Content-Type": "application/json"}

    return base_url.rstrip("/"), api_key, headers


def get_actual_model(agent_model_name):
    """将 agent frontmatter 中的模型名映射到实际模型"""
    return MODEL_MAP.get(agent_model_name, DEFAULT_MODEL)

# ── 路由矩阵 ───────────────────────────────────
ROUTING = {
    "coder": ["写", "改", "重构", "代码", "实现", "开发", "修复", "bug", "函数", "类", "模块"],
    "explorer": ["查", "搜", "找", "定位", "分析", "grep", "搜索", "在哪", "哪些文件"],
    "code-reviewer": ["审查", "review", "检查代码"],
    "python-reviewer": ["python", "django", "fastapi", "flask", "pip", "pytest"],
    "go-reviewer": ["go ", "golang", "goroutine", "go mod"],
    "typescript-reviewer": ["typescript", "ts ", "react", "node.js", "前端", "vue"],
    "security-reviewer": ["安全", "审计", "漏洞", "注入", "xss", "csrf", "加密"],
    "test-runner": ["测试", "验证", "跑测试", "跑一下", "test", "通过没"],
    "tdd-guide": ["tdd", "测试驱动", "先写测试"],
    "e2e-runner": ["e2e", "端到端", "playwright", "浏览器测试"],
    "build-error-resolver": ["构建", "编译", "构建错误", "编译失败", "build error", "装不上"],
    "planner": ["规划", "设计", "架构", "方案", "计划", "怎么实现", "技术选型"],
    "database-reviewer": ["数据库", "sql", "schema", "索引", "查询", "慢查询", "postgres", "mysql"],
    "performance-optimizer": ["性能", "优化", "瓶颈", "慢", "卡", "内存", "cpu"],
    "cost-analyst": ["费用", "用量", "成本", "花了多少", "账单"],
    "doc-updater": ["文档", "readme", "changelog", "更新文档"],
    "refactor-cleaner": ["清理", "死代码", "重复", "未用依赖", "删掉"],
    "general-worker": ["整理", "配置", "杂务", "通用", "帮我看"],
    "webnovel-writer": ["小说", "章节", "大纲", "人物", "世界观", "故事"],
    "orchestrator": ["拆解", "分配", "协作", "多个任务", "全部", "整套", "完整项目", "全流程"],
}


def route_task(task):
    """根据任务关键词匹配最佳 Agent，平局时优先更精确/更专业的 agent"""
    task_lower = task.lower()
    scores = {}
    for agent, keywords in ROUTING.items():
        score = 0
        total_kw_len = 0
        for kw in keywords:
            if kw.lower() in task_lower:
                score += 1
                total_kw_len += len(kw)
        if score > 0:
            # 三元组：(命中数, 命中关键词总长, -关键词总数)
            # 数多 > 字长(精确) > 词少(专业)
            scores[agent] = (score, total_kw_len, -len(keywords))

    if not scores:
        return "coder", 0  # 默认 coder

    best = max(scores, key=scores.get)
    return best, scores[best][0]


# ── Agent 加载 ─────────────────────────────────
def load_agent(name):
    """读 agents/{name}.md，返回 system_prompt"""
    agent_file = PROJECT_ROOT / "agents" / f"{name}.md"
    if not agent_file.exists():
        # 模糊匹配
        for f in (PROJECT_ROOT / "agents").glob("*.md"):
            if name in f.stem:
                agent_file = f
                break

    if not agent_file.exists():
        return f"你是一个 {name}。请完成任务。", DEFAULT_MODEL

    content = agent_file.read_text(encoding="utf-8")
    model = DEFAULT_MODEL

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if fm:
                    model = get_actual_model(fm.get("model", ""))
            except Exception:
                pass
            return parts[2].strip(), model

    return content.strip(), model


# ── DeepSeek API ───────────────────────────────
def chat(system_prompt, user_message, model=DEFAULT_MODEL):
    """流式调用 LLM API（多提供者支持）"""
    base_url, api_key, headers = get_provider_config()
    if not base_url:
        print("=" * 50)
        print("  需要配置 API Key")
        print("=" * 50)
        print()
        print("在项目根目录创建 .env，配置以下之一：")
        print("  DEEPSEEK_API_KEY=sk-xxxxxxxx")
        print("  OPENAI_API_KEY=sk-xxxxxxxx")
        print("  OLLAMA_BASE_URL=http://localhost:11434/v1")
        sys.exit(1)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 8192,
    }

    start_time = time.time()
    in_tokens = len(system_prompt) // 4 + len(user_message) // 4  # 粗略估算
    out_chars = 0

    max_retries = 2
    resp = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=300,
            )
            break
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                time.sleep(1)
            else:
                print(f"\n✗ 连接失败，已重试{max_retries}次")
                return in_tokens, 0, 0
        except KeyboardInterrupt:
            print("\n\n已中断。")
            return in_tokens, 0, 0

    if resp is None:
        return in_tokens, 0, 0

    if resp.status_code != 200:
        print(f"\n✗ API 错误 ({resp.status_code}): {resp.text[:300]}")
        return in_tokens, 0, 0

    print()
    for line in resp.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8")
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    print(content, end="", flush=True)
                    out_chars += len(content)
            except json.JSONDecodeError:
                pass
    print()

    elapsed = time.time() - start_time
    out_tokens = out_chars // 2
    cost = estimate_cost(model, in_tokens, out_tokens)

    print(f"\n── Agent: {current_agent} | 模型: {model} | {elapsed:.1f}s | ~${cost:.4f}")

    # 记录成本
    record_cost(in_tokens, out_tokens, cost, model, elapsed)

    return in_tokens, out_tokens, cost


# ── 成本估算 ───────────────────────────────────
PRICING = {
    "deepseek-chat":    (0.27, 1.10),    # $/1M tokens (input, output)
    "deepseek-reasoner": (0.55, 2.19),
}

def estimate_cost(model, in_tokens, out_tokens):
    """估算费用"""
    if model in PRICING:
        in_price, out_price = PRICING[model]
        return (in_tokens / 1_000_000) * in_price + (out_tokens / 1_000_000) * out_price
    return 0.0


def record_cost(in_tokens, out_tokens, cost, model, elapsed):
    """记录到 cost.db"""
    try:
        db_path = PROJECT_ROOT / "maestro" / "cost.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT, channel TEXT, model TEXT,
                in_tokens INTEGER, out_tokens INTEGER,
                cost_usd REAL, duration_s REAL
            )
        """)
        conn.execute(
            "INSERT INTO costs (time, channel, model, in_tokens, out_tokens, cost_usd, duration_s) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), "main", model, in_tokens, out_tokens, cost, elapsed),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        import logging
        logging.warning(f"cost recording failed (non-fatal): {e}")


# ── 全局变量（用于显示） ────────────────────────
current_agent = ""


# ── 主入口 ─────────────────────────────────────
def main():
    global current_agent

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    if sys.argv[1] == "--list-routes":
        print("路由表：\n")
        for agent, keywords in ROUTING.items():
            print(f"  {agent:<25} → {', '.join(keywords[:5])}...")
        return

    # 解析参数
    model = DEFAULT_MODEL
    args = sys.argv[1:]

    if args[0] == "--model":
        if len(args) < 3:
            print("用法: python maestro/main.py --model <模型名> \"任务\"")
            return
        model = args[1]
        args = args[2:]

    task = " ".join(args) if args else ""
    if not task:
        task = input("任务描述: ").strip()
        if not task:
            print("任务不能为空。")
            return

    # 路由
    agent_name, score = route_task(task)
    current_agent = agent_name

    print(f"→ 路由: {agent_name} (匹配度: {score})")

    # 加载 Agent
    system_prompt, agent_model = load_agent(agent_name)
    if model == DEFAULT_MODEL:
        model = agent_model

    # 执行
    chat(system_prompt, task, model)


if __name__ == "__main__":
    main()
