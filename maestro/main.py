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

# ── 日志 ──────────────────────────────────────
import logging
log = logging.getLogger(__name__)

# ── 路由矩阵（加权关键词）────────────────────────
ROUTING = {
    "coder": [
        ("写",10),("改",10),("重构",9),("代码",10),("实现",9),("开发",9),("修复",10),("bug",8),
        ("函数",7),("类",7),("模块",7),("接口",8),("api",8),("后端",7),("脚本",7),("算法",7),
        ("写一个",9),("改一下",8),("修bug",10),("编程",8),("程序",7),("加个功能",9),
        ("新建文件",8),("改代码",9),("写代码",9),("改函数",8),
        ("死代码",7),("清理代码",7),("简化代码",6),("删掉",6),("重复",6),("精简",6),
    ],
    "explorer": [
        ("查",9),("搜",9),("找",8),("定位",8),("分析",7),("grep",8),("搜索",9),("在哪",8),
        ("哪些文件",9),("找一下",8),("看看哪里",8),("找找看",7),("搜一下",8),
        ("哪里有",7),("查一下",7),("过一遍",6),("排查",7),("追溯",7),
    ],
    "code-reviewer": [
        ("审查",10),("review",9),("检查代码",9),("代码审查",10),("代码检查",9),
        ("code review",10),("审阅",8),("复查",8),("检查一下",7),
    ],
    "python-reviewer": [
        ("python",10),("django",10),("fastapi",10),("flask",9),("pip",7),("pytest",8),
        ("python代码",9),("py文件",8),("python项目",9),
    ],
    "go-reviewer": [
        ("go",10),("golang",10),("goroutine",9),("go mod",8),("go代码",9),
        ("go项目",8),("go语言",8),
    ],
    "typescript-reviewer": [
        ("typescript",10),("ts",9),("react",10),("node.js",8),("前端",9),("vue",8),
        ("javascript",9),("js",8),("tsx",8),("jsx",8),("组件",8),
    ],
    "security-reviewer": [
        ("安全",10),("审计",8),("漏洞",10),("注入",9),("xss",10),("csrf",9),("加密",8),
        ("安全隐患",10),("安全检查",9),("安全审查",10),("sql注入",10),
    ],
    "test-runner": [
        ("测试",10),("验证",7),("跑测试",9),("跑一下",6),("test",7),("通过没",7),
        ("单元测试",9),("集成测试",8),("测试用例",8),("跑一遍",7),("验证一下",7),
        ("测试策略",9),("边界用例",8),("回归测试",9),("质量保证",7),("测试计划",8),
    ],
    "tdd-guide": [
        ("tdd",10),("测试驱动",10),("先写测试",9),("测试驱动开发",10),
    ],
    "e2e-runner": [
        ("e2e",10),("端到端",10),("playwright",10),("浏览器测试",9),
        ("端到端测试",10),("e2e测试",10),
    ],
    "build-error-resolver": [
        ("构建",10),("编译",10),("构建错误",10),("编译失败",10),("build error",8),
        ("装不上",8),("构建失败",10),("编译报错",10),("装不了",7),
    ],
    "planner": [
        ("规划",9),("设计",8),("架构",10),("方案",8),("计划",7),("怎么实现",8),
        ("技术选型",10),("系统设计",10),("设计方案",9),("整体设计",9),
        ("架构设计",10),("规划一下",8),("设计一下",7),
    ],
    "database-reviewer": [
        ("数据库",10),("sql",10),("schema",9),("索引",9),("查询",8),("慢查询",9),
        ("postgres",9),("mysql",9),("orm",8),("表结构",9),("建表",9),
    ],
    "performance-optimizer": [
        ("性能",10),("优化",9),("瓶颈",8),("慢",7),("卡",6),("内存",7),("cpu",7),
        ("性能优化",10),("加速",8),("提速",8),("快一点",6),("太慢",7),
    ],
    "cost-analyst": [
        ("费用",10),("用量",9),("成本",10),("花了多少",9),("账单",8),
        ("花费",9),("费用统计",9),("成本分析",9),
    ],
    "doc-updater": [
        ("文档",7),("readme",8),("changelog",8),("更新文档",10),
        ("写文档",9),("补文档",8),("更新readme",9),
    ],
    "general-worker": [
        ("整理",7),("配置",7),("杂务",5),("通用",7),("帮我看",6),
        ("帮我看看",6),("处理一下",5),("帮忙",5),("看下",4),
    ],
    "webnovel-writer": [
        ("小说",10),("章节",9),("大纲",8),("人物",8),("世界观",8),("故事",9),
        ("写小说",10),("情节",8),("角色",8),("续写",8),
    ],
    "orchestrator": [
        ("拆解",10),("分配",9),("协作",9),("多个任务",10),("全部",7),("整套",8),
        ("完整项目",9),("全流程",9),("所有任务",9),("全部完成",9),
        ("统筹",9),("编排",9),
    ],
    "ceo": [
        ("产品",10),("需求",9),("优先级",9),("用户故事",10),("验收标准",9),("功能范围",8),
        ("功能需求",9),("需求分析",10),("产品需求",9),("prd",8),
    ],
    "devops": [
        ("ci/cd",10),("docker",10),("部署",10),("环境配置",9),("devops",10),("运维",9),
        ("容器化",9),("dockerfile",9),("k8s",9),("kubernetes",9),("上线",8),
        ("ci",8),("cd",8),("容器",8),("镜像",8),("编排",7),
    ],
    "release-manager": [
        ("发布",10),("版本",9),("changelog",8),("tag",7),("release",9),("回滚",8),
        ("semver",7),("发版",9),("版本号",8),("发布管理",9),("发布检查",9),
        ("release note",8),("发布说明",8),
    ],
    "lead": [
        ("委派",10),("领导",9),("异步",8),("后台执行",9),("大任务",9),("lead",10),
        ("异步任务",9),("后台任务",8),("委派任务",9),("领导任务",9),
    ],
    "architect": [
        ("系统设计",10),("架构设计",10),("技术选型",10),("接口设计",9),("模块划分",9),("架构方案",10),("系统架构",10),
    ],
    "debugger": [
        ("调试",9),("debug",9),("排查bug",10),("定位问题",9),("错误分析",10),("堆栈跟踪",10),("根因分析",10),("排查",8),
    ],
    "verifier": [
        ("验证改动",10),("检查修复",10),("确认修复",9),("改动验证",10),("回归检查",9),
    ],
    "designer": [
        ("界面设计",10),("UI设计",10),("UX设计",10),("交互设计",10),("页面设计",9),("原型",8),("网页设计",10),
    ],
    "test-generator": [
        ("生成测试",10),("写测试用例",10),("测试生成",10),("单元测试生成",10),("mock",7),
    ],
    "critic": [
        ("评估输出",10),("质量检查",9),("输出审查",9),("格式检查",8),
    ],
    "memory-keeper": [
        ("压缩上下文",10),("摘要",8),("记忆管理",9),("会话总结",9),
    ],
    "router": [
        ("路由",8),("意图识别",9),("agent选择",9),
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
        for kw, weight in keywords:
            if kw.lower() in task_lower:
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


# ── LLM 兜底缓存（72h 过期）──
import threading
_fallback_cache = {}  # {task_hash: (agent, timestamp)}
_fallback_cache_lock = threading.Lock()
_fallback_stats = {"total_routes": 0, "fallback_count": 0}


def llm_fallback(task: str, candidates: list[dict], model: str = "deepseek-chat") -> str | None:
    """用轻量模型做路由兜底。返回 agent name 或 None。

    Args:
        task: 用户输入的任务描述
        candidates: 候选 Agent 列表 [{"name": "...", "description": "..."}, ...]
        model: 使用的轻量模型（light 级别）

    Returns:
        选中的 agent name，失败返回 None
    """
    if not candidates:
        return None

    # 构建 prompt
    candidate_lines = [f"- {a['name']}: {a.get('description', '无描述')[:80]}" for a in candidates[:15]]
    prompt = (
        f"以下任务该分配给哪个 Agent？只返回 Agent 名称，不要解释。\n\n"
        f"任务：{task}\n\n"
        f"可选 Agent：\n" + "\n".join(candidate_lines) +
        f"\n\nAgent 名称："
    )

    base_url, api_key, headers = get_provider_config()
    if not base_url or not api_key:
        log.warning("llm_fallback: 无 API 配置，无法调用 LLM 兜底")
        return None

    # 使用 light 模型
    light_model = os.environ.get("LIGHT_MODEL", resolve_model("haiku"))

    payload = {
        "model": light_model if light_model and light_model != model else model,
        "messages": [
            {"role": "system", "content": "你是一个路由助手。只返回 Agent 名称，不要任何解释。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 16,
        "temperature": 0.0,
    }

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if resp.status_code != 200:
            log.warning(f"llm_fallback: API 返回 {resp.status_code}")
            return None

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        # 去掉可能的标点符号和多余文字
        for name in [a["name"] for a in candidates]:
            if name.lower() in content.lower():
                return name

        # 模糊匹配：取第一行作为 agent 名
        first_line = content.split("\n")[0].strip().rstrip(".").strip()
        for name in [a["name"] for a in candidates]:
            if name.lower() == first_line.lower():
                return name

        log.info(f"llm_fallback: 无法从输出解析 agent，原始输出: {content[:80]}")
        return None

    except requests.exceptions.Timeout:
        log.warning("llm_fallback: 请求超时")
        return None
    except Exception as e:
        log.warning(f"llm_fallback: 异常: {e}")
        return None


def _clean_fallback_cache():
    """清理超过 72 小时的缓存条目"""
    now = time.time()
    expired = [k for k, v in _fallback_cache.items() if now - v[1] > 72 * 3600]
    for k in expired:
        del _fallback_cache[k]


def route_with_fallback(task, force_agent=None):
    """三级路由融合：加权关键词(40%) + 语义匹配(48%) + LLM兜底(12%)

    返回格式: {
        "agent": "...",
        "model": "...",
        "confidence": 0.85,
        "keyword_score": 0.9,
        "semantic_score": 0.72,
        "source": "keyword" | "semantic" | "llm",
        "method": "three_tier",
    }
    """
    # ── 更新统计 ──
    with _fallback_cache_lock:
        _fallback_stats["total_routes"] += 1

    if force_agent:
        return {
            "agent": force_agent,
            "model": "",
            "confidence": 0.99,
            "keyword_score": 0.99,
            "semantic_score": 0.0,
            "source": "force",
            "method": "force",
        }

    # ── Layer 1: 加权关键词 ──
    kw_agent, kw_raw_score, kw_confidence = route_task(task)

    # ── Layer 2: 语义匹配 ──
    from maestro.embedding import semantic_match as embedding_match
    sem_agent, sem_score = embedding_match(task)

    # ── 归一化 + 融合 ──
    # keyword_score 归一化（raw score 通常在 0~50 范围）
    keyword_score = min(1.0, kw_raw_score / 30.0)
    # semantic_score 已经在 0~1 范围

    final_score = keyword_score * 0.4 + sem_score * 0.48

    # 决定来源和最终 agent
    if keyword_score > sem_score + 0.15:
        source = "keyword"
        best_agent = kw_agent
        final_score = max(final_score, keyword_score * 0.6)
    elif sem_score > keyword_score + 0.10:
        source = "semantic"
        best_agent = sem_agent
        final_score = max(final_score, sem_score * 0.7)
    else:
        # 接近时优先关键词的 agent
        source = "keyword" if keyword_score >= sem_score else "semantic"
        best_agent = kw_agent if keyword_score >= sem_score else sem_agent

    # ── Layer 3: LLM 兜底 ──
    FALLBACK_THRESHOLD = 4  # 等效于原有阈值
    llm_used = False

    if kw_raw_score < FALLBACK_THRESHOLD and sem_score < 0.10:
        task_hash = hashlib.md5(task.encode()).hexdigest()

        # 检查缓存
        with _fallback_cache_lock:
            _clean_fallback_cache()
            if task_hash in _fallback_cache:
                cached_agent, cached_time = _fallback_cache[task_hash]
                if time.time() - cached_time < 72 * 3600:
                    best_agent = cached_agent
                    source = "llm_cached"
                    llm_used = True

        if not llm_used:
            # 构建候选列表（取 Top 10 语义候选 + 关键词候选）
            from maestro.shared import load_agents
            all_agents = load_agents()
            candidate_names = {kw_agent, sem_agent}
            # 加入 top 语义候选
            from maestro.embedding import get_embedding_router
            router = get_embedding_router()
            for name, _ in router.search(task, top_k=5):
                candidate_names.add(name)
            candidates = [{"name": a["name"], "description": a.get("description", "")}
                          for a in all_agents if a["name"] in candidate_names]
            if not candidates and all_agents:
                candidates = all_agents[:10]

            llm_result = llm_fallback(task, candidates)
            if llm_result:
                best_agent = llm_result
                source = "llm"
                llm_used = True

                # 缓存结果
                with _fallback_cache_lock:
                    _fallback_cache[task_hash] = (best_agent, time.time())
                    # 限制缓存大小
                    if len(_fallback_cache) > 500:
                        keys = sorted(_fallback_cache.keys())
                        for k in keys[:100]:
                            del _fallback_cache[k]

                # 融合 LLM 分数
                final_score = final_score * 0.88 + 0.12

        with _fallback_cache_lock:
            _fallback_stats["fallback_count"] += 1

    # ── 兜底频率监控 ──
    with _fallback_cache_lock:
        total = _fallback_stats["total_routes"]
        fb = _fallback_stats["fallback_count"]
        if total > 10:
            rate = fb / total
            if rate > 0.05:
                log.warning(f"LLM 兜底频率偏高: {fb}/{total} = {rate:.1%} (阈值 5%)")

    # ── 构建返回 ──
    from maestro.shared import _agent_models
    model = _agent_models.get(best_agent, "")

    return {
        "agent": best_agent,
        "model": model,
        "confidence": round(final_score, 4),
        "keyword_score": round(keyword_score, 4),
        "semantic_score": round(sem_score, 4),
        "source": source,
        "method": "three_tier",
    }


# 简单 LRU 缓存：最近 100 条路由结果
_route_cache = {}  # {task_hash: route_result_dict}
_route_lock = threading.Lock()


def route_with_cache(task, force_agent=None):
    """带缓存的路由入口"""
    task_hash = hashlib.md5(task.encode()).hexdigest()[:8]

    with _route_lock:
        if task_hash in _route_cache and not force_agent:
            result = dict(_route_cache[task_hash])
            result["source"] = "cache"
            return result

    result = route_with_fallback(task, force_agent)

    with _route_lock:
        if len(_route_cache) > 100:
            oldest = next(iter(_route_cache))
            del _route_cache[oldest]
        _route_cache[task_hash] = dict(result)

    return result


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
    route_result = route_with_cache(task)
    current_agent = route_result["agent"]

    print(f"→ 路由: {current_agent} (置信度: {route_result['confidence']:.2f}, 来源: {route_result.get('source', 'N/A')})")

    # 加载 Agent
    system_prompt, agent_model = load_agent(current_agent)
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
