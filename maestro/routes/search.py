"""全局搜索 API — 跨所有会话全文检索（Phase 3）
不可移除——头部栏🔍按钮依赖此端点"""

import json, re, logging
from pathlib import Path

log = logging.getLogger(__name__)


def _scan_conversations():
    """扫描 conversations.json + sessions/*.jsonl，提取可搜索文本"""
    results = []
    base = Path(__file__).resolve().parent.parent

    # 1. conversations.json
    conv_file = base / "conversations.json"
    if conv_file.exists():
        try:
            data = json.loads(conv_file.read_text(encoding="utf-8"))
            for c in data.get("conversations", []):
                results.append({
                    "source": "conversation",
                    "id": c.get("id", ""),
                    "title": c.get("title", ""),
                    "preview": c.get("preview", ""),
                    "updated": c.get("updated", 0),
                })
        except Exception:
            pass

    # 2. sessions/*.jsonl — 取前50行做摘要
    sessions_dir = base / "sessions"
    if sessions_dir.exists():
        for f in sorted(sessions_dir.glob("*.jsonl"), reverse=True):
            try:
                lines = f.read_text(encoding="utf-8").strip().split("\n")
                preview = ""
                for line in lines[:50]:
                    try:
                        evt = json.loads(line)
                        if evt.get("type") == "user_message":
                            preview += evt.get("content", "")[:200]
                    except Exception:
                        pass
                results.append({
                    "source": "session",
                    "id": f.stem,
                    "title": f"会话 {f.stem[:8]}",
                    "preview": preview[:300],
                    "updated": int(f.stat().st_mtime * 1000),
                })
            except Exception:
                pass
    return results


def handle_search(handler, parsed):
    """GET /api/search?q=关键词 — 跨会话全文搜索"""
    qp = parsed.get("query_params", {}) if isinstance(parsed, dict) else {}
    q = qp.get("q", "").strip()
    if not q:
        handler.send_json({"ok": True, "results": [], "query": ""})
        return True

    results = []
    q_lower = q.lower()
    items = _scan_conversations()
    for item in items:
        title_match = q_lower in item.get("title", "").lower()
        preview_match = q_lower in item.get("preview", "").lower()
        if title_match or preview_match:
            text = item.get("title", "") + " " + item.get("preview", "")
            idx = text.lower().find(q_lower)
            ctx_start = max(0, idx - 40)
            ctx_end = min(len(text), idx + len(q) + 60)
            snippet = ("..." if ctx_start > 0 else "") + text[ctx_start:ctx_end] + ("..." if ctx_end < len(text) else "")
            snippet = re.sub(re.escape(q), f"<mark>{q}</mark>", snippet, flags=re.IGNORECASE)
            item["snippet"] = snippet
            item["_score"] = (2 if title_match else 0) + (1 if preview_match else 0)
            results.append(item)

    results.sort(key=lambda x: (-x["_score"], -x.get("updated", 0)))
    for r in results:
        del r["_score"]

    handler.send_json({"ok": True, "results": results[:20], "query": q, "total": len(items)})
    return True
