#!/usr/bin/env python3
"""
Agency Run — 独立运行入口
配一个 key 就能用，不依赖 Claude Code。

用法:
  python maestro/run.py coder "写一个快排函数"
  python maestro/run.py explorer "找到所有 TODO"
  python maestro/run.py --model deepseek-reasoner planner "设计用户系统架构"
  python maestro/run.py --list          # 列出所有可用 Agent
"""

import os
import sys
import json
import yaml
import requests
from pathlib import Path

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

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


# ── 加载 Agent ──────────────────────────────────
def load_agent(name):
    """读 agents/{name}.md，返回 (system_prompt, model)"""
    agent_file = PROJECT_ROOT / "agents" / f"{name}.md"
    if not agent_file.exists():
        # 尝试模糊匹配
        for f in (PROJECT_ROOT / "agents").glob("*.md"):
            if name in f.stem:
                agent_file = f
                break

    if not agent_file.exists():
        print(f"✗ Agent '{name}' 不存在。用 --list 查看可用 Agent。")
        sys.exit(1)

    content = agent_file.read_text(encoding="utf-8")

    # 解析 YAML frontmatter
    model = DEFAULT_MODEL
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if fm:
                    model_map = {"haiku": "deepseek-chat", "sonnet": "deepseek-chat", "opus": "deepseek-reasoner"}
                    model = model_map.get(fm.get("model", ""), DEFAULT_MODEL)
            except Exception:
                pass
            system_prompt = parts[2].strip()
    else:
        system_prompt = content.strip()

    return system_prompt, model


def list_agents():
    """列出所有可用 Agent"""
    agents_dir = PROJECT_ROOT / "agents"
    print("可用 Agent：\n")
    for f in sorted(agents_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        name = f.stem
        desc = ""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    desc = fm.get("description", "")
                except Exception:
                    pass
        print(f"  {name:<25} {desc}")
    print(f"\n用法: python maestro/run.py <agent名> \"你的任务\"\n")


# ── DeepSeek API 调用 ────────────────────────────
def chat(system_prompt, user_message, model=DEFAULT_MODEL):
    """调 DeepSeek Chat API，流式输出"""
    if not DEEPSEEK_API_KEY:
        print("=" * 50)
        print("  需要配置 DeepSeek API Key")
        print("=" * 50)
        print()
        print("1. 打开 https://platform.deepseek.com/api_keys")
        print("2. 创建 API Key")
        print("3. 在项目根目录创建 .env 文件：")
        print()
        print("     DEEPSEEK_API_KEY=sk-xxxxxxxx")
        print()
        print("   或者设置环境变量：")
        print()
        print("     export DEEPSEEK_API_KEY=sk-xxxxxxxx")
        print()
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE}/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=120,
        )

        if resp.status_code != 200:
            print(f"✗ API 错误 ({resp.status_code}): {resp.text[:500]}")
            sys.exit(1)

        print()  # 分隔
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
                except json.JSONDecodeError:
                    pass
        print()  # 结尾换行

    except requests.exceptions.ConnectionError:
        print("✗ 无法连接 DeepSeek API。检查网络或代理设置。")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n已中断。")
        sys.exit(0)


# ── 主入口 ───────────────────────────────────
def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    if sys.argv[1] == "--list":
        list_agents()
        return

    # 解析参数
    model = DEFAULT_MODEL
    args = sys.argv[1:]

    if args[0] == "--model":
        if len(args) < 3:
            print("用法: python maestro/run.py --model <模型名> <agent名> \"任务\"")
            sys.exit(1)
        model = args[1]
        args = args[2:]

    agent_name = args[0]
    task = args[1] if len(args) > 1 else ""

    if not task:
        task = input("任务描述: ").strip()
        if not task:
            print("任务不能为空。")
            sys.exit(1)

    # 加载 Agent
    system_prompt, agent_model = load_agent(agent_name)

    # 如果命令行没指定 model，用 agent frontmatter 里的
    if model == DEFAULT_MODEL:
        model = agent_model

    print(f"Agent: {agent_name} | 模型: {model} | 任务: {task[:50]}...")

    # 调 API
    chat(system_prompt, task, model)


if __name__ == "__main__":
    main()
