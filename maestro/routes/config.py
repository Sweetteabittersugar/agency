"""配置管理路由 — settings / version / skills / MCP / Skills toggle / MCP config"""
import json
import yaml
import time
import logging
from urllib.parse import parse_qs
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def handle_version(handler, parsed):
    """GET /api/version"""
    from maestro.shared import AGENCY_VERSION
    handler.send_json({"version": AGENCY_VERSION})
    return True


def handle_settings(handler, parsed):
    """GET /api/settings — 运行配置"""
    from maestro.shared import AGENCY_VERSION, CLAUDE_BIN, _claude_dir
    import os
    handler.send_json({
        "claude_bin": CLAUDE_BIN or "not found",
        "config_dir": str(_claude_dir),
        "has_api_key": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")),
        "version": AGENCY_VERSION,
    })
    return True


def handle_skills(handler, parsed):
    """GET /api/skills — Skills 列表"""
    skills = []
    for skills_dir in [
        PROJECT_ROOT / ".claude" / "skills",
        Path.home() / ".claude" / "skills",
    ]:
        if not skills_dir.exists():
            continue
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skmd = skill_dir / "SKILL.md"
            if skmd.exists():
                try:
                    content = skmd.read_text(encoding="utf-8")
                    fm = {}
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            try:
                                fm = yaml.safe_load(parts[1]) or {}
                            except Exception:
                                log.debug(f"Failed to parse frontmatter for skill {skill_dir.name}")
                    skills.append({
                        "name": skill_dir.name,
                        "description": fm.get("description", ""),
                        "triggers": fm.get("triggers", fm.get("trigger", [])),
                        "model": fm.get("model", ""),
                        "enabled": True,
                        "path": str(skmd.resolve()),
                    })
                except Exception:
                    log.debug(f"Failed to read skill {skill_dir.name}", exc_info=True)
    handler.send_json(skills)
    return True


def _check_mcp_running(name, args):
    """检测 MCP 进程是否在运行"""
    import subprocess
    try:
        # 检查是否有匹配的 npx/node 进程
        r = subprocess.run(
            "wmic process where \"name='node.exe' or name='npx.exe'\" get commandline /format:csv",
            capture_output=True, text=True, timeout=5, shell=True
        )
        search = name
        if args:
            for a in args:
                if a.startswith("@") or a.startswith("-"):
                    continue
                search = a
                break
        return search.lower() in r.stdout.lower()
    except Exception:
        return False  # 无法检测时返回离线


def handle_mcp_status(handler, parsed):
    """GET /api/mcp/status — MCP 服务状态（扫描多个 .mcp.json）"""
    servers = []
    seen = set()
    mcp_sources = [
        PROJECT_ROOT / ".mcp.json",
        Path.home() / ".claude" / ".mcp.json",
        PROJECT_ROOT.parent / ".mcp.json",
    ]
    for src in mcp_sources:
        if not src.exists():
            continue
        try:
            mcp = json.loads(src.read_text(encoding="utf-8"))
            for name, cfg in mcp.get("mcpServers", {}).items():
                if name in seen:
                    continue
                seen.add(name)
                running = _check_mcp_running(name, cfg.get("args", []))
                servers.append({
                    "name": name,
                    "command": cfg.get("command", ""),
                    "args": cfg.get("args", []),
                    "env": list(cfg.get("env", {}).keys()) if cfg.get("env") else [],
                    "running": running,
                    "source": str(src),
                    "tools": [],
                    "callCount": 0,
                })
        except Exception:
            log.debug(f"Failed to read MCP config from {src}", exc_info=True)
    handler.send_json({"servers": servers})
    return True


def handle_skills_toggle(handler, body):
    """POST /api/skills/toggle — 启用/禁用 Skill"""
    name = body.get("name", "")
    enabled = body.get("enabled", True)
    if not name:
        handler.send_json({"error": "name required"}, 400)
        return True
    skills_dir = PROJECT_ROOT / ".claude" / "skills" / name
    skill_path = skills_dir / "SKILL.md"
    disabled_path = skills_dir / "SKILL.md.disabled"
    try:
        if enabled and disabled_path.exists():
            disabled_path.rename(skill_path)
        elif not enabled and skill_path.exists():
            skill_path.rename(disabled_path)
        handler.send_json({"ok": True, "name": name, "enabled": enabled})
    except Exception as e:
        handler.send_json({"error": str(e)}, 500)
    return True


def handle_mcp_config(handler, body):
    """POST /api/mcp/config — 保存 MCP 配置"""
    mcp_config = body.get("config", body)
    try:
        (PROJECT_ROOT / ".mcp.json").write_text(
            json.dumps(mcp_config, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        handler.send_json({"ok": True})
    except Exception as e:
        handler.send_json({"error": str(e)}, 500)
    return True


def handle_settings_patch(handler, body):
    """POST /api/settings — PATCH settings.json"""
    patch = body.get("patch", body)
    settings_path = PROJECT_ROOT / ".claude" / "settings.json"
    current = {}
    if settings_path.exists():
        try:
            current = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            log.warning("Failed to read settings.json for PATCH update")
    current.update(patch)
    settings_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    handler.send_json({"ok": True})
    return True
