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
from urllib.parse import urlparse

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
.app-title span{color:var(--muted);font-weight:400;font-size:13px;margin-left:6px;}

.mode-switch{display:flex;gap:0;background:var(--bg);border-radius:6px;overflow:hidden;border:1px solid var(--border);}
.mode-btn{
  padding:6px 16px;font-size:13px;border:none;cursor:pointer;
  background:transparent;color:var(--muted);transition:all .15s;
}
.mode-btn.active{background:var(--blue);color:#fff;}
.mode-btn:hover:not(.active){color:var(--text);background:#1c2128;}

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
  display:flex;gap:10px;padding:16px 20px;border-bottom:1px solid var(--border);
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
  transition:background .15s;
}
#send-btn:hover{background:var(--green-hover);}
#send-btn:disabled{opacity:.5;cursor:not-allowed;}

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
.agent-test-row{display:flex;gap:8px;margin-top:10px;}
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

/* Scrollbar ------------------------------------------------------ */
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:#484f58;}

/* Responsive ----------------------------------------------------- */
@media(max-width:768px){
  .app-header{padding:10px 16px;}
  .app-title{font-size:16px;}
  .mode-btn{padding:5px 12px;font-size:12px;}
  .history-panel{display:none;}
  .history-panel.mobile-open{
    display:flex;position:fixed;top:53px;left:0;bottom:0;z-index:200;
    width:260px;box-shadow:4px 0 20px rgba(0,0,0,.5);
  }
  .history-toggle{
    display:flex!important;align-items:center;justify-content:center;
  }
  .input-row{padding:12px 16px;}
  #task-input{font-size:16px;}
  #output-area{padding:16px;}
  .agents-grid{grid-template-columns:1fr;}
  .cost-stats{flex-direction:column;}
  .tabs{overflow-x:auto;padding:0 8px;}
  .tab-btn{padding:10px 14px;font-size:12px;white-space:nowrap;}
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
  font-size:13px;color:#fff;z-index:300;animation:toastIn .3s ease;
  box-shadow:0 4px 12px rgba(0,0,0,.4);
}
.toast.error{background:var(--red);}
.toast.info{background:var(--blue);}
@keyframes toastIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
</style>
</head>
<body>

<!-- ============ HEADER ============ -->
<header class="app-header">
  <div class="app-title">Agency<span>Agent Test Console</span></div>
  <div class="mode-switch">
    <button class="mode-btn active" data-mode="user" id="mode-user-btn">使用者</button>
    <button class="mode-btn" data-mode="dev" id="mode-dev-btn">开发者</button>
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
      <div class="route-badge" id="route-badge"></div>
      <div id="output-area"><span class="placeholder">等待输入任务...</span></div>
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
        <h3>提示</h3>
        <div class="setting-row" style="color:var(--muted);font-size:13px;">
          修改 .env 后需重启 <code style="color:var(--blue);">python maestro/web.py</code> 使配置生效。
        </div>
      </div>
    </div>

  </div><!-- /dev-mode -->
</div><!-- /main-content -->

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
const historyList = $('#history-list');
const historyPanel = $('#history-panel');
const historyToggle = $('#history-toggle');
const historyClear = $('#history-clear');

// Dev mode tabs
const tabBtns = $$('.tab-btn');
const tabPanels = $$('.tab-panel');

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
// User Mode: Chat
// ===================================================================
let isStreaming = false;

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

sendBtn.addEventListener('click', sendTask);

async function sendTask() {
  if (isStreaming) return;
  const task = taskInput.value.trim();
  if (!task) return;

  isStreaming = true;
  sendBtn.disabled = true;
  taskInput.disabled = true;
  outputArea.innerHTML = '<span class="placeholder"><span class="spinner"></span>路由中...</span>';
  routeBadge.innerHTML = '';

  const startTime = performance.now();
  let agent = '';
  let model = '';

  try {
    // 1. Route
    const routeResp = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task })
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
      body: JSON.stringify({ task, agent })
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

  } catch (e) {
    outputArea.innerHTML = '<span class="output-error">请求失败: ' + escHtml(e.message) + '</span>';
  } finally {
    isStreaming = false;
    sendBtn.disabled = false;
    taskInput.disabled = false;
    taskInput.focus();
    taskInput.style.height = 'auto';
  }
}

// ===================================================================
// Dev Mode: Agents Tab
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
        '</div>' +
      '</div>' +
    '</div>';
  }).join('');

  // Click to expand/collapse
  grid.querySelectorAll('.agent-card').forEach(card => {
    card.addEventListener('click', (e) => {
      // Don't toggle if clicking on test input or button
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
  });
}

async function sendTaskDirect(task, agent) {
  if (isStreaming) return;
  isStreaming = true;
  sendBtn.disabled = true;
  taskInput.disabled = true;
  outputArea.innerHTML = '<span class="placeholder"><span class="spinner"></span>直接调用 ' + escHtml(agent) + '...</span>';
  routeBadge.innerHTML = '';

  const startTime = performance.now();
  let model = '';

  try {
    // Use /api/route just to get model info
    const routeResp = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task })
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
      body: JSON.stringify({ task, agent })
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

  } catch(e) {
    outputArea.innerHTML = '<span class="output-error">请求失败: ' + escHtml(e.message) + '</span>';
  } finally {
    isStreaming = false;
    sendBtn.disabled = false;
    taskInput.disabled = false;
    taskInput.focus();
  }
}

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

        elif parsed.path == "/api/settings":
            self.send_json({
                "deepseek_key_configured": bool(DEEPSEEK_API_KEY),
            })

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
                        self.wfile.write(f"{line}\n\n".encode("utf-8"))
                        self.wfile.flush()
                self.wfile.write("data: [DONE]\n\n".encode("utf-8"))
                self.wfile.flush()
            except Exception as e:
                self.wfile.write(
                    f'data: {{"error": "{str(e)}"}}\n\n'.encode("utf-8")
                )

        elif parsed.path == "/api/stat":
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
    print(f"\n  Agency Web UI  ->  http://localhost:{PORT}\n")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
