/* Agency — 开发者设置面板 */
function saveApiKey(){var newKey=$('api-key').value.trim();var newProvider=$('api-provider').value;var oldKey=apiKey;var oldProvider=apiProvider;apiKey=newKey;apiProvider=newProvider;localStorage.setItem('agency_api_key',apiKey);localStorage.setItem('agency_api_provider',apiProvider);$('api-status').textContent=apiKey?'已保存':'已清除';if(!apiKey){localStorage.removeItem('agency_api_key');localStorage.removeItem('agency_api_provider')}showUndoableToast(t('configSaved'),function(){apiKey=oldKey;apiProvider=oldProvider;localStorage.setItem('agency_api_key',oldKey);localStorage.setItem('agency_api_provider',oldProvider);$('api-key').value=oldKey;$('api-provider').value=oldProvider;$('api-status').textContent=oldKey?'已保存':'已清除';if(!oldKey){localStorage.removeItem('agency_api_key');localStorage.removeItem('agency_api_provider')}},5000)}
function toggleDevOverlay(){devMode=!devMode;var ov=$('devOverlay'),btn=$('devBtn');ov.classList.toggle('on',devMode);btn.classList.toggle('on',devMode);if(devMode){var ak=$('api-key');if(ak&&apiKey)ak.value=apiKey;var ap=$('api-provider');if(ap&&apiProvider)ap.value=apiProvider;loadMemList();loadRemotePanel();loadIntegrationPanel();loadMCPConfig()}}

function loadMemList(){var domEl=$('mem-list');if(!domEl)return;fetch('/api/memory').then(function(r){return r.json()}).then(function(d){var files=d.files||[];domEl.innerHTML=files.length?files.map(function(f){return'<div class="mem-file" onclick="openMemEditor(\''+escHtml(f.path)+'\',\''+escHtml(f.name)+'\')"><span class="icon">📄</span><span>'+escHtml(f.name)+'</span><span style="color:var(--muted);font-size:10px;margin-left:auto">'+(f.size||0)+'B</span></div>'}).join(''):'暂无记忆文件'}).catch(function(){domEl.innerHTML='无法加载记忆文件列表。服务可能未启动，请刷新页面重试'})}
function generateAgent(){var input=$('agent-factory-input'),output=$('agent-factory-output');var req=input.value.trim();if(!req)return;output.innerHTML='生成中…';fetch('/api/agent-generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({requirement:req,api_key:apiKey||undefined,api_provider:apiProvider||undefined})}).then(function(resp){var reader=resp.body.getReader(),decoder=new TextDecoder(),buf='',txt='';function read(){reader.read().then(function(result){if(result.done){finish();return}buf+=decoder.decode(result.value,{stream:!0});buf=buf.replace(/\r\n/g,'\n');var lines=buf.split('\n');buf=lines.pop()||'';for(var i=0;i<lines.length;i++){if(lines[i].indexOf('data: ')!==0)continue;try{var d=JSON.parse(lines[i].slice(6));if(d.content)txt+=d.content;if(d.error){output.innerHTML='<span style=color:var(--danger)>'+escHtml(d.error)+'</span>';return}}catch(_){}}read()})}function finish(){output.innerHTML='<pre style=\"font-size:10px;max-height:200px;overflow:auto;background:var(--bg);padding:8px;border-radius:4px\">'+escHtml(txt)+'</pre><button class=\"new-chat-btn\" style=\"margin-top:4px\" onclick=\"saveAgent()\">保存此 Agent</button>';output._agentContent=txt}read()}).catch(function(){output.innerHTML='AI 生成中断。可能是网络问题或 API Key 无效，请检查后重试'})}
function saveAgent(){var txt=$('agent-factory-output')._agentContent;if(!txt)return;var m=txt.match(/name:\s*"?([a-z0-9-]+)"?/i);var name=m?m[1]:('agent-'+Date.now().toString(36));fetch('/api/agent-create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,content:txt})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('Agent 已保存: '+name);loadAgents()}else{showToast(d.error||'保存失败，请检查文件权限或磁盘空间后重试',!0)}}).catch(function(e){showToast('保存失败: '+(e.message||'请检查网络连接后重试'),!0)})}
function loadRemotePanel(){
  var domEl=$('remote-panel');if(!domEl){console.debug('remote-panel not found');return}
  fetch('/api/remote/status').then(function(r){
    if(!r.ok)throw new Error('HTTP '+r.status);
    return r.json();
  }).then(function(d){
    var html='';
    if(d.enabled){
      html+='<div style=\"background:rgba(34,211,160,.08);border:1px solid var(--accent);border-radius:6px;padding:8px 10px;margin-bottom:8px\">';
      html+='<div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:4px\"><span style=\"color:var(--accent);font-weight:600\">已启用</span><button class=\"btn\" onclick=\"toggleRemote(false)\" style=\"font-size:10px\">关闭</button></div>';
      html+='<div style=\"font-size:10px;color:var(--text2);margin-bottom:6px\">连接地址</div>';
      html+='<div style=\"display:flex;gap:4px;align-items:center\"><input class=\"proj-input\" value=\"'+escHtml(d.url||'')+'\" readonly style=\"flex:1;margin:0;font-size:11px\" id=\"remote-url\"><button class=\"btn\" onclick=\"copyRemoteUrl()\" style=\"font-size:10px;white-space:nowrap\">复制</button></div>';
      html+='<div style=\"margin-top:6px;font-size:10px;color:var(--text2)\">访问密码</div>';
      html+='<div style=\"display:flex;gap:4px;align-items:center;margin-top:2px\"><input class=\"proj-input\" id=\"remote-token-input\" style=\"flex:1;margin:0;font-size:11px;font-family:monospace\" placeholder=\"输入新密码…\"><button class=\"btn\" onclick=\"setRemoteToken()\" style=\"font-size:10px;white-space:nowrap\">更新</button><button class=\"btn\" onclick=\"genRemoteToken()\" style=\"font-size:10px\">随机</button></div>';
      html+='</div>';
    } else {
      html+='<div style=\"background:var(--surface2);border-radius:6px;padding:8px 10px;margin-bottom:8px\"><div style=\"display:flex;justify-content:space-between;align-items:center\"><span style=\"color:var(--muted)\">未启用</span><button class=\"btn\" onclick=\"toggleRemote(true)\" style=\"font-size:10px;background:var(--accent);color:#000;border-color:var(--accent)\">开启</button></div><div style=\"font-size:10px;color:var(--muted);margin-top:4px\">开启后可从手机/其他设备访问</div></div>';
    }
    domEl.innerHTML=html;
  }).catch(function(e){console.error('loadRemotePanel:',e);domEl.innerHTML='加载失败: '+escHtml(e.message)});
}
function toggleRemote(on){
  fetch('/api/remote/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:on})}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      if(d.token){authToken=d.token;localStorage.setItem('agency_auth_token',d.token);showToast('远端已开启')}
      else showToast('远端已关闭');
      loadRemotePanel();
    } else showToast(d.error||'远程开关失败。可能服务未启动，请刷新页面重试',!0);
  }).catch(function(e){showToast('远程操作失败: '+(e.message||'请检查网络连接'),!0);console.error(e)});
}
function setRemoteToken(){
  var t=$('remote-token-input').value.trim();if(!t)return;
  fetch('/api/remote/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:true,token:t})}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){authToken=d.token;localStorage.setItem('agency_auth_token',d.token);$('remote-token-input').value='';showToast('密码已更新');}
    else showToast(d.error||'密码更新失败。可能服务未启动，请刷新页面重试',!0);
  }).catch(function(e){showToast('密码更新失败: '+(e.message||'请检查网络连接'),!0)});
}
function genRemoteToken(){
  fetch('/api/remote/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:true,token:''})}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){authToken=d.token;localStorage.setItem('agency_auth_token',d.token);$('remote-token-input').value=d.token;showToast('新密码: '+d.token);}
    else showToast(d.error||'密码生成失败。可能服务未启动，请刷新页面重试',!0);
  }).catch(function(e){showToast('密码生成失败: '+(e.message||'请检查网络连接'),!0)});
}
function copyRemoteUrl(){
  var domEl=$('remote-url');if(!domEl)return;
  var url=domEl.value||domEl.textContent||'';if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(url).then(function(){showToast('已复制连接地址')}).catch(function(){domEl.select();document.execCommand('copy');showToast('已复制连接地址')})}else{domEl.select();document.execCommand('copy');showToast('已复制连接地址')}
}
function loadIntegrationPanel(){
  var domEl=$('integration-panel');if(!domEl)return;
  fetch('/api/remote/status').then(function(r){return r.json()}).then(function(d){
    var baseUrl=d.url||('http://'+d.ip+':'+d.port),hookUrl=baseUrl+'/api/webhook/generic';
    var html='<div style=\"margin-bottom:12px\">';
    html+='<p style=\"font-size:10px;color:var(--text2);margin-bottom:8px\">外部服务通过 Webhook 调用 Agency</p>';
    html+='<div style=\"background:var(--surface2);border-radius:6px;padding:8px 10px;margin-bottom:6px\">';
    html+='<div style=\"font-weight:600;font-size:11px;color:var(--accent);margin-bottom:4px\">通用 Webhook</div>';
    html+='<div style=\"font-size:10px;color:var(--text2);margin-bottom:4px;word-break:break-all\">POST '+escHtml(hookUrl)+'</div>';
    html+='<div style=\"font-size:10px;color:var(--muted)\">Body: {\"message\":\"...\", \"session_id\":\"...\"}</div>';
    html+='<div style=\"margin-top:4px\"><button class=\"btn\" style=\"font-size:10px\" id=\"hook-copy-btn\">复制 URL</button></div>';
    html+='</div>';
    html+='<details style=\"margin-top:6px\"><summary style=\"font-size:10px;cursor:pointer;color:var(--text2)\">curl / Python 示例</summary>';
    html+='<pre style=\"font-size:9px;background:var(--bg);padding:6px;border-radius:4px;margin-top:4px;overflow-x:auto\">'+escHtml('curl -X POST '+hookUrl+' -H \"Content-Type: application/json\" -H \"Authorization: Bearer <token>\" -d \"{\\\"message\\\":\\\"你好\\\"}\"')+'</pre>';
    html+='</details>';
    html+='<p style=\"font-size:10px;color:var(--muted);margin-top:8px\">飞书/微信接入请在各平台配置此 Webhook 地址</p>';
    html+='</div>';
    domEl.innerHTML=html;
    var btn=document.getElementById('hook-copy-btn');
    if(btn)btn.onclick=function(){copyText(hookUrl)};
  }).catch(function(){domEl.innerHTML='无法加载集成面板数据。服务可能未启动，请刷新页面重试'});
}
function openMemEditor(path,name){
  var fname=name.split('\\').pop().split('/').pop();
  fetch('/api/memory/'+encodeURIComponent(fname)).then(function(r){return r.json()}).then(function(d){
    if(d.error){showToast(d.error,!0);return}
    var ed=$('mem-editor');
    ed.innerHTML='<div style="margin-bottom:4px;font-size:11px;color:var(--text2)">编辑: '+escHtml(d.name)+'</div><textarea class="mem-editor" id="mem-edit-area">'+escHtml(d.content)+'</textarea><div style="margin-top:6px;display:flex;gap:6px"><button class="btn" onclick="saveMemFile(\''+escHtml(fname)+'\')">💾 保存</button><button class="btn" onclick="document.getElementById(\'mem-editor\').innerHTML=\'\';loadMemList()">取消</button></div>';
  }).catch(function(e){showToast('无法加载文件: '+(e.message||'请检查网络连接后刷新重试'),!0)});
}
function saveMemFile(name){
  var content=document.getElementById('mem-edit-area');if(!content)return;
  fetch('/api/memory/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:content.value})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('已保存: '+d.name);document.getElementById('mem-editor').innerHTML='';loadMemList()}else{showToast(d.error||'保存失败，请检查文件权限或磁盘空间后重试',!0)}}).catch(function(e){showToast('保存失败: '+e.message,!0)});
}

/* ── MCP 配置面板 ── */
var MCP_DESCRIPTIONS = {
  'playwright': '浏览器自动化',
  'context7': '文档查询',
  'github': 'GitHub API',
  'brave-search': '网络搜索',
  'sequential-thinking': '深度推理'
};

function loadMCPConfig(){
  var domEl=$('mcp-config-list');if(!domEl)return;
  fetch('/api/mcp/status').then(function(r){return r.json()}).then(function(d){
    var servers=d.servers||[];
    if(!servers.length){domEl.innerHTML='<span style="color:var(--muted);font-size:10px">未检测到 MCP 服务。请检查 .mcp.json 配置</span>';return}
    domEl.innerHTML=servers.map(function(s){
      var desc=MCP_DESCRIPTIONS[s.name]||s.name;
      var dotColor=s.running?'var(--accent)':'var(--danger)';
      var checked=s.enabled!==false?'checked':'';
      return '<label class="mcp-row" style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border);cursor:pointer;font-size:11px">'+
        '<input type="checkbox" '+checked+' onchange="toggleMCPServer(\''+escAttr(s.name)+'\',this.checked)" style="accent-color:var(--accent)">'+
        '<span style="flex:1">'+escHtml(s.name)+'</span>'+
        '<span style="font-size:9px;color:var(--muted);margin-right:4px">'+escHtml(desc)+'</span>'+
        '<span title="'+(s.running?'运行中':'离线')+'" style="width:7px;height:7px;border-radius:50%;background:'+dotColor+';flex-shrink:0"></span>'+
        '</label>';
    }).join('');
  }).catch(function(){domEl.innerHTML='无法加载 MCP 配置。服务可能未启动，请刷新页面重试'});
}

function toggleMCPServer(name,enabled){
  fetch('/api/mcp/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'toggle',server:name,enabled:enabled})}).then(function(r){return r.json()}).then(function(d){
    if(!d.ok){showToast(d.error||'MCP 配置更新失败，请重试',!0);loadMCPConfig()}
  }).catch(function(){showToast('MCP 配置更新失败，请检查网络连接',!0);loadMCPConfig()});
}

/* ── 全局信任模式 ── */
var TRUST_MODES = {
  cautious: { label: '谨慎模式', desc: '所有需确认操作都询问', icon: '🛡️' },
  normal:   { label: '正常模式', desc: '同类操作只问一次（24h 内记住）', icon: '⚖️' },
  trusted:  { label: '信任模式', desc: '仅拦截高危操作（rm -rf /等）', icon: '🚀' }
};
var trustMode = localStorage.getItem('agency_trust_mode') || 'cautious';

function getTrustMode(){ return trustMode; }

function setTrustMode(mode){
  if(!TRUST_MODES[mode]) return;
  trustMode = mode;
  localStorage.setItem('agency_trust_mode', mode);
  updateTrustModeUI();
  showToast('信任模式已切换: ' + TRUST_MODES[mode].label);
  fetch('/api/permissions/decision', {
    method:'POST',
    headers:{'Content-Type':'application/json','X-Agency-Trust-Mode':mode},
    body:JSON.stringify({decision:'config',tool_name:'trust_mode',risk:mode,reason:'用户切换信任模式'})
  }).catch(function(){});
}

function updateTrustModeUI(){
  var sel = document.getElementById('trust-mode-select');
  if(sel) sel.value = trustMode;
  var desc = document.getElementById('trust-mode-desc');
  if(desc && TRUST_MODES[trustMode]) desc.textContent = TRUST_MODES[trustMode].desc;
  var btns = document.querySelectorAll('.trust-mode-btn');
  btns.forEach(function(b){
    var mode = b.getAttribute('data-mode');
    b.classList.toggle('active', mode === trustMode);
  });
}

/* ── 权限确认弹窗 ── */
function showPermissionConfirm(toolName, risk, reason, args){
  if(trustMode === 'trusted'){
    confirmPermission(toolName, 'allow', args);
    return;
  }
  if(trustMode === 'normal'){
    fetch('/api/permissions/history?limit=10').then(function(r){return r.json()}).then(function(d){
      var hist = d.history || [];
      var found = hist.find(function(h){ return h.tool === toolName && h.decision === 'allow'; });
      if(found){
        confirmPermission(toolName, 'allow', args);
        return;
      }
      _showConfirmDialog(toolName, risk, reason, args);
    }).catch(function(){ _showConfirmDialog(toolName, risk, reason, args); });
    return;
  }
  _showConfirmDialog(toolName, risk, reason, args);
}

function _showConfirmDialog(toolName, risk, reason, args){
  var riskColor = risk === 'high' ? 'var(--danger)' : risk === 'medium' ? '#f0a020' : 'var(--accent)';
  var overlay = document.createElement('div');
  overlay.className = 'agent-prompt-overlay';
  overlay.style.display = 'flex';
  overlay.innerHTML =
    '<div class="agent-prompt-modal" style="width:400px">'+
    '<div class="apm-header"><span>⚡ 权限确认</span></div>'+
    '<div class="apm-body">'+
    '<div style="margin-bottom:12px"><span style="color:var(--text2);font-size:11px">工具:</span> <code style="background:var(--bg);padding:2px 6px;border-radius:3px;font-size:11px">'+escHtml(toolName)+'</code></div>'+
    '<div style="margin-bottom:12px"><span style="color:var(--text2);font-size:11px">风险:</span> <span style="color:'+riskColor+';font-weight:600;font-size:11px">'+escHtml(risk)+'</span></div>'+
    '<div style="margin-bottom:12px;font-size:11px;color:var(--text2)">'+escHtml(reason||'此操作需要你的确认')+'</div>'+
    '<label style="display:flex;align-items:center;gap:6px;font-size:10px;color:var(--muted);margin-bottom:12px;cursor:pointer"><input type="checkbox" id="perm-remember" style="accent-color:var(--accent)"> 24h 内记住此选择</label>'+
    '</div>'+
    '<div class="apm-footer" style="display:flex;gap:8px">'+
    '<button class="btn" style="flex:1;border-color:var(--danger);color:var(--danger)" id="perm-deny-btn">拒绝</button>'+
    '<button class="new-chat-btn" style="flex:1" id="perm-allow-btn">允许执行</button>'+
    '</div>'+
    '</div>';
  document.body.appendChild(overlay);

  document.getElementById('perm-allow-btn').onclick = function(){
    overlay.remove();
    confirmPermission(toolName, 'allow', args);
  };
  document.getElementById('perm-deny-btn').onclick = function(){
    overlay.remove();
    confirmPermission(toolName, 'deny', args);
  };
  overlay.onclick = function(e){
    if(e.target === overlay){ overlay.remove(); confirmPermission(toolName, 'deny', args); }
  };
}

function confirmPermission(toolName, choice, args){
  fetch('/api/permissions/confirm', {
    method:'POST',
    headers:{'Content-Type':'application/json','X-Agency-Trust-Mode':trustMode},
    body:JSON.stringify({tool_name:toolName, choice:choice, trust_mode:trustMode, args:args||''})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      if(choice === 'allow') showToast('已允许: '+toolName);
      else showToast('已拒绝: '+toolName);
    }
  }).catch(function(e){ showToast('权限确认失败: '+(e.message||'网络错误'),!0); });
}

/* ── 权限审计面板 ── */
function loadPermissionAudit(){
  var domEl = document.getElementById('perm-audit-list');
  if(!domEl) return;
  fetch('/api/permissions/audit?limit=50').then(function(r){return r.json()}).then(function(d){
    var logs = d.logs || [];
    var stats = d.stats || {};
    var html = '<div style="margin-bottom:8px;display:flex;gap:12px;font-size:11px">'+
      '<span style="color:var(--accent)">允许: '+stats.allowed+'</span>'+
      '<span style="color:#f0a020">询问: '+stats.asked+'</span>'+
      '<span style="color:var(--danger)">拒绝: '+stats.denied+'</span>'+
      '<span style="color:var(--muted)">总计: '+stats.total+'</span>'+
      '</div>';
    if(logs.length){
      html += '<div style="max-height:300px;overflow-y:auto">';
      logs.forEach(function(l){
        var decColor = l.decision === 'allow' ? 'var(--accent)' : l.decision === 'deny' ? 'var(--danger)' : '#f0a020';
        html += '<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:10px">'+
          '<span style="color:var(--muted)">'+escHtml((l.time||'').slice(-8))+'</span> '+
          '<code style="color:var(--text);font-size:10px">'+escHtml(l.tool)+'</code> '+
          '<span style="color:'+decColor+'">'+escHtml(l.decision)+'</span> '+
          (l.reason ? '<span style="color:var(--muted)"> — '+escHtml(l.reason.slice(0,40))+'</span>' : '')+
          '</div>';
      });
      html += '</div>';
    } else {
      html += '<span style="color:var(--muted);font-size:10px">暂无审计记录</span>';
    }
    domEl.innerHTML = html;
  }).catch(function(){ domEl.innerHTML = '权限审计数据加载失败。请检查服务是否正常运行'; });
}

// 初始化信任模式 UI
document.addEventListener('DOMContentLoaded', function(){
  updateTrustModeUI();
  updateProfileUI();
});

/* ── Profile 选择器（设置面板专用）── */
function showProfilePicker(){
  // 在设置面板打开时刷新 profile 列表
  fetch('/api/profile').then(function(r){return r.json()}).then(function(d){
    var sel = document.getElementById('profile-select');
    if(!sel) return;
    var profiles = d.profiles || {};
    var keys = Object.keys(profiles);
    if(!keys.length) keys = ['minimal','standard','full'];
    sel.innerHTML = keys.map(function(k){
      var p = profiles[k] || {};
      var label = PROFILE_LABELS[k] || k;
      var icon = PROFILE_ICONS[k] || '';
      return '<option value="'+escHtml(k)+'">'+icon+' '+escHtml(label)+' — '+escHtml(p.trigger||k)+'</option>';
    }).join('');
    sel.value = agencyProfile;
  }).catch(function(){});
}

/* ── Key 可见性切换 ── */
function toggleKeyVisibility(){var inp=$('api-key');var btn=$('key-toggle-btn');if(inp.type==='password'){inp.type='text';btn.textContent='🙈'}else{inp.type='password';btn.textContent='👁'}}

/* ── Provider 切换提示 ── */
function onProviderChange(){showToast(t('providerSwitchWarn'),false,'warn',3000)}

/* ── 主题切换 ── */
function setTheme(theme){
  localStorage.setItem('agency_theme', theme);
  document.documentElement.setAttribute('data-theme', theme==='dark'?null:theme);
  document.body.className = theme==='high-contrast'?'theme-high-contrast':'';
  var sel = document.getElementById('theme-selector');
  if(sel){
    sel.querySelectorAll('.theme-opt').forEach(function(o){
      o.classList.toggle('active', o.getAttribute('data-theme-val')===theme);
    });
  }
  showToast(t('configSaved'));
}
function initTheme(){
  var saved = localStorage.getItem('agency_theme') || '';
  // 检测系统高对比度偏好
  if(window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches){
    var hint = document.getElementById('contrast-hint');
    if(hint) hint.classList.add('show');
    if(!saved){
      saved = 'high-contrast';
    }
  }
  if(saved && saved !== 'dark'){
    document.documentElement.setAttribute('data-theme', saved);
    document.body.className = saved==='high-contrast'?'theme-high-contrast':'';
    var sel = document.getElementById('theme-selector');
    if(sel){
      sel.querySelectorAll('.theme-opt').forEach(function(o){
        o.classList.toggle('active', o.getAttribute('data-theme-val')===saved);
      });
    }
  }

  // 监听系统对比度变化
  if(window.matchMedia){
    window.matchMedia('(prefers-contrast: more)').addEventListener('change', function(e){
      var hint = document.getElementById('contrast-hint');
      if(e.matches){
        if(hint) hint.classList.add('show');
        if(!localStorage.getItem('agency_theme')) setTheme('high-contrast');
      } else {
        if(hint) hint.classList.remove('show');
      }
    });
  }
}

/* ── 功能解锁 UI ── */
function renderFeatureUnlock(){
  var domEl = document.getElementById('feature-unlock-content');
  if(!domEl) return;
  var day = getUserDay();
  var unlocked = localStorage.getItem('agency_unlock_all') === 'true';
  var keys = Object.keys(FEATURE_SCHEDULE);
  var labelMap = {chat:'基础聊天',settings:'设置面板',dashboard:'仪表盘',agents:'Agent列表',routing:'智能调度',multipanel:'多面板','agent-factory':'Agent工厂',skills:'Skill编辑',profiles:'Profile切换'};
  var html = '<p style="font-size:10px;color:var(--muted);margin-bottom:8px">'+t('currentDay').replace('{day}', day)+'</p>';
  html += '<table class="feature-unlock-table">';
  var hasLocked = false;
  for(var i=0;i<keys.length;i++){
    var s = FEATURE_SCHEDULE[keys[i]];
    var isUnlocked = unlocked || day >= s.minDay;
    if(!isUnlocked) hasLocked = true;
    var featuresStr = s.features.map(function(f){ return labelMap[f] || f; }).join(' + ');
    html += '<tr><td class="fu-icon">'+(isUnlocked?'✅':'🔒')+'</td>';
    html += '<td><div class="fu-features">'+escHtml(featuresStr)+'</div><div class="fu-desc">'+(s.desc[_lang]||s.desc.zh)+'</div></td>';
    html += '<td class="fu-day">Day '+s.minDay+'</td>';
    html += '<td class="fu-status '+(isUnlocked?'unlocked':'locked')+'">'+(isUnlocked?t('unlockAll'):t('featureLocked').replace('{day}',s.minDay))+'</td></tr>';
  }
  html += '</table>';
  if(hasLocked && !unlocked){
    html += '<div style="padding:8px 10px;margin:10px 0;background:rgba(96,165,250,.08);border-left:3px solid #60a5fa;border-radius:4px;font-size:11px;color:var(--text);line-height:1.6">'+t('featureUnlockHint')+'</div>';
  }
  html += '<div class="feature-unlock-switch"><span>🔓 解锁全部功能</span><label class="toggle-sw"><input type="checkbox" id="unlock-all-toggle" onchange="toggleUnlockAll(this.checked)"'+(unlocked?' checked':'')+'><span class="toggle-slider"></span></label></div>';
  domEl.innerHTML = html;
}
function toggleUnlockAll(on){
  localStorage.setItem('agency_unlock_all', on?'true':'false');
  showToast(t('configSaved'));
  renderFeatureUnlock();
  // 刷新 UI
  if(typeof renderAgents === 'function') loadAgents();
  if(typeof loadSidebarSkills === 'function') loadSidebarSkills();
}
function showLockedHint(el, featureName){
  var minDay = FEATURE_UNLOCK_DAYS[featureName] || 7;
  el.setAttribute('data-locked-hint', t('featureLocked').replace('{day}', minDay));
  el.classList.add('locked-feature');
}

/* ── 配置导出 ── */
function exportConfig(){
  var config = {
    version: 1,
    exported_at: new Date().toISOString(),
    agents: typeof agents !== 'undefined' ? agents : [],
    skills: typeof allSkills !== 'undefined' ? allSkills : [],
    preferences: {
      theme: localStorage.getItem('agency_theme') || 'dark',
      font_size: localStorage.getItem('agency_font_size') || '14px',
      sidebar_width: localStorage.getItem('agency_sidebar_width') || '280',
      trust_mode: localStorage.getItem('agency_trust_mode') || 'cautious',
      profile: localStorage.getItem('agency_profile') || 'standard',
      output_dir: localStorage.getItem('agency_output_dir') || '',
      unlock_all: localStorage.getItem('agency_unlock_all') || 'false'
    },
    custom_templates: getCustomTemplates()
  };
  // 预览摘要
  var preview = document.getElementById('config-export-preview');
  if(preview){
    var previewHTML = '<div class="config-export-preview"><div style="font-weight:600;margin-bottom:4px">'+t('exportPreview')+'</div>';
    previewHTML += '<div class="preview-row"><span>Agent</span><span class="preview-val">'+(config.agents.length||0)+' 个</span></div>';
    previewHTML += '<div class="preview-row"><span>Skills</span><span class="preview-val">'+(config.skills.length||0)+' 个</span></div>';
    previewHTML += '<div class="preview-row"><span>自定义模板</span><span class="preview-val">'+(config.custom_templates.length||0)+' 个</span></div>';
    previewHTML += '<div class="preview-row"><span>偏好设置</span><span class="preview-val">'+Object.keys(config.preferences).length+' 项</span></div>';
    previewHTML += '</div>';
    preview.innerHTML = previewHTML;
  }
  var blob = new Blob([JSON.stringify(config, null, 2)], {type:'application/json'});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'agency-config.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(t('configExportDone'));
}

/* ── 配置导入 ── */
function importConfig(){
  var input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = function(e){
    var file = e.target.files[0];
    if(!file) return;
    var reader = new FileReader();
    reader.onload = function(ev){
      try{
        var imported = JSON.parse(ev.target.result);
        showImportDiff(imported);
      }catch(err){
        showToast(t('error')+': JSON 格式无效', true);
      }
    };
    reader.readAsText(file);
  };
  input.click();
}
function showImportDiff(imported){
  var current = {
    agents: typeof agents !== 'undefined' ? agents : [],
    skills: typeof allSkills !== 'undefined' ? allSkills : [],
    preferences: {
      theme: localStorage.getItem('agency_theme') || 'dark',
      font_size: localStorage.getItem('agency_font_size') || '14px',
      sidebar_width: localStorage.getItem('agency_sidebar_width') || '280',
      trust_mode: localStorage.getItem('agency_trust_mode') || 'cautious',
      profile: localStorage.getItem('agency_profile') || 'standard',
      output_dir: localStorage.getItem('agency_output_dir') || '',
      unlock_all: localStorage.getItem('agency_unlock_all') || 'false'
    },
    custom_templates: getCustomTemplates()
  };

  var diffs = [];
  // agents
  var impAgents = imported.agents || [];
  var curAgents = current.agents;
  impAgents.forEach(function(ia){
    var ca = curAgents.find(function(a){return a.name===ia.name});
    if(!ca){
      diffs.push({type:'new',section:'Agent',name:ia.name,val:ia.description||''});
    }
  });
  // skills
  var impSkills = imported.skills || [];
  var curSkills = current.skills;
  impSkills.forEach(function(is){
    var cs = curSkills.find(function(s){return s.name===is.name});
    if(!cs){
      diffs.push({type:'new',section:'Skill',name:is.name,val:is.description||''});
    }
  });
  // preferences
  var impPrefs = imported.preferences || {};
  var curPrefs = current.preferences;
  Object.keys(impPrefs).forEach(function(k){
    if(impPrefs[k] !== curPrefs[k]){
      diffs.push({type:'change',section:'偏好',name:k,old:curPrefs[k]||'(空)',val:impPrefs[k]||'(空)'});
    }
  });
  // custom templates
  var impTpls = imported.custom_templates || [];
  var curTpls = current.custom_templates;
  impTpls.forEach(function(it){
    var ct = curTpls.find(function(t){return t.label===it.label});
    if(!ct){
      diffs.push({type:'new',section:'模板',name:it.label||it.content.slice(0,20),val:it.content||''});
    }
  });

  var overlay = document.createElement('div');
  overlay.className = 'config-diff-overlay';
  var html = '<div class="config-diff-modal">';
  html += '<div class="config-diff-header"><span>'+t('importDiff')+' ('+diffs.length+' 项)</span><button class="btn" id="diff-close-btn">✕</button></div>';
  html += '<div class="config-diff-body">';
  if(diffs.length === 0){
    html += '<p style="color:var(--muted);text-align:center;padding:20px">配置无差异，无需导入</p>';
  } else {
    diffs.forEach(function(d,i){
      html += '<div class="config-diff-item" id="diff-item-'+i+'">';
      html += '<div class="diff-name">['+escHtml(d.section)+'] '+escHtml(d.name)+'</div>';
      if(d.type==='change'){
        html += '<div class="diff-row"><span class="diff-old">'+escHtml(d.old)+'</span><span class="diff-arrow">→</span><span class="diff-new">'+escHtml(d.val)+'</span></div>';
        html += '<div class="diff-actions"><button class="replace" onclick="applyDiffItem('+i+',\'replace\')">'+t('replaceWithImport')+'</button><button onclick="applyDiffItem('+i+',\'keep\')">'+t('keepExisting')+'</button></div>';
      } else {
        html += '<div class="diff-row"><span class="diff-new-only">(新增) '+escHtml(d.val)+'</span></div>';
        html += '<div class="diff-actions"><button class="replace" onclick="applyDiffItem('+i+',\'import\')">'+t('importNewItem')+'</button><button onclick="applyDiffItem('+i+',\'skip\')">'+t('skipImport')+'</button></div>';
      }
      html += '</div>';
    });
  }
  html += '</div>';
  html += '<div class="config-diff-actions">';
  if(diffs.length > 0){
    html += '<button class="btn primary" onclick="applyAllDiffs()">'+t('replaceAll')+'</button>';
    html += '<button class="btn" onclick="skipAllDiffs()">'+t('keepAll')+'</button>';
  }
  html += '<button class="btn" id="diff-cancel-btn">'+t('cancel')+'</button>';
  html += '</div></div>';
  overlay.innerHTML = html;
  document.body.appendChild(overlay);

  overlay._diffs = diffs;
  overlay._imported = imported;
  overlay._decisions = {};
  diffs.forEach(function(d,i){ overlay._decisions[i] = 'replace'; });

  function cleanup(){ overlay.remove(); }
  overlay.querySelector('#diff-close-btn').addEventListener('click', cleanup);
  overlay.querySelector('#diff-cancel-btn').addEventListener('click', cleanup);
  overlay.addEventListener('click', function(e){ if(e.target===overlay) cleanup(); });
}

function applyDiffItem(idx, decision){
  var overlay = document.querySelector('.config-diff-overlay');
  if(!overlay) return;
  overlay._decisions[idx] = decision;
  var item = document.getElementById('diff-item-'+idx);
  if(item){
    item.style.opacity = decision==='replace'||decision==='import'?'.6':'.3';
    item.style.borderLeftColor = decision==='replace'||decision==='import'?'var(--accent)':'var(--muted)';
  }
}

function applyAllDiffs(){
  var overlay = document.querySelector('.config-diff-overlay');
  if(!overlay) return;
  var diffs = overlay._diffs;
  for(var i=0;i<diffs.length;i++) overlay._decisions[i]='replace';
  executeImport(overlay._imported, overlay._decisions);
  overlay.remove();
}

function skipAllDiffs(){
  var overlay = document.querySelector('.config-diff-overlay');
  if(!overlay) return;
  overlay.remove();
  showToast(t('configImportCancel'));
}

function executeImport(imported, decisions){
  // Apply preferences
  var impPrefs = imported.preferences || {};
  Object.keys(impPrefs).forEach(function(k){
    var prefKey = {theme:'agency_theme',font_size:'agency_font_size',sidebar_width:'agency_sidebar_width',trust_mode:'agency_trust_mode',profile:'agency_profile',output_dir:'agency_output_dir',unlock_all:'agency_unlock_all'}[k];
    if(prefKey) localStorage.setItem(prefKey, impPrefs[k]);
  });
  showToast(t('configImportDone'));
  setTimeout(function(){ location.reload(); }, 1000);
}

/* ── 配置重置 ── */
function resetConfig(){
  showDeleteConfirm(t('confirmReset'), function(){
    var savedKey = localStorage.getItem('agency_api_key');
    var savedProvider = localStorage.getItem('agency_api_provider');
    localStorage.clear();
    if(savedKey) localStorage.setItem('agency_api_key', savedKey);
    if(savedProvider) localStorage.setItem('agency_api_provider', savedProvider);
    showToast(t('resetDone'));
    setTimeout(function(){ location.reload(); }, 800);
  });
}

/* ── 清空全部对话历史 ── */
function clearAllHistory(){
  showDeleteConfirm(t('clearAllHistoryConfirm'), function(){
    var savedConvos = conversations.slice();
    var savedLocal = localStorage.getItem('agency_convos');
    conversations = [];
    localStorage.setItem('agency_convos', '[]');
    // 清空所有面板
    panels.forEach(function(p){
      if(p.isStreaming && p.abortController) p.abortController.abort();
      p.currentConvo = {id: Date.now(), title: '', messages: [], sessionId: ''};
      p.dom.messages.innerHTML = '<div class="empty-panel"><div class="logo">👋</div><h3>' + t('chatEmptyTitle') + '</h3><div class="empty-state-actions"><button class="btn quick-action" onclick="quickAction('+p.id+',1)">'+t('chatEmptyBtn1')+'</button><button class="btn quick-action" onclick="quickAction('+p.id+',2)">'+t('chatEmptyBtn2')+'</button><button class="btn quick-action" onclick="quickAction('+p.id+',3)">'+t('chatEmptyBtn3')+'</button></div></div>';
      p.dom.route.innerHTML = '<span style="color:var(--muted);font-size:9px">' + t('routeEmpty') + '</span>';
      p.dom.agentName.textContent = '就绪';
    });
    if(typeof renderHistory === 'function') renderHistory();
    showUndoableToast(t('clearAllHistoryDone'), function(){
      conversations = savedConvos;
      localStorage.setItem('agency_convos', savedLocal || '[]');
      renderHistory();
    }, 5000);
  });
}

/* ── 全局 Agent 粘性 ── */
function renderStickyAgentDropdown(containerEl){
  if(!containerEl) return;
  var list = (typeof agents !== 'undefined' ? agents : []);
  if(typeof _demoMode !== 'undefined' && _demoMode) list = getDemoAgents();
  var cur = localStorage.getItem('sticky_agent') || '';
  var html = '<p style="font-size:10px;color:var(--muted);margin-bottom:6px">' + t('stickyAgentDesc') + '</p>';
  html += '<select class="proj-input" id="sticky-agent-select" onchange="setStickyAgent(this.value)" style="width:100%;margin-bottom:4px">';
  html += '<option value="">' + t('stickyAgentNone') + '</option>';
  list.forEach(function(a){
    html += '<option value="' + escAttr(a.name) + '"' + (cur === a.name ? ' selected' : '') + '>' + escHtml(a.name) + '</option>';
  });
  html += '</select>';
  containerEl.innerHTML = html;
}

function setStickyAgent(name){
  if(name){
    localStorage.setItem('sticky_agent', name);
  } else {
    localStorage.removeItem('sticky_agent');
  }
  showToast(t('configSaved'));
}

/* ── 自定义快捷键编辑器 ── */
function renderShortcutEditor(containerEl){
  if(!containerEl) return;
  var custom = {};
  try{ custom = JSON.parse(localStorage.getItem('custom_shortcuts') || '{}'); }catch(e){}
  var html = '<div style="max-height:400px;overflow-y:auto">';
  for(var i=0; i<KEYBOARD_SHORTCUTS.length; i++){
    var ks = KEYBOARD_SHORTCUTS[i];
    var actionId = ks.action;
    var curKeys = custom[actionId] || ks.keys;
    html += '<div class="shortcut-row" style="display:flex;align-items:center;gap:8px;padding:8px 10px;margin-bottom:4px;background:var(--surface2);border-radius:var(--radius)">';
    html += '<span style="flex:1;font-size:11px;color:var(--text)">' + escHtml(ks.desc) + '</span>';
    html += '<code class="shortcut-keys" style="background:var(--bg);padding:2px 8px;border-radius:4px;font-size:11px;font-family:JetBrains Mono,monospace;color:var(--accent);min-width:80px;text-align:center;cursor:pointer" onclick="captureShortcutKey(\'' + escAttr(actionId) + '\', this)" data-action="' + escAttr(actionId) + '">' + escHtml(curKeys) + '</code>';
    html += '<button class="btn" style="font-size:10px;padding:3px 8px" onclick="captureShortcutKey(\'' + escAttr(actionId) + '\', this.parentNode.querySelector(\'.shortcut-keys\'))">' + t('editShortcut') + '</button>';
    html += '</div>';
  }
  html += '</div>';
  html += '<button class="btn" onclick="resetShortcuts()" style="margin-top:8px;font-size:11px;padding:6px 12px;color:var(--danger);border-color:var(--danger)">' + t('resetShortcuts') + '</button>';
  containerEl.innerHTML = html;
}

function captureShortcutKey(actionId, displayEl){
  var overlay = document.createElement('div');
  overlay.className = 'confirm-overlay';
  overlay.innerHTML = '<div class="confirm-box" style="text-align:center"><p style="font-size:14px;margin-bottom:8px">' + t('pressNewShortcut') + '</p><p style="font-size:11px;color:var(--muted);margin-bottom:12px">' + t('shortcutCapture') + '</p><div class="btn-row"><button class="btn btn-cancel" id="shortcut-capture-cancel">' + t('cancel') + '</button></div></div>';
  document.body.appendChild(overlay);

  var cancelBtn = overlay.querySelector('#shortcut-capture-cancel');
  function closeCapture(){
    overlay.remove();
    document.removeEventListener('keydown', handler);
  }
  cancelBtn.addEventListener('click', closeCapture);
  overlay.addEventListener('click', function(e){ if(e.target === overlay) closeCapture(); });

  function handler(e){
    if(e.key === 'Escape'){ closeCapture(); return; }
    if(e.key === 'Control' || e.key === 'Shift' || e.key === 'Alt' || e.key === 'Meta') return;
    e.preventDefault();
    var parts = [];
    if(e.ctrlKey || e.metaKey) parts.push('Ctrl');
    if(e.altKey) parts.push('Alt');
    if(e.shiftKey) parts.push('Shift');
    var key = e.key;
    if(key === ' ') key = 'Space';
    else if(key.length === 1) key = key.toUpperCase();
    else if(key === 'ArrowUp') key = '↑';
    else if(key === 'ArrowDown') key = '↓';
    else if(key === 'ArrowLeft') key = '←';
    else if(key === 'ArrowRight') key = '→';
    parts.push(key);
    var newKeys = parts.join('+');

    // Conflict detection
    var custom = {};
    try{ custom = JSON.parse(localStorage.getItem('custom_shortcuts') || '{}'); }catch(e){}
    for(var i=0; i<KEYBOARD_SHORTCUTS.length; i++){
      var ks = KEYBOARD_SHORTCUTS[i];
      var existing = custom[ks.action] || ks.keys;
      if(ks.action !== actionId && existing === newKeys){
        showToast(t('shortcutConflict').replace('{key}', newKeys).replace('{action}', ks.desc), true);
        closeCapture();
        return;
      }
    }

    custom[actionId] = newKeys;
    localStorage.setItem('custom_shortcuts', JSON.stringify(custom));
    if(displayEl) displayEl.textContent = newKeys;
    if(typeof updateShortcutBindings === 'function') updateShortcutBindings();
    showToast(t('shortcutSaved'));
    closeCapture();
  }
  document.addEventListener('keydown', handler);
}

function resetShortcuts(){
  showDeleteConfirm(t('shortcutsReset'), function(){
    localStorage.removeItem('custom_shortcuts');
    if(typeof updateShortcutBindings === 'function') updateShortcutBindings();
    showToast(t('shortcutsReset'));
    if(typeof loadAllSettingsPanels === 'function') loadAllSettingsPanels();
  });
}
