"""记忆引擎 — 提炼 / 注入 / 索引

三层架构:
  记录层 → session_store.append_event() 写入 JSONL (session_store 已有)
  提炼层 → 对话结束时让 Claude 提取关键信息 → 写入 memory/*.md
  注入层 → 新会话开始前匹配相关记忆 → 注入任务前缀
"""

import re
import logging
from pathlib import Path
from datetime import datetime, timezone

log = logging.getLogger(__name__)

MEMORY_EXTRACT_PROMPT = """[系统指令]

以上对话已结束。请从对话中提取所有值得长期记住的信息，以结构化格式输出。

重要：不要在回答中使用任何工具，只输出纯文本。即使你在之前的回复中提到过"已记录"或"已保存"，那些只是文字描述而非实际存储——请现在将关键信息真正输出。

对每条值得记住的信息，严格按以下格式输出：

```memory
name: <英文短横线命名>
description: <一句话中文描述>
type: user | project | feedback | reference
---
<具体事实内容，不超过300字>
```

规则：
1. 提取所有对后续工作有价值的偏好、决策、约束、教训
2. 你之前声称"已保存"但实际未持久化的信息，现在必须输出
3. 如果确实没有任何值得记住的内容，输出「无需记录」四个字
4. 每条记忆用独立的 ```memory 块包裹
5. 不要省略任何字段"""


def get_memory_dir(project_root: str | Path) -> Path:
    return Path(project_root) / "memory"


def list_memory_files(project_root: str | Path) -> list[dict]:
    """扫描 memory/ 目录，返回记忆文件列表"""
    mem_dir = get_memory_dir(project_root)
    if not mem_dir.exists():
        return []
    results = []
    for fp in sorted(mem_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = fp.read_text(encoding="utf-8")
        name = fp.stem
        desc = ""
        body = text
        fm_match = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            n = re.search(r"name:\s*(.+)", fm)
            if n:
                name = n.group(1).strip()
            d = re.search(r"description:\s*(.+)", fm)
            if d:
                desc = d.group(1).strip()
            body = text[fm_match.end() :].strip()
        results.append(
            {
                "filename": fp.name,
                "name": name,
                "description": desc,
                "body": body,
                "preview": body[:120],
                "size": fp.stat().st_size,
                "updated": datetime.fromtimestamp(fp.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
        )
    return results


def parse_memory_blocks(response_text: str) -> list[dict]:
    """从 Claude 回复中解析 ```memory ... ``` 块"""
    pattern = r"```memory\s*\n(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    memories = []
    for block in matches:
        block = block.strip()
        parts = block.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[0].strip()
            body = parts[2].strip()
        else:
            fm_text = block.split("\n")[0] if "\n" in block else ""
            body = block

        name = re.search(r"name:\s*(.+)", fm_text)
        desc = re.search(r"description:\s*(.+)", fm_text)
        mtype = re.search(r"type:\s*(.+)", fm_text)

        memories.append(
            {
                "name": name.group(1).strip() if name else f"mem-{datetime.now():%Y%m%d%H%M%S}",
                "description": desc.group(1).strip() if desc else "",
                "type": mtype.group(1).strip() if mtype else "reference",
                "body": body.strip(),
            }
        )
    return memories


def save_memory_file(project_root: str | Path, memory: dict) -> Path | None:
    """保存一条记忆到 memory/<name>.md"""
    mem_dir = get_memory_dir(project_root)
    mem_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{memory['name']}.md"
    filepath = mem_dir / filename

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = f"""---
name: {memory["name"]}
description: {memory.get("description", "")}
metadata:
  type: {memory.get("type", "reference")}
  created: {now}
---

{memory.get("body", "")}
"""
    filepath.write_text(content, encoding="utf-8")
    log.info(f"记忆已保存: {filename}")
    return filepath


def _tokenize(text: str) -> set[str]:
    """中文用2-gram，英文用单词，返回特征集合"""
    tokens = set()
    # 英文单词
    for m in re.finditer(r"[a-zA-Z][a-zA-Z0-9_]*", text):
        tokens.add(m.group().lower())
    # 中文2-gram 滑动窗口
    cjk_chars = re.sub(r"[^一-鿿]", "", text)
    for i in range(len(cjk_chars) - 1):
        tokens.add(cjk_chars[i : i + 2])
    # 单字也纳入
    for ch in cjk_chars:
        tokens.add(ch)
    return tokens


def find_relevant_memories(task: str, project_root: str | Path, limit: int = 5) -> list[dict]:
    """关键词匹配，返回与任务相关的记忆列表"""
    all_memories = list_memory_files(project_root)
    if not all_memories or not task:
        return []

    task_tokens = _tokenize(task)
    if not task_tokens:
        return []

    scored = []
    for mem in all_memories:
        search_text = f"{mem['name']} {mem['description']} {mem['body']}".lower()
        search_tokens = _tokenize(search_text)
        overlap = task_tokens & search_tokens
        if overlap:
            scored.append((len(overlap), mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [mem for _, mem in scored[:limit]]


def build_injection_prefix(task: str, project_root: str | Path, limit: int = 5) -> str:
    """构建记忆注入前缀，拼接在用户任务前面"""
    relevant = find_relevant_memories(task, project_root, limit)
    if not relevant:
        return task

    lines = ["[相关记忆 — 从历史对话中提炼，仅供参考]\n"]
    for mem in relevant:
        summary = mem["body"][:200]
        lines.append(f"• [{mem['name']}] {mem['description']}: {summary}")

    lines.append(f"\n---\n[用户当前任务]\n{task}")
    return "\n".join(lines)
