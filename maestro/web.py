#!/usr/bin/env python3
"""
Agency Web UI --- 浏览器里测试 Agent
  python maestro/web.py   ->   http://localhost:8800

两种模式：
  使用者模式（默认）--- 简洁聊天界面，流式输出
  开发者模式           --- Agents / Routes / Cost / Settings 四个面板
"""
import os
import sys
import json
import time
import yaml
import sqlite3
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))

# --- 加载 .env -------------------------------------------------------
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

from main import route_task, load_agent, estimate_cost, ROUTING

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com"
PORT = 8800


# =====================================================================
# Version
# =====================================================================
def _read_version():
    vf = PROJECT_ROOT / "VERSION"
    if vf.exists():
        return vf.read_text(encoding="utf-8").strip()
    return "0.1.0"

AGENCY_VERSION = _read_version()


# =====================================================================
# HTML 单页应用
# =====================================================================
HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agency</title>
<style>
/* ===== Reset & Base ============================================= */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;
  --muted:#8b949e;--blue:#58a6ff;--green:#238636;--green-hover:#2ea043;
  --orange:#f0883e;--purple:#d2a8ff;--red:#f85149;--cyan:#7ee787;
}
body{
  font:14px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
}

/* ===== Header =================================================== */
.app-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:12px 24px;background:var(--card);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;
}
.app-title{font-size:18px;font-weight:700;color:var(--blue);letter-spacing:-0.5px;}
.app-title .ver{color:var(--muted);font-weight:400;font-size:11px;margin-left:6px;}

.header-right{display:flex;align-items:center;gap:16px;}

/* Mode Toggle Switch ============================================== */
.mode-switch{
  display:flex;align-items:center;gap:8px;background:var(--bg);
  border:1px solid var(--border);border-radius:20px;padding:3px;
}
.mode-option{
  padding:5px 14px;font-size:12px;font-weight:500;border:none;cursor:pointer;
  border-radius:17px;background:transparent;color:var(--muted);transition:all .2s;
  white-space:nowrap;
}
.mode-option.active{background:var(--blue);color:#fff;box-shadow:0 2px 8px rgba(88,166,255,.3);}
.mode-option:hover:not(.active){color:var(--text);}

/* ===== Layout =================================================== */
.main-content{display:flex;height:calc(100vh - 53px);}

/* User Mode ------------------------------------------------------ */
#user-mode{display:flex;width:100%;}
#user-mode.hidden{display:none;}

.history-panel{
  width:260px;min-width:260px;background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow:hidden;
}
.history-panel h3{
  font-size:13px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.5px;padding:16px;border-bottom:1px solid var(--border);
}
.history-list{flex:1;overflow-y:auto;padding:8px;}
.history-item{
  padding:10px 12px;border-radius:6px;cursor:pointer;margin-bottom:4px;
  border:1px solid transparent;transition:all .15s;
}
.history-item:hover{background:#1c2128;border-color:var(--border);}
.history-item .hi-task{font-size:13px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.history-item .hi-meta{font-size:11px;color:var(--muted);margin-top:2px;display:flex;gap:8px;}
.history-clear{
  padding:10px 16px;border-top:1px solid var(--border);
  font-size:12px;color:var(--muted);cursor:pointer;text-align:center;transition:color .15s;
}
.history-clear:hover{color:var(--red);}
.history-empty{color:var(--muted);font-size:12px;text-align:center;padding:24px 8px;}

.chat-area{
  flex:1;display:flex;flex-direction:column;min-width:0;background:var(--bg);
}
.input-row{
  display:flex;gap:10px;padding:16px 20px 8px;border-bottom:1px solid var(--border);
}
#task-input{
  flex:1;padding:12px 16px;background:var(--card);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:14px;outline:none;resize:none;
  min-height:44px;max-height:120px;font-family:inherit;line-height:1.5;
}
#task-input:focus{border-color:var(--blue);}
#task-input::placeholder{color:var(--muted);}
#send-btn{
  padding:10px 22px;background:var(--green);color:#fff;border:none;
  border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;white-space:nowrap;
  transition:all .15s;min-width:70px;
}
#send-btn:hover{background:var(--green-hover);}
#send-btn:disabled{opacity:.5;cursor:not-allowed;}
#send-btn.stopping{background:var(--red);}
#send-btn.stopping:hover{background:#e04040;}

/* Quick Buttons Row ----------------------------------------------- */
.quick-row{
  display:flex;gap:6px;padding:6px 20px 8px;flex-wrap:wrap;
  border-bottom:1px solid var(--border);
}
.quick-btn{
  padding:4px 12px;font-size:12px;border:1px solid var(--border);
  border-radius:14px;background:transparent;color:var(--muted);cursor:pointer;
  transition:all .15s;white-space:nowrap;
}
.quick-btn:hover{color:var(--blue);border-color:var(--blue);background:rgba(88,166,255,0.06);}

.route-badge{
  display:flex;gap:12px;padding:8px 20px;font-size:12px;flex-wrap:wrap;
  min-height:20px;
}
.route-badge span{
  padding:2px 10px;border-radius:10px;font-weight:500;
  border:1px solid var(--border);
}
.route-badge .rb-agent{color:var(--blue);background:rgba(88,166,255,0.1);border-color:rgba(88,166,255,0.25);}
.route-badge .rb-model{color:var(--purple);background:rgba(210,168,255,0.1);border-color:rgba(210,168,255,0.25);}
.route-badge .rb-time{color:var(--cyan);}
.route-badge .rb-cost{color:var(--orange);}

#output-area{
  flex:1;overflow-y:auto;padding:20px;font:13px/1.7 'Cascadia Code','Fira Code','JetBrains Mono',monospace;
  white-space:pre-wrap;word-break:break-word;
}
#output-area .placeholder{color:var(--muted);font-family:inherit;font-size:14px;}
.output-error{color:var(--red);}

/* Copy Button ---------------------------------------------------- */
.output-footer{
  display:flex;justify-content:flex-end;padding:0 20px 12px;border-top:1px solid var(--border);padding-top:8px;
}
.copy-btn{
  padding:6px 16px;font-size:12px;background:var(--card);color:var(--muted);
  border:1px solid var(--border);border-radius:6px;cursor:pointer;transition:all .15s;
}
.copy-btn:hover{color:var(--blue);border-color:var(--blue);}
.copy-btn.copied{color:var(--green);border-color:var(--green);}

/* Dev Mode ------------------------------------------------------- */
#dev-mode{display:none;width:100%;flex-direction:column;}
#dev-mode.visible{display:flex;}

.tabs{
  display:flex;gap:0;padding:0 20px;background:var(--card);border-bottom:1px solid var(--border);
}
.tab-btn{
  padding:12px 20px;font-size:13px;font-weight:500;background:none;border:none;
  color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;
  transition:all .15s;margin-bottom:-1px;
}
.tab-btn:hover{color:var(--text);}
.tab-btn.active{color:var(--blue);border-bottom-color:var(--orange);}

.tab-panel{display:none;flex:1;overflow-y:auto;padding:20px;}
.tab-panel.active{display:block;}

/* Agents Tab ----------------------------------------------------- */
.agents-grid{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;
}
.agent-card{
  background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:16px;cursor:pointer;transition:all .15s;
}
.agent-card:hover{border-color:var(--blue);}
.agent-card.expanded{border-color:var(--blue);grid-column:1/-1;}
.agent-card-name{font-size:15px;font-weight:600;color:var(--blue);}
.agent-card-desc{font-size:12px;color:var(--muted);margin-top:4px;}
.agent-card-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;}
.agent-card-meta .tag{
  font-size:11px;padding:2px 8px;border-radius:4px;
  background:rgba(88,166,255,0.1);color:var(--blue);border:1px solid rgba(88,166,255,0.2);
}
.agent-card-meta .tag.model-tag{background:rgba(210,168,255,0.1);color:var(--purple);border-color:rgba(210,168,255,0.2);}
.agent-card-detail{display:none;margin-top:14px;padding-top:14px;border-top:1px solid var(--border);}
.agent-card.expanded .agent-card-detail{display:block;}
.agent-prompt{
  background:var(--bg);border:1px solid var(--border);border-radius:6px;
  padding:12px;font:12px/1.6 'Cascadia Code','Fira Code',monospace;
  max-height:300px;overflow-y:auto;white-space:pre-wrap;word-break:break-word;
  color:var(--text);
}
.agent-test-row{display:flex;gap:8px;margin-top:10px;align-items:center;}
.agent-test-input{
  flex:1;padding:8px 12px;background:var(--bg);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-size:13px;outline:none;font-family:inherit;
}
.agent-test-input:focus{border-color:var(--blue);}
.agent-test-btn{
  padding:8px 16px;background:var(--green);color:#fff;border:none;
  border-radius:6px;font-size:13px;cursor:pointer;white-space:nowrap;
}
.agent-test-btn:hover{background:var(--green-hover);}
.agent-edit-btn{
  padding:8px 16px;background:var(--blue);color:#fff;border:none;
  border-radius:6px;font-size:13px;cursor:pointer;white-space:nowrap;margin-left:4px;
}
.agent-edit-btn:hover{opacity:.9;}

/* Routes Tab ----------------------------------------------------- */
.route-input-row{display:flex;gap:10px;margin-bottom:16px;}
#route-test-input{
  flex:1;padding:10px 14px;background:var(--card);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:14px;outline:none;font-family:inherit;
}
#route-test-input:focus{border-color:var(--blue);}
#route-test-btn{
  padding:10px 20px;background:var(--blue);color:#fff;border:none;
  border-radius:8px;font-size:14px;cursor:pointer;white-space:nowrap;
}
#route-test-btn:hover{opacity:.9;}

.route-table{width:100%;border-collapse:collapse;font-size:13px;}
.route-table th{
  text-align:left;padding:8px 12px;border-bottom:2px solid var(--border);
  color:var(--muted);font-weight:600;font-size:12px;position:sticky;top:0;background:var(--bg);
}
.route-table td{padding:8px 12px;border-bottom:1px solid var(--border);}
.route-table tr:hover td{background:#1c2128;}
.route-table tr.best td{background:rgba(35,134,54,0.1);}
.route-table tr.best .score-badge{background:var(--green);color:#fff;}
.score-badge{
  display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;
  font-weight:600;background:rgba(240,136,62,0.15);color:var(--orange);min-width:24px;text-align:center;
}
.kw-tags{display:flex;gap:4px;flex-wrap:wrap;}
.kw-tags .kw{
  font-size:11px;padding:1px 6px;border-radius:3px;
  background:rgba(88,166,255,0.08);color:var(--blue);border:1px solid rgba(88,166,255,0.15);
}
.kw-tags .kw.hit{background:rgba(35,134,54,0.15);color:var(--cyan);border-color:rgba(35,134,54,0.3);}

/* Cost Tab ------------------------------------------------------- */
.cost-stats{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;}
.cost-stat-card{
  background:var(--card);border:1px solid var(--border);border-radius:8px;
  padding:16px 20px;min-width:160px;flex:1;
}
.cost-stat-card .csc-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;}
.cost-stat-card .csc-value{font-size:24px;font-weight:700;color:var(--text);margin-top:4px;}
.cost-stat-card .csc-value.accent{color:var(--orange);}

.cost-model-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px;}
.cost-model-table th{
  text-align:left;padding:8px 12px;border-bottom:2px solid var(--border);color:var(--muted);font-weight:600;font-size:12px;
}
.cost-model-table td{padding:8px 12px;border-bottom:1px solid var(--border);}
.cost-model-table tr:hover td{background:#1c2128;}

.cost-section-title{font-size:14px;font-weight:600;color:var(--text);margin:24px 0 12px;}
.cost-recent-table{width:100%;border-collapse:collapse;font-size:12px;}
.cost-recent-table th{
  text-align:left;padding:6px 10px;border-bottom:2px solid var(--border);color:var(--muted);font-weight:600;font-size:11px;
}
.cost-recent-table td{padding:6px 10px;border-bottom:1px solid var(--border);}
.cost-recent-table tr:hover td{background:#1c2128;}
.cost-recent-table .time-col{white-space:nowrap;color:var(--muted);}
.cost-recent-table .cost-col{color:var(--orange);font-weight:500;}

/* Settings Tab --------------------------------------------------- */
.settings-group{margin-bottom:24px;}
.settings-group h3{font-size:14px;font-weight:600;color:var(--text);margin-bottom:10px;}
.setting-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:8px;
  margin-bottom:8px;
}
.setting-row .sr-label{font-size:13px;color:var(--text);}
.setting-row .sr-desc{font-size:11px;color:var(--muted);margin-top:2px;}
.status-badge{
  display:inline-block;padding:3px 12px;border-radius:10px;font-size:12px;font-weight:600;
}
.status-badge.ok{background:rgba(35,134,54,0.15);color:var(--green);border:1px solid rgba(35,134,54,0.3);}
.status-badge.no{background:rgba(248,81,73,0.15);color:var(--red);border:1px solid rgba(248,81,73,0.3);}
.model-select{
  padding:6px 12px;background:var(--bg);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-size:13px;outline:none;cursor:pointer;
}
.model-select:focus{border-color:var(--blue);}

/* Spinner -------------------------------------------------------- */
.spinner{
  display:inline-block;width:14px;height:14px;border:2px solid var(--border);
  border-top-color:var(--blue);border-radius:50%;animation:spin .7s linear infinite;
  vertical-align:middle;margin-right:6px;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* Loading overlay ------------------------------------------------- */
.loading-text{color:var(--muted);font-size:13px;text-align:center;padding:20px;}

/* Modal ---------------------------------------------------------- */
.modal-overlay{
  position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.6);
  z-index:400;display:flex;align-items:center;justify-content:center;
}
.modal-overlay.hidden{display:none;}
.modal-box{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  width:90%;max-width:800px;max-height:85vh;display:flex;flex-direction:column;
  box-shadow:0 8px 40px rgba(0,0,0,.5);
}
.modal-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;border-bottom:1px solid var(--border);
}
.modal-header h3{font-size:16px;color:var(--blue);}
.modal-close-btn{
  background:none;border:none;color:var(--muted);font-size:20px;cursor:pointer;
  padding:4px 8px;border-radius:4px;
}
.modal-close-btn:hover{color:var(--red);background:#1c2128;}
.modal-body{flex:1;overflow-y:auto;padding:20px;}
#modal-editor{
  width:100%;min-height:400px;resize:vertical;background:var(--bg);
  border:1px solid var(--border);border-radius:8px;color:var(--text);
  font:13px/1.6 'Cascadia Code','Fira Code',monospace;padding:14px;outline:none;
}
#modal-editor:focus{border-color:var(--blue);}
.modal-footer{
  display:flex;gap:10px;justify-content:flex-end;
  padding:14px 20px;border-top:1px solid var(--border);
}
.modal-save-btn{
  padding:8px 20px;background:var(--green);color:#fff;border:none;
  border-radius:6px;font-size:13px;cursor:pointer;transition:background .15s;
}
.modal-save-btn:hover{background:var(--green-hover);}
.modal-cancel-btn{
  padding:8px 20px;background:var(--bg);color:var(--text);border:1px solid var(--border);
  border-radius:6px;font-size:13px;cursor:pointer;transition:all .15s;
}
.modal-cancel-btn:hover{border-color:var(--muted);}

/* Scrollbar ------------------------------------------------------ */
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:#484f58;}

/* Responsive ----------------------------------------------------- */
@media(max-width:768px){
  .app-header{padding:10px 16px;}
  .app-title{font-size:16px;}
  .mode-option{padding:4px 10px;font-size:11px;}
  .history-panel{display:none;}
  .history-panel.mobile-open{
    display:flex;position:fixed;top:53px;left:0;bottom:0;z-index:200;
    width:260px;box-shadow:4px 0 20px rgba(0,0,0,.5);
  }
  .history-toggle{
    display:flex!important;align-items:center;justify-content:center;
  }
  .input-row{padding:12px 16px 6px;}
  .quick-row{padding:4px 16px 8px;}
  #task-input{font-size:16px;}
  #output-area{padding:16px;}
  .agents-grid{grid-template-columns:1fr;}
  .cost-stats{flex-direction:column;}
  .tabs{overflow-x:auto;padding:0 8px;}
  .tab-btn{padding:10px 14px;font-size:12px;white-space:nowrap;}
  .modal-box{width:95%;max-height:90vh;}
}

.history-toggle{
  display:none;position:fixed;left:0;top:50%;transform:translateY(-50%);
  background:var(--card);border:1px solid var(--border);border-left:none;
  border-radius:0 6px 6px 0;padding:12px 4px;cursor:pointer;z-index:199;
  color:var(--muted);font-size:11px;writing-mode:vertical-rl;
}
.history-toggle:hover{color:var(--blue);}

/* Toast ---------------------------------------------------------- */
.toast{
  position:fixed;bottom:20px;right:20px;padding:10px 20px;border-radius:8px;
  font-size:13px;color:#fff;z-index:500;animation:toastIn .3s ease;
  box-shadow:0 4px 12px rgba(0,0,0,.4);
}
.toast.error{background:var(--red);}
.toast.info{background:var(--blue);}
.toast.success{background:var(--green);}
@keyframes toastIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
</style>
</head>
<body>

<!-- ============ HEADER ============ -->
<header class="app-header">
  <div class="app-title">Agency<span class="ver" id="version-tag">v0.1.0</span></div>
  <div class="header-right">
    <div class="mode-switch">
      <button class="mode-option active" data-mode="user" id="mode-user-btn">使用者</button>
      <button class="mode-option" data-mode="dev" id="mode-dev-btn">开发者</button>
    </div>
  </div>
</header>

<!-- ============ MAIN ============ -->
<div class="main-content">

  <!-- ===== USER MODE ===== -->
  <div id="user-mode">
    <button class="history-toggle" id="history-toggle" title="历史记录">历史</button>
    <aside class="history-panel" id="history-panel">
      <h3>历史记录</h3>
      <div class="history-list" id="history-list"></div>
      <div class="history-clear" id="history-clear">清除全部历史</div>
    </aside>
    <div class="chat-area">
      <div class="input-row">
        <textarea id="task-input" placeholder="输入任何任务，系统自动分配 Agent..." rows="1"></textarea>
        <button id="send-btn">发送</button>
      </div>
      <div class="quick-row" id="quick-row">
        <button class="quick-btn" data-prompt="帮我写一段 Python 代码来实现一个简单的 REST API">写代码</button>
        <button class="quick-btn" data-prompt="审查这段代码的安全性和性能问题">审查代码</button>
        <button class="quick-btn" data-prompt="这段代码运行时报错了，帮我找找 Bug">找Bug</button>
        <button class="quick-btn" data-prompt="帮我为这个模块编写全面的单元测试">写测试</button>
        <button class="quick-btn" data-prompt="帮我解释一下这段代码的逻辑和流程">解释代码</button>
        <button class="quick-btn" data-prompt="帮我优化这段代码的性能，减少不必要的计算和内存分配">优化性能</button>
      </div>
      <div class="route-badge" id="route-badge"></div>
      <div id="output-area"><span class="placeholder">等待输入任务...</span></div>
      <div class="output-footer" id="output-footer" style="display:none;">
        <button class="copy-btn" id="copy-btn" onclick="copyOutput()">复制结果</button>
      </div>
    </div>
  </div>

  <!-- ===== DEV MODE ===== -->
  <div id="dev-mode">
    <nav class="tabs">
      <button class="tab-btn active" data-tab="agents">Agents</button>
      <button class="tab-btn" data-tab="routes">Routes</button>
      <button class="tab-btn" data-tab="cost">Cost</button>
      <button class="tab-btn" data-tab="settings">Settings</button>
    </nav>

    <!-- Agents Tab -->
    <div class="tab-panel active" id="tab-agents">
      <div class="agents-grid" id="agents-grid"><span class="loading-text">加载中...</span></div>
    </div>

    <!-- Routes Tab -->
    <div class="tab-panel" id="tab-routes">
      <div class="route-input-row">
        <input id="route-test-input" placeholder="输入测试文本，查看所有 Agent 的路由匹配得分...">
        <button id="route-test-btn" onclick="runRouteTest()">测试</button>
      </div>
      <div style="max-height:calc(100vh - 200px);overflow-y:auto;">
        <table class="route-table">
          <thead><tr><th>Agent</th><th>得分</th><th>关键词 <span style="font-weight:400;color:var(--muted)">(绿色=命中)</span></th></tr></thead>
          <tbody id="route-table-body"><tr><td colspan="3" style="text-align:center;color:var(--muted);padding:20px;">输入关键词后点击"测试"查看匹配结果</td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- Cost Tab -->
    <div class="tab-panel" id="tab-cost">
      <div class="cost-stats" id="cost-stats"><span class="loading-text">加载中...</span></div>
      <table class="cost-model-table">
        <thead><tr><th>模型</th><th>调用次数</th><th>费用 (USD)</th></tr></thead>
        <tbody id="cost-model-tbody"></tbody>
      </table>
      <div class="cost-section-title">最近调用记录</div>
      <div style="max-height:400px;overflow-y:auto;">
        <table class="cost-recent-table">
          <thead><tr><th>时间</th><th>Agent</th><th>模型</th><th>输入 Token</th><th>输出 Token</th><th>费用</th><th>耗时</th></tr></thead>
          <tbody id="cost-recent-tbody"><tr><td colspan="7" style="text-align:center;color:var(--muted);padding:20px;">加载中...</td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- Settings Tab -->
    <div class="tab-panel" id="tab-settings">
      <div class="settings-group">
        <h3>API 配置</h3>
        <div class="setting-row">
          <div>
            <div class="sr-label">DEEPSEEK_API_KEY</div>
            <div class="sr-desc">在项目根目录 .env 中配置</div>
          </div>
          <span class="status-badge" id="key-status">检查中...</span>
        </div>
      </div>
      <div class="settings-group">
        <h3>默认模型</h3>
        <div class="setting-row">
          <div>
            <div class="sr-label">聊天模型</div>
            <div class="sr-desc">未指定模型时使用的默认模型</div>
          </div>
          <select class="model-select" id="default-model-select">
            <option value="deepseek-chat">deepseek-chat</option>
            <option value="deepseek-reasoner">deepseek-reasoner</option>
          </select>
        </div>
      </div>
      <div class="settings-group">
        <h3>系统信息</h3>
        <div class="setting-row">
          <div>
            <div class="sr-label">版本</div>
            <div class="sr-desc">Agency 当前版本号</div>
          </div>
          <span style="color:var(--blue);font-weight:600;font-size:14px;" id="settings-version">v0.1.0</span>
        </div>
      </div>
      <div class="settings-group">
        <h3>提示</h3>
        <div class="setting-row" style="color:var(--muted);font-size:13px;">
          修改 .env 后需重启 <code style="color:var(--blue);">python maestro/web.py</code> 使配置生效。
        </div>
      </div>
    </div>

  </div><!-- /dev-mode -->
</div><!-- /main-content -->

<!-- ============ EDIT MODAL ============ -->
<div class="modal-overlay hidden" id="edit-modal-overlay">
  <div class="modal-box">
    <div class="modal-header">
      <h3 id="modal-title">编辑 Agent</h3>
      <button class="modal-close-btn" onclick="closeEditModal()">&times;</button>
    </div>
    <div class="modal-body">
      <textarea id="modal-editor" placeholder="加载中..."></textarea>
    </div>
    <div class="modal-footer">
      <button class="modal-cancel-btn" onclick="closeEditModal()">取消</button>
      <button class="modal-save-btn" onclick="saveAgent()">保存</button>
    </div>
  </div>
</div>

<!-- ============ SCRIPT ============ -->
<script>
// ===================================================================
// Constants
// ===================================================================
const HISTORY_KEY = 'agency_history';
const MAX_HISTORY = 10;
const SETTINGS_KEY = 'agency_settings';

// ===================================================================
// DOM refs
// ===================================================================
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// Mode
const userMode = $('#user-mode');
const devMode = $('#dev-mode');
const modeUserBtn = $('#mode-user-btn');
const modeDevBtn = $('#mode-dev-btn');

// User mode
const taskInput = $('#task-input');
const sendBtn = $('#send-btn');
const routeBadge = $('#route-badge');
const outputArea = $('#output-area');
const outputFooter = $('#output-footer');
const copyBtn = $('#copy-btn');
const historyList = $('#history-list');
const historyPanel = $('#history-panel');
const historyToggle = $('#history-toggle');
const historyClear = $('#history-clear');

// Dev mode tabs
const tabBtns = $$('.tab-btn');
const tabPanels = $$('.tab-panel');

// Version
const versionTag = $('#version-tag');
const settingsVersion = $('#settings-version');

// Edit modal
const editModalOverlay = $('#edit-modal-overlay');
const modalEditor = $('#modal-editor');
const modalTitle = $('#modal-title');
let editingAgentName = '';

// ===================================================================
// Mode Switching
// ===================================================================
function switchMode(mode) {
  if (mode === 'dev') {
    userMode.classList.add('hidden');
    devMode.classList.add('visible');
    modeUserBtn.classList.remove('active');
    modeDevBtn.classList.add('active');
    // Load dev tab content on first switch
    if (!devMode.dataset.loaded) {
      devMode.dataset.loaded = '1';
      loadAgents();
      loadCost();
      loadCostRecent();
      loadSettings();
    }
  } else {
    userMode.classList.remove('hidden');
    devMode.classList.remove('visible');
    modeUserBtn.classList.add('active');
    modeDevBtn.classList.remove('active');
    taskInput.focus();
  }
}

modeUserBtn.addEventListener('click', () => switchMode('user'));
modeDevBtn.addEventListener('click', () => switchMode('dev'));

// ===================================================================
// Dev Tab Switching
// ===================================================================
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    tabBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    tabPanels.forEach(p => p.classList.remove('active'));
    $('#tab-' + tab).classList.add('active');
    // Load cost recent on switch
    if (tab === 'cost') loadCostRecent();
  });
});

// ===================================================================
// Toast
// ===================================================================
function toast(msg, type) {
  type = type || 'info';
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ===================================================================
// User Mode: History
// ===================================================================
function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  } catch(e) { return []; }
}

function saveHistory(items) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, MAX_HISTORY)));
}

function addHistory(task, agent, model, result, elapsed, cost) {
  const items = loadHistory();
  items.unshift({
    id: Date.now(),
    task: task,
    agent: agent,
    model: model,
    result: result,
    elapsed: elapsed,
    cost: cost,
    date: new Date().toLocaleString('zh-CN')
  });
  saveHistory(items);
  renderHistory();
}

function renderHistory() {
  const items = loadHistory();
  if (items.length === 0) {
    historyList.innerHTML = '<div class="history-empty">暂无历史记录</div>';
  } else {
    historyList.innerHTML = items.map((h, i) =>
      '<div class="history-item" data-idx="' + i + '" title="' + escHtml(h.task) + '">' +
        '<div class="hi-task">' + escHtml(h.task.substring(0, 50)) + '</div>' +
        '<div class="hi-meta">' +
          '<span style="color:#58a6ff">' + escHtml(h.agent) + '</span>' +
          '<span>' + escHtml(h.elapsed || '?') + '</span>' +
        '</div>' +
      '</div>'
    ).join('');
  }

  // Click to replay
  historyList.querySelectorAll('.history-item').forEach(el => {
    el.addEventListener('click', () => {
      const items = loadHistory();
      const h = items[parseInt(el.dataset.idx)];
      if (h) {
        taskInput.value = h.task;
        outputArea.innerHTML = '<span class="placeholder">点击发送重新执行此任务...</span>';
        routeBadge.innerHTML = '';
        outputFooter.style.display = 'none';
        sendBtn.click();
      }
    });
  });
}

historyClear.addEventListener('click', () => {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
  toast('历史记录已清除', 'info');
});

// Mobile history toggle
historyToggle.addEventListener('click', () => {
  historyPanel.classList.toggle('mobile-open');
});

// Close mobile history when clicking outside
document.addEventListener('click', (e) => {
  if (historyPanel.classList.contains('mobile-open') &&
      !historyPanel.contains(e.target) &&
      e.target !== historyToggle) {
    historyPanel.classList.remove('mobile-open');
  }
});

// ===================================================================
// Quick Buttons
// ===================================================================
document.querySelectorAll('.quick-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (isStreaming) return;
    taskInput.value = btn.dataset.prompt;
    taskInput.style.height = 'auto';
    taskInput.style.height = Math.min(taskInput.scrollHeight, 120) + 'px';
    sendTask();
  });
});

// ===================================================================
// Copy Output
// ===================================================================
function copyOutput() {
  const text = outputArea.textContent || '';
  if (!text.trim()) return;
  navigator.clipboard.writeText(text).then(() => {
    copyBtn.textContent = '已复制';
    copyBtn.classList.add('copied');
    setTimeout(() => {
      copyBtn.textContent = '复制结果';
      copyBtn.classList.remove('copied');
    }, 2000);
  }).catch(() => {
    // Fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    toast('已复制到剪贴板', 'success');
  });
}

// ===================================================================
// User Mode: Chat (with AbortController support)
// ===================================================================
let isStreaming = false;
let abortController = null;

taskInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendTask();
  }
});

taskInput.addEventListener('input', () => {
  // Auto-resize textarea
  taskInput.style.height = 'auto';
  taskInput.style.height = Math.min(taskInput.scrollHeight, 120) + 'px';
});

sendBtn.addEventListener('click', () => {
  if (isStreaming) {
    // 正在流式输出中，点击 = 停止
    stop();
  } else {
    sendTask();
  }
});

function setSendingUI(sending) {
  if (sending) {
    sendBtn.textContent = '停止';
    sendBtn.classList.add('stopping');
    sendBtn.disabled = false;
    taskInput.disabled = true;
  } else {
    sendBtn.textContent = '发送';
    sendBtn.classList.remove('stopping');
    sendBtn.disabled = false;
    taskInput.disabled = false;
  }
}

function stop() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
  isStreaming = false;
  setSendingUI(false);
  outputArea.textContent += '\n\n[已停止]';
  outputArea.scrollTop = outputArea.scrollHeight;
  outputFooter.style.display = 'block';
  setTimeout(() => taskInput.focus(), 100);
}

async function sendTask() {
  if (isStreaming) return;
  const task = taskInput.value.trim();
  if (!task) return;

  // Clean up previous state
  if (abortController) {
    abortController.abort();
    abortController = null;
  }

  isStreaming = true;
  setSendingUI(true);
  abortController = new AbortController();
  outputArea.innerHTML = '<span class="placeholder"><span class="spinner"></span>路由中...</span>';
  outputFooter.style.display = 'none';
  routeBadge.innerHTML = '';

  const startTime = performance.now();
  let agent = '';
  let model = '';

  try {
    // 1. Route
    const routeResp = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task }),
      signal: abortController.signal
    });
    const routeData = await routeResp.json();
    if (routeData.error) {
      outputArea.innerHTML = '<span class="output-error">路由失败: ' + escHtml(routeData.error) + '</span>';
      return;
    }
    agent = routeData.agent;
    model = routeData.model;

    routeBadge.innerHTML =
      '<span class="rb-agent">Agent: ' + escHtml(agent) + '</span>' +
      '<span class="rb-model">模型: ' + escHtml(model) + '</span>';

    outputArea.textContent = '';

    // 2. Stream chat
    const chatResp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, agent }),
      signal: abortController.signal
    });

    if (!chatResp.ok) {
      const errText = await chatResp.text();
      outputArea.innerHTML = '<span class="output-error">API 错误: ' + escHtml(errText.substring(0, 200)) + '</span>';
      return;
    }

    const reader = chatResp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullOutput = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') break;
          if (data === '[CANCELLED]') {
            fullOutput += '\n\n[已停止]';
            outputArea.textContent = fullOutput;
            outputArea.scrollTop = outputArea.scrollHeight;
            break;
          }
          try {
            const chunk = JSON.parse(data);
            const content = chunk.choices?.[0]?.delta?.content;
            if (content) {
              fullOutput += content;
              outputArea.textContent = fullOutput;
              outputArea.scrollTop = outputArea.scrollHeight;
            }
          } catch(e) { /* skip malformed JSON */ }
        }
      }
    }

    const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);

    // 3. Get stats
    let cost = '?';
    try {
      const statResp = await fetch('/api/stat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, agent })
      });
      const stat = await statResp.json();
      if (!stat.error && stat.cost && stat.cost !== '?') {
        cost = stat.cost;
      }
    } catch(e) { /* ignore */ }

    // Update badge with time & cost
    routeBadge.innerHTML =
      '<span class="rb-agent">Agent: ' + escHtml(agent) + '</span>' +
      '<span class="rb-model">模型: ' + escHtml(model) + '</span>' +
      '<span class="rb-time">' + elapsed + 's</span>' +
      '<span class="rb-cost">$' + cost + '</span>';

    // Save to history
    addHistory(task, agent, model, fullOutput.substring(0, 500), elapsed + 's', '$' + cost);

    // Show copy button
    outputFooter.style.display = 'flex';

  } catch (e) {
    if (e.name === 'AbortError') {
      outputArea.textContent += '\n\n[已停止]';
    } else {
      outputArea.innerHTML = '<span class="output-error">请求失败: ' + escHtml(e.message) + '</span>';
    }
  } finally {
    isStreaming = false;
    abortController = null;
    setSendingUI(false);
    taskInput.focus();
    taskInput.style.height = 'auto';
    outputFooter.style.display = (outputArea.textContent && outputArea.textContent.trim()) ? 'flex' : 'none';
  }
}

// ===================================================================
// User Mode: sendTaskDirect (for agent test button, with abort support)
// ===================================================================
async function sendTaskDirect(task, agent) {
  if (isStreaming) return;

  if (abortController) {
    abortController.abort();
    abortController = null;
  }

  isStreaming = true;
  setSendingUI(true);
  abortController = new AbortController();
  outputArea.innerHTML = '<span class="placeholder"><span class="spinner"></span>直接调用 ' + escHtml(agent) + '...</span>';
  outputFooter.style.display = 'none';
  routeBadge.innerHTML = '';

  const startTime = performance.now();
  let model = '';

  try {
    // Use /api/route just to get model info
    const routeResp = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task }),
      signal: abortController.signal
    });
    const routeData = await routeResp.json();
    model = routeData.model || 'deepseek-chat';

    routeBadge.innerHTML =
      '<span class="rb-agent">Agent: ' + escHtml(agent) + ' (直接指定)</span>' +
      '<span class="rb-model">模型: ' + escHtml(model) + '</span>';

    outputArea.textContent = '';

    const chatResp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, agent }),
      signal: abortController.signal
    });

    if (!chatResp.ok) {
      const errText = await chatResp.text();
      outputArea.innerHTML = '<span class="output-error">API 错误: ' + escHtml(errText.substring(0, 200)) + '</span>';
      return;
    }

    const reader = chatResp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullOutput = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') break;
          if (data === '[CANCELLED]') {
            fullOutput += '\n\n[已停止]';
            outputArea.textContent = fullOutput;
            outputArea.scrollTop = outputArea.scrollHeight;
            break;
          }
          try {
            const chunk = JSON.parse(data);
            const content = chunk.choices?.[0]?.delta?.content;
            if (content) {
              fullOutput += content;
              outputArea.textContent = fullOutput;
              outputArea.scrollTop = outputArea.scrollHeight;
            }
          } catch(e) {}
        }
      }
    }

    const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
    routeBadge.innerHTML +=
      '<span class="rb-time">' + elapsed + 's</span>';

    addHistory(task, agent, model, fullOutput.substring(0, 500), elapsed + 's', '?');

    outputFooter.style.display = 'flex';

  } catch(e) {
    if (e.name === 'AbortError') {
      outputArea.textContent += '\n\n[已停止]';
    } else {
      outputArea.innerHTML = '<span class="output-error">请求失败: ' + escHtml(e.message) + '</span>';
    }
  } finally {
    isStreaming = false;
    abortController = null;
    setSendingUI(false);
    taskInput.focus();
    outputFooter.style.display = (outputArea.textContent && outputArea.textContent.trim()) ? 'flex' : 'none';
  }
}

// ===================================================================
// Dev Mode: Agents Tab (with edit button)
// ===================================================================
let agentsData = [];

async function loadAgents() {
  try {
    const resp = await fetch('/api/agents');
    agentsData = await resp.json();
    renderAgents(agentsData);
  } catch(e) {
    $('#agents-grid').innerHTML = '<span class="output-error">加载 Agent 列表失败: ' + escHtml(e.message) + '</span>';
  }
}

function renderAgents(agents) {
  const grid = $('#agents-grid');
  if (!agents || agents.length === 0) {
    grid.innerHTML = '<span class="loading-text">无 Agent 数据</span>';
    return;
  }

  const modelLabel = { 'haiku': 'Haiku', 'sonnet': 'Sonnet', 'opus': 'Opus', 'deepseek-chat': 'DS-Chat', 'deepseek-reasoner': 'DS-R1' };

  grid.innerHTML = agents.map(a => {
    const kws = (a.keywords || []).slice(0, 6).map(k => '<span class="tag">' + escHtml(k) + '</span>').join('');
    const modelName = modelLabel[a.model] || a.model || '?';
    const tools = (a.tools || []).slice(0, 4).map(t => '<span class="tag">' + escHtml(t) + '</span>').join('');
    return '<div class="agent-card" data-name="' + escHtml(a.name) + '">' +
      '<div class="agent-card-name">' + escHtml(a.name) + '</div>' +
      '<div class="agent-card-desc">' + escHtml(a.description || '') + '</div>' +
      '<div class="agent-card-meta">' +
        '<span class="tag model-tag">' + escHtml(modelName) + '</span>' +
        tools + kws +
      '</div>' +
      '<div class="agent-card-detail">' +
        '<div style="font-size:12px;color:var(--muted);margin-bottom:6px;">System Prompt</div>' +
        '<div class="agent-prompt">' + escHtml(a.prompt_full || a.prompt_preview || '') + '</div>' +
        '<div class="agent-test-row">' +
          '<input class="agent-test-input" placeholder="输入测试任务发给 ' + escHtml(a.name) + '...">' +
          '<button class="agent-test-btn">测试</button>' +
          '<button class="agent-edit-btn">编辑</button>' +
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');

  // Click to expand/collapse
  grid.querySelectorAll('.agent-card').forEach(card => {
    card.addEventListener('click', (e) => {
      // Don't toggle if clicking on test input, buttons
      if (e.target.closest('.agent-test-row')) return;
      const wasExpanded = card.classList.contains('expanded');
      // Collapse all
      grid.querySelectorAll('.agent-card').forEach(c => c.classList.remove('expanded'));
      // Toggle this one
      if (!wasExpanded) card.classList.add('expanded');
    });

    // Test button
    const testBtn = card.querySelector('.agent-test-btn');
    const testInput = card.querySelector('.agent-test-input');
    testBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const t = testInput.value.trim();
      if (!t) { toast('请输入测试任务', 'error'); return; }
      // Switch to user mode and send
      switchMode('user');
      taskInput.value = t;
      // Temporarily override routing to use this agent
      await sendTaskDirect(t, card.dataset.name);
    });

    // Edit button
    const editBtn = card.querySelector('.agent-edit-btn');
    editBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      openEditModal(card.dataset.name);
    });
  });
}

// ===================================================================
// Agent Edit Modal
// ===================================================================
async function openEditModal(name) {
  editingAgentName = name;
  modalTitle.textContent = '编辑 Agent: ' + name;
  modalEditor.value = '加载中...';
  modalEditor.disabled = true;
  editModalOverlay.classList.remove('hidden');

  try {
    const resp = await fetch('/api/agent-content?name=' + encodeURIComponent(name));
    const data = await resp.json();
    if (data.error) {
      modalEditor.value = '加载失败: ' + data.error;
    } else {
      modalEditor.value = data.content || '';
    }
  } catch(e) {
    modalEditor.value = '加载失败: ' + e.message;
  } finally {
    modalEditor.disabled = false;
    modalEditor.focus();
  }
}

function closeEditModal() {
  editModalOverlay.classList.add('hidden');
  editingAgentName = '';
  modalEditor.value = '';
}

async function saveAgent() {
  if (!editingAgentName) return;
  const content = modalEditor.value;

  try {
    const resp = await fetch('/api/agent-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: editingAgentName, content: content })
    });
    const data = await resp.json();
    if (data.ok) {
      toast('Agent "' + editingAgentName + '" 已保存', 'success');
      closeEditModal();
      // Reload agents to refresh
      loadAgents();
    } else {
      toast('保存失败: ' + (data.error || '未知错误'), 'error');
    }
  } catch(e) {
    toast('保存失败: ' + e.message, 'error');
  }
}

// Close modal on overlay click
editModalOverlay.addEventListener('click', (e) => {
  if (e.target === editModalOverlay) closeEditModal();
});

// Close modal on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !editModalOverlay.classList.contains('hidden')) {
    closeEditModal();
  }
});

// ===================================================================
// Dev Mode: Routes Tab
// ===================================================================
async function runRouteTest() {
  const task = $('#route-test-input').value.trim();
  if (!task) { toast('请输入测试文本', 'error'); return; }

  const tbody = $('#route-table-body');
  tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:20px;"><span class="spinner"></span>路由分析中...</td></tr>';

  try {
    const resp = await fetch('/api/route-test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task })
    });
    const results = await resp.json();
    if (!results.length) {
      tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--muted);padding:20px;">无匹配结果</td></tr>';
      return;
    }

    const maxScore = results[0].score;
    tbody.innerHTML = results.map((r, i) => {
      const isBest = i === 0 && r.score > 0;
      const kws = r.keywords.map(kw => {
        const hit = task.toLowerCase().includes(kw.toLowerCase());
        return '<span class="kw' + (hit ? ' hit' : '') + '">' + escHtml(kw) + '</span>';
      }).join('');
      return '<tr class="' + (isBest ? 'best' : '') + '">' +
        '<td>' + escHtml(r.agent) + (isBest ? ' <span style="color:var(--green);font-size:11px;">&#x2714; 最佳匹配</span>' : '') + '</td>' +
        '<td><span class="score-badge">' + r.score + '</span></td>' +
        '<td><div class="kw-tags">' + kws + '</div></td>' +
      '</tr>';
    }).join('');
  } catch(e) {
    tbody.innerHTML = '<tr><td colspan="3" class="output-error">错误: ' + escHtml(e.message) + '</td></tr>';
  }
}

$('#route-test-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') runRouteTest();
});

// ===================================================================
// Dev Mode: Cost Tab
// ===================================================================
async function loadCost() {
  try {
    const resp = await fetch('/api/cost');
    const data = await resp.json();

    if (data.error) {
      $('#cost-stats').innerHTML = '<span class="output-error">加载失败: ' + escHtml(data.error) + '</span>';
      return;
    }

    $('#cost-stats').innerHTML =
      '<div class="cost-stat-card">' +
        '<div class="csc-label">总调用次数</div>' +
        '<div class="csc-value">' + (data.total_calls || 0) + '</div>' +
      '</div>' +
      '<div class="cost-stat-card">' +
        '<div class="csc-label">总费用</div>' +
        '<div class="csc-value accent">$' + (data.total_cost || 0).toFixed(4) + '</div>' +
      '</div>';

    const tbody = $('#cost-model-tbody');
    const byModel = data.by_model || [];
    if (byModel.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--muted);padding:20px;">暂无数据</td></tr>';
    } else {
      tbody.innerHTML = byModel.map(m =>
        '<tr>' +
          '<td>' + escHtml(m.model) + '</td>' +
          '<td>' + m.calls + '</td>' +
          '<td>$' + (m.cost || 0).toFixed(4) + '</td>' +
        '</tr>'
      ).join('');
    }
  } catch(e) {
    $('#cost-stats').innerHTML = '<span class="output-error">加载费用数据失败: ' + escHtml(e.message) + '</span>';
  }
}

async function loadCostRecent() {
  try {
    const tbody = $('#cost-recent-tbody');
    const resp = await fetch('/api/cost-recent');
    const rows = await resp.json();

    if (!rows || rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:20px;">暂无记录</td></tr>';
      return;
    }

    tbody.innerHTML = rows.map(r =>
      '<tr>' +
        '<td class="time-col">' + escHtml(r.time || '') + '</td>' +
        '<td>' + escHtml(r.channel || '') + '</td>' +
        '<td>' + escHtml(r.model || '') + '</td>' +
        '<td>' + (r.in_tokens || 0) + '</td>' +
        '<td>' + (r.out_tokens || 0) + '</td>' +
        '<td class="cost-col">$' + ((r.cost_usd || 0)).toFixed(6) + '</td>' +
        '<td>' + (r.duration_s || 0) + 's</td>' +
      '</tr>'
    ).join('');
  } catch(e) {
    $('#cost-recent-tbody').innerHTML = '<tr><td colspan="7" class="output-error">加载失败: ' + escHtml(e.message) + '</td></tr>';
  }
}

// ===================================================================
// Version
// ===================================================================
async function loadVersion() {
  try {
    const resp = await fetch('/api/version');
    const data = await resp.json();
    const v = 'v' + (data.version || '0.1.0');
    if (versionTag) versionTag.textContent = v;
    if (settingsVersion) settingsVersion.textContent = v;
  } catch(e) {
    // ignore
  }
}

// ===================================================================
// Dev Mode: Settings Tab
// ===================================================================
async function loadSettings() {
  // Check API key status
  try {
    const resp = await fetch('/api/settings');
    const data = await resp.json();
    const badge = $('#key-status');
    if (data.deepseek_key_configured) {
      badge.textContent = '已配置';
      badge.className = 'status-badge ok';
    } else {
      badge.textContent = '未配置';
      badge.className = 'status-badge no';
    }
  } catch(e) {
    $('#key-status').textContent = '检查失败';
    $('#key-status').className = 'status-badge no';
  }

  // Default model
  const settings = loadAppSettings();
  const sel = $('#default-model-select');
  sel.value = settings.defaultModel || 'deepseek-chat';
  sel.addEventListener('change', () => {
    saveAppSettings({ defaultModel: sel.value });
    toast('默认模型已更新为 ' + sel.value, 'info');
  });
}

function loadAppSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
  } catch(e) { return {}; }
}

function saveAppSettings(s) {
  const current = loadAppSettings();
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(Object.assign(current, s)));
}

// ===================================================================
// Utility
// ===================================================================
function escHtml(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ===================================================================
// Init
// ===================================================================
loadVersion();
renderHistory();
taskInput.focus();
</script>

</body>
</html>"""


# =====================================================================
# HTTP Handler
# =====================================================================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))

        elif parsed.path == "/api/agents":
            agents_list = []
            agents_dir = PROJECT_ROOT / "agents"
            if agents_dir.exists():
                for f in sorted(agents_dir.glob("*.md")):
                    content = f.read_text(encoding="utf-8")
                    fm = {}
                    body = content
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            try:
                                fm = yaml.safe_load(parts[1]) or {}
                            except Exception:
                                pass
                            body = parts[2].strip()
                    agents_list.append({
                        "name": f.stem,
                        "description": fm.get("description", ""),
                        "model": fm.get("model", ""),
                        "tools": fm.get("tools", []),
                        "prompt_preview": body[:200],
                        "prompt_full": body,
                        "keywords": ROUTING.get(f.stem, []),
                    })
            self.send_json(agents_list)

        elif parsed.path == "/api/cost":
            try:
                db_path = PROJECT_ROOT / "maestro" / "cost.db"
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    cur = conn.execute(
                        "SELECT COUNT(*), COALESCE(SUM(cost_usd),0) FROM costs"
                    )
                    total_calls, total_cost = cur.fetchone()
                    cur = conn.execute(
                        "SELECT model, COUNT(*), COALESCE(SUM(cost_usd),0) FROM costs GROUP BY model"
                    )
                    by_model = [
                        {"model": r[0], "calls": r[1], "cost": round(r[2] or 0, 4)}
                        for r in cur.fetchall()
                    ]
                    conn.close()
                    self.send_json({
                        "total_calls": total_calls or 0,
                        "total_cost": round(total_cost or 0, 4),
                        "by_model": by_model,
                    })
                else:
                    self.send_json({"total_calls": 0, "total_cost": 0, "by_model": []})
            except Exception as e:
                self.send_json({"error": str(e)})

        elif parsed.path == "/api/cost-recent":
            try:
                db_path = PROJECT_ROOT / "maestro" / "cost.db"
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    rows = conn.execute(
                        "SELECT time, channel, model, in_tokens, out_tokens, cost_usd, duration_s "
                        "FROM costs ORDER BY id DESC LIMIT 20"
                    ).fetchall()
                    conn.close()
                    result = [
                        {
                            "time": r[0],
                            "channel": r[1],
                            "model": r[2],
                            "in_tokens": r[3],
                            "out_tokens": r[4],
                            "cost_usd": r[5],
                            "duration_s": r[6],
                        }
                        for r in rows
                    ]
                    self.send_json(result)
                else:
                    self.send_json([])
            except Exception as e:
                self.send_json({"error": str(e)})

        elif parsed.path == "/api/settings":
            self.send_json({
                "deepseek_key_configured": bool(DEEPSEEK_API_KEY),
            })

        elif parsed.path == "/api/version":
            self.send_json({"version": AGENCY_VERSION})

        elif parsed.path.startswith("/api/agent-content"):
            qs = parse_qs(parsed.query)
            agent_name = qs.get("name", [""])[0]
            agent_file = PROJECT_ROOT / "agents" / f"{agent_name}.md"
            if agent_file.exists():
                self.send_json({
                    "name": agent_name,
                    "content": agent_file.read_text(encoding="utf-8"),
                })
            else:
                self.send_json({"error": "not found"})

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length > 0:
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                try:
                    body = json.loads(raw.decode("gbk", errors="replace"))
                except Exception:
                    body = {}

        # --- 现有端点（保留） ---
        if parsed.path == "/api/route":
            task = body.get("task", "")
            agent, score = route_task(task)
            system_prompt, model = load_agent(agent)
            self.send_json({"agent": agent, "score": score, "model": model})

        elif parsed.path == "/api/chat":
            task = body.get("task", "")
            agent = body.get("agent", "coder")
            system_prompt, model = load_agent(agent)

            import requests as req

            key = os.environ.get("DEEPSEEK_API_KEY", "")
            if not key:
                self.send_json({"error": "DEEPSEEK_API_KEY not set"})
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                resp = req.post(
                    f"{DEEPSEEK_BASE}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": task},
                        ],
                        "stream": True,
                        "temperature": 0.7,
                        "max_tokens": 8192,
                    },
                    stream=True,
                    timeout=300,
                )
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        try:
                            self.wfile.write(f"{line}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            break  # 客户端断开（点了停止）
                self.wfile.write("data: [DONE]\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # 用户主动停止，正常
            except Exception as e:
                try:
                    self.wfile.write(
                        f'data: {{"error": "{str(e)}"}}\n\n'.encode("utf-8")
                    )
                    self.wfile.flush()
                except Exception:
                    pass

        elif parsed.path == "/api/stat":
            task = body.get("task", "")
            agent = body.get("agent", "coder")
            try:
                db_path = PROJECT_ROOT / "maestro" / "cost.db"
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    row = conn.execute(
                        "SELECT cost_usd, duration_s FROM costs WHERE channel=? ORDER BY id DESC LIMIT 1",
                        (agent,),
                    ).fetchone()
                    conn.close()
                    if row:
                        self.send_json({
                            "elapsed": f"{row[1] or 0:.1f}",
                            "cost": f"{row[0] or 0:.6f}",
                        })
                    else:
                        self.send_json({"elapsed": "?", "cost": "?"})
                else:
                    self.send_json({"elapsed": "?", "cost": "?"})
            except Exception:
                self.send_json({"elapsed": "?", "cost": "?"})

        # --- 新增端点 ---
        elif parsed.path == "/api/route-test":
            task = body.get("task", "")
            results = []
            for agent_name, keywords in ROUTING.items():
                score = sum(
                    1 for kw in keywords if kw.lower() in task.lower()
                )
                results.append({
                    "agent": agent_name,
                    "score": score,
                    "keywords": keywords,
                })
            results.sort(key=lambda x: x["score"], reverse=True)
            self.send_json(results)

        elif parsed.path == "/api/agent-save":
            name = body.get("name", "")
            content = body.get("content", "")
            if not name:
                self.send_json({"ok": False, "error": "name is required"})
                return
            agent_file = PROJECT_ROOT / "agents" / f"{name}.md"
            agent_file.write_text(content, encoding="utf-8")
            self.send_json({"ok": True})

        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass  # 安静模式


# =====================================================================
# Entry point
# =====================================================================
if __name__ == "__main__":
    print(f"\n  Agency Web UI v{AGENCY_VERSION}  ->  http://localhost:{PORT}\n")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
