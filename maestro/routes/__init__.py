"""路由注册中心 — 将所有路由绑定到 Handler 类"""
from maestro.routes import agents, chat, cost, config, harness, memory, files, orchestrate, static, agent_factory, remote, setup, restart


def register_all(Handler):
    """将所有路由模块的函数注入 Handler 类"""
    # GET 路由分发（"/" 在 Handler.do_GET 中单独处理，不在此注册）
    Handler._get_routes = [
        ("/api/agents", agents.handle_list),
        ("/api/agents/", agents.handle_detail),
        ("/api/version", config.handle_version),
        ("/api/settings", config.handle_settings),
        ("/api/cost", cost.handle_cost),
        ("/api/cost/history", cost.handle_history),
        ("/api/cost/alerts", cost.handle_alerts),
        ("/api/harness/stream", harness.handle_stream),
        ("/api/permissions/allowlist", harness.handle_permissions_allowlist),
        ("/api/permissions/history", harness.handle_permissions_history),
        ("/api/permissions/stats", harness.handle_permissions_stats),
        ("/api/harness/context", harness.handle_context),
        ("/api/harness/subagents", harness.handle_subagents),
        ("/api/harness/events", harness.handle_events),
        ("/api/skills", config.handle_skills),
        ("/api/memory", memory.handle_list),
        ("/api/memory/", memory.handle_get),
        ("/api/files", files.handle_list),
        ("/api/mcp/status", config.handle_mcp_status),
        ("/api/remote/status", remote.handle_status),
        ("/api/setup/status", setup.handle_status),
    ]
    # POST 路由分发
    Handler._post_routes = [
        ("/api/chat", chat.handle_chat),
        ("/api/route", orchestrate.handle_route),
        ("/api/orchestrate", orchestrate.handle_orchestrate),
        ("/api/hooks/", harness.handle_hooks_callback),
        ("/api/permissions/allowlist", harness.handle_permissions_allowlist_post),
        ("/api/permissions/decision", harness.handle_permissions_decision),
        ("/api/memory/", memory.handle_save),
        ("/api/skills/toggle", config.handle_skills_toggle),
        ("/api/mcp/config", config.handle_mcp_config),
        ("/api/agent-update", agents.handle_update),
        ("/api/agent-generate", agent_factory.handle_generate),
        ("/api/agent-create", agent_factory.handle_create),
        ("/api/settings", config.handle_settings_patch),
        ("/api/remote/config", remote.handle_config),
        ("/api/setup", setup.handle_save),
        ("/api/restart", restart.handle_restart),
    ]
