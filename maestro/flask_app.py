"""Flask 应用入口 — 注册所有路由，保持旧 web.py 兼容"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, send_from_directory
from flask_cors import CORS

from maestro.flask_adapter import adapt_handler
from maestro.app_config import PORT, BIND_ADDR
from maestro.sandbox import check_docker_available

app = Flask(__name__, static_folder=None)
CORS(app, origins=["http://localhost:*", "http://127.0.0.1:*"])

# ─── 导入所有路由处理函数 ───
from maestro.routes import (
    agents, chat, cost, config, harness, memory, files,
    orchestrate, agent_factory, remote, setup, restart,
    webhook, health, test_api, routing_feedback,
    sessions, operations, weixin_api, reset, static as static_routes,
    session_fork
)
from maestro import worktree_manager

# ─── GET 路由 ───
app.add_url_rule("/api/health", "health", adapt_handler(health.handle_health))
app.add_url_rule("/api/version", "version", adapt_handler(config.handle_version))
app.add_url_rule("/api/settings", "settings", adapt_handler(config.handle_settings))
app.add_url_rule("/api/agents", "agents", adapt_handler(agents.handle_list))
app.add_url_rule("/api/skills", "skills", adapt_handler(config.handle_skills))
app.add_url_rule("/api/cost", "cost", adapt_handler(cost.handle_cost))
app.add_url_rule("/api/cost/history", "cost_hist", adapt_handler(cost.handle_history))
app.add_url_rule("/api/cost/alerts", "cost_alerts", adapt_handler(cost.handle_alerts))
app.add_url_rule("/api/cost/summary", "cost_sum", adapt_handler(cost.handle_summary))
app.add_url_rule("/api/cost/dashboard", "cost_dash", adapt_handler(cost.handle_dashboard))
app.add_url_rule("/api/harness/stream", "harness_stream", adapt_handler(harness.handle_stream))
app.add_url_rule("/api/harness/context", "harness_ctx", adapt_handler(harness.handle_context))
app.add_url_rule("/api/harness/subagents", "harness_sub", adapt_handler(harness.handle_subagents))
app.add_url_rule("/api/harness/events", "harness_evt", adapt_handler(harness.handle_events))
app.add_url_rule("/api/harness/status", "harness_st", adapt_handler(harness.handle_harness_status))
app.add_url_rule("/api/hooks/config", "hooks_cfg", adapt_handler(harness.handle_hooks_config))
app.add_url_rule("/api/permissions/allowlist", "perm_al", adapt_handler(harness.handle_permissions_allowlist))
app.add_url_rule("/api/permissions/history", "perm_hist", adapt_handler(harness.handle_permissions_history))
app.add_url_rule("/api/permissions/stats", "perm_stats", adapt_handler(harness.handle_permissions_stats))
app.add_url_rule("/api/permissions/audit", "perm_audit", adapt_handler(harness.handle_permission_audit))
app.add_url_rule("/api/memory", "memory", adapt_handler(memory.handle_list))
app.add_url_rule("/api/memory/search", "mem_search", adapt_handler(memory.handle_search))
app.add_url_rule("/api/memory/timeline", "mem_timeline", adapt_handler(memory.handle_timeline))
app.add_url_rule("/api/files", "files", adapt_handler(files.handle_list))
app.add_url_rule("/api/mcp/status", "mcp", adapt_handler(config.handle_mcp_status))
app.add_url_rule("/api/remote/status", "remote_st", adapt_handler(remote.handle_status))
app.add_url_rule("/api/setup/status", "setup_st", adapt_handler(setup.handle_status))
app.add_url_rule("/api/profile", "profile", adapt_handler(config.handle_profile))
app.add_url_rule("/api/profiles", "profiles", adapt_handler(config.handle_profiles_list))
app.add_url_rule("/api/check-update", "check_update", adapt_handler(config.handle_check_update))
app.add_url_rule("/api/routing/feedback/stats", "feedback_stats", adapt_handler(routing_feedback.handle_stats))
app.add_url_rule("/api/worktrees", "worktrees", adapt_handler(worktree_manager.worktree_handle_list))
app.add_url_rule("/api/sessions", "sessions", adapt_handler(sessions.handle_list))
app.add_url_rule("/api/sessions/search", "sessions_search", adapt_handler(sessions.handle_search))
app.add_url_rule("/api/operations", "operations", adapt_handler(operations.handle_list))
app.add_url_rule("/api/weixin/status", "weixin_st", adapt_handler(weixin_api.handle_status))
app.add_url_rule("/api/reset/status", "reset_st", adapt_handler(reset.handle_reset_status))

# ─── 带路径参数的 GET 路由 ───
app.add_url_rule("/api/agents/<name>", "agent_detail", adapt_handler(agents.handle_detail))
app.add_url_rule("/api/skills/content/<name>", "skill_content", adapt_handler(config.handle_skills_content))
app.add_url_rule("/api/memory/<path:filepath>", "memory_get", adapt_handler(memory.handle_get))
app.add_url_rule("/api/sessions/<sid>", "sessions_get", adapt_handler(sessions.handle_get))
app.add_url_rule("/api/test/status/<run_id>", "test_status", adapt_handler(test_api.handle_test_status))

# ─── POST 路由 ───
app.add_url_rule("/api/chat", "chat", adapt_handler(chat.handle_chat), methods=["POST"])
app.add_url_rule("/api/route", "route", adapt_handler(orchestrate.handle_route), methods=["POST"])
app.add_url_rule("/api/orchestrate", "orchestrate", adapt_handler(orchestrate.handle_orchestrate), methods=["POST"])
app.add_url_rule("/api/agent-update", "agent_update", adapt_handler(agents.handle_update), methods=["POST"])
app.add_url_rule("/api/agent-generate", "agent_generate", adapt_handler(agent_factory.handle_generate), methods=["POST"])
app.add_url_rule("/api/agent-create", "agent_create", adapt_handler(agent_factory.handle_create), methods=["POST"])
app.add_url_rule("/api/agent-delete", "agent_delete", adapt_handler(agents.handle_delete), methods=["POST"])
app.add_url_rule("/api/skills/toggle", "skill_toggle", adapt_handler(config.handle_skills_toggle), methods=["POST"])
app.add_url_rule("/api/skills/save", "skill_save", adapt_handler(config.handle_skills_save), methods=["POST"])
app.add_url_rule("/api/settings", "settings_patch", adapt_handler(config.handle_settings_patch), methods=["POST"])
app.add_url_rule("/api/mcp/config", "mcp_config", adapt_handler(config.handle_mcp_config), methods=["POST"])
app.add_url_rule("/api/memory/<path:filepath>", "memory_save", adapt_handler(memory.handle_save), methods=["POST"])
app.add_url_rule("/api/hooks/<path:channel>", "hooks_cb", adapt_handler(harness.handle_hooks_callback), methods=["POST"])
app.add_url_rule("/api/permissions/allowlist", "perm_al_post", adapt_handler(harness.handle_permissions_allowlist_post), methods=["POST"])
app.add_url_rule("/api/permissions/decision", "perm_dec", adapt_handler(harness.handle_permissions_decision), methods=["POST"])
app.add_url_rule("/api/permissions/confirm", "perm_conf", adapt_handler(harness.handle_permission_confirm), methods=["POST"])
app.add_url_rule("/api/permissions/memory/clear", "perm_mem_clear", adapt_handler(harness.handle_permission_memory_clear), methods=["POST"])
app.add_url_rule("/api/remote/config", "remote_cfg", adapt_handler(remote.handle_config), methods=["POST"])
app.add_url_rule("/api/setup", "setup_save", adapt_handler(setup.handle_save), methods=["POST"])
app.add_url_rule("/api/restart", "restart", adapt_handler(restart.handle_restart), methods=["POST"])
app.add_url_rule("/api/webhook/<channel>", "webhook", adapt_handler(webhook.handle_webhook), methods=["POST"])
app.add_url_rule("/api/test/run", "test_run", adapt_handler(test_api.handle_test_run), methods=["POST"])
app.add_url_rule("/api/session/delete", "session_del", adapt_handler(harness.handle_session_delete), methods=["POST"])
app.add_url_rule("/api/profile", "profile_set", adapt_handler(config.handle_profile_set), methods=["POST"])
app.add_url_rule("/api/routing/feedback", "routing_fb", adapt_handler(routing_feedback.handle_feedback), methods=["POST"])
app.add_url_rule("/api/worktrees/create", "wt_create", adapt_handler(worktree_manager.worktree_handle_create), methods=["POST"])
app.add_url_rule("/api/worktrees/remove", "wt_remove", adapt_handler(worktree_manager.worktree_handle_remove), methods=["POST"])
app.add_url_rule("/api/worktrees/cleanup", "wt_clean", adapt_handler(worktree_manager.worktree_handle_cleanup), methods=["POST"])
app.add_url_rule("/api/sessions/append", "sessions_append", adapt_handler(sessions.handle_append), methods=["POST"])
app.add_url_rule("/api/sessions/fork", "sessions_fork", adapt_handler(session_fork.handle_fork), methods=["POST"])
app.add_url_rule("/api/weixin/login/start", "wx_login", adapt_handler(weixin_api.handle_login_start), methods=["POST"])
app.add_url_rule("/api/weixin/start", "wx_start", adapt_handler(weixin_api.handle_start), methods=["POST"])
app.add_url_rule("/api/weixin/stop", "wx_stop", adapt_handler(weixin_api.handle_stop), methods=["POST"])
app.add_url_rule("/api/weixin/logout", "wx_logout", adapt_handler(weixin_api.handle_logout), methods=["POST"])
app.add_url_rule("/api/reset/user-file", "reset_file", adapt_handler(reset.handle_reset_user_file), methods=["POST"])
app.add_url_rule("/api/reset/user-all", "reset_all", adapt_handler(reset.handle_reset_user_all), methods=["POST"])
app.add_url_rule("/api/reset/system-category", "reset_cat", adapt_handler(reset.handle_reset_system_category), methods=["POST"])
app.add_url_rule("/api/reset/full", "reset_full", adapt_handler(reset.handle_reset_full), methods=["POST"])

# ─── DELETE 路由 ───
app.add_url_rule("/api/skills/<name>", "skill_del", adapt_handler(config.handle_skills_delete), methods=["DELETE"])
app.add_url_rule("/api/sessions/<sid>", "sessions_del", adapt_handler(sessions.handle_delete), methods=["DELETE"])

# ─── 静态文件 ───
WEBUI_DIR = Path(__file__).resolve().parent.parent / "webui"


@app.route("/")
def index():
    return send_from_directory(str(WEBUI_DIR), "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(WEBUI_DIR), filename)


def main():
    """启动 Flask 应用"""
    if os.environ.get("AGENCY_USE_LEGACY") == "1":
        from maestro.web import main as legacy_main
        legacy_main()
        return

    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print(f"\U0001f680 Agency v0.4.0 — Flask 模式")
    print(f"   地址: http://{BIND_ADDR}:{PORT}")

    if check_docker_available():
        print("🐳 Docker 已就绪")
    else:
        print("💡 安装 Docker 可启用沙箱隔离")

    app.run(host=BIND_ADDR, port=PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
