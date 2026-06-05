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

PORT = 8800


# --- 提供者解析 ---
def get_provider_config():
    """解析 API 配置，返回 (base_url, api_key, headers)"""
    base_url = ""
    api_key = ""

    # DeepSeek
    if os.environ.get("DEEPSEEK_API_KEY"):
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        api_key = os.environ["DEEPSEEK_API_KEY"]
    # OpenAI 兼容
    elif os.environ.get("OPENAI_API_KEY"):
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.environ["OPENAI_API_KEY"]
    # Ollama
    elif os.environ.get("OLLAMA_BASE_URL"):
        base_url = os.environ["OLLAMA_BASE_URL"]
        api_key = "ollama"
    else:
        return None, None, None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if api_key == "ollama":
        headers = {"Content-Type": "application/json"}

    return base_url.rstrip("/"), api_key, headers


MODEL_MAP = {
    "haiku": os.environ.get("LIGHT_MODEL", "deepseek-chat"),
    "sonnet": os.environ.get("STANDARD_MODEL", "deepseek-chat"),
    "opus": os.environ.get("HEAVY_MODEL", "deepseek-reasoner"),
}


def get_actual_model(agent_model_name):
    """将 agent frontmatter 中的模型名映射到实际模型"""
    return MODEL_MAP.get(agent_model_name, os.environ.get("DEFAULT_MODEL", "deepseek-chat"))


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
[data-theme="light"]{
  --bg-start:#f8f9fa;--bg-end:#e9ecef;
  --surface:#fff;--surface2:#f1f3f5;
  --card:rgba(0,0,0,.02);--card-hover:rgba(0,0,0,.04);
  --border:rgba(0,0,0,.08);--border-focus:rgba(108,92,231,.3);
  --text:#212529;--text2:#495057;--muted:#868e96;
  --shadow-card:0 2px 8px rgba(0,0,0,.06);
  --shadow-lg:0 8px 24px rgba(0,0,0,.1);
}
[data-theme="light"] body{
  background:linear-gradient(160deg,#f8f9fa 0%,#f1f3f5 35%,#e9ecef 70%,#f8f9fa 100%);
}
[data-theme="light"] .topbar{background:rgba(255,255,255,.85);}
[data-theme="light"] .sidebar{background:rgba(248,249,250,.7);}
[data-theme="light"] .agent-card .ac-prompt{background:rgba(0,0,0,.03);}
[data-theme="light"] #output-body{background:rgba(255,255,255,.5);}
[data-theme="light"] .modal-box{background:#fff;}
[data-theme="light"] .setting-row{background:rgba(0,0,0,.02);}
[data-theme="light"] .topbar-logo .name{color:#6C5CE7;}
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

/* Theme Toggle Button */
#theme-btn{
  background:none;border:1px solid var(--border);border-radius:50%;
  width:32px;height:32px;display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:16px;color:var(--muted);transition:var(--transition);
}
#theme-btn:hover{color:var(--text);border-color:rgba(255,255,255,.2);}

/* Shortcuts Help Button */
#shortcuts-btn{
  position:fixed;bottom:20px;right:20px;z-index:300;
  width:34px;height:34px;border-radius:50%;background:rgba(108,92,231,.15);
  border:1px solid rgba(108,92,231,.25);color:#a78bfa;font-size:15px;
  cursor:pointer;display:flex;align-items:center;justify-content:center;
  transition:var(--transition);font-weight:700;
}
#shortcuts-btn:hover{background:rgba(108,92,231,.25);color:#c4b5fd;transform:scale(1.08);}

/* Shortcuts Modal */
.shortcuts-modal{max-width:420px;}
.shortcuts-modal .modal-body{font-size:13px;line-height:2;}
.shortcuts-modal kbd{
  display:inline-block;padding:2px 8px;background:rgba(108,92,231,.12);
  border:1px solid rgba(108,92,231,.25);border-radius:4px;
  font:11px var(--mono);color:#c4b5fd;margin:0 2px;
}
.shortcuts-modal .shortcut-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:6px 0;border-bottom:1px solid var(--border);
}
.shortcuts-modal .shortcut-desc{color:var(--text2);}

/* Pipeline Tab */
.pipeline-list{display:flex;flex-direction:column;gap:12px;}
.pipeline-card{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:18px;transition:var(--transition);
}
.pipeline-card:hover{border-color:rgba(108,92,231,.2);}
.pipeline-card .pl-name{font-size:15px;font-weight:600;color:#c4b5fd;margin-bottom:6px;}
.pipeline-card .pl-chain{
  font-size:12px;color:var(--muted);margin-bottom:4px;
}
.pipeline-card .pl-chain span{color:var(--primary);font-weight:500;}
.pipeline-card .pl-desc{font-size:12px;color:var(--text2);margin-bottom:12px;}
.pipeline-card .pl-actions{display:flex;gap:8px;align-items:center;}
.pipeline-progress{
  margin-top:12px;padding:12px;background:rgba(0,0,0,.15);
  border-radius:var(--radius);font:12px/1.8 var(--mono);
}
.pipeline-progress .pp-step{padding:2px 0;}
.pipeline-progress .pp-done{color:var(--green);}
.pipeline-progress .pp-running{color:var(--orange);}
.pipeline-progress .pp-wait{color:var(--muted);}

/* MD Rendering */
.md-code{
  background:#0d1117;border:1px solid rgba(255,255,255,.1);
  border-radius:8px;margin:8px 0;overflow:hidden;
}
.md-code-lang{
  display:block;padding:4px 14px;font-size:11px;color:var(--muted);
  background:rgba(255,255,255,.03);border-bottom:1px solid rgba(255,255,255,.06);
}
.md-code pre{
  padding:12px 14px;margin:0;font:12px/1.6 var(--mono);
  color:#7ee787;overflow-x:auto;white-space:pre-wrap;
}
.md-inline{
  background:rgba(108,92,231,.12);color:#c4b5fd;padding:1px 5px;
  border-radius:3px;font:12px var(--mono);
}
.md-h3{font-size:15px;font-weight:600;color:var(--text);margin:12px 0 6px;}
.md-h4{font-size:13px;font-weight:600;color:var(--text2);margin:10px 0 4px;}
.md-li{color:var(--text2);margin-left:16px;line-height:1.8;}
[data-theme="light"] .md-code{background:#1e1e2e;}
[data-theme="light"] .md-inline{background:rgba(108,92,231,.08);}

/* History item delete + rename */
.sidebar-item{position:relative;}
.sidebar-item .si-delete{
  position:absolute;right:6px;top:50%;transform:translateY(-50%);
  display:none;width:20px;height:20px;border-radius:50%;
  background:rgba(255,107,107,.15);border:1px solid rgba(255,107,107,.2);
  color:var(--red);font-size:12px;cursor:pointer;line-height:18px;text-align:center;
  transition:var(--transition);
}
.sidebar-item:hover .si-delete{display:block;}
.sidebar-item .si-delete:hover{background:rgba(255,107,107,.3);}
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
    <button id="theme-btn" title="切换主题">☀</button>
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
        <textarea id="task-input" placeholder="输入任务，或 @agent名 指定 Agent..." rows="1"></textarea>
        <button id="send-btn" title="发送 (Enter) / 停止 (Esc)">&#10132;</button>
      </div>
      <!-- @agent Hint -->
      <div class="route-badge" id="at-hint" style="margin-bottom:10px;">
        <span style="font-size:11px;color:var(--muted);">@coder 写代码 | @reviewer 审查 | @planner 做规划 | @explorer 搜索 | @orchestrator 拆解任务</span>
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
            <button class="footer-btn" id="btn-copy-md">复制 MD</button>
            <button class="footer-btn" id="btn-download-md">下载 .md</button>
            <button class="footer-btn" id="btn-copy-text">复制文本</button>
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
      <button class="dev-tab" data-tab="pipeline">流水线</button>
    </nav>

    <!-- Agents -->
    <div class="dev-panel active" id="panel-agents">
      <div style="margin-bottom:14px;">
        <button class="btn-sm primary" id="btn-create-agent" style="font-size:13px;padding:8px 18px;">&#10024; 用 AI 创建 Agent</button>
      </div>
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
        <h3>API 提供者</h3>
        <div class="setting-row">
          <div><div class="sr-label">提供者</div><div class="sr-desc">选择 API 服务（需在 .env 中配置对应 Key）</div></div>
          <select class="model-select" id="settings-provider">
            <option value="deepseek">DeepSeek</option>
            <option value="openai">OpenAI 兼容</option>
            <option value="ollama">Ollama 本地</option>
            <option value="custom">自定义</option>
          </select>
        </div>
        <div class="setting-row">
          <div><div class="sr-label">API Key</div><div class="sr-desc">运行时使用（.env 优先）</div></div>
          <input type="password" id="settings-apikey" style="padding:6px 12px;background:rgba(0,0,0,.3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;outline:none;width:240px;" placeholder="sk-...">
        </div>
        <div class="setting-row">
          <div><div class="sr-label">Base URL</div><div class="sr-desc">API 端点地址</div></div>
          <input type="text" id="settings-baseurl" style="padding:6px 12px;background:rgba(0,0,0,.3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;outline:none;width:280px;" placeholder="https://api.deepseek.com">
        </div>
        <div class="setting-row">
          <div><div class="sr-label">状态</div><div class="sr-desc">当前 API 配置检测</div></div>
          <span class="status-dot" id="key-status">检查中...</span>
        </div>
      </div>
      <div class="settings-group">
        <h3>模型映射</h3>
        <div class="setting-row">
          <div><div class="sr-label">Light（轻量级）</div><div class="sr-desc">Haiku 级 Agent（explorer 等）</div></div>
          <input type="text" id="settings-light-model" style="padding:6px 12px;background:rgba(0,0,0,.3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;outline:none;width:200px;" placeholder="deepseek-chat">
        </div>
        <div class="setting-row">
          <div><div class="sr-label">Standard（标准）</div><div class="sr-desc">Sonnet 级 Agent（coder 等）</div></div>
          <input type="text" id="settings-standard-model" style="padding:6px 12px;background:rgba(0,0,0,.3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;outline:none;width:200px;" placeholder="deepseek-chat">
        </div>
        <div class="setting-row">
          <div><div class="sr-label">Heavy（重量级）</div><div class="sr-desc">Opus 级 Agent（planner 等）</div></div>
          <input type="text" id="settings-heavy-model" style="padding:6px 12px;background:rgba(0,0,0,.3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;outline:none;width:200px;" placeholder="deepseek-reasoner">
        </div>
      </div>
      <div class="settings-group">
        <h3>生成参数</h3>
        <div class="setting-row">
          <div><div class="sr-label">Temperature</div><div class="sr-desc" id="temp-val-label">0.7</div></div>
          <input type="range" id="settings-temperature" min="0" max="2" step="0.1" value="0.7" style="width:180px;accent-color:var(--primary);">
        </div>
        <div class="setting-row">
          <div><div class="sr-label">Max Tokens</div><div class="sr-desc">单次输出上限</div></div>
          <input type="number" id="settings-max-tokens" value="8192" min="256" max="65536" step="256" style="padding:6px 12px;background:rgba(0,0,0,.3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:12px;outline:none;width:120px;">
        </div>
        <div class="setting-row">
          <div><div class="sr-label">默认模型</div><div class="sr-desc">未指定时的默认选择</div></div>
          <select class="model-select" id="default-model">
            <option value="deepseek-chat">deepseek-chat</option>
            <option value="deepseek-reasoner">deepseek-reasoner</option>
          </select>
        </div>
      </div>
      <div class="settings-group">
        <button class="btn-sm primary" id="btn-save-settings" style="margin-right:8px;">保存设置</button>
        <button class="btn-sm" id="btn-reload-config" style="background:transparent;color:var(--text);border:1px solid var(--border);">重新加载 .env</button>
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
          提供者和模型映射需在 .env 中配置后重启生效；其他设置保存在浏览器本地
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

    <!-- Pipeline -->
    <div class="dev-panel" id="panel-pipeline">
      <div class="pipeline-list" id="pipeline-list"></div>
      <div class="pipeline-progress" id="pipeline-progress" style="display:none;"></div>
    </div>
  </div>
</div>

<!-- ====================== SHORTCUTS BUTTON ====================== -->
<button id="shortcuts-btn" title="快捷键 (? 键)">?</button>

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

<!-- ====================== AGENT FACTORY MODAL ====================== -->
<div class="modal-overlay hidden" id="factory-overlay">
  <div class="modal-box">
    <div class="modal-header">
      <h3 id="factory-title">&#10024; 用 AI 创建 Agent</h3>
      <button class="modal-close" id="factory-close">&times;</button>
    </div>
    <div class="modal-body" id="factory-body">
      <!-- Step 1: Describe -->
      <div id="factory-step-1">
        <div style="margin-bottom:12px;color:var(--text2);font-size:13px;line-height:1.7;">
          描述你想要的 Agent，AI 会自动生成完整的 Agent 定义文件。<br>
          例如：<span style="color:var(--muted);">"我需要一个能分析日志文件并找出异常的 Agent"</span>
        </div>
        <textarea id="factory-requirement"
          style="width:100%;min-height:100px;resize:vertical;background:rgba(0,0,0,.35);border:1px solid var(--border);border-radius:8px;color:var(--text);font:13px/1.6 var(--font);padding:12px;outline:none;"
          placeholder="描述你需要的 Agent..."></textarea>
        <div style="margin-top:12px;text-align:right;">
          <button class="btn-sm primary" id="factory-generate-btn">&#10024; 生成</button>
        </div>
      </div>
      <!-- Step 2: Generating & Review -->
      <div id="factory-step-2" style="display:none;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
          <span class="spinner" id="factory-spinner"></span>
          <span style="color:var(--muted);font-size:12px;" id="factory-status">正在生成...</span>
        </div>
        <textarea id="factory-generated"
          style="width:100%;min-height:320px;resize:vertical;background:rgba(0,0,0,.35);border:1px solid var(--border);border-radius:8px;color:var(--text);font:13px/1.6 var(--mono);padding:14px;outline:none;"
          placeholder="等待生成..."></textarea>
        <div style="margin-top:12px;display:flex;gap:8px;justify-content:flex-end;">
          <button class="btn-sm" style="background:transparent;color:var(--text);border:1px solid var(--border);" id="factory-regenerate-btn">&#8635; 重新生成</button>
          <button class="btn-sm green" id="factory-save-btn" disabled>&#128190; 保存 Agent</button>
        </div>
      </div>
      <!-- Step 3: Done -->
      <div id="factory-step-3" style="display:none;text-align:center;padding:40px 20px;">
        <div style="font-size:48px;margin-bottom:16px;">&#10024;</div>
        <div style="font-size:15px;color:var(--green);font-weight:600;margin-bottom:8px;">Agent 创建成功！</div>
        <div style="color:var(--muted);font-size:13px;margin-bottom:20px;" id="factory-done-msg"></div>
        <button class="btn-sm primary" id="factory-done-btn">关闭并刷新</button>
      </div>
    </div>
  </div>
</div>

<!-- ====================== SHORTCUTS MODAL ====================== -->
<div class="modal-overlay hidden" id="shortcuts-overlay">
  <div class="modal-box shortcuts-modal">
    <div class="modal-header">
      <h3>键盘快捷键</h3>
      <button class="modal-close" id="shortcuts-close">&times;</button>
    </div>
    <div class="modal-body">
      <div class="shortcut-row"><span class="shortcut-desc">发送任务</span><kbd>Ctrl+Enter</kbd></div>
      <div class="shortcut-row"><span class="shortcut-desc">停止生成</span><kbd>Esc</kbd></div>
      <div class="shortcut-row"><span class="shortcut-desc">指定 Agent</span><kbd>@agent名</kbd></div>
      <div class="shortcut-row"><span class="shortcut-desc">换行</span><kbd>Shift+Enter</kbd></div>
      <div class="shortcut-row"><span class="shortcut-desc">显示此面板</span><kbd>?</kbd></div>
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

// Theme + Shortcuts
var themeBtn = $('#theme-btn');
var shortcutsOverlay = $('#shortcuts-overlay');
var outputRawText = '';

// ===================================================================
// Constants
// ===================================================================
var HIST_KEY = 'agency_history_v2';
var MAX_HIST = 15;
var SETTINGS_KEY = 'agency_settings_v2';
var CONV_KEY = 'agency_conversations';
var MAX_CONV_ROUNDS = 20;

// ===================================================================
// Core State
// ===================================================================
var isStreaming = false;
var abortCtrl = null;
var streamTimer = null;  // elapsed timer
var conversationMessages = [];  // 多轮会话 messages 数组
var currentAgent = '';   // 当前对话的 Agent 名
var currentModel = '';   // 当前对话的模型名
var currentSystemPrompt = '';  // 当前 system prompt

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
// Markdown Rendering
// ===================================================================
function renderMD(text) {
  if (!text) return text;
  // Code blocks
  text = text.replace(/```(\w*)\n([\s\S]*?)```/g,
    '<div class="md-code"><span class="md-code-lang">$1</span><pre>$2</pre></div>');
  // Inline code
  text = text.replace(/`([^`]+)`/g, '<code class="md-inline">$1</code>');
  // Bold
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Headings (must do before lists)
  text = text.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>');
  text = text.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>');
  // List items
  text = text.replace(/^- (.+)$/gm, '<li class="md-li">$1</li>');
  return text;
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
function saveConversation(convId) {
  try {
    var convs = JSON.parse(localStorage.getItem(CONV_KEY) || '{}');
    convs[convId] = {
      messages: conversationMessages,
      agent: currentAgent,
      model: currentModel,
      updated: Date.now()
    };
    // 只保留最近 20 个对话
    var keys = Object.keys(convs).sort(function(a,b) { return convs[b].updated - convs[a].updated; });
    if (keys.length > 20) {
      var trimmed = {};
      keys.slice(0, 20).forEach(function(k) { trimmed[k] = convs[k]; });
      convs = trimmed;
    }
    localStorage.setItem(CONV_KEY, JSON.stringify(convs));
  } catch(_) {}
}
function restoreConversation(convId) {
  try {
    var convs = JSON.parse(localStorage.getItem(CONV_KEY) || '{}');
    var conv = convs[convId];
    if (conv && conv.messages) {
      conversationMessages = conv.messages;
      currentAgent = conv.agent || '';
      currentModel = conv.model || '';
      if (conv.messages.length > 0 && conv.messages[0].role === 'system') {
        currentSystemPrompt = conv.messages[0].content;
      }
    }
  } catch(_) {}
}
function addHistory(task, agent, model, elapsed, cost) {
  var items = loadHistory();
  var convId = Date.now();
  items.unshift({ id: convId, task: task, agent: agent, model: model, elapsed: elapsed, cost: cost, date: new Date().toLocaleString('zh-CN') });
  saveHistory(items);
  saveConversation(convId);
  renderHistory();
}
function renderHistory() {
  var items = loadHistory();
  var list = $('#hist-list');
  if (items.length === 0) {
    list.innerHTML = '<div class="sidebar-empty">暂无记录</div>';
  } else {
    list.innerHTML = items.map(function(h, i) {
      return '<div class="sidebar-item" data-idx="' + i + '" data-conv-id="' + h.id + '" title="' + escHtml(h.task) + '">'
        + '<button class="si-delete" data-idx="' + i + '" title="删除">&times;</button>'
        + '<div class="si-task">' + escHtml(h.task.substring(0, 45)) + '</div>'
        + '<div class="si-meta"><span style="color:#a78bfa">' + escHtml(h.agent) + '</span><span>' + escHtml(h.elapsed || '?') + '</span></div>'
        + '</div>';
    }).join('');
  }
  // Delete button handler
  list.querySelectorAll('.si-delete').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      var idx = parseInt(btn.dataset.idx);
      var items = loadHistory();
      items.splice(idx, 1);
      saveHistory(items);
      renderHistory();
    });
  });
  // Replay click -- restore conversation context
  list.querySelectorAll('.sidebar-item').forEach(function(el) {
    el.addEventListener('click', function(e) {
      if (e.target.classList.contains('si-delete')) return;
      var items = loadHistory();
      var h = items[parseInt(el.dataset.idx)];
      if (h) {
        restoreConversation(h.id);
        taskInput.value = h.task;
        outputBody.innerHTML = '<span class="placeholder">对话已恢复（' + conversationMessages.length + ' 条消息），点击发送继续...</span>';
        routeBadge.innerHTML =
          '<span class="badge badge-agent">Agent: ' + escHtml(h.agent) + '</span>'
          + '<span class="badge badge-model">' + escHtml(h.model) + '</span>';
        outputFooter.style.display = 'flex';
        statTime.textContent = h.elapsed || '';
        statCost.textContent = h.cost || '';
        statusDot.classList.add('idle');
        outputLabel.textContent = 'Agent: ' + h.agent;
        taskInput.focus();
      }
    });
    // Double-click to rename
    el.addEventListener('dblclick', function(e) {
      e.stopPropagation();
      var items = loadHistory();
      var h = items[parseInt(el.dataset.idx)];
      if (h) {
        var newName = prompt('新名称:', h.task.substring(0, 45));
        if (newName && newName.trim()) {
          h.task = newName.trim();
          h.title = newName.trim();
          saveHistory(items);
          renderHistory();
        }
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
  conversationMessages = [];
  currentAgent = '';
  currentModel = '';
  currentSystemPrompt = '';
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
// Export: Copy Markdown
// ===================================================================
$('#btn-copy-md').addEventListener('click', function() {
  var text = outputBody.textContent || '';
  if (!text.trim()) return;
  var md = '# Agency 对话\n\n**Agent**: ' + escHtml(currentAgent || '?') + ' | **模型**: ' + escHtml(currentModel || '?') + '\n\n---\n\n' + text;
  var btn = $('#btn-copy-md');
  navigator.clipboard.writeText(md).then(function() {
    btn.textContent = '已复制'; btn.classList.add('copied');
    setTimeout(function() { btn.textContent = '复制 MD'; btn.classList.remove('copied'); }, 2000);
  }).catch(function() {
    var ta = document.createElement('textarea');
    ta.value = md; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
    toast('已复制', 'success');
  });
});

// ===================================================================
// Export: Download .md
// ===================================================================
$('#btn-download-md').addEventListener('click', function() {
  var text = outputBody.textContent || '';
  if (!text.trim()) return;
  var md = '# Agency 对话\n\n**Agent**: ' + escHtml(currentAgent || '?') + ' | **模型**: ' + escHtml(currentModel || '?') + '\n\n---\n\n' + text;
  var blob = new Blob([md], { type: 'text/markdown' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url; a.download = 'agency-' + Date.now() + '.md';
  a.click();
  URL.revokeObjectURL(url);
  toast('已下载', 'success');
});

// ===================================================================
// Export: Copy Plain Text
// ===================================================================
$('#btn-copy-text').addEventListener('click', function() {
  var text = outputBody.textContent || '';
  if (!text.trim()) return;
  var btn = $('#btn-copy-text');
  navigator.clipboard.writeText(text).then(function() {
    btn.textContent = '已复制'; btn.classList.add('copied');
    setTimeout(function() { btn.textContent = '复制文本'; btn.classList.remove('copied'); }, 2000);
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
    if (tab === 'pipeline') renderPipelines();
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
// sendTask() -- 多轮会话核心发送逻辑
// ===================================================================
async function sendTask() {
  if (isStreaming) return;
  var rawTask = taskInput.value.trim();
  if (!rawTask) return;

  // 清理残留
  if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }

  // @agent 解析
  var forceAgent = '';
  var task = rawTask;
  var atMatch = rawTask.match(/^@(\S+)\s+/);
  if (atMatch) {
    var requestedAgent = atMatch[1].toLowerCase();
    task = rawTask.slice(atMatch[0].length);
    if (!task) { toast('请在 @agent名 后输入任务描述', 'error'); return; }
    // 模糊匹配 agent 名（用已知别名简化前端匹配）
    var agentAliases = {
      'coder': 'coder', '写代码': 'coder', 'code': 'coder',
      'reviewer': 'code-reviewer', '审查': 'code-reviewer', 'review': 'code-reviewer',
      'explorer': 'explorer', '搜索': 'explorer', '查找': 'explorer', 'search': 'explorer',
      'test': 'test-runner', '测试': 'test-runner', 'test-runner': 'test-runner',
      'planner': 'planner', '规划': 'planner', '设计': 'planner', 'plan': 'planner',
      'security': 'security-reviewer', '安全': 'security-reviewer',
      'writer': 'webnovel-writer', '写小说': 'webnovel-writer', 'novel': 'webnovel-writer',
      'orchestrator': 'orchestrator', '调度': 'orchestrator', '拆解': 'orchestrator',
      'general': 'general-worker', '杂务': 'general-worker', '通用': 'general-worker',
      'tdd': 'tdd-guide', 'tdd-guide': 'tdd-guide',
      'build': 'build-error-resolver', '编译': 'build-error-resolver',
      'doc': 'doc-updater', '文档': 'doc-updater',
      'refactor': 'refactor-cleaner', '清理': 'refactor-cleaner',
      'e2e': 'e2e-runner', 'e2e-runner': 'e2e-runner',
      'cost': 'cost-analyst', '费用': 'cost-analyst',
      'db': 'database-reviewer', '数据库': 'database-reviewer',
      'perf': 'performance-optimizer', '性能': 'performance-optimizer',
    };
    // 先用别名映射，再用服务器端精确/模糊匹配
    if (agentAliases[requestedAgent]) {
      forceAgent = agentAliases[requestedAgent];
    } else {
      forceAgent = requestedAgent;  // 让服务器端处理
    }
  }

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
    var routeBody = { task: task };
    if (forceAgent) { routeBody.force_agent = forceAgent; }
    var routeResp = await fetch('/api/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(routeBody),
      signal: abortCtrl.signal
    });
    var routeData = await routeResp.json();
    if (routeData.error) {
      outputBody.innerHTML = '<span class="error-text">路由失败: ' + escHtml(routeData.error) + '</span>';
      return;
    }
    agent = routeData.agent;
    model = routeData.model;
    currentAgent = agent;
    currentModel = model;

    var directLabel = routeData.direct ? ' (指定)' : '';
    routeBadge.innerHTML =
      '<span class="badge badge-agent">Agent: ' + escHtml(agent) + directLabel + '</span>'
      + '<span class="badge badge-model">' + escHtml(model) + '</span>';

    outputLabel.textContent = 'Agent: ' + agent;
    outputBody.textContent = '';

    // 2) 构建 messages（多轮会话）
    var actualModel = model;
    var appSettings = loadAppSettings();
    if (appSettings.defaultModel && appSettings.defaultModel !== 'deepseek-chat') {
      actualModel = appSettings.defaultModel;
    }

    if (conversationMessages.length === 0) {
      // 第一轮：加载 system prompt
      var agentResp = await fetch('/api/agent-content?name=' + encodeURIComponent(agent));
      var agentData = await agentResp.json();
      currentSystemPrompt = agentData.content || '';
      conversationMessages = [
        { role: 'system', content: currentSystemPrompt },
        { role: 'user', content: task }
      ];
    } else {
      // 后续轮：追加 user message
      conversationMessages.push({ role: 'user', content: task });
      // 截断：保留 system + 最近 MAX_CONV_ROUNDS 轮
      if (conversationMessages.length > 1 + MAX_CONV_ROUNDS * 2) {
        var sys = conversationMessages[0];
        var recent = conversationMessages.slice(-(MAX_CONV_ROUNDS * 2));
        conversationMessages = [sys].concat(recent);
      }
    }

    // 3) Stream chat（发送完整 messages 数组）
    var chatResp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: conversationMessages, model: actualModel }),
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
    var assistantContent = '';

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
            assistantContent += '\n\n[已停止]';
            fullOutput += '\n\n[已停止]';
            outputBody.textContent = fullOutput;
            outputBody.scrollTop = outputBody.scrollHeight;
            break;
          }
          try {
            var errJson = JSON.parse(data);
            if (errJson.error) {
              outputBody.innerHTML = '<span class="error-text">' + escHtml(errJson.error) + '</span>';
              return;
            }
          } catch(_) {}
          try {
            var chunk = JSON.parse(data);
            var content = chunk.choices && chunk.choices[0] && chunk.choices[0].delta && chunk.choices[0].delta.content;
            if (content) {
              assistantContent += content;
              fullOutput += content;
              outputBody.textContent = fullOutput;
              outputBody.scrollTop = outputBody.scrollHeight;
            }
          } catch(_) {}
        }
      }
    }

    // 4) 将 assistant 回复加入对话历史
    if (assistantContent) {
      conversationMessages.push({ role: 'assistant', content: assistantContent });
    }

    var elapsed = ((performance.now() - startTime) / 1000).toFixed(1);

    // 5) Cost stat
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
    // Render MD after streaming done
    if (outputBody.textContent && outputBody.textContent.trim()) {
      outputRawText = outputBody.textContent;
      outputBody.innerHTML = renderMD(outputRawText);
    }
  }
}

// ===================================================================
// sendTaskDirect -- 直接指定 agent（开发者测试用，支持多轮）
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
    currentAgent = agent;
    currentModel = model;

    routeBadge.innerHTML =
      '<span class="badge badge-agent">Agent: ' + escHtml(agent) + ' (指定)</span>'
      + '<span class="badge badge-model">' + escHtml(model) + '</span>';

    outputLabel.textContent = 'Agent: ' + agent;
    outputBody.textContent = '';

    // 构建 messages
    var agentResp = await fetch('/api/agent-content?name=' + encodeURIComponent(agent));
    var agentData = await agentResp.json();
    currentSystemPrompt = agentData.content || '';
    conversationMessages = [
      { role: 'system', content: currentSystemPrompt },
      { role: 'user', content: task }
    ];

    var chatResp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: conversationMessages, model: model }),
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
    var assistantContent = '';
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
          if (data === '[CANCELLED]') {
            assistantContent += '\n\n[已停止]';
            fullOutput += '\n\n[已停止]';
            outputBody.textContent = fullOutput;
            break;
          }
          try { var ej = JSON.parse(data); if (ej.error) { outputBody.innerHTML = '<span class="error-text">' + escHtml(ej.error) + '</span>'; return; } } catch(_) {}
          try {
            var c = JSON.parse(data);
            var ct = c.choices && c.choices[0] && c.choices[0].delta && c.choices[0].delta.content;
            if (ct) { assistantContent += ct; fullOutput += ct; outputBody.textContent = fullOutput; outputBody.scrollTop = outputBody.scrollHeight; }
          } catch(_) {}
        }
      }
    }

    if (assistantContent) {
      conversationMessages.push({ role: 'assistant', content: assistantContent });
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
    // Render MD after streaming done
    if (outputBody.textContent && outputBody.textContent.trim()) {
      outputRawText = outputBody.textContent;
      outputBody.innerHTML = renderMD(outputRawText);
    }
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
  if (e.key === 'Escape' && !factoryOverlay.classList.contains('hidden')) closeFactoryWizard();
  if (e.key === 'Escape' && !shortcutsOverlay.classList.contains('hidden')) shortcutsOverlay.classList.add('hidden');
  // ? key shortcuts panel
  if (e.key === '?' && document.activeElement !== taskInput && document.activeElement !== modalEditor) {
    e.preventDefault();
    shortcutsOverlay.classList.remove('hidden');
  }
});

// Shortcuts modal events
$('#shortcuts-close').addEventListener('click', function() { shortcutsOverlay.classList.add('hidden'); });
shortcutsOverlay.addEventListener('click', function(e) { if (e.target === shortcutsOverlay) shortcutsOverlay.classList.add('hidden'); });
$('#shortcuts-btn').addEventListener('click', function() { shortcutsOverlay.classList.remove('hidden'); });

// ===================================================================
// Theme Toggle
// ===================================================================
var currentTheme = localStorage.getItem('agency_theme') || 'dark';
document.documentElement.setAttribute('data-theme', currentTheme);
themeBtn.textContent = currentTheme === 'dark' ? '☀' : '☾';
themeBtn.addEventListener('click', function() {
  currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', currentTheme);
  localStorage.setItem('agency_theme', currentTheme);
  themeBtn.textContent = currentTheme === 'dark' ? '☀' : '☾';
});

// ===================================================================
// Agent Factory Wizard
// ===================================================================
var factoryOverlay = $('#factory-overlay');
var factoryAbortCtrl = null;
var factoryGeneratedContent = '';

$('#btn-create-agent').addEventListener('click', function() {
  openFactoryWizard();
});

function openFactoryWizard() {
  // Reset to step 1
  $('#factory-step-1').style.display = 'block';
  $('#factory-step-2').style.display = 'none';
  $('#factory-step-3').style.display = 'none';
  $('#factory-requirement').value = '';
  $('#factory-generated').value = '';
  $('#factory-save-btn').disabled = true;
  factoryGeneratedContent = '';
  factoryOverlay.classList.remove('hidden');
  $('#factory-requirement').focus();
}

function closeFactoryWizard() {
  if (factoryAbortCtrl) { factoryAbortCtrl.abort(); factoryAbortCtrl = null; }
  factoryOverlay.classList.add('hidden');
}

$('#factory-close').addEventListener('click', closeFactoryWizard);
factoryOverlay.addEventListener('click', function(e) {
  if (e.target === factoryOverlay) closeFactoryWizard();
});

// Step 1 -> Step 2: Generate
$('#factory-generate-btn').addEventListener('click', async function() {
  var req = $('#factory-requirement').value.trim();
  if (!req) { toast('请先描述你需要的 Agent', 'error'); return; }

  // Switch to step 2
  $('#factory-step-1').style.display = 'none';
  $('#factory-step-2').style.display = 'block';
  $('#factory-generated').value = '';
  $('#factory-spinner').style.display = 'inline-block';
  $('#factory-status').textContent = '正在生成...';
  $('#factory-save-btn').disabled = true;

  factoryAbortCtrl = new AbortController();
  var fullText = '';

  try {
    var resp = await fetch('/api/agent-generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ requirement: req }),
      signal: factoryAbortCtrl.signal
    });

    if (!resp.ok) {
      $('#factory-generated').value = 'API 错误 (' + resp.status + ')';
      $('#factory-spinner').style.display = 'none';
      $('#factory-status').textContent = '生成失败';
      return;
    }

    var reader = resp.body.getReader();
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
          try {
            var chunk = JSON.parse(data);
            var content = chunk.choices && chunk.choices[0] && chunk.choices[0].delta && chunk.choices[0].delta.content;
            if (content) {
              fullText += content;
              $('#factory-generated').value = fullText;
              $('#factory-generated').scrollTop = $('#factory-generated').scrollHeight;
            }
          } catch(_) {}
        }
      }
    }

    factoryGeneratedContent = fullText;
    $('#factory-spinner').style.display = 'none';
    $('#factory-status').textContent = fullText ? '生成完成，可编辑后保存' : '生成为空，请重试';
    if (fullText) {
      $('#factory-save-btn').disabled = false;
      $('#factory-status').textContent = '生成完成，可编辑后保存';
    } else {
      $('#factory-status').textContent = '生成为空，请重新描述需求';
    }
  } catch(e) {
    if (e.name === 'AbortError') {
      $('#factory-status').textContent = '已取消';
    } else {
      $('#factory-generated').value = '请求失败: ' + (e.message || String(e));
      $('#factory-status').textContent = '生成失败';
    }
    $('#factory-spinner').style.display = 'none';
  } finally {
    factoryAbortCtrl = null;
  }
});

// Regenerate
$('#factory-regenerate-btn').addEventListener('click', function() {
  // Go back to step 1
  $('#factory-step-2').style.display = 'none';
  $('#factory-step-1').style.display = 'block';
  $('#factory-requirement').value = '';
  $('#factory-generated').value = '';
  $('#factory-requirement').focus();
});

// Save
$('#factory-save-btn').addEventListener('click', async function() {
  var content = $('#factory-generated').value.trim();
  if (!content) { toast('没有可保存的内容', 'error'); return; }

  // Extract agent name from YAML frontmatter
  var nameMatch = content.match(/^---\s*\nname:\s*(\S+)/m);
  if (!nameMatch) {
    toast('无法从生成内容中提取 Agent name，请确保 frontmatter 中有 name 字段', 'error');
    return;
  }
  var agentName = nameMatch[1];

  $('#factory-save-btn').disabled = true;
  $('#factory-save-btn').textContent = '保存中...';

  try {
    var resp = await fetch('/api/agent-create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: agentName, content: content })
    });
    var data = await resp.json();
    if (data.ok) {
      // Show step 3
      $('#factory-step-2').style.display = 'none';
      $('#factory-step-3').style.display = 'block';
      $('#factory-done-msg').textContent = 'Agent "' + agentName + '" 已创建并注册到 agent.yaml 和 agents.json';
    } else {
      toast('保存失败: ' + (data.error || '?'), 'error');
      $('#factory-save-btn').disabled = false;
      $('#factory-save-btn').textContent = '保存 Agent';
    }
  } catch(e) {
    toast('保存失败: ' + (e.message || String(e)), 'error');
    $('#factory-save-btn').disabled = false;
    $('#factory-save-btn').textContent = '保存 Agent';
  }
});

// Done
$('#factory-done-btn').addEventListener('click', function() {
  closeFactoryWizard();
  loadAgents();  // Refresh agent list
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
    if (data.has_key) { badge.textContent = '已配置 (' + (data.provider_type || '?') + ')'; badge.className = 'status-dot ok'; }
    else { badge.textContent = '未配置'; badge.className = 'status-dot bad'; }

    // 填充表单
    var prov = $('#settings-provider');
    if (data.provider_type === 'deepseek') prov.value = 'deepseek';
    else if (data.provider_type === 'openai') prov.value = 'openai';
    else if (data.provider_type === 'ollama') prov.value = 'ollama';
    else prov.value = 'custom';

    $('#settings-baseurl').value = data.base_url || '';
    $('#settings-light-model').value = (data.model_mapping && data.model_mapping.light) || 'deepseek-chat';
    $('#settings-standard-model').value = (data.model_mapping && data.model_mapping.standard) || 'deepseek-chat';
    $('#settings-heavy-model').value = (data.model_mapping && data.model_mapping.heavy) || 'deepseek-reasoner';
  } catch(_) { $('#key-status').textContent = '检查失败'; $('#key-status').className = 'status-dot bad'; }

  var s = loadAppSettings();
  var sel = $('#default-model');
  sel.value = s.defaultModel || 'deepseek-chat';
  sel.addEventListener('change', function() { saveAppSettings({ defaultModel: sel.value }); toast('默认模型已更新', 'info'); });

  // Temperature
  var tempSlider = $('#settings-temperature');
  tempSlider.value = s.temperature !== undefined ? s.temperature : 0.7;
  $('#temp-val-label').textContent = tempSlider.value;
  tempSlider.addEventListener('input', function() {
    $('#temp-val-label').textContent = tempSlider.value;
  });

  // Max Tokens
  $('#settings-max-tokens').value = s.maxTokens || 8192;

  // API Key (from localStorage, .env is source of truth)
  var ak = $('#settings-apikey');
  ak.value = s.apiKey || '';

  // Base URL
  $('#settings-baseurl').value = s.baseUrl || $('#settings-baseurl').value;

  // Model mapping fields
  $('#settings-light-model').value = s.lightModel || $('#settings-light-model').value;
  $('#settings-standard-model').value = s.standardModel || $('#settings-standard-model').value;
  $('#settings-heavy-model').value = s.heavyModel || $('#settings-heavy-model').value;

  // Provider
  $('#settings-provider').value = s.provider || $('#settings-provider').value;
}

// Save Settings button
$('#btn-save-settings').addEventListener('click', function() {
  var settings = {
    provider: $('#settings-provider').value,
    apiKey: $('#settings-apikey').value,
    baseUrl: $('#settings-baseurl').value,
    lightModel: $('#settings-light-model').value,
    standardModel: $('#settings-standard-model').value,
    heavyModel: $('#settings-heavy-model').value,
    temperature: parseFloat($('#settings-temperature').value),
    maxTokens: parseInt($('#settings-max-tokens').value) || 8192,
    defaultModel: $('#default-model').value,
  };
  saveAppSettings(settings);
  toast('设置已保存（模型映射和提供者需在 .env 中配置后重启生效）', 'success');
});

// Reload .env button
$('#btn-reload-config').addEventListener('click', async function() {
  try {
    var resp = await fetch('/api/config-reload', { method: 'POST' });
    var data = await resp.json();
    if (data.ok) { toast('.env 已重新加载', 'success'); loadSettings(); }
    else { toast('加载失败: ' + (data.error || '?'), 'error'); }
  } catch(e) { toast('请求失败: ' + e.message, 'error'); }
});

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
// Pipeline
// ===================================================================
var pipelines = [
  {
    name: '代码审查流水线',
    chain: 'coder → code-reviewer → security-reviewer',
    desc: '写代码 → 通用审查 → 安全检查',
    steps: ['coder', 'code-reviewer', 'security-reviewer']
  },
  {
    name: '新功能开发流水线',
    chain: 'planner → coder → test-runner → code-reviewer',
    desc: '规划 → 实现 → 测试 → 审查',
    steps: ['planner', 'coder', 'test-runner', 'code-reviewer']
  },
  {
    name: 'Bug 修复流水线',
    chain: 'explorer → coder → test-runner',
    desc: '定位 → 修复 → 验证',
    steps: ['explorer', 'coder', 'test-runner']
  }
];

function renderPipelines() {
  var list = $('#pipeline-list');
  var prog = $('#pipeline-progress');
  prog.style.display = 'none';
  prog.innerHTML = '';
  list.innerHTML = pipelines.map(function(pl, pi) {
    return '<div class="pipeline-card">'
      + '<div class="pl-name">' + pl.name + '</div>'
      + '<div class="pl-chain">' + pl.chain.replace(/ → /g, ' <span>→</span> ') + '</div>'
      + '<div class="pl-desc">' + pl.desc + '</div>'
      + '<div class="pl-actions">'
        + '<button class="btn-sm primary pl-run-btn" data-pipe-idx="' + pi + '">执行</button>'
      + '</div></div>';
  }).join('');
  list.querySelectorAll('.pl-run-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var pi = parseInt(btn.dataset.pipeIdx);
      runPipeline(pipelines[pi]);
    });
  });
}

function runPipeline(pipeline) {
  var prog = $('#pipeline-progress');
  prog.style.display = 'block';
  var steps = pipeline.steps.map(function(s) { return { agent: s, status: 'wait', output: '' }; });
  prog.innerHTML = '<div style="font-weight:600;color:#c4b5fd;margin-bottom:8px;">🔄 流水线: ' + pipeline.name + '</div>'
    + '<div style="color:var(--muted);">──────────────────────────</div>'
    + steps.map(function(s, i) {
        return '<div class="pp-step pp-wait" id="pp-step-' + i + '">⬜ 第' + (i+1) + '步: ' + s.agent + ' — 等待中</div>';
      }).join('');

  (async function() {
    for (var i = 0; i < steps.length; i++) {
      var el = $('#pp-step-' + i);
      el.className = 'pp-step pp-running';
      el.innerHTML = '⏳ 第' + (i+1) + '步: ' + steps[i].agent + ' — 执行中...';
      try {
        var resp = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: [
              { role: 'system', content: '你是' + steps[i].agent + '。完成以下任务，直接输出结果。' },
              { role: 'user', content: (steps[i-1] && steps[i-1].output) ? ('上一步输出:\n' + steps[i-1].output.substring(0, 1000) + '\n\n请基于此继续完成你的部分。') : '执行你的任务。' }
            ]
          })
        });
        if (resp.ok) {
          var reader = resp.body.getReader();
          var decoder = new TextDecoder();
          var buffer = '';
          var content = '';
          var done = false;
          while (!done) {
            var rr = await reader.read();
            if (rr.done) break;
            buffer += decoder.decode(rr.value, { stream: true });
            var lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (var j = 0; j < lines.length; j++) {
              var line = lines[j];
              if (line.indexOf('data: ') === 0) {
                var data = line.slice(6);
                if (data === '[DONE]') { done = true; break; }
                try {
                  var chunk = JSON.parse(data);
                  var ct = chunk.choices && chunk.choices[0] && chunk.choices[0].delta && chunk.choices[0].delta.content;
                  if (ct) content += ct;
                } catch(_) {}
              }
            }
          }
          steps[i].output = content;
          el.className = 'pp-step pp-done';
          el.innerHTML = '✅ 第' + (i+1) + '步: ' + steps[i].agent + ' — 已完成';
        } else {
          el.className = 'pp-step pp-done';
          el.innerHTML = '❌ 第' + (i+1) + '步: ' + steps[i].agent + ' — 失败';
        }
      } catch(e) {
        el.className = 'pp-step pp-done';
        el.innerHTML = '❌ 第' + (i+1) + '步: ' + steps[i].agent + ' — 错误: ' + (e.message || '?');
      }
    }
    prog.innerHTML += '<div style="margin-top:8px;color:var(--green);">✅ 流水线执行完毕</div>';
    // Display final output in main area
    var lastOut = steps[steps.length-1].output;
    if (lastOut) {
      switchMode('user');
      outputBody.textContent = lastOut;
      outputRawText = lastOut;
      outputBody.innerHTML = renderMD(outputRawText);
      outputFooter.style.display = 'flex';
      outputLabel.textContent = '流水线完成';
    }
  })();
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
            provider_type = ""
            has_key = False
            if os.environ.get("DEEPSEEK_API_KEY"):
                provider_type = "deepseek"
                has_key = True
            elif os.environ.get("OPENAI_API_KEY"):
                provider_type = "openai"
                has_key = True
            elif os.environ.get("OLLAMA_BASE_URL"):
                provider_type = "ollama"
                has_key = True

            base_url, _, _ = get_provider_config()
            self.send_json({
                "provider_type": provider_type,
                "base_url": base_url or "",
                "has_key": has_key,
                "model_mapping": {
                    "light": os.environ.get("LIGHT_MODEL", "deepseek-chat"),
                    "standard": os.environ.get("STANDARD_MODEL", "deepseek-chat"),
                    "heavy": os.environ.get("HEAVY_MODEL", "deepseek-reasoner"),
                },
                "default_model": os.environ.get("DEFAULT_MODEL", "deepseek-chat"),
                "temperature": 0.7,
                "max_tokens": 8192,
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
            force_agent = body.get("force_agent", "")

            if force_agent:
                # 模糊匹配 agent 名
                matched = None
                agents_dir = PROJECT_ROOT / "agents"
                # 精确匹配
                exact = agents_dir / f"{force_agent}.md"
                if exact.exists():
                    matched = force_agent
                else:
                    # 模糊匹配
                    for f in sorted(agents_dir.glob("*.md")):
                        if force_agent in f.stem:
                            matched = f.stem
                            break
                    # 别名映射
                    ALIASES = {
                        "reviewer": "code-reviewer",
                        "test": "test-runner",
                        "writer": "webnovel-writer",
                        "planner": "planner",
                        "security": "security-reviewer",
                        "explorer": "explorer",
                        "coder": "coder",
                        "orchestrator": "orchestrator",
                        "cost": "cost-analyst",
                        "general": "general-worker",
                        "docker": "general-worker",
                        "tdd": "tdd-guide",
                        "build": "build-error-resolver",
                        "doc": "doc-updater",
                        "refactor": "refactor-cleaner",
                        "e2e": "e2e-runner",
                        "perf": "performance-optimizer",
                    }
                    if not matched and force_agent in ALIASES:
                        matched = ALIASES[force_agent]

                if matched:
                    system_prompt, model = load_agent(matched)
                    self.send_json({
                        "agent": matched,
                        "score": 99,
                        "model": model,
                        "direct": True,
                    })
                else:
                    self.send_json({
                        "error": f"Agent '{force_agent}' 不存在。可用: {', '.join(sorted(f.stem for f in agents_dir.glob('*.md')))}"
                    })
                return

            agent, score = route_task(task)
            system_prompt, model = load_agent(agent)
            self.send_json({"agent": agent, "score": score, "model": model})

        elif parsed.path == "/api/chat":
            # 支持两种模式：
            # 1) messages 数组（多轮会话）
            # 2) task + agent（兼容旧版 / 开发者测试）
            messages = body.get("messages")
            task = body.get("task", "")
            agent = body.get("agent", "coder")
            req_model = body.get("model", "")

            base_url, api_key, headers = get_provider_config()
            if not base_url:
                self.send_json({"error": "未配置 API Key。请在 .env 中设置 DEEPSEEK_API_KEY / OPENAI_API_KEY / OLLAMA_BASE_URL"})
                return

            if messages:
                # 多轮会话模式：前端直接传完整的 messages 数组
                model = req_model or os.environ.get("DEFAULT_MODEL", "deepseek-chat")
            else:
                # 兼容旧版：后端构建 messages
                system_prompt, model = load_agent(agent)
                if not req_model:
                    req_model = model
                model = req_model or model
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": task},
                ]

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            import requests as req

            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 8192,
            }

            max_retries = 2
            resp = None
            for attempt in range(max_retries + 1):
                try:
                    resp = req.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        stream=True,
                        timeout=300,
                    )
                    break
                except req.exceptions.ConnectionError:
                    if attempt < max_retries:
                        time.sleep(1)
                    else:
                        try:
                            self.wfile.write(f"data: {{\"error\": \"连接失败，已重试{max_retries}次\"}}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        except Exception:
                            pass
                        return

            if resp is None:
                return

            if resp.status_code != 200:
                try:
                    err_text = resp.text[:300] if hasattr(resp, 'text') else str(resp.status_code)
                    self.wfile.write(f'data: {{"error": "API 错误 ({resp.status_code}): {err_text}"}}\n\n'.encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass
                return

            try:
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

        elif parsed.path == "/api/config-reload":
            """重新加载 .env（不重启服务器）"""
            env_file = PROJECT_ROOT / ".env"
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
                self.send_json({"ok": True, "message": ".env 已重新加载"})
            else:
                self.send_json({"ok": False, "error": ".env 文件不存在"})

        elif parsed.path == "/api/agent-generate":
            """AI 生成 Agent 定义（流式）"""
            requirement = body.get("requirement", "")
            if not requirement:
                self.send_json({"error": "requirement 不能为空"})
                return

            gen_prompt = f"""你是一个 Agent 设计专家。根据用户需求生成一个完整的 Agent 定义文件。

输出格式严格如下：

---
name: agent-name（英文，kebab-case，如 log-analyzer、data-cleaner）
description: 一句话描述（中文）
tools: ["Read", "Write", "Bash", "Grep", "Glob"]
model: sonnet
---

# Agent 名称 -- 一句话描述

## 角色
（2-3句话说明这个 agent 是谁、负责什么）

## 核心能力
- 能力1
- 能力2
- 能力3

## 工作流
1. 步骤1
2. 步骤2
3. 步骤3

## 输出格式
直接对话回复，包含：
1. 结论（一句话）
2. 详细结果
3. 建议（如有）

## 约束
- 根据需求填充

---

用户需求：{requirement}

请直接输出完整的 Agent 定义文件，不要任何额外说明。"""

            base_url, api_key, headers = get_provider_config()
            if not base_url:
                self.send_json({"error": "未配置 API Key"})
                return

            model = os.environ.get("DEFAULT_MODEL", "deepseek-chat")

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            import requests as req
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": gen_prompt},
                ],
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 4096,
            }

            try:
                resp = req.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=120,
                )
                if resp.status_code != 200:
                    err = resp.text[:300] if hasattr(resp, 'text') else str(resp.status_code)
                    self.wfile.write(f'data: {{"error": "API 错误 ({resp.status_code}): {err}"}}\n\n'.encode("utf-8"))
                    self.wfile.flush()
                    return

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
            except Exception as e:
                try:
                    self.wfile.write(f'data: {{"error": "{str(e)}"}}\n\n'.encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass

        elif parsed.path == "/api/agent-create":
            """保存新 Agent 定义，同时更新 agent.yaml 和 agents.json"""
            agent_name = body.get("name", "").strip()
            content = body.get("content", "").strip()

            if not agent_name:
                self.send_json({"ok": False, "error": "name 不能为空"})
                return
            if not content:
                self.send_json({"ok": False, "error": "content 不能为空"})
                return

            # 安全校验：name 只能包含字母、数字、连字符
            import re
            if not re.match(r'^[a-z0-9][-a-z0-9]*$', agent_name):
                self.send_json({"ok": False, "error": "Agent 名称只能包含小写字母、数字和连字符，必须以字母或数字开头"})
                return

            agents_dir = PROJECT_ROOT / "agents"
            agent_file = agents_dir / f"{agent_name}.md"

            # 检查是否已存在
            if agent_file.exists():
                self.send_json({"ok": False, "error": f"Agent '{agent_name}' 已存在，请使用其他名称或先删除"})
                return

            # 1. 写入 .md 文件
            agent_file.write_text(content, encoding="utf-8")

            # 2. 追加到 agents.json
            json_path = PROJECT_ROOT / "maestro" / "agents.json"
            try:
                if json_path.exists():
                    agents_data = json.loads(json_path.read_text(encoding="utf-8"))
                    agents_data[agent_name] = {
                        "name": agent_name,
                        "description": "",
                        "system_prompt_file": f"agents/{agent_name}.md",
                        "allowed_tools": "Read,Write,Bash,Grep,Glob",
                        "model": "sonnet",
                        "collaborates_with": [],
                        "output_type": "task_result",
                        "isolation": "none",
                        "parallel_safe": True,
                    }
                    json_path.write_text(json.dumps(agents_data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass  # agents.json 更新失败不阻塞

            # 3. 追加到 agent.yaml
            yaml_path = PROJECT_ROOT / "agent.yaml"
            try:
                if yaml_path.exists():
                    with open(str(yaml_path), "a", encoding="utf-8") as f:
                        f.write(f"\n  {agent_name}:\n")
                        f.write(f"    file: agents/{agent_name}.md\n")
                        f.write(f"    model: sonnet\n")
                        f.write(f"    tools: [Read, Write, Bash, Grep, Glob]\n")
                        f.write(f"    routing: []\n")
            except Exception:
                pass

            self.send_json({"ok": True, "name": agent_name})

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
