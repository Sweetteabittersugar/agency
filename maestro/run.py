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
import time
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
                    model = get_actual_model(fm.get("model", ""))
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
    """调 LLM API，流式输出（多提供者支持）"""
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
        "max_tokens": 4096,
    }

    max_retries = 2
    resp = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=120,
            )
            break
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                time.sleep(1)
            else:
                print(f"\n✗ 连接失败，已重试{max_retries}次")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n已中断。")
            sys.exit(0)

    if resp is None:
        sys.exit(1)

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
