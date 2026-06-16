"""Agent 管理路由"""

import re
import logging
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_list(handler, parsed):
    """GET /api/agents — 所有 Agent 列表"""
    from maestro.shared import load_agents

    # profile filter: only pass when explicitly requested via ?profile=minimal|standard|full
    # parse query params from ParseResult (namedtuple, not dict — .get() won't work)
    from urllib.parse import parse_qs
    qp = parse_qs(parsed.query) if hasattr(parsed, 'query') else {}
    profile = qp.get('profile', [None])[0]
    if profile:
        handler.send_json(load_agents(profile_complexity=profile))
    else:
        handler.send_json(load_agents())
    return True


def handle_detail(handler, parsed):
    """GET /api/agents/{name} — 读取单个 Agent .md"""
    name = parsed.path[len("/api/agents/") :]
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        handler.send_json(
            {"error": "Agent 名称格式无效。请使用英文大小写字母、数字、下划线和连字符"}, 400
        )
        return True
    agent_content = None
    for search_dir in [
        PROJECT_ROOT / "agents",
        PROJECT_ROOT / ".claude" / "agents",
        Path.home() / ".claude" / "agents",
    ]:
        # 先查扁平路径
        candidate = search_dir / f"{name}.md"
        if candidate.exists():
            agent_content = candidate.read_text(encoding="utf-8")
            break
        # 再递归查子目录
        for f in search_dir.glob("**/*.md"):
            if f.stem == name:
                agent_content = f.read_text(encoding="utf-8")
                break
        if agent_content is not None:
            break
    if agent_content is not None:
        handler.send_json({"name": name, "content": agent_content})
    else:
        handler.send_json(
            {
                "error": f"未找到 Agent '{name}'。请检查 Agent 名称是否正确，或从侧边栏 Agent 列表中选择"
            },
            404,
        )
    return True


def handle_update(handler, body):
    """POST /api/agent-update — 保存 Agent .md 并同步三个目录"""
    name = body.get("name", "")
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        handler.send_json(
            {"error": "Agent 名称格式无效。请使用英文大小写字母、数字、下划线和连字符"}, 400
        )
        return True
    content = body.get("content", "")
    if not name or not content:
        handler.send_json(
            {"error": "缺少必填字段。请同时提供 name（Agent 名称）和 content（Agent 内容）"}, 400
        )
        return True
    try:
        # 写入 agents/user/ 目录（不覆盖系统 Agent）
        agent_file = PROJECT_ROOT / "agents" / "user" / f"{name}.md"
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        agent_file.write_text(content, encoding="utf-8")
        # 同步到 .claude/agents/user/
        claude_dir = PROJECT_ROOT / ".claude" / "agents" / "user"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / f"{name}.md").write_text(content, encoding="utf-8")
        # 同步到 .claude-isolated/agents/user/
        iso_dir = PROJECT_ROOT / ".claude-isolated" / "agents" / "user"
        iso_dir.mkdir(parents=True, exist_ok=True)
        (iso_dir / f"{name}.md").write_text(content, encoding="utf-8")
        handler.send_json({"ok": True, "name": name})
    except Exception as e:
        handler.send_json({"error": str(e)}, 500)
    return True


def handle_delete(handler, body):
    """POST /api/agent-delete — 删除 Agent"""
    name = body.get("name", "")
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        handler.send_json(
            {"error": "Agent 名称格式无效。请使用英文大小写字母、数字、下划线和连字符"}, 400
        )
        return True
    deleted = 0
    for base in [
        PROJECT_ROOT / "agents",
        PROJECT_ROOT / ".claude" / "agents",
        PROJECT_ROOT / ".claude-isolated" / "agents",
    ]:
        # 先查 flat 路径
        f = base / f"{name}.md"
        if f.exists():
            f.unlink()
            deleted += 1
        # 也查 user/ 子目录
        uf = base / "user" / f"{name}.md"
        if uf.exists():
            uf.unlink()
            deleted += 1
    handler.send_json({"ok": True, "deleted": deleted})
    return True
