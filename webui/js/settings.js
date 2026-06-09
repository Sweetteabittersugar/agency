/* Agency — 开发者设置面板 */
function saveApiKey(){apiKey=$('api-key').value.trim();apiProvider=$('api-provider').value;localStorage.setItem('agency_api_key',apiKey);localStorage.setItem('agency_api_provider',apiProvider);$('api-status').textContent=apiKey?'已保存':'已清除';if(!apiKey){localStorage.removeItem('agency_api_key');localStorage.removeItem('agency_api_provider')}}
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
