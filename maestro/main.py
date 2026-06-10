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
from maestro.shared import ROUTING_KEYWORDS as ROUTING


# ── 置信度门控阈值 ──
from maestro.app_config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, SEMANTIC_THRESHOLD


def _keyword_match(task):
    """内部函数：加权关键词匹配，返回完整得分字典。
    Returns: dict {agent_name: {"score": int, "matched": [str]}} 或空 dict
    """
    if task is None:
        return {}

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
        return {}

    # 成功率权重调整（复合学习）
    agent_stats = get_agent_stats()
    for agent_name in list(scores.keys()):
        if agent_name in agent_stats:
            rate = agent_stats[agent_name]["success_rate"]
            if rate < 0.5 and agent_stats[agent_name]["total"] >= 3:
                scores[agent_name]["score"] = int(scores[agent_name]["score"] * 0.7)

    return scores


def _rank_keyword_scores(scores: dict):
    """对关键词得分做排序，返回 (best_agent, raw_score, confidence, matched_count)。"""
    if not scores:
        return None

    ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else (None, {"score": 0})

    if second[1]["score"] > 0:
        confidence = (best[1]["score"] - second[1]["score"]) / best[1]["score"]
    else:
        confidence = 1.0

    matched_count = len(best[1]["matched"])
    return best[0], best[1]["score"], max(0, min(1, confidence)), matched_count


def route_task(task, force_agent=None):
    """路由 v2 -- 加权关键词匹配 + 置信度（保持向后兼容）"""
    if force_agent:
        return force_agent, 99, 0.99

    if task is None:
        return "coder", 0, 0.0

    scores = _keyword_match(task)
    ranked = _rank_keyword_scores(scores)
    if ranked is None:
        return "coder", 0, 0.0

    return ranked[0], ranked[1], ranked[2]


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
    """三级路由 + 置信度门控：关键词 → embedding 语义检索 → LLM 兜底

    返回格式: {
        "agent": "...",
        "model": "...",
        "confidence": 0.85,
        "keyword_score": 0.9,
        "semantic_score": 0.72,
        "source": "keyword" | "semantic" | "cross_validated" | "llm" | "llm_cached" | "force" | "fallback",
        "method": "three_tier",
        "matched_keywords": 3,
        "candidates": [...],
        "low_confidence": false,
        "fallback_chain": [...],
    }

    门控层级:
      1. 关键词置信度 >= 0.7 且命中 >= 2 个关键词 → 直接返回（快速路径）
      2. 语义相似度 >= 0.6 → 直接返回
      3. 关键词(0.4~0.7) + 语义交叉验证通过 → "cross_validated"
      4. 两者都低置信(< 0.4 / < 0.15) → LLM 兜底
      5. 所有层低置信 → 返回最佳候选 + low_confidence 标记
    """
    # ── 更新统计 ──
    with _fallback_cache_lock:
        _fallback_stats["total_routes"] += 1

    from maestro.shared import _agent_models

    def _make_result(agent, confidence, source, **kwargs):
        """构建统一返回格式"""
        result = {
            "agent": agent,
            "model": _agent_models.get(agent, ""),
            "confidence": round(confidence, 4),
            "keyword_score": round(keyword_score, 4),
            "semantic_score": round(sem_score, 4),
            "source": source,
            "method": "three_tier",
            "matched_keywords": kw_matches,
            "candidates": [{"agent": a, "score": round(s, 4)} for a, s in emb_results],
            "low_confidence": kwargs.get("low_confidence", False),
            "fallback_chain": kwargs.get("fallback_chain", []),
        }
        if kwargs.get("reason"):
            result["reason"] = kwargs["reason"]
        return result

    if force_agent:
        keyword_score = 0.99
        sem_score = 0.0
        kw_matches = 0
        emb_results = []
        return _make_result(force_agent, 0.99, "force")

    if not task or not task.strip():
        keyword_score = 0.0
        sem_score = 0.0
        kw_matches = 0
        emb_results = []
        return _make_result("general-worker", 0.0, "fallback",
                          low_confidence=True, reason="empty_task")

    # ── Layer 1: 关键词匹配（带匹配计数）──
    kw_scores = _keyword_match(task)
    kw_ranked = _rank_keyword_scores(kw_scores)
    if kw_ranked:
        kw_agent, kw_raw_score, kw_confidence, kw_matches = kw_ranked
    else:
        kw_agent, kw_raw_score, kw_confidence, kw_matches = "general-worker", 0, 0.0, 0

    keyword_score = min(1.0, kw_raw_score / 30.0)

    # ── Layer 2: Embedding 语义检索 ──
    from maestro.embedding import get_embedding_router
    router = get_embedding_router()
    emb_results = router.search(task, top_k=3)
    if emb_results:
        sem_agent, sem_score = emb_results[0]
    else:
        sem_agent, sem_score = "general-worker", 0.0

    # ── Gate 1: 高置信关键词（得分 >= 0.7 且 2+ 关键词命中）→ 快速路径 ──
    if keyword_score >= CONFIDENCE_HIGH and kw_matches >= 2:
        return _make_result(kw_agent, keyword_score, "keyword")

    # ── Gate 2: 高置信语义 → 直接返回 ──
    if sem_score >= SEMANTIC_THRESHOLD:
        return _make_result(sem_agent, sem_score, "semantic")

    # ── Gate 3: 关键词 + 语义交叉验证（关键词中等置信时，用语义二次确认）──
    cv_attempted = False
    if keyword_score >= CONFIDENCE_MEDIUM:
        cv_attempted = True
        for emb_agent, emb_score in emb_results:
            if emb_agent == kw_agent and emb_score >= 0.5:
                return _make_result(kw_agent, (keyword_score + emb_score) / 2,
                                  "cross_validated", fallback_chain=["keyword", "semantic"])

    # ── Gate 4: LLM 兜底（关键词无信号，或关键词有信号但语义交叉验证失败）──
    llm_used = False
    best_agent = kw_agent
    source = "keyword"

    if keyword_score < CONFIDENCE_MEDIUM or cv_attempted:
        task_hash = hashlib.md5(task.encode()).hexdigest()

        with _fallback_cache_lock:
            _clean_fallback_cache()
            if task_hash in _fallback_cache:
                cached_agent, cached_time = _fallback_cache[task_hash]
                if time.time() - cached_time < 72 * 3600:
                    best_agent = cached_agent
                    source = "llm_cached"
                    llm_used = True

        if not llm_used:
            from maestro.shared import load_agents
            all_agents = load_agents()
            candidate_names = {kw_agent, sem_agent}
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

                with _fallback_cache_lock:
                    _fallback_cache[task_hash] = (best_agent, time.time())
                    if len(_fallback_cache) > 500:
                        keys = sorted(_fallback_cache.keys())
                        for k in keys[:100]:
                            del _fallback_cache[k]

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

    # ── Gate 5: 构建最终返回 ──
    if llm_used:
        llm_confidence = 0.6
        return _make_result(best_agent, llm_confidence, source,
                          fallback_chain=["keyword", "semantic", "llm"])

    # 关键词或语义有部分信号 — 降级返回
    if keyword_score >= 0.3:
        return _make_result(kw_agent, keyword_score * 0.7, "keyword_fallback",
                          low_confidence=True, fallback_chain=["keyword"])

    if sem_score > 0.0:
        return _make_result(sem_agent, sem_score * 0.7, "semantic_fallback",
                          low_confidence=True, fallback_chain=["semantic"])

    # 完全无匹配
    return _make_result("general-worker", 0.0, "fallback",
                      low_confidence=True, reason="no_match")


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
    """读 agents/{name}.md（支持子目录递归查找），返回 system_prompt, model"""
    agent_file = PROJECT_ROOT / "agents" / f"{name}.md"
    if not agent_file.exists():
        # 递归查找子目录
        for f in (PROJECT_ROOT / "agents").glob("**/*.md"):
            if f.stem == name:
                agent_file = f
                break
    if not agent_file.exists():
        # 模糊匹配
        for f in (PROJECT_ROOT / "agents").glob("**/*.md"):
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
