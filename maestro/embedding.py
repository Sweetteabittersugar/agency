#!/usr/bin/env python3
"""
语义路由引擎 — 零依赖 TF-IDF + Cosine Similarity

用法:
  from maestro.embedding import EmbeddingRouter
  router = EmbeddingRouter(agents)
  results = router.search("查询任务", top_k=3)
  # → [("coder", 0.85), ("explorer", 0.72), ("planner", 0.45)]
"""

import math
import re
from collections import Counter
from pathlib import Path
from typing import Optional


# ── 中文分词辅助 ──
# 不做真正的分词（零依赖），用 unigram + bigram 字符级 N-gram 替代
# 对中文任务描述已经足够区分语义


def _tokenize(text: str) -> list[str]:
    """将文本切分为 unigram + bigram token。

    对中文逐字切分，同时生成相邻字符对（bigram）。英文按空白分词。
    这比纯 Jaccard 2-gram 更能捕获语义。
    """
    tokens: list[str] = []

    # 英文: 按空白/标点分词
    english_words = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    for w in english_words:
        tokens.append(w)
        # 添加 bigram
        for i in range(len(w) - 1):
            tokens.append(w[i : i + 2])

    # 中文: 字符级 unigram + bigram
    chinese_chars = re.findall(r"[一-鿿㐀-䶿]", text)
    for ch in chinese_chars:
        tokens.append(ch)
    for i in range(len(chinese_chars) - 1):
        tokens.append(chinese_chars[i] + chinese_chars[i + 1])

    return tokens


class EmbeddingRouter:
    """基于 TF-IDF + Cosine Similarity 的语义路由器。

    启动时对所有 Agent description 建索引，后续对任务 query 做语义匹配。
    纯本地、零依赖。
    """

    def __init__(self, agents: list[dict]):
        """
        Args:
            agents: [{"name": "coder", "description": "写代码...", ...}, ...]
        """
        self.agents = agents
        self.agent_names: list[str] = []
        self.agent_texts: list[str] = []
        self.vocab: dict[str, int] = {}  # token → index
        self.idf: dict[str, float] = {}  # token → idf
        self.tfidf_matrix: list[dict[int, float]] = []  # [agent_idx] → {token_idx: tfidf}
        self._built = False

        if agents:
            self._build_index()

    def _build_index(self):
        """构建 TF-IDF 向量索引。"""
        self.agent_names = [a.get("name", "") for a in self.agents]
        self.agent_texts = [a.get("name", "") + " " + a.get("description", "") for a in self.agents]

        # 第一步：分词 + 构建文档列表
        doc_tokens: list[list[str]] = []
        for text in self.agent_texts:
            tokens = _tokenize(text)
            doc_tokens.append(tokens)

        # 第二步：构建词表
        vocab_set: set[str] = set()
        for tokens in doc_tokens:
            vocab_set.update(tokens)
        self.vocab = {token: idx for idx, token in enumerate(sorted(vocab_set))}

        # 第三步：计算 IDF
        N = len(doc_tokens)
        for token, idx in self.vocab.items():
            df = sum(1 for tokens in doc_tokens if token in tokens)
            self.idf[token] = math.log((N + 1) / (df + 1)) + 1.0

        # 第四步：构建 TF-IDF 向量
        self.tfidf_matrix = []
        for tokens in doc_tokens:
            tf = Counter(tokens)
            max_tf = max(tf.values()) if tf else 1
            vec: dict[int, float] = {}
            for token, count in tf.items():
                if token in self.vocab:
                    idx = self.vocab[token]
                    # 归一化 TF
                    norm_tf = count / max_tf
                    vec[idx] = norm_tf * self.idf[token]
            # L2 归一化
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            vec = {k: v / norm for k, v in vec.items()}
            self.tfidf_matrix.append(vec)

        self._built = True

    def _vectorize(self, text: str) -> dict[int, float]:
        """将查询文本转为 TF-IDF 向量。"""
        tokens = _tokenize(text)
        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1
        vec: dict[int, float] = {}
        for token, count in tf.items():
            if token in self.vocab:
                idx = self.vocab[token]
                norm_tf = count / max_tf
                # 使用预计算的 IDF，未知词给默认 IDF
                idf = self.idf.get(token, 1.0)
                vec[idx] = norm_tf * idf
        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {k: v / norm for k, v in vec.items()}

    def _cosine(self, v1: dict[int, float], v2: dict[int, float]) -> float:
        """两个稀疏向量的余弦相似度。"""
        keys = set(v1.keys()) | set(v2.keys())
        dot = sum(v1.get(k, 0.0) * v2.get(k, 0.0) for k in keys)
        return max(0.0, min(1.0, dot))  # 已 L2 归一化，dot 即 cosine

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """语义搜索 — 返回最匹配的 Agent 及相似度分数。

        Args:
            query: 用户输入的任务描述
            top_k: 返回前 K 个结果

        Returns:
            [(agent_name, cosine_similarity), ...]  按相似度降序
        """
        if not self._built or not self.tfidf_matrix:
            if self.agent_names:
                return [(self.agent_names[0], 0.0)]
            return []

        q_vec = self._vectorize(query)
        scores: list[tuple[str, float]] = []
        for i, doc_vec in enumerate(self.tfidf_matrix):
            sim = self._cosine(q_vec, doc_vec)
            if sim > 0.0:
                scores.append((self.agent_names[i], round(sim, 4)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def search_one(self, query: str) -> tuple[str, float]:
        """返回最匹配的单个 Agent。"""
        results = self.search(query, top_k=1)
        if results:
            return results[0]
        return (self.agent_names[0] if self.agent_names else "coder", 0.0)


# ── 全局单例（惰性初始化）──
_embedding_router: Optional[EmbeddingRouter] = None


def get_embedding_router(agents: Optional[list[dict]] = None) -> EmbeddingRouter:
    """获取全局 EmbeddingRouter 单例。首次调用时从 agents/ 目录加载。"""
    global _embedding_router
    if _embedding_router is not None:
        return _embedding_router

    if agents is None:
        # 从 agents/ 目录自动加载
        from maestro.agent_parser import parse_agent_md

        project_root = Path(__file__).resolve().parent.parent
        agents_dir = project_root / "agents"
        agents = []
        if agents_dir.exists():
            for f in sorted(agents_dir.glob("**/*.md")):
                info = parse_agent_md(f)
                agents.append(
                    {
                        "name": info["name"],
                        "description": info["description"],
                    }
                )

    _embedding_router = EmbeddingRouter(agents)
    return _embedding_router


def semantic_match(task: str, agents: Optional[list[dict]] = None) -> tuple[str, float]:
    """便捷函数：对任务做语义匹配，返回 (agent_name, score)。"""
    router = get_embedding_router(agents)
    return router.search_one(task)
