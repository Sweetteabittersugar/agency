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
import hashlib
import sqlite3
import requests
from pathlib import Path
from datetime import datetime

# ── 项目根目录 ──────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── 加载 .env ──────────────────────────────────
from maestro.env_loader import load_dotenv
load_dotenv(PROJECT_ROOT)

sys.path.insert(0, str(PROJECT_ROOT / "maestro"))
from models import get_provider_config, resolve_model, get_default_model

DEFAULT_MODEL = get_default_model()

# ── 路由矩阵 ───────────────────────────────────
ROUTING = {
    "coder": [
        "写", "改", "重构", "代码", "实现", "开发", "修复", "bug",
        "函数", "类", "模块", "接口", "api", "后端", "脚本", "算法",
        "写一个", "改一下", "修bug", "编程", "程序", "加个功能",
        "新建文件", "改代码", "写代码", "改函数",
    ],
    "explorer": [
        "查", "搜", "找", "定位", "分析", "grep", "搜索", "在哪",
        "哪些文件", "找一下", "看看哪里", "找找看", "搜一下",
        "哪里有", "查一下", "过一遍", "排查", "追溯",
    ],
    "code-reviewer": [
        "审查", "review", "检查代码", "代码审查", "代码检查",
        "code review", "审阅", "复查", "检查一下",
    ],
    "python-reviewer": [
        "python", "django", "fastapi", "flask", "pip", "pytest",
        "python代码", "py文件", "python项目",
    ],
    "go-reviewer": [
        "go ", "golang", "goroutine", "go mod", "go代码",
        "go项目", "go语言",
    ],
    "typescript-reviewer": [
        "typescript", "ts ", "react", "node.js", "前端", "vue",
        "javascript", "js ", "tsx", "jsx", "组件",
    ],
    "security-reviewer": [
        "安全", "审计", "漏洞", "注入", "xss", "csrf", "加密",
        "安全隐患", "安全检查", "安全审查", "sql注入",
    ],
    "test-runner": [
        "测试", "验证", "跑测试", "跑一下", "test", "通过没",
        "单元测试", "集成测试", "测试用例", "跑一遍", "验证一下",
    ],
    "tdd-guide": ["tdd", "测试驱动", "先写测试", "测试驱动开发"],
    "e2e-runner": [
        "e2e", "端到端", "playwright", "浏览器测试",
        "端到端测试", "e2e测试",
    ],
    "build-error-resolver": [
        "构建", "编译", "构建错误", "编译失败", "build error",
        "装不上", "构建失败", "编译报错", "装不了",
    ],
    "planner": [
        "规划", "设计", "架构", "方案", "计划", "怎么实现",
        "技术选型", "系统设计", "设计方案", "整体设计",
        "架构设计", "规划一下", "设计一下",
    ],
    "database-reviewer": [
        "数据库", "sql", "schema", "索引", "查询", "慢查询",
        "postgres", "mysql", "orm", "表结构", "建表",
    ],
    "performance-optimizer": [
        "性能", "优化", "瓶颈", "慢", "卡", "内存", "cpu",
        "性能优化", "加速", "提速", "快一点", "太慢",
    ],
    "cost-analyst": [
        "费用", "用量", "成本", "花了多少", "账单",
        "花费", "费用统计", "成本分析",
    ],
    "doc-updater": [
        "文档", "readme", "changelog", "更新文档",
        "写文档", "补文档", "更新readme",
    ],
    "refactor-cleaner": [
        "清理", "死代码", "重复", "未用依赖", "删掉",
        "重构整理", "代码清理", "精简",
    ],
    "general-worker": [
        "整理", "配置", "杂务", "通用", "帮我看",
        "帮我看看", "处理一下", "帮忙", "看下",
    ],
    "webnovel-writer": [
        "小说", "章节", "大纲", "人物", "世界观", "故事",
        "写小说", "情节", "角色", "续写",
    ],
    "orchestrator": [
        "拆解", "分配", "协作", "多个任务", "全部", "整套",
        "完整项目", "全流程", "所有任务", "全部完成",
        "统筹", "编排",
    ],
    "ceo": [
        "产品", "需求", "优先级", "用户故事", "验收标准", "功能范围",
        "功能需求", "需求分析", "产品需求", "prd",
    ],
    "qa": [
        "测试策略", "边界用例", "回归", "qa", "质量保证", "测试计划",
        "测试用例", "边界条件", "异常测试", "质量", "用例设计",
    ],
    "devops": [
        "ci/cd", "docker", "部署", "环境配置", "devops", "运维",
        "容器化", "dockerfile", "k8s", "kubernetes", "上线",
        "ci", "cd", "容器", "镜像", "编排",
    ],
    "release-manager": [
        "发布", "版本", "changelog", "tag", "release", "回滚",
        "semver", "发版", "版本号", "发布管理", "发布检查",
        "release note", "发布说明",
    ],
    "lead": [
        "委派", "领导", "异步", "后台执行", "大任务", "lead",
        "异步任务", "后台任务", "委派任务", "领导任务",
    ],
}


def route_task(task, force_agent=None):
    """路由 v2 -- 加权关键词匹配 + 置信度"""
    if force_agent:
        return force_agent, 99, 0.99

    task_lower = task.lower()
    scores = {}

    for agent, keywords in ROUTING.items():
        score = 0
        matched = []
        for kw in keywords:
            if kw.lower() in task_lower:
                # 加权：长关键词 > 短，越长越精确
                weight = len(kw) * 2
                score += weight
                matched.append(kw)
        if score > 0:
            scores[agent] = {"score": score, "matched": matched}

    if not scores:
        return "coder", 0, 0.0

    # 成功率权重调整（复合学习）
    agent_stats = get_agent_stats()
    for agent_name in list(scores.keys()):
        if agent_name in agent_stats:
            rate = agent_stats[agent_name]["success_rate"]
            if rate < 0.5 and agent_stats[agent_name]["total"] >= 3:
                scores[agent_name]["score"] = int(scores[agent_name]["score"] * 0.7)

    # 排序
    ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else (None, {"score": 0})

    # 置信度 = (最高分 - 次高分) / 最高分
    if second[1]["score"] > 0:
        confidence = (best[1]["score"] - second[1]["score"]) / best[1]["score"]
    else:
        confidence = 1.0

    return best[0], best[1]["score"], max(0, min(1, confidence))


def semantic_match(task):
    """基于 Jaccard 2-gram 相似度的语义匹配。零依赖，轻量实现。"""
    best_agent = "coder"
    best_score = 0.0
    task_ngrams = set()
    for i in range(len(task) - 1):
        task_ngrams.add(task[i : i + 2])

    if not task_ngrams:
        return best_agent, 0.0

    agents_dir = PROJECT_ROOT / "agents"
    if not agents_dir.exists():
        return best_agent, 0.0

    for f in sorted(agents_dir.glob("*.md")):
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        desc = ""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    desc = fm.get("description", "") if fm else ""
                except Exception:
                    pass
        if not desc:
            continue

        desc_ngrams = set()
        for i in range(len(desc) - 1):
            desc_ngrams.add(desc[i : i + 2])
        if not desc_ngrams:
            continue

        intersection = len(task_ngrams & desc_ngrams)
        union = len(task_ngrams | desc_ngrams)
        score = intersection / union if union > 0 else 0

        if score > best_score:
            best_score = score
            best_agent = f.stem

    return best_agent, best_score


def route_with_fallback(task, force_agent=None):
    """三层路由：加权关键词 -> 语义相似 -> 低置信度标记"""
    # Layer 1: 加权关键词（始终运行）
    agent, score, confidence = route_task(task, force_agent)

    if confidence >= 0.7 or force_agent:
        return agent, score, confidence, "keyword"

    # Layer 2: 语义匹配
    sem_agent, sem_score = semantic_match(task)
    if sem_agent != agent and sem_score > 0.05:
        # 语义匹配与关键词不同，且有一定匹配度
        return sem_agent, sem_score, confidence, "semantic"

    # Layer 3: 低置信度，标记
    return agent, score, confidence, "keyword_low_confidence"


# 简单 LRU 缓存：最近 100 条路由结果
import threading
_route_cache = {}  # {task_hash: (agent, score, confidence, method)}
_route_lock = threading.Lock()


def route_with_cache(task, force_agent=None):
    """带缓存的路由入口"""
    task_hash = hashlib.md5(task.encode()).hexdigest()[:8]

    with _route_lock:
        if task_hash in _route_cache and not force_agent:
            agent, score, confidence, method = _route_cache[task_hash]
            return agent, score, confidence, "cache"

    agent, score, confidence, method = route_with_fallback(task, force_agent)

    with _route_lock:
        if len(_route_cache) > 100:
            oldest = next(iter(_route_cache))
            del _route_cache[oldest]
        _route_cache[task_hash] = (agent, score, confidence, method)

    return agent, score, confidence, method


# ── Agent 加载 ─────────────────────────────────
from maestro.agent_parser import parse_agent_md

def load_agent(name):
    """读 agents/{name}.md，返回 system_prompt, model"""
    agent_file = PROJECT_ROOT / "agents" / f"{name}.md"
    if not agent_file.exists():
        # 模糊匹配
        for f in (PROJECT_ROOT / "agents").glob("*.md"):
            if name in f.stem:
                agent_file = f
                break

    if not agent_file.exists():
        return f"你是一个 {name}。请完成任务。", DEFAULT_MODEL

    info = parse_agent_md(agent_file)
    model = resolve_model(info["model"]) if info["model"] else DEFAULT_MODEL
    return info["body"], model


# ── DeepSeek API ───────────────────────────────
def chat(system_prompt, user_message, model=DEFAULT_MODEL):
    """流式调用 LLM API（多提供者支持）"""
    # === 安全护栏 ===
    from safety import check_input, check_output, sanitize_output, check_rate_limit

    # 输入安全检查
    is_safe, reason = check_input(user_message)
    if not is_safe:
        print(f"\n[安全拦截] {reason}")
        return len(system_prompt) // 4 + len(user_message) // 4, 0, 0

    # 速率限制
    if not check_rate_limit():
        print("\n[速率限制] 请求过于频繁，请稍候")
        return len(system_prompt) // 4 + len(user_message) // 4, 0, 0

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
    collected_chunks = []
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
                    collected_chunks.append(content)
                    print(content, end="", flush=True)
                    out_chars += len(content)
            except json.JSONDecodeError:
                pass
    print()

    # === 输出安全检查 ===
    output = "".join(collected_chunks)
    output = sanitize_output(output)
    is_safe, issues = check_output(output)
    if not is_safe:
        print(f"\n[安全提示] 检测到 {len(issues)} 个潜在问题")

    elapsed = time.time() - start_time
    out_tokens = out_chars // 2
    cost = estimate_cost(model, in_tokens, out_tokens)

    print(f"\n── Agent: {current_agent} | 模型: {model} | {elapsed:.1f}s | ~${cost:.4f}")

    # 记录成本
    record_cost(in_tokens, out_tokens, cost, model, elapsed)

    return in_tokens, out_tokens, cost


# ── 成本估算 ───────────────────────────────────
from models import estimate_cost, PRICING  # noqa: E402


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
    agent_name, score, confidence = route_task(task)
    current_agent = agent_name

    print(f"→ 路由: {agent_name} (得分: {score}, 置信度: {confidence:.2f})")

    # 加载 Agent
    system_prompt, agent_model = load_agent(agent_name)
    if model == DEFAULT_MODEL:
        model = agent_model

    # 执行
    chat(system_prompt, task, model)


# ── Agent 成功率追踪（Superpowers Compound Learning） ──
_agent_stats = {}  # {agent: {"success": N, "total": N}}

def record_agent_result(agent, success):
    """记录 Agent 执行结果，用于未来路由优化"""
    with _route_lock:
        if agent not in _agent_stats:
            _agent_stats[agent] = {"success": 0, "total": 0}
        _agent_stats[agent]["total"] += 1
        if success:
            _agent_stats[agent]["success"] += 1

def get_agent_stats():
    """返回 Agent 成功率统计"""
    with _route_lock:
        result = {}
        for agent, stats in _agent_stats.items():
            rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            result[agent] = {"success_rate": round(rate, 2), "total": stats["total"]}
        return result


if __name__ == "__main__":
    main()
