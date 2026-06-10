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
            disabled_skmd = skill_dir / "SKILL.md.disabled"
            target_file = None
            enabled = True
            if skmd.exists():
                target_file = skmd
                enabled = True
            elif disabled_skmd.exists():
                target_file = disabled_skmd
                enabled = False
            else:
                continue
            try:
                content = target_file.read_text(encoding="utf-8")
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
                    "enabled": enabled,
                    "path": str(target_file.resolve()),
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
    # 加载启用状态
    mcp_state = {}
    try:
        state_file = PROJECT_ROOT / "maestro" / "mcp_state.json"
        if state_file.exists():
            mcp_state = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        pass

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
                    "enabled": mcp_state.get(name, True),
                })
        except Exception:
            log.debug(f"Failed to read MCP config from {src}", exc_info=True)
    handler.send_json({"servers": servers})
    return True


def handle_skills_save(handler, body):
    """POST /api/skills/save — 保存 Skill 源码"""
    name = body.get("name", "")
    content = body.get("content", "")
    if not name or not content:
        handler.send_json({"error": "缺少必填字段。请同时提供 name（Skill 名称）和 content（Skill 源码内容）"}, 400)
        return True
    skills_dir = PROJECT_ROOT / ".claude" / "skills" / name
    skills_dir.mkdir(parents=True, exist_ok=True)
    try:
        # 如果存在 disabled 文件，先删除它，保存即启用
        disabled = skills_dir / "SKILL.md.disabled"
        if disabled.exists():
            disabled.unlink()
        (skills_dir / "SKILL.md").write_text(content, encoding="utf-8")
        handler.send_json({"ok": True, "name": name})
    except Exception as e:
        handler.send_json({"error": str(e)}, 500)
    return True


def handle_skills_toggle(handler, body):
    """POST /api/skills/toggle — 启用/禁用 Skill"""
    name = body.get("name", "")
    enabled = body.get("enabled", True)
    if not name:
        handler.send_json({"error": "缺少必填字段 name。请提供 Skill 名称"}, 400)
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
    """POST /api/mcp/config — 保存 MCP 配置或切换单服务启用状态

    支持两种模式:
      - 全量保存: body 包含 "config" 字段 → 写入 .mcp.json
      - 单服务切换: body 包含 "action":"toggle", "server":"<name>", "enabled":true/false
    """
    action = body.get("action", "")
    if action == "toggle":
        server_name = body.get("server", "")
        enabled = bool(body.get("enabled", True))
        if not server_name:
            handler.send_json({"error": "缺少必填字段 server。请提供 MCP 服务名称"}, 400)
            return True
        try:
            state_file = PROJECT_ROOT / "maestro" / "mcp_state.json"
            state = {}
            if state_file.exists():
                state = json.loads(state_file.read_text(encoding="utf-8"))
            state[server_name] = enabled
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
            handler.send_json({"ok": True, "server": server_name, "enabled": enabled})
            return True
        except Exception as e:
            handler.send_json({"error": str(e)}, 500)
            return True

    # 全量保存模式
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


def handle_skills_content(handler, parsed):
    """GET /api/skills/content/:name — 查看 Skill 源码"""
    path = parsed.path
    name = path.replace("/api/skills/content/", "").strip("/")
    if not name:
        handler.send_json({"error": "缺少必填字段 name。请提供 Skill 名称"}, 400)
        return True
    search_dirs = [
        Path(__file__).resolve().parent.parent.parent / ".claude" / "skills",
        Path.home() / ".claude" / "skills",
    ]
    for base in search_dirs:
        skmd = base / name / "SKILL.md"
        disabled_skmd = base / name / "SKILL.md.disabled"
        if skmd.exists():
            content = skmd.read_text(encoding="utf-8")
            handler.send_json({"name": name, "content": content})
            return True
        elif disabled_skmd.exists():
            content = disabled_skmd.read_text(encoding="utf-8")
            handler.send_json({"name": name, "content": content})
            return True
    handler.send_json({"error": "未找到该 Skill。请检查名称是否正确"}, 404)
    return True


def handle_skills_delete(handler, parsed):
    """DELETE /api/skills/:name — 删除 Skill"""
    import shutil
    path = parsed.path
    name = path.replace("/api/skills/", "").strip("/")
    if not name:
        handler.send_json({"error": "缺少必填字段 name。请提供 Skill 名称"}, 400)
        return True
    search_dirs = [
        Path(__file__).resolve().parent.parent.parent / ".claude" / "skills",
        Path.home() / ".claude" / "skills",
    ]
    for base in search_dirs:
        skill_dir = base / name
        if skill_dir.exists() and skill_dir.is_dir():
            try:
                shutil.rmtree(skill_dir)
                handler.send_json({"ok": True, "name": name})
            except Exception as e:
                handler.send_json({"error": str(e)}, 500)
            return True
    handler.send_json({"error": "未找到该 Skill。请检查名称是否正确"}, 404)
    return True


# ── Profile API ──

def handle_profile(handler, parsed):
    """GET /api/profile — 返回当前可用 profile 列表和当前选择"""
    profiles_path = PROJECT_ROOT / "profiles.json"
    profiles = {}
    if profiles_path.exists():
        try:
            data = json.loads(profiles_path.read_text(encoding="utf-8"))
            profiles = data.get("profiles", {})
        except Exception:
            log.warning("Failed to read profiles.json")

    try:
        from maestro.profiles import estimate_complexity, load_profile
        _has = True
    except ImportError:
        _has = False

    handler.send_json({
        "profiles": profiles,
        "available": list(profiles.keys()) if profiles else ["minimal", "standard", "full"],
        "has_engine": _has,
    })
    return True


def handle_profile_set(handler, body):
    """POST /api/profile — 设置当前 profile 级别（客户端管理，此处仅做校验返回）"""
    level = body.get("level", "")
    valid = ["minimal", "standard", "full"]
    if level not in valid:
        handler.send_json({
            "error": "无效的 profile 级别。可选: minimal, standard, full",
            "valid": valid,
        }, 400)
        return True

    # 验证 profiles.json 中是否包含此级别
    profile = {}
    try:
        from maestro.profiles import load_profile
        profile = load_profile(level)
    except Exception:
        pass

    handler.send_json({
        "ok": True,
        "level": level,
        "profile": profile,
    })
    return True


def handle_profiles_list(handler, parsed):
    """GET /api/profiles — 返回 profiles.json 完整内容（复数路由，供外部工具调用）"""
    profiles_path = PROJECT_ROOT / "profiles.json"
    if not profiles_path.exists():
        handler.send_json({
            "version": "0.2.0",
            "description": "Profile 分级未配置",
            "profiles": {},
            "available": ["minimal", "standard", "full"],
        })
        return True
    try:
        data = json.loads(profiles_path.read_text(encoding="utf-8"))
        handler.send_json(data)
    except Exception as e:
        handler.send_json({"error": f"读取 profiles.json 失败: {e}"}, 500)
    return True
