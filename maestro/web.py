#!/usr/bin/env python3
"""
Agency Web UI --- 浏览器里测试 Agent
  python maestro/web.py   ->   http://localhost:8800

两种模式：
  使用者模式（默认）--- 简洁聊天界面，流式输出
  开发者模式           --- Agents / Routes / Cost / Settings / Logs 五个面板
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
/* ===== CSS Variables & Reset ===================================== */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg-start:#0f0f1a;--bg-end:#1a1030;
  --surface:#161622;--surface2:#1e1e30;
  --card:rgba(255,255,255,.025);--card-hover:rgba(255,255,255,.05);
  --border:rgba(255,255,255,.06);--border-focus:rgba(108,92,231,.35);
  --text:#e2e8f0;--text2:#cbd5e1;--muted:#64748b;
  --primary:#6C5CE7;--primary-glow:rgba(108,92,231,.25);
  --green:#00B894;--green-glow:rgba(0,184,148,.25);
  --red:#FF6B6B;--orange:#f0a060;--cyan:#7ee787;
  --radius-sm:8px;--radius:12px;--radius-lg:16px;
  --font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;
  --mono:'JetBrains Mono','Cascadia Code','Fira Code','Consolas',monospace;
  --shadow-card:0 2px 12px rgba(0,0,0,.3);
  --shadow-lg:0 8px 32px rgba(0,0,0,.5);
  --transition:all .2s cubic-bezier(.4,0,.2,1);
}
body{
  font:14px/1.6 var(--font);
  background:linear-gradient(160deg,var(--bg-start) 0%,#15132b 35%,var(--bg-end) 70%,#0f1629 100%);
  background-attachment:fixed;color:var(--text);min-height:100vh;
  -webkit-font-smoothing:antialiased;
}

/* ===== Top Bar ==================================================== */
.topbar{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 24px;background:rgba(18,16,32,.85);
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border-bottom:1px solid rgba(108,92,231,.12);
  position:sticky;top:0;z-index:100;
}
.topbar-logo{display:flex;align-items:baseline;gap:8px;}
.topbar-logo .name{font-size:18px;font-weight:700;color:#c4b5fd;letter-spacing:-.3px;}
.topbar-logo .ver{font-size:11px;color:var(--muted);font-weight:400;}
.topbar-right{display:flex;align-items:center;gap:14px;}

/* Mode Switch ------------------------------------------------------- */
.mode-switch{
  display:flex;align-items:center;gap:2px;background:rgba(255,255,255,.04);
  border:1px solid var(--border);border-radius:22px;padding:3px;
}
.mode-opt{
  padding:5px 15px;font-size:12px;font-weight:500;border:none;cursor:pointer;
  border-radius:19px;background:transparent;color:var(--muted);
  transition:var(--transition);white-space:nowrap;
}
.mode-opt.active{background:var(--primary);color:#fff;box-shadow:0 2px 12px var(--primary-glow);}
.mode-opt:hover:not(.active){color:var(--text);}

/* History Toggle (mobile) ------------------------------------------- */
.history-toggle{
  display:none;position:fixed;left:0;top:50%;transform:translateY(-50%);
  background:rgba(22,22,34,.9);border:1px solid var(--border);border-left:none;
  border-radius:0 6px 6px 0;padding:14px 4px;cursor:pointer;z-index:199;
  color:var(--muted);font-size:11px;writing-mode:vertical-rl;
}
.history-toggle:hover{color:var(--primary);}

/* ===== Layout ====================================================== */
.main-wrap{display:flex;height:calc(100vh - 49px);max-width:1100px;margin:0 auto;}

/* User Mode --------------------------------------------------------- */
#user-mode{display:flex;width:100%;}
#user-mode.hidden{display:none;}

/* Sidebar */
.sidebar{
  width:250px;min-width:250px;background:rgba(14,14,26,.7);
  border-right:1px solid var(--border);display:flex;flex-direction:column;
  overflow:hidden;transition:var(--transition);
}
.sidebar h3{
  font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.8px;padding:16px 18px 12px;
}
.sidebar-list{flex:1;overflow-y:auto;padding:4px 8px;}
.sidebar-item{
  padding:10px 12px;border-radius:8px;cursor:pointer;margin-bottom:3px;
  transition:var(--transition);border:1px solid transparent;
}
.sidebar-item:hover{background:rgba(255,255,255,.03);border-color:var(--border);}
.sidebar-item .si-task{
  font-size:12px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.sidebar-item .si-meta{font-size:10px;color:var(--muted);margin-top:2px;display:flex;gap:8px;}
.sidebar-empty{color:var(--muted);font-size:12px;text-align:center;padding:32px 8px;}
.sidebar-clear{
  padding:12px 18px;border-top:1px solid var(--border);font-size:12px;
  color:var(--muted);cursor:pointer;text-align:center;transition:var(--transition);
}
.sidebar-clear:hover{color:var(--red);}

/* Chat Area */
.chat-area{
  flex:1;display:flex;flex-direction:column;min-width:0;padding:20px 24px;
}

/* Input Section */
.input-section{
  display:flex;gap:10px;margin-bottom:12px;
}
#task-input{
  flex:1;padding:14px 18px;background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius-lg);color:var(--text);font-size:15px;outline:none;
  resize:none;min-height:52px;max-height:140px;font-family:var(--font);line-height:1.5;
  transition:var(--transition);
}
#task-input:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-glow);}
#task-input::placeholder{color:var(--muted);}
#task-input:disabled{opacity:.45;cursor:not-allowed;}
#send-btn{
  width:52px;min-width:52px;height:52px;background:linear-gradient(135deg,var(--primary),#5A4BD1);
  color:#fff;border:none;border-radius:var(--radius);font-size:18px;cursor:pointer;
  transition:var(--transition);display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 14px var(--primary-glow);
}
#send-btn:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(108,92,231,.35);}
#send-btn:active{transform:translateY(0);}
#send-btn.stopping{
  background:linear-gradient(135deg,var(--red),#e55a5a);
  box-shadow:0 4px 14px rgba(255,107,107,.3);
  animation:pulse-stop 1.8s ease-in-out infinite;
}
#send-btn.stopping:hover{box-shadow:0 6px 20px rgba(255,107,107,.4);}
@keyframes pulse-stop{
  0%,100%{box-shadow:0 0 0 0 rgba(255,107,107,.45);}
  50%{box-shadow:0 0 0 12px rgba(255,107,107,0);}
}

/* Quick Tags */
.tag-row{
  display:flex;gap:7px;margin-bottom:14px;flex-wrap:wrap;
}
.tag-chip{
  padding:6px 15px;font-size:12px;border:1px solid rgba(108,92,231,.18);
  border-radius:20px;background:rgba(108,92,231,.06);color:#a78bfa;
  cursor:pointer;transition:var(--transition);white-space:nowrap;
  font-weight:500;
}
.tag-chip:hover{
  background:rgba(108,92,231,.15);color:#c4b5fd;border-color:rgba(108,92,231,.35);
  transform:translateY(-1px);
}

/* Route Badge */
.route-badge{
  display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;min-height:22px;align-items:center;
}
.route-badge .badge{
  padding:3px 11px;border-radius:10px;font-size:11px;font-weight:500;
}
.badge-agent{background:rgba(108,92,231,.12);color:#a78bfa;border:1px solid rgba(108,92,231,.2);}
.badge-model{background:rgba(0,184,148,.1);color:#5eead4;border:1px solid rgba(0,184,148,.18);}
.badge-time{color:var(--muted);font-size:11px;}
.badge-cost{color:var(--orange);font-size:11px;font-weight:600;}

/* Output Panel */
.output-panel{
  flex:1;background:rgba(0,0,0,.35);border:1px solid var(--border);
  border-radius:var(--radius-lg);display:flex;flex-direction:column;overflow:hidden;
  box-shadow:inset 0 2px 8px rgba(0,0,0,.2);
}
.output-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 16px;background:rgba(0,0,0,.25);border-bottom:1px solid var(--border);
  font-size:12px;color:var(--muted);
}
.output-header .oh-left{display:flex;align-items:center;gap:8px;}
.output-header .oh-dot{width:7px;height:7px;border-radius:50%;background:var(--green);
  box-shadow:0 0 6px var(--green-glow);}
.output-header .oh-dot.idle{background:var(--muted);box-shadow:none;}
#output-body{
  flex:1;overflow-y:auto;padding:16px;font:13px/1.75 var(--mono);
  white-space:pre-wrap;word-break:break-word;color:#94a3b8;
}
#output-body .placeholder{color:var(--muted);font-family:var(--font);font-size:14px;}
#output-body .error-text{color:var(--red);}
#output-body .streaming-cursor{
  display:inline-block;width:8px;height:16px;background:var(--primary);
  animation:blink 1s step-end infinite;vertical-align:text-bottom;margin-left:1px;
}
@keyframes blink{50%{opacity:0}}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

/* Output Footer */
.output-footer{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 16px;background:rgba(0,0,0,.2);border-top:1px solid var(--border);
  font-size:12px;
}
.of-left{display:flex;align-items:center;gap:12px;color:var(--muted);}
.of-right{display:flex;gap:8px;}
.footer-btn{
  padding:5px 13px;font-size:11px;background:transparent;color:var(--muted);
  border:1px solid var(--border);border-radius:6px;cursor:pointer;
  transition:var(--transition);font-family:var(--font);
}
.footer-btn:hover{color:var(--text);border-color:rgba(255,255,255,.15);}
.footer-btn.copied{color:var(--green);border-color:rgba(0,184,148,.3);}

/* Dev Mode ---------------------------------------------------------- */
#dev-mode{display:none;width:100%;flex-direction:column;padding:0 24px;}
#dev-mode.visible{display:flex;}

.dev-tabs{
  display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:20px;
}
.dev-tab{
  padding:10px 20px;font-size:13px;font-weight:500;background:none;border:none;
  color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;
  transition:var(--transition);margin-bottom:-1px;font-family:var(--font);
}
.dev-tab:hover{color:var(--text);}
.dev-tab.active{color:var(--primary);border-bottom-color:var(--primary);}

.dev-panel{display:none;flex:1;overflow-y:auto;padding-bottom:24px;}
.dev-panel.active{display:block;animation:fadeIn .25s ease;}

/* Agent Cards Grid */
.agent-grid{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;
}
.agent-card{
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:18px;cursor:pointer;transition:var(--transition);position:relative;
}
.agent-card:hover{border-color:rgba(108,92,231,.25);box-shadow:0 4px 16px rgba(0,0,0,.2);}
.agent-card.expanded{border-color:var(--primary);grid-column:1/-1;}
.agent-card .ac-name{font-size:16px;font-weight:600;color:#c4b5fd;}
.agent-card .ac-desc{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.5;}
.agent-card .ac-meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px;}
.agent-card .ac-tag{
  font-size:10px;padding:2px 8px;border-radius:4px;
  background:rgba(108,92,231,.1);color:#a78bfa;border:1px solid rgba(108,92,231,.18);
  font-weight:500;
}
.agent-card .ac-tag.model-tag{background:rgba(0,184,148,.08);color:#5eead4;border-color:rgba(0,184,148,.15);}
.agent-card .ac-detail{display:none;margin-top:14px;padding-top:14px;border-top:1px solid var(--border);}
.agent-card.expanded .ac-detail{display:block;}
.agent-card .ac-prompt{
  background:rgba(0,0,0,.35);border:1px solid var(--border);border-radius:8px;
  padding:12px;font:12px/1.6 var(--mono);max-height:280px;overflow-y:auto;
  white-space:pre-wrap;word-break:break-word;color:var(--text2);
}
.agent-card .ac-test-row{display:flex;gap:8px;margin-top:10px;align-items:center;}
.agent-card .ac-test-input{
  flex:1;padding:8px 12px;background:rgba(0,0,0,.3);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:12px;outline:none;font-family:var(--font);
}
.agent-card .ac-test-input:focus{border-color:var(--primary);}
.btn-sm{
  padding:7px 14px;font-size:12px;border:none;border-radius:6px;cursor:pointer;
  font-weight:500;transition:var(--transition);font-family:var(--font);
}
.btn-sm.primary{background:var(--primary);color:#fff;}
.btn-sm.primary:hover{box-shadow:0 2px 10px var(--primary-glow);}
.btn-sm.green{background:var(--green);color:#fff;}
.btn-sm.green:hover{box-shadow:0 2px 10px var(--green-glow);}

/* Route Tab */
.route-search{display:flex;gap:10px;margin-bottom:16px;}
.route-search input{
  flex:1;padding:10px 14px;background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);color:var(--text);font-size:14px;outline:none;font-family:var(--font);
}
.route-search input:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-glow);}

.route-table{width:100%;border-collapse:collapse;font-size:12px;}
.route-table th{
  text-align:left;padding:8px 12px;border-bottom:2px solid var(--border);
  color:var(--muted);font-weight:600;font-size:11px;position:sticky;top:0;
  background:var(--bg-start);
}
.route-table td{padding:8px 12px;border-bottom:1px solid var(--border);}
.route-table tr:hover td{background:rgba(255,255,255,.02);}
.route-table tr.best td{background:rgba(0,184,148,.05);}
.score-badge{
  display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;
  font-weight:600;background:rgba(240,160,96,.12);color:var(--orange);min-width:24px;text-align:center;
}
.route-table tr.best .score-badge{background:rgba(0,184,148,.18);color:var(--green);}
.kw-tags{display:flex;gap:3px;flex-wrap:wrap;}
.kw-tags .kw{
  font-size:10px;padding:1px 6px;border-radius:3px;
  background:rgba(108,92,231,.06);color:#a78bfa;border:1px solid rgba(108,92,231,.12);
}
.kw-tags .kw.hit{background:rgba(0,184,148,.12);color:var(--cyan);border-color:rgba(0,184,148,.22);}

/* Cost Tab */
.cost-summary{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;}
.cost-card{
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:16px 20px;min-width:150px;flex:1;transition:var(--transition);
}
.cost-card:hover{border-color:rgba(108,92,231,.15);}
.cost-card .cc-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;}
.cost-card .cc-value{font-size:22px;font-weight:700;color:var(--text);margin-top:4px;}
.cost-card .cc-value.highlight{color:var(--orange);}

.model-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:12px;}
.model-table th{
  text-align:left;padding:8px 12px;border-bottom:2px solid var(--border);
  color:var(--muted);font-weight:600;font-size:11px;
}
.model-table td{padding:8px 12px;border-bottom:1px solid var(--border);}
.model-table tr:hover td{background:rgba(255,255,255,.02);}
.cost-section-title{font-size:13px;font-weight:600;color:var(--text);margin:24px 0 10px;}

/* Settings Tab */
.settings-group{margin-bottom:20px;}
.settings-group h3{font-size:13px;font-weight:600;color:var(--text);margin-bottom:10px;}
.setting-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:12px 16px;background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius);margin-bottom:8px;transition:var(--transition);
}
.setting-row:hover{border-color:rgba(255,255,255,.08);}
.setting-row .sr-label{font-size:13px;color:var(--text);}
.setting-row .sr-desc{font-size:11px;color:var(--muted);margin-top:2px;}
.status-dot{
  display:inline-block;padding:3px 12px;border-radius:10px;font-size:11px;font-weight:600;
}
.status-dot.ok{background:rgba(0,184,148,.1);color:var(--green);border:1px solid rgba(0,184,148,.2);}
.status-dot.bad{background:rgba(255,107,107,.1);color:var(--red);border:1px solid rgba(255,107,107,.2);}
.model-select{
  padding:6px 12px;background:rgba(0,0,0,.3);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-size:12px;outline:none;cursor:pointer;
}
.model-select:focus{border-color:var(--primary);}

/* Logs Tab */
.logs-table{width:100%;border-collapse:collapse;font-size:12px;}
.logs-table th{
  text-align:left;padding:6px 10px;border-bottom:2px solid var(--border);
  color:var(--muted);font-weight:600;font-size:11px;
}
.logs-table td{padding:6px 10px;border-bottom:1px solid var(--border);}
.logs-table tr:hover td{background:rgba(255,255,255,.02);}
.logs-table .time-col{white-space:nowrap;color:var(--muted);font-size:11px;}
.logs-table .cost-col{color:var(--orange);font-weight:500;}

/* Spinner ----------------------------------------------------------- */
.spinner{
  display:inline-block;width:14px;height:14px;border:2px solid var(--border);
  border-top-color:var(--primary);border-radius:50%;animation:spin .7s linear infinite;
  vertical-align:middle;margin-right:6px;
}
@keyframes spin{to{transform:rotate(360deg)}}

/* Modal */
.modal-overlay{
  position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.65);
  z-index:400;display:flex;align-items:center;justify-content:center;
}
.modal-overlay.hidden{display:none;}
.modal-box{
  background:#1a1a2e;border:1px solid var(--border);border-radius:var(--radius-lg);
  width:90%;max-width:800px;max-height:85vh;display:flex;flex-direction:column;
  box-shadow:var(--shadow-lg);
}
.modal-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px 20px;border-bottom:1px solid var(--border);
}
.modal-header h3{font-size:15px;color:#c4b5fd;}
.modal-close{
  background:none;border:none;color:var(--muted);font-size:22px;cursor:pointer;
  padding:4px 8px;border-radius:4px;transition:var(--transition);
}
.modal-close:hover{color:var(--red);}
.modal-body{flex:1;overflow-y:auto;padding:20px;}
#modal-editor{
  width:100%;min-height:380px;resize:vertical;background:rgba(0,0,0,.35);
  border:1px solid var(--border);border-radius:8px;color:var(--text);
  font:13px/1.6 var(--mono);padding:14px;outline:none;
}
#modal-editor:focus{border-color:var(--primary);}
.modal-footer{
  display:flex;gap:8px;justify-content:flex-end;padding:14px 20px;border-top:1px solid var(--border);
}

/* Toast */
.toast{
  position:fixed;bottom:24px;right:24px;padding:10px 20px;border-radius:var(--radius);
  font-size:13px;color:#fff;z-index:500;animation:slideUp .3s ease;
  box-shadow:0 4px 16px rgba(0,0,0,.4);
}
.toast.error{background:var(--red);}
.toast.info{background:var(--primary);}
.toast.success{background:var(--green);}
@keyframes slideUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}

/* Scrollbar */
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.08);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,.14);}

/* Responsive */
@media(max-width:768px){
  .topbar{padding:8px 14px;}
  .topbar-logo .name{font-size:16px;}
  .mode-opt{padding:4px 10px;font-size:11px;}
  .sidebar{display:none;}
  .sidebar.mobile-open{
    display:flex;position:fixed;top:49px;left:0;bottom:0;z-index:200;
    width:250px;box-shadow:4px 0 24px rgba(0,0,0,.6);
  }
  .history-toggle{display:flex;align-items:center;justify-content:center;}
  .chat-area{padding:14px 12px;}
  #task-input{font-size:16px;padding:12px 14px;min-height:48px;}
  #send-btn{width:46px;min-width:46px;height:46px;}
  .output-panel{border-radius:var(--radius);}
  .agent-grid{grid-template-columns:1fr;}
  .cost-summary{flex-direction:column;}
  .dev-tabs{overflow-x:auto;}
  .dev-tab{padding:8px 12px;font-size:11px;white-space:nowrap;}
  .modal-box{width:95%;max-height:90vh;}
  #dev-mode{padding:0 12px;}
}
</style>
</head>
<body>

<!-- ====================== TOP BAR ====================== -->
<header class="topbar">
  <div class="topbar-logo">
    <span class="name">Agency</span>
    <span class="ver" id="ver-tag">v0.1.0</span>
  </div>
  <div class="topbar-right">
    <div class="mode-switch" id="mode-switch">
      <button class="mode-opt active" data-mode="user">使用者</button>
      <button class="mode-opt" data-mode="dev">开发者</button>
    </div>
  </div>
</header>

<!-- ====================== MAIN CONTENT ====================== -->
<div class="main-wrap">

  <!-- ===== USER MODE ===== -->
  <div id="user-mode">
    <button class="history-toggle" id="hist-toggle" title="历史">历史</button>
    <aside class="sidebar" id="sidebar">
      <h3>历史记录</h3>
      <div class="sidebar-list" id="hist-list"></div>
      <div class="sidebar-clear" id="hist-clear">清空全部</div>
    </aside>

    <div class="chat-area">
      <!-- Input -->
      <div class="input-section">
        <textarea id="task-input" placeholder="告诉 Agency 你想做什么..." rows="1"></textarea>
        <button id="send-btn" title="发送 (Enter) / 停止 (Esc)">&#10132;</button>
      </div>
      <!-- Quick Tags -->
      <div class="tag-row" id="tag-row">
        <span class="tag-chip" data-prompt="帮我写一段 Python 代码来实现一个简单的 REST API">写代码</span>
        <span class="tag-chip" data-prompt="审查这段代码的安全性和性能问题">审查</span>
        <span class="tag-chip" data-prompt="这段代码运行时报错了，帮我找找 Bug">找Bug</span>
        <span class="tag-chip" data-prompt="帮我为这个模块编写全面的单元测试">测试</span>
        <span class="tag-chip" data-prompt="帮我解释一下这段代码的逻辑和流程">解释</span>
        <span class="tag-chip" data-prompt="帮我优化这段代码的性能，减少不必要的计算和内存分配">优化</span>
      </div>
      <!-- Route Badge -->
      <div class="route-badge" id="route-badge"></div>
      <!-- Output Panel -->
      <div class="output-panel">
        <div class="output-header">
          <div class="oh-left">
            <span class="oh-dot idle" id="status-dot"></span>
            <span id="output-label">就绪</span>
          </div>
        </div>
        <div id="output-body"><span class="placeholder">输入任务后按 Enter 发送</span></div>
        <div class="output-footer" id="output-footer" style="display:none">
          <div class="of-left">
            <span id="stat-time"></span>
            <span id="stat-cost"></span>
          </div>
          <div class="of-right">
            <button class="footer-btn" id="btn-copy">复制结果</button>
            <button class="footer-btn" id="btn-new-chat">新对话</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ===== DEV MODE ===== -->
  <div id="dev-mode">
    <nav class="dev-tabs" id="dev-tabs">
      <button class="dev-tab active" data-tab="agents">Agents</button>
      <button class="dev-tab" data-tab="routes">Routes</button>
      <button class="dev-tab" data-tab="cost">Cost</button>
      <button class="dev-tab" data-tab="settings">Settings</button>
      <button class="dev-tab" data-tab="logs">Logs</button>
    </nav>

    <!-- Agents -->
    <div class="dev-panel active" id="panel-agents">
      <div class="agent-grid" id="agent-grid"><span style="color:var(--muted);font-size:13px;">加载中...</span></div>
    </div>

    <!-- Routes -->
    <div class="dev-panel" id="panel-routes">
      <div class="route-search">
        <input id="route-search-input" placeholder="输入关键词，测试所有 Agent 的匹配得分...">
        <button class="btn-sm primary" id="route-search-btn">测试</button>
      </div>
      <div style="max-height:calc(100vh - 260px);overflow-y:auto;">
        <table class="route-table">
          <thead><tr><th>Agent</th><th>得分</th><th>关键词 <span style="font-weight:400;color:var(--muted)">(绿色=命中)</span></th></tr></thead>
          <tbody id="route-tbody"><tr><td colspan="3" style="text-align:center;color:var(--muted);padding:24px;">输入关键词后点击"测试"</td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- Cost -->
    <div class="dev-panel" id="panel-cost">
      <div class="cost-summary" id="cost-summary"><span style="color:var(--muted);font-size:13px;">加载中...</span></div>
      <table class="model-table">
        <thead><tr><th>模型</th><th>调用次数</th><th>费用 (USD)</th></tr></thead>
        <tbody id="cost-model-tbody"></tbody>
      </table>
      <div class="cost-section-title">最近调用</div>
      <div style="max-height:380px;overflow-y:auto;">
        <table class="logs-table">
          <thead><tr><th>时间</th><th>Agent</th><th>模型</th><th>入Token</th><th>出Token</th><th>费用</th><th>耗时</th></tr></thead>
          <tbody id="cost-recent-tbody"><tr><td colspan="7" style="text-align:center;color:var(--muted);padding:24px;">加载中...</td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- Settings -->
    <div class="dev-panel" id="panel-settings">
      <div class="settings-group">
        <h3>API 配置</h3>
        <div class="setting-row">
          <div><div class="sr-label">DEEPSEEK_API_KEY</div><div class="sr-desc">在项目根目录 .env 中配置</div></div>
          <span class="status-dot" id="key-status">检查中...</span>
        </div>
      </div>
      <div class="settings-group">
        <h3>默认模型</h3>
        <div class="setting-row">
          <div><div class="sr-label">对话模型</div><div class="sr-desc">未指定模型时的默认选择</div></div>
          <select class="model-select" id="default-model">
            <option value="deepseek-chat">deepseek-chat</option>
            <option value="deepseek-reasoner">deepseek-reasoner</option>
          </select>
        </div>
      </div>
      <div class="settings-group">
        <h3>系统</h3>
        <div class="setting-row">
          <div><div class="sr-label">版本</div><div class="sr-desc">Agency 当前版本</div></div>
          <span style="color:#c4b5fd;font-weight:600;" id="settings-ver">v0.1.0</span>
        </div>
      </div>
      <div class="settings-group">
        <div class="setting-row" style="color:var(--muted);font-size:12px;justify-content:flex-start;">
          修改 .env 后需重启 <code style="color:var(--primary);">python maestro/web.py</code>
        </div>
      </div>
    </div>

    <!-- Logs -->
    <div class="dev-panel" id="panel-logs">
      <div style="max-height:calc(100vh - 180px);overflow-y:auto;">
        <table class="logs-table">
          <thead><tr><th>时间</th><th>Agent</th><th>模型</th><th>入Token</th><th>出Token</th><th>费用</th><th>耗时</th></tr></thead>
          <tbody id="logs-tbody"><tr><td colspan="7" style="text-align:center;color:var(--muted);padding:24px;">加载中...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ====================== EDIT MODAL ====================== -->
<div class="modal-overlay hidden" id="modal-overlay">
  <div class="modal-box">
    <div class="modal-header">
      <h3 id="modal-title">编辑 Agent</h3>
      <button class="modal-close" id="modal-close">&times;</button>
    </div>
    <div class="modal-body">
      <textarea id="modal-editor" placeholder="加载中..."></textarea>
    </div>
    <div class="modal-footer">
      <button class="btn-sm" style="background:transparent;color:var(--text);border:1px solid var(--border);" id="modal-cancel">取消</button>
      <button class="btn-sm green" id="modal-save">保存</button>
    </div>
  </div>
</div>

<!-- ====================== SCRIPTS ====================== -->
<script>
// ===================================================================
// DOM Refs
// ===================================================================
var $ = function(s) { return document.querySelector(s); };
var $$ = function(s) { return document.querySelectorAll(s); };

var taskInput = $('#task-input');
var sendBtn = $('#send-btn');
var routeBadge = $('#route-badge');
var outputBody = $('#output-body');
var outputFooter = $('#output-footer');
var statusDot = $('#status-dot');
var outputLabel = $('#output-label');
var statTime = $('#stat-time');
var statCost = $('#stat-cost');
var verTag = $('#ver-tag');
var settingsVer = $('#settings-ver');
var userMode = $('#user-mode');
var devMode = $('#dev-mode');
var sidebar = $('#sidebar');

// Modal
var modalOverlay = $('#modal-overlay');
var modalEditor = $('#modal-editor');
var modalTitle = $('#modal-title');
var editingAgent = '';

// ===================================================================
// Constants
// ===================================================================
var HIST_KEY = 'agency_history_v2';
var MAX_HIST = 15;
var SETTINGS_KEY = 'agency_settings_v2';

// ===================================================================
// Core State
// ===================================================================
var isStreaming = false;
var abortCtrl = null;
var streamTimer = null;  // elapsed timer

// ===================================================================
// resetUI() -- 唯一的状态恢复入口
// ===================================================================
function resetUI() {
  isStreaming = false;
  abortCtrl = null;
  if (streamTimer) { clearInterval(streamTimer); streamTimer = null; }
  sendBtn.textContent = '➤';
  sendBtn.classList.remove('stopping');
  sendBtn.disabled = false;
  taskInput.disabled = false;
  taskInput.readOnly = false;
  taskInput.style.pointerEvents = 'auto';
  statusDot.classList.add('idle');
  outputLabel.textContent = '就绪';
  // 移除闪烁光标
  var cur = outputBody.querySelector('.streaming-cursor');
  if (cur) cur.remove();
  setTimeout(function() { taskInput.focus(); }, 60);
}

// ===================================================================
// setSendingUI -- 进入发送状态
// ===================================================================
function setSendingUI() {
  sendBtn.textContent = '■';
  sendBtn.classList.add('stopping');
  sendBtn.disabled = false;
  taskInput.disabled = true;
  taskInput.readOnly = true;
  statusDot.classList.remove('idle');
  outputLabel.textContent = '处理中...';
  outputFooter.style.display = 'none';
}

// ===================================================================
// stop() -- 最小化：只 abort，不碰 UI 状态
// ===================================================================
function stop() {
  if (abortCtrl) {
    abortCtrl.abort();
  }
}

// ===================================================================
// Utility
// ===================================================================
function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toast(msg, type) {
  type = type || 'info';
  var el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(function() { el.remove(); }, 3000);
}

// ===================================================================
// History
// ===================================================================
function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HIST_KEY) || '[]'); } catch(e) { return []; }
}
function saveHistory(items) {
  localStorage.setItem(HIST_KEY, JSON.stringify(items.slice(0, MAX_HIST)));
}
function addHistory(task, agent, model, elapsed, cost) {
  var items = loadHistory();
  items.unshift({ id: Date.now(), task: task, agent: agent, model: model, elapsed: elapsed, cost: cost, date: new Date().toLocaleString('zh-CN') });
  saveHistory(items);
  renderHistory();
}
function renderHistory() {
  var items = loadHistory();
  var list = $('#hist-list');
  if (items.length === 0) {
    list.innerHTML = '<div class="sidebar-empty">暂无记录</div>';
  } else {
    list.innerHTML = items.map(function(h, i) {
      return '<div class="sidebar-item" data-idx="' + i + '" title="' + escHtml(h.task) + '">'
        + '<div class="si-task">' + escHtml(h.task.substring(0, 45)) + '</div>'
        + '<div class="si-meta"><span style="color:#a78bfa">' + escHtml(h.agent) + '</span><span>' + escHtml(h.elapsed || '?') + '</span></div>'
        + '</div>';
    }).join('');
  }
  // Replay click
  list.querySelectorAll('.sidebar-item').forEach(function(el) {
    el.addEventListener('click', function() {
      var items = loadHistory();
      var h = items[parseInt(el.dataset.idx)];
      if (h) {
        taskInput.value = h.task;
        outputBody.innerHTML = '<span class="placeholder">点击发送重新执行...</span>';
        routeBadge.innerHTML = '';
        outputFooter.style.display = 'none';
        sendBtn.click();
      }
    });
  });
}
$('#hist-clear').addEventListener('click', function() {
  localStorage.removeItem(HIST_KEY);
  renderHistory();
  toast('历史已清除', 'info');
});

// Mobile sidebar toggle
$('#hist-toggle').addEventListener('click', function() {
  sidebar.classList.toggle('mobile-open');
});
document.addEventListener('click', function(e) {
  if (sidebar.classList.contains('mobile-open') && !sidebar.contains(e.target) && e.target !== $('#hist-toggle')) {
    sidebar.classList.remove('mobile-open');
  }
});

// ===================================================================
// New Chat
// ===================================================================
function newChat() {
  outputBody.innerHTML = '<span class="placeholder">输入任务后按 Enter 发送</span>';
  routeBadge.innerHTML = '';
  outputFooter.style.display = 'none';
  statTime.textContent = '';
  statCost.textContent = '';
  statusDot.classList.add('idle');
  outputLabel.textContent = '就绪';
  taskInput.value = '';
  taskInput.style.height = 'auto';
  taskInput.focus();
}
$('#btn-new-chat').addEventListener('click', newChat);

// ===================================================================
// Copy
// ===================================================================
$('#btn-copy').addEventListener('click', function() {
  var text = outputBody.textContent || '';
  if (!text.trim()) return;
  var btn = $('#btn-copy');
  navigator.clipboard.writeText(text).then(function() {
    btn.textContent = '已复制'; btn.classList.add('copied');
    setTimeout(function() { btn.textContent = '复制结果'; btn.classList.remove('copied'); }, 2000);
  }).catch(function() {
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
    toast('已复制', 'success');
  });
});

// ===================================================================
// Mode Switching
// ===================================================================
function switchMode(mode) {
  if (mode === 'dev') {
    userMode.classList.add('hidden');
    devMode.classList.add('visible');
    $$('.mode-opt')[0].classList.remove('active');
    $$('.mode-opt')[1].classList.add('active');
    if (!devMode.dataset.loaded) { devMode.dataset.loaded = '1'; loadAgents(); loadCostData(); loadCostRecent(); loadSettings(); }
  } else {
    userMode.classList.remove('hidden');
    devMode.classList.remove('visible');
    $$('.mode-opt')[0].classList.add('active');
    $$('.mode-opt')[1].classList.remove('active');
    taskInput.focus();
  }
}
$$('.mode-opt')[0].addEventListener('click', function() { switchMode('user'); });
$$('.mode-opt')[1].addEventListener('click', function() { switchMode('dev'); });

// Dev tabs
$$('.dev-tab').forEach(function(btn) {
  btn.addEventListener('click', function() {
    var tab = btn.dataset.tab;
    $$('.dev-tab').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    $$('.dev-panel').forEach(function(p) { p.classList.remove('active'); });
    $('#panel-' + tab).classList.add('active');
    if (tab === 'cost') loadCostRecent();
    if (tab === 'logs') loadLogs();
  });
});

// ===================================================================
// Input Events
// ===================================================================
taskInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (isStreaming) { stop(); } else { sendTask(); }
  }
  if (e.key === 'Escape' && isStreaming) {
    e.preventDefault();
    stop();
  }
});

taskInput.addEventListener('input', function() {
  taskInput.style.height = 'auto';
  taskInput.style.height = Math.min(taskInput.scrollHeight, 140) + 'px';
});

sendBtn.addEventListener('click', function() {
  if (isStreaming) { stop(); } else { sendTask(); }
});

// ===================================================================
// Quick Tags
// ===================================================================
$$('.tag-chip').forEach(function(chip) {
  chip.addEventListener('click', function() {
    if (isStreaming) { toast('请先停止当前任务', 'info'); return; }
    taskInput.value = chip.dataset.prompt;
    taskInput.style.height = 'auto';
    taskInput.style.height = Math.min(taskInput.scrollHeight, 140) + 'px';
    sendTask();
  });
});

// ===================================================================
// sendTask() -- 核心发送逻辑（完整 try-catch-finally）
// ===================================================================
async function sendTask() {
  if (isStreaming) return;
  var task = taskInput.value.trim();
  if (!task) return;

  // 清理残留
  if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }

  isStreaming = true;
  abortCtrl = new AbortController();
  setSendingUI();
  outputBody.innerHTML = '<span class="placeholder"><span class="spinner"></span>路由中...</span>';
  routeBadge.innerHTML = '';

  var startTime = performance.now();
  var agent = '', model = '';
  var fullOutput = '';

  // elapsed timer
  streamTimer = setInterval(function() {
    var el = ((performance.now() - startTime) / 1000).toFixed(1);
    statTime.textContent = el + 's';
    outputFooter.style.display = 'flex';
  }, 200);

  try {
    // 1) Route
    var routeResp = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: task }),
      signal: abortCtrl.signal
    });
    var routeData = await routeResp.json();
    if (routeData.error) {
      outputBody.innerHTML = '<span class="error-text">路由失败: ' + escHtml(routeData.error) + '</span>';
      return;
    }
    agent = routeData.agent;
    model = routeData.model;

    routeBadge.innerHTML =
      '<span class="badge badge-agent">Agent: ' + escHtml(agent) + '</span>'
      + '<span class="badge badge-model">' + escHtml(model) + '</span>';

    outputLabel.textContent = 'Agent: ' + agent;
    outputBody.textContent = '';

    // 2) Stream chat
    var chatResp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: task, agent: agent }),
      signal: abortCtrl.signal
    });

    if (!chatResp.ok) {
      var errText = await chatResp.text();
      outputBody.innerHTML = '<span class="error-text">API 错误 (' + chatResp.status + '): ' + escHtml(errText.substring(0, 300)) + '</span>';
      return;
    }

    var reader = chatResp.body.getReader();
    var decoder = new TextDecoder();
    var buffer = '';

    while (true) {
      var readResult = await reader.read();
      if (readResult.done) break;
      buffer += decoder.decode(readResult.value, { stream: true });
      var lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (line.indexOf('data: ') === 0) {
          var data = line.slice(6);
          if (data === '[DONE]') break;
          if (data === '[CANCELLED]') {
            fullOutput += '\n\n[已停止]';
            outputBody.textContent = fullOutput;
            outputBody.scrollTop = outputBody.scrollHeight;
            break;
          }
          try {
            var chunk = JSON.parse(data);
            var content = chunk.choices && chunk.choices[0] && chunk.choices[0].delta && chunk.choices[0].delta.content;
            if (content) {
              fullOutput += content;
              outputBody.textContent = fullOutput;
              outputBody.scrollTop = outputBody.scrollHeight;
            }
          } catch(_) {}
        }
      }
    }

    var elapsed = ((performance.now() - startTime) / 1000).toFixed(1);

    // 3) Cost stat
    var cost = '?';
    try {
      var statResp = await fetch('/api/stat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: task, agent: agent })
      });
      var stat = await statResp.json();
      if (!stat.error && stat.cost && stat.cost !== '?') { cost = stat.cost; }
    } catch(_) {}

    routeBadge.innerHTML =
      '<span class="badge badge-agent">Agent: ' + escHtml(agent) + '</span>'
      + '<span class="badge badge-model">' + escHtml(model) + '</span>'
      + '<span class="badge-time">' + elapsed + 's</span>'
      + '<span class="badge-cost">$' + cost + '</span>';

    statTime.textContent = elapsed + 's';
    statCost.textContent = '$' + cost;

    addHistory(task, agent, model, elapsed + 's', '$' + cost);
    outputFooter.style.display = 'flex';

  } catch(e) {
    if (e.name === 'AbortError') {
      fullOutput += '\n\n[已停止]';
      outputBody.textContent = (outputBody.textContent || '') + '\n\n[已停止]';
    } else {
      outputBody.innerHTML = '<span class="error-text">请求失败: ' + escHtml(e.message || String(e)) + '</span>';
    }
  } finally {
    resetUI();
    taskInput.value = '';
    taskInput.style.height = 'auto';
    outputFooter.style.display = (outputBody.textContent && outputBody.textContent.trim()) ? 'flex' : 'none';
  }
}

// ===================================================================
// sendTaskDirect -- 直接指定 agent（开发者测试用）
// ===================================================================
async function sendTaskDirect(task, agent) {
  if (isStreaming) return;
  if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }

  isStreaming = true;
  abortCtrl = new AbortController();
  setSendingUI();
  outputBody.innerHTML = '<span class="placeholder"><span class="spinner"></span>直接调用 ' + escHtml(agent) + '...</span>';
  routeBadge.innerHTML = '';

  var startTime = performance.now();
  var model = '';
  var fullOutput = '';

  streamTimer = setInterval(function() {
    statTime.textContent = ((performance.now() - startTime) / 1000).toFixed(1) + 's';
    outputFooter.style.display = 'flex';
  }, 200);

  try {
    var routeResp = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: task }),
      signal: abortCtrl.signal
    });
    var routeData = await routeResp.json();
    model = routeData.model || 'deepseek-chat';

    routeBadge.innerHTML =
      '<span class="badge badge-agent">Agent: ' + escHtml(agent) + ' (指定)</span>'
      + '<span class="badge badge-model">' + escHtml(model) + '</span>';

    outputLabel.textContent = 'Agent: ' + agent;
    outputBody.textContent = '';

    var chatResp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: task, agent: agent }),
      signal: abortCtrl.signal
    });
    if (!chatResp.ok) {
      var eT = await chatResp.text();
      outputBody.innerHTML = '<span class="error-text">API 错误: ' + escHtml(eT.substring(0, 300)) + '</span>';
      return;
    }

    var reader = chatResp.body.getReader();
    var decoder = new TextDecoder();
    var buffer = '';
    while (true) {
      var rr = await reader.read();
      if (rr.done) break;
      buffer += decoder.decode(rr.value, { stream: true });
      var lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (line.indexOf('data: ') === 0) {
          var data = line.slice(6);
          if (data === '[DONE]') break;
          if (data === '[CANCELLED]') { fullOutput += '\n\n[已停止]'; outputBody.textContent = fullOutput; break; }
          try {
            var c = JSON.parse(data);
            var ct = c.choices && c.choices[0] && c.choices[0].delta && c.choices[0].delta.content;
            if (ct) { fullOutput += ct; outputBody.textContent = fullOutput; outputBody.scrollTop = outputBody.scrollHeight; }
          } catch(_) {}
        }
      }
    }

    var elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
    routeBadge.innerHTML += '<span class="badge-time">' + elapsed + 's</span>';
    statTime.textContent = elapsed + 's';
    addHistory(task, agent, model, elapsed + 's', '?');
    outputFooter.style.display = 'flex';
  } catch(e) {
    if (e.name === 'AbortError') {
      outputBody.textContent = (outputBody.textContent || '') + '\n\n[已停止]';
    } else {
      outputBody.innerHTML = '<span class="error-text">请求失败: ' + escHtml(e.message || String(e)) + '</span>';
    }
  } finally {
    resetUI();
    outputFooter.style.display = (outputBody.textContent && outputBody.textContent.trim()) ? 'flex' : 'none';
  }
}

// ===================================================================
// Dev: Agents Tab
// ===================================================================
var agentsData = [];
async function loadAgents() {
  try {
    var resp = await fetch('/api/agents');
    agentsData = await resp.json();
    renderAgents(agentsData);
  } catch(e) {
    $('#agent-grid').innerHTML = '<span class="error-text">加载失败: ' + escHtml(e.message) + '</span>';
  }
}

function renderAgents(agents) {
  var grid = $('#agent-grid');
  if (!agents || agents.length === 0) {
    grid.innerHTML = '<span style="color:var(--muted);">无 Agent 数据</span>';
    return;
  }
  var ml = { 'haiku':'Haiku','sonnet':'Sonnet','opus':'Opus','deepseek-chat':'DS-Chat','deepseek-reasoner':'DS-R1' };

  grid.innerHTML = agents.map(function(a) {
    var kws = (a.keywords || []).slice(0,5).map(function(k) { return '<span class="ac-tag">' + escHtml(k) + '</span>'; }).join('');
    return '<div class="agent-card" data-name="' + escHtml(a.name) + '">'
      + '<div class="ac-name">' + escHtml(a.name) + '</div>'
      + '<div class="ac-desc">' + escHtml(a.description || '') + '</div>'
      + '<div class="ac-meta"><span class="ac-tag model-tag">' + escHtml(ml[a.model] || a.model || '?') + '</span>' + kws + '</div>'
      + '<div class="ac-detail">'
        + '<div style="font-size:11px;color:var(--muted);margin-bottom:6px;">System Prompt</div>'
        + '<div class="ac-prompt">' + escHtml(a.prompt_full || '') + '</div>'
        + '<div class="ac-test-row">'
          + '<input class="ac-test-input" placeholder="测试 ' + escHtml(a.name) + '...">'
          + '<button class="btn-sm green test-btn">测试</button>'
          + '<button class="btn-sm primary edit-btn">编辑</button>'
        + '</div>'
      + '</div>'
    + '</div>';
  }).join('');

  grid.querySelectorAll('.agent-card').forEach(function(card) {
    card.addEventListener('click', function(e) {
      if (e.target.closest('.ac-test-row')) return;
      var was = card.classList.contains('expanded');
      grid.querySelectorAll('.agent-card').forEach(function(c) { c.classList.remove('expanded'); });
      if (!was) card.classList.add('expanded');
    });
    var ti = card.querySelector('.ac-test-input');
    card.querySelector('.test-btn').addEventListener('click', function(e) {
      e.stopPropagation();
      var t = ti.value.trim();
      if (!t) { toast('请先输入测试任务', 'error'); return; }
      switchMode('user');
      taskInput.value = t;
      sendTaskDirect(t, card.dataset.name);
    });
    card.querySelector('.edit-btn').addEventListener('click', function(e) {
      e.stopPropagation();
      openEditModal(card.dataset.name);
    });
  });
}

// ===================================================================
// Edit Modal
// ===================================================================
async function openEditModal(name) {
  editingAgent = name;
  modalTitle.textContent = '编辑 Agent: ' + name;
  modalEditor.value = '加载中...';
  modalEditor.disabled = true;
  modalOverlay.classList.remove('hidden');
  try {
    var resp = await fetch('/api/agent-content?name=' + encodeURIComponent(name));
    var data = await resp.json();
    modalEditor.value = data.error ? '加载失败: ' + data.error : (data.content || '');
  } catch(ee) {
    modalEditor.value = '加载失败: ' + ee.message;
  }
  modalEditor.disabled = false;
  modalEditor.focus();
}
function closeEditModal() {
  modalOverlay.classList.add('hidden');
  editingAgent = '';
  modalEditor.value = '';
}
$('#modal-close').addEventListener('click', closeEditModal);
$('#modal-cancel').addEventListener('click', closeEditModal);
modalOverlay.addEventListener('click', function(e) { if (e.target === modalOverlay) closeEditModal(); });
$('#modal-save').addEventListener('click', async function() {
  if (!editingAgent) return;
  try {
    var resp = await fetch('/api/agent-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: editingAgent, content: modalEditor.value })
    });
    var data = await resp.json();
    if (data.ok) { toast('已保存', 'success'); closeEditModal(); loadAgents(); }
    else { toast('保存失败: ' + (data.error || '?'), 'error'); }
  } catch(ee) { toast('保存失败: ' + ee.message, 'error'); }
});
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && !modalOverlay.classList.contains('hidden')) closeEditModal();
});

// ===================================================================
// Dev: Routes Tab
// ===================================================================
$('#route-search-btn').addEventListener('click', runRouteTest);
$('#route-search-input').addEventListener('keydown', function(e) { if (e.key === 'Enter') runRouteTest(); });
async function runRouteTest() {
  var task = $('#route-search-input').value.trim();
  if (!task) { toast('请输入测试文本', 'error'); return; }
  var tbody = $('#route-tbody');
  tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:20px;"><span class="spinner"></span>分析中...</td></tr>';
  try {
    var resp = await fetch('/api/route-test', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task: task })
    });
    var results = await resp.json();
    if (!results.length) { tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--muted);padding:20px;">无匹配</td></tr>'; return; }
    tbody.innerHTML = results.map(function(r, i) {
      var best = i === 0 && r.score > 0;
      var kws = (r.keywords||[]).map(function(kw) {
        var hit = task.toLowerCase().indexOf(kw.toLowerCase()) !== -1;
        return '<span class="kw' + (hit?' hit':'') + '">' + escHtml(kw) + '</span>';
      }).join('');
      return '<tr class="' + (best?'best':'') + '">'
        + '<td>' + escHtml(r.agent) + (best?' <span style="color:var(--green);font-size:10px;">&#10003; 最佳</span>':'') + '</td>'
        + '<td><span class="score-badge">' + r.score + '</span></td>'
        + '<td><div class="kw-tags">' + kws + '</div></td></tr>';
    }).join('');
  } catch(ee) { tbody.innerHTML = '<tr><td colspan="3" class="error-text">错误: ' + escHtml(ee.message) + '</td></tr>'; }
}

// ===================================================================
// Dev: Cost Tab
// ===================================================================
async function loadCostData() {
  try {
    var resp = await fetch('/api/cost'); var data = await resp.json();
    if (data.error) { $('#cost-summary').innerHTML = '<span class="error-text">' + escHtml(data.error) + '</span>'; return; }
    $('#cost-summary').innerHTML =
      '<div class="cost-card"><div class="cc-label">总调用</div><div class="cc-value">' + (data.total_calls||0) + '</div></div>'
      + '<div class="cost-card"><div class="cc-label">总费用</div><div class="cc-value highlight">$' + ((data.total_cost||0)).toFixed(4) + '</div></div>';
    var tbody = $('#cost-model-tbody');
    var bm = data.by_model || [];
    tbody.innerHTML = bm.length ? bm.map(function(m) {
      return '<tr><td>' + escHtml(m.model) + '</td><td>' + m.calls + '</td><td>$' + (m.cost||0).toFixed(4) + '</td></tr>';
    }).join('') : '<tr><td colspan="3" style="text-align:center;color:var(--muted);padding:20px;">暂无数据</td></tr>';
  } catch(ee) { $('#cost-summary').innerHTML = '<span class="error-text">加载失败: ' + escHtml(ee.message) + '</span>'; }
}
async function loadCostRecent() {
  try {
    var tbody = $('#cost-recent-tbody');
    var resp = await fetch('/api/cost-recent'); var rows = await resp.json();
    if (!rows || !rows.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:24px;">暂无记录</td></tr>'; return; }
    tbody.innerHTML = rows.map(function(r) {
      return '<tr><td class="time-col">' + escHtml(r.time||'') + '</td><td>' + escHtml(r.channel||'') + '</td><td>' + escHtml(r.model||'') + '</td>'
        + '<td>' + (r.in_tokens||0) + '</td><td>' + (r.out_tokens||0) + '</td><td class="cost-col">$' + ((r.cost_usd||0)).toFixed(6) + '</td><td>' + (r.duration_s||0) + 's</td></tr>';
    }).join('');
  } catch(ee) { $('#cost-recent-tbody').innerHTML = '<tr><td colspan="7" class="error-text">加载失败: ' + escHtml(ee.message) + '</td></tr>'; }
}
async function loadLogs() {
  try {
    var tbody = $('#logs-tbody');
    var resp = await fetch('/api/cost-recent'); var rows = await resp.json();
    if (!rows || !rows.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:24px;">暂无日志</td></tr>'; return; }
    tbody.innerHTML = rows.map(function(r) {
      return '<tr><td class="time-col">' + escHtml(r.time||'') + '</td><td>' + escHtml(r.channel||'') + '</td><td>' + escHtml(r.model||'') + '</td>'
        + '<td>' + (r.in_tokens||0) + '</td><td>' + (r.out_tokens||0) + '</td><td class="cost-col">$' + ((r.cost_usd||0)).toFixed(6) + '</td><td>' + (r.duration_s||0) + 's</td></tr>';
    }).join('');
  } catch(ee) { $('#logs-tbody').innerHTML = '<tr><td colspan="7" class="error-text">加载失败: ' + escHtml(ee.message) + '</td></tr>'; }
}

// ===================================================================
// Dev: Settings
// ===================================================================
async function loadSettings() {
  try {
    var resp = await fetch('/api/settings'); var data = await resp.json();
    var badge = $('#key-status');
    if (data.deepseek_key_configured) { badge.textContent = '已配置'; badge.className = 'status-dot ok'; }
    else { badge.textContent = '未配置'; badge.className = 'status-dot bad'; }
  } catch(_) { $('#key-status').textContent = '检查失败'; $('#key-status').className = 'status-dot bad'; }
  var s = loadAppSettings();
  var sel = $('#default-model');
  sel.value = s.defaultModel || 'deepseek-chat';
  sel.addEventListener('change', function() { saveAppSettings({ defaultModel: sel.value }); toast('默认模型已更新', 'info'); });
}
function loadAppSettings() { try { return JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}'); } catch(_) { return {}; } }
function saveAppSettings(s) { var c = loadAppSettings(); localStorage.setItem(SETTINGS_KEY, JSON.stringify(Object.assign(c, s))); }

// ===================================================================
// Version
// ===================================================================
async function loadVersion() {
  try {
    var resp = await fetch('/api/version'); var data = await resp.json();
    var v = 'v' + (data.version || '0.1.0');
    if (verTag) verTag.textContent = v;
    if (settingsVer) settingsVer.textContent = v;
  } catch(_) {}
}

// ===================================================================
// Init
// ===================================================================
loadVersion(); renderHistory(); taskInput.focus();
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
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
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
                            break
                self.wfile.write("data: [DONE]\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
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
    import webbrowser
    import threading

    print(f"\n  Agency Web UI v{AGENCY_VERSION}  ->  http://localhost:{PORT}\n")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
