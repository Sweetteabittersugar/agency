"""统一路由注册表 — flask_app.py 和 routes/__init__.py 共用的唯一路由定义

格式: (method, path, handler_module_attr, endpoint_name)
新增路由只需在此文件添加一行，两端自动同步。
"""

# ── 导入所有路由模块 ──
from maestro.routes import (
    agents, chat, cost, config, harness, memory, files,
    orchestrate, agent_factory, remote, setup, restart, webhook,
    health, test_api, routing_feedback, sessions, operations,
    weixin_api, reset, session_fork, session_replay, conversations,
    cron, search, pr,
)
from maestro import worktree_manager


def _h(mod, name):
    """快捷引用: _h(agents, 'handle_list') → agents.handle_list"""
    return getattr(mod, name)


# ── 统一路由表 ──
# 每项: (method, path, handler, endpoint_name)
ROUTES = [
    # ═══ GET ═══
    ("GET",  "/api/health",                  _h(health, "handle_health"),              "health"),
    ("GET",  "/api/version",                 _h(config, "handle_version"),             "version"),
    ("GET",  "/api/settings",                _h(config, "handle_settings"),            "settings"),
    ("GET",  "/api/agents",                  _h(agents, "handle_list"),                "agents"),
    ("GET",  "/api/agents/<name>",           _h(agents, "handle_detail"),              "agent_detail"),
    ("GET",  "/api/skills",                  _h(config, "handle_skills"),              "skills"),
    ("GET",  "/api/skills/content/<name>",   _h(config, "handle_skills_content"),      "skill_content"),
    ("GET",  "/api/cost",                    _h(cost, "handle_cost"),                  "cost"),
    ("GET",  "/api/cost/history",            _h(cost, "handle_history"),               "cost_hist"),
    ("GET",  "/api/cost/alerts",             _h(cost, "handle_alerts"),                "cost_alerts"),
    ("GET",  "/api/cost/summary",            _h(cost, "handle_summary"),               "cost_sum"),
    ("GET",  "/api/cost/dashboard",          _h(cost, "handle_dashboard"),             "cost_dash"),
    ("GET",  "/api/harness/stream",          _h(harness, "handle_stream"),             "harness_stream"),
    ("GET",  "/api/harness/context",         _h(harness, "handle_context"),            "harness_ctx"),
    ("GET",  "/api/harness/subagents",       _h(harness, "handle_subagents"),          "harness_sub"),
    ("GET",  "/api/harness/events",          _h(harness, "handle_events"),             "harness_evt"),
    ("GET",  "/api/harness/status",          _h(harness, "handle_harness_status"),     "harness_st"),
    ("GET",  "/api/hooks/config",            _h(harness, "handle_hooks_config"),       "hooks_cfg"),
    ("GET",  "/api/permissions/allowlist",   _h(harness, "handle_permissions_allowlist"), "perm_al"),
    ("GET",  "/api/permissions/history",     _h(harness, "handle_permissions_history"),   "perm_hist"),
    ("GET",  "/api/permissions/stats",       _h(harness, "handle_permissions_stats"),     "perm_stats"),
    ("GET",  "/api/permissions/audit",       _h(harness, "handle_permission_audit"),      "perm_audit"),
    ("GET",  "/api/memory",                  _h(memory, "handle_list"),                "memory"),
    ("GET",  "/api/memory/search",           _h(memory, "handle_search"),              "mem_search"),
    ("GET",  "/api/memory/timeline",         _h(memory, "handle_timeline"),            "mem_timeline"),
    ("GET",  "/api/memory/<path:filepath>",  _h(memory, "handle_get"),                 "memory_get"),
    ("GET",  "/api/files",                   _h(files, "handle_list"),                 "files"),
    ("GET",  "/api/mcp/status",              _h(config, "handle_mcp_status"),          "mcp"),
    ("GET",  "/api/remote/status",           _h(remote, "handle_status"),              "remote_st"),
    ("GET",  "/api/setup/status",            _h(setup, "handle_status"),               "setup_st"),
    ("GET",  "/api/profile",                 _h(config, "handle_profile"),             "profile"),
    ("GET",  "/api/profiles",                _h(config, "handle_profiles_list"),       "profiles"),
    ("GET",  "/api/check-update",            _h(config, "handle_check_update"),        "check_update"),
    ("GET",  "/api/config/key",              _h(config, "handle_get_api_key"),         "config_key_get"),
    ("GET",  "/api/config/prefs",            _h(config, "handle_get_prefs"),           "config_prefs_get"),
    ("GET",  "/api/routing/feedback/stats",  _h(routing_feedback, "handle_stats"),     "feedback_stats"),
    ("GET",  "/api/worktrees",               _h(worktree_manager, "worktree_handle_list"), "worktrees"),
    ("GET",  "/api/sessions",                _h(sessions, "handle_list"),              "sessions"),
    ("GET",  "/api/sessions/search",         _h(sessions, "handle_search"),            "sessions_search"),
    ("GET",  "/api/sessions/<sid>",          _h(sessions, "handle_get"),               "sessions_get"),
    ("GET",  "/api/sessions/timeline",       _h(session_replay, "handle_timeline"),    "session_timeline"),
    ("GET",  "/api/sessions/replay/<sid>",   _h(session_replay, "handle_replay"),      "session_replay"),
    ("GET",  "/api/sessions/processes",      _h(sessions, "handle_list_processes"),    "session_processes"),
    ("GET",  "/api/operations",              _h(operations, "handle_list"),            "operations"),
    ("GET",  "/api/weixin/status",           _h(weixin_api, "handle_status"),          "weixin_st"),
    ("GET",  "/api/reset/status",            _h(reset, "handle_reset_status"),         "reset_st"),
    ("GET",  "/api/test/status/<run_id>",    _h(test_api, "handle_test_status"),       "test_status"),
    ("GET",  "/api/conversations",           _h(conversations, "handle_list"),         "conversations_list"),
    ("GET",  "/api/conversations/archived",  _h(conversations, "handle_archived_list"), "conversations_archived"),
    ("GET",  "/api/conversations/<id>",      _h(conversations, "handle_get"),          "conversations_get"),
    ("GET",  "/api/cron",                    _h(cron, "handle_list"),                  "cron_list"),
    ("GET",  "/api/search",                  _h(search, "handle_search"),              "search"),
    ("GET",  "/api/pr/list",                 _h(pr, "handle_pr_list"),                 "pr_list"),
    ("GET",  "/api/pr/diff",                 _h(pr, "handle_pr_diff"),                 "pr_diff"),
    ("GET",  "/api/settings/compaction",     _h(config, "handle_compaction_config"),   "compaction_config"),

    # ═══ POST ═══
    ("POST", "/api/chat",                    _h(chat, "handle_chat"),                  "chat"),
    ("POST", "/api/route",                   _h(orchestrate, "handle_route"),          "route"),
    ("POST", "/api/orchestrate",             _h(orchestrate, "handle_orchestrate"),    "orchestrate"),
    ("POST", "/api/agent-update",            _h(agents, "handle_update"),              "agent_update"),
    ("POST", "/api/agent-generate",          _h(agent_factory, "handle_generate"),     "agent_generate"),
    ("POST", "/api/agent-create",            _h(agent_factory, "handle_create"),       "agent_create"),
    ("POST", "/api/agent-delete",            _h(agents, "handle_delete"),              "agent_delete"),
    ("POST", "/api/skills/toggle",           _h(config, "handle_skills_toggle"),       "skill_toggle"),
    ("POST", "/api/skills/save",             _h(config, "handle_skills_save"),         "skill_save"),
    ("POST", "/api/settings",                _h(config, "handle_settings_patch"),      "settings_patch"),
    ("POST", "/api/settings/compaction",     _h(config, "handle_compaction_save"),     "compaction_save"),
    ("POST", "/api/config/key",              _h(config, "handle_save_api_key"),        "config_key_save"),
    ("POST", "/api/config/prefs",            _h(config, "handle_save_prefs"),          "config_prefs_save"),
    ("POST", "/api/mcp/config",              _h(config, "handle_mcp_config"),          "mcp_config"),
    ("POST", "/api/memory/<path:filepath>",  _h(memory, "handle_save"),                "memory_save"),
    ("POST", "/api/hooks/<path:channel>",    _h(harness, "handle_hooks_callback"),     "hooks_cb"),
    ("POST", "/api/permissions/allowlist",   _h(harness, "handle_permissions_allowlist_post"), "perm_al_post"),
    ("POST", "/api/permissions/decision",    _h(harness, "handle_permissions_decision"), "perm_dec"),
    ("POST", "/api/permissions/confirm",     _h(harness, "handle_permission_confirm"),   "perm_conf"),
    ("POST", "/api/permissions/memory/clear",_h(harness, "handle_permission_memory_clear"), "perm_mem_clear"),
    ("POST", "/api/remote/config",           _h(remote, "handle_config"),              "remote_cfg"),
    ("POST", "/api/setup",                   _h(setup, "handle_save"),                 "setup_save"),
    ("POST", "/api/restart",                 _h(restart, "handle_restart"),            "restart"),
    ("POST", "/api/webhook/<channel>",       _h(webhook, "handle_webhook"),            "webhook"),
    ("POST", "/api/test/run",                _h(test_api, "handle_test_run"),          "test_run"),
    ("POST", "/api/session/delete",          _h(harness, "handle_session_delete"),     "session_del"),
    ("POST", "/api/profile",                 _h(config, "handle_profile_set"),         "profile_set"),
    ("POST", "/api/routing/feedback",        _h(routing_feedback, "handle_feedback"),  "routing_fb"),
    ("POST", "/api/worktrees/create",        _h(worktree_manager, "worktree_handle_create"), "wt_create"),
    ("POST", "/api/worktrees/remove",        _h(worktree_manager, "worktree_handle_remove"), "wt_remove"),
    ("POST", "/api/worktrees/cleanup",       _h(worktree_manager, "worktree_handle_cleanup"), "wt_clean"),
    ("POST", "/api/sessions/append",         _h(sessions, "handle_append"),            "sessions_append"),
    ("POST", "/api/sessions/kill",           _h(sessions, "handle_kill"),              "session_kill"),
    ("POST", "/api/sessions/fork",           _h(session_fork, "handle_fork"),          "sessions_fork"),
    ("POST", "/api/weixin/login/start",      _h(weixin_api, "handle_login_start"),     "wx_login"),
    ("POST", "/api/weixin/start",            _h(weixin_api, "handle_start"),           "wx_start"),
    ("POST", "/api/weixin/stop",             _h(weixin_api, "handle_stop"),            "wx_stop"),
    ("POST", "/api/weixin/logout",           _h(weixin_api, "handle_logout"),          "wx_logout"),
    ("POST", "/api/reset/user-file",         _h(reset, "handle_reset_user_file"),      "reset_file"),
    ("POST", "/api/reset/user-all",          _h(reset, "handle_reset_user_all"),       "reset_all"),
    ("POST", "/api/reset/system-category",   _h(reset, "handle_reset_system_category"), "reset_cat"),
    ("POST", "/api/reset/full",              _h(reset, "handle_reset_full"),           "reset_full"),
    ("POST", "/api/conversations/save",      _h(conversations, "handle_save"),         "conversations_save"),
    ("POST", "/api/cron",                    _h(cron, "handle_create"),                "cron_create"),

    # ═══ DELETE ═══
    ("DELETE", "/api/skills/<name>",         _h(config, "handle_skills_delete"),       "skill_del"),
    ("DELETE", "/api/sessions/<sid>",        _h(sessions, "handle_delete"),            "sessions_del"),
    ("DELETE", "/api/conversations/<id>",    _h(conversations, "handle_delete"),       "conversations_del"),
    ("DELETE", "/api/cron/<id>",             _h(cron, "handle_delete"),                "cron_delete"),
]


def register_flask(app, adapt_handler_fn):
    """向 Flask app 注册所有路由——集中注册，消除散落代码"""
    for method, path, handler, endpoint in ROUTES:
        wrapped = adapt_handler_fn(handler)
        app.add_url_rule(path, endpoint, wrapped, methods=[method])
