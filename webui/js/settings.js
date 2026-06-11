/* Agency — 开发者设置面板 */
function saveApiKey(){var newKey=$('api-key').value.trim();var newProvider=$('api-provider').value;var oldKey=apiKey;var oldProvider=apiProvider;apiKey=newKey;apiProvider=newProvider;localStorage.setItem('agency_api_provider',apiProvider);window.apiKey=apiKey;$('api-status').textContent=apiKey?'已保存（仅内存，刷新后需重输）':'已清除';showUndoableToast(t('configSaved'),function(){apiKey=oldKey;apiProvider=oldProvider;localStorage.setItem('agency_api_provider',oldProvider);window.apiKey=oldKey;$('api-key').value=oldKey;$('api-provider').value=oldProvider;$('api-status').textContent=oldKey?'已保存（仅内存，刷新后需重输）':'已清除'},5000)}
function toggleDevOverlay(){devMode=!devMode;var ov=$('devOverlay'),btn=$('devBtn');ov.classList.toggle('on',devMode);btn.classList.toggle('on',devMode);if(devMode){var ak=$('api-key');if(ak&&apiKey)ak.value=apiKey;var ap=$('api-provider');if(ap&&apiProvider)ap.value=apiProvider;loadMemList();loadRemotePanel();loadIntegrationPanel();loadMCPConfig();setTimeout(initSettingsAccordion,200)}}

/* ── 设置面板折叠分组 ── */
var _settingsAccordionDone=false;
function initSettingsAccordion(){
  if(_settingsAccordionDone)return;
  var container=document.querySelector('#devOverlay .harness-overlay-content');
  if(!container)return;
  var sections=container.querySelectorAll('.settings-section');
  if(!sections.length)return;

  // 分组映射：h3 文本关键词 -> group key
  var groupMap={
    'API Key':'api','MCP':'api','集成':'api','远端':'api',
    '主题':'appearance','Profile':'appearance',
    '信任模式':'security','功能解锁':'security',
    '记忆':'data','输出目录':'data','配置管理':'data','恢复默认':'data','清空':'data','快捷键':'data','默认 Agent':'data'
  };
  var groups={api:{icon:'🔑',title:'API 与 Provider',sections:[]},appearance:{icon:'🎨',title:'外观',sections:[]},security:{icon:'🛡️',title:'安全',sections:[]},data:{icon:'💾',title:'数据管理',sections:[]}};
  var uncategorized=[];

  // 先分类、同时从 DOM 分离
  var secArr=Array.prototype.slice.call(sections);
  secArr.forEach(function(sec){
    sec.remove();
    var h3=sec.querySelector('h3');
    var title=h3?h3.textContent.trim():'';
    var cleanTitle=title.replace(/^[^一-龥a-zA-Z]+/,'');
    var matched=false;
    for(var k in groupMap){
      if(cleanTitle.indexOf(k)===0){groups[groupMap[k]].sections.push(sec);matched=true;break}
    }
    if(!matched)uncategorized.push(sec);
  });

  // 构建折叠组 HTML
  var wrapper=document.createElement('div');
  var groupKeys=['api','appearance','security','data'];
  groupKeys.forEach(function(key){
    var g=groups[key];
    if(!g.sections.length)return;
    var groupDiv=document.createElement('div');
    groupDiv.className='settings-group';
    groupDiv.innerHTML='<div class="settings-group-header"><span class="settings-group-icon">▼</span> '+g.icon+' '+g.title+'</div><div class="settings-group-body"></div>';
    var body=groupDiv.querySelector('.settings-group-body');
    g.sections.forEach(function(sec){body.appendChild(sec)});
    var header=groupDiv.querySelector('.settings-group-header');
    header.addEventListener('click',function(){
      this.parentNode.classList.toggle('collapsed');
    });
    wrapper.appendChild(groupDiv);
  });

  // Agent 工厂、Skills 保持原样追加（未归组）
  uncategorized.forEach(function(sec){wrapper.appendChild(sec)});

  // 挂到容器最前面（resize-handle 保持原位）
  container.insertBefore(wrapper,container.firstChild);
  _settingsAccordionDone=true;
}

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

/* ── Profile 选择器（设置面板专用）── */
function showProfilePicker(){
  // 在设置面板打开时刷新 profile 列表
  fetch('/api/profile').then(function(r){return r.json()}).then(function(d){
    var sel = document.getElementById('profile-select');
    var profiles = d.profiles || {};
    var keys = Object.keys(profiles);
    if(!keys.length) keys = ['minimal','standard','full'];
    if(sel){
      sel.innerHTML = keys.map(function(k){
        var p = profiles[k] || {};
        var label = PROFILE_LABELS[k] || k;
        var icon = PROFILE_ICONS[k] || '';
        return '<option value="'+escHtml(k)+'">'+icon+' '+escHtml(label)+' — '+escHtml(p.description||p.trigger||k)+'</option>';
      }).join('');
      sel.value = agencyProfile;
    }
    // 同步加载描述文字
    if(typeof loadedProfileDescriptions !== 'undefined'){
      loadedProfileDescriptions = {};
      keys.forEach(function(k){
        loadedProfileDescriptions[k] = (profiles[k]||{}).description || (typeof PROFILE_DESC_FALLBACK !== 'undefined' ? PROFILE_DESC_FALLBACK[k] : '') || '';
      });
      if(typeof updateProfileUI === 'function') updateProfileUI();
    }
  }).catch(function(){});
}

/* ── Key 可见性切换 ── */
function toggleKeyVisibility(){var inp=$('api-key');var btn=$('key-toggle-btn');if(inp.type==='password'){inp.type='text';btn.textContent='🙈'}else{inp.type='password';btn.textContent='👁'}}

/* ── Provider 切换提示 ── */
function onProviderChange(){showToast(t('providerSwitchWarn'),false,'warn',3000)}

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

/* ── 恢复默认 ── */
function renderResetSection(container) {
  fetch('/api/reset/status')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var html = '<div style="padding:8px 0;">';

      html += '<h4 style="margin:0 0 8px;font-size:13px;">用户自定义</h4>';
      html += '<p style="color:var(--muted);font-size:11px;margin:0 0 10px;">删除 user/ 目录下的自定义内容。系统文件不受影响。</p>';

      var customs = data.user_customizations || {};
      var agents = customs.agents || [];
      var skills = customs.skills || [];

      if (agents.length + skills.length === 0) {
        html += '<p style="color:var(--muted);font-size:11px;padding:8px;background:var(--bg);border-radius:4px;">暂无用户自定义内容</p>';
      } else {
        if (agents.length > 0) {
          html += '<div style="margin-bottom:6px;font-size:12px;font-weight:600;">自定义 Agent (' + agents.length + ')</div>';
          agents.forEach(function(a) {
            html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:5px 8px;margin-bottom:3px;background:var(--bg);border-radius:4px;">';
            html += '<span style="font-size:11px;">' + escHtml(a.name) + ' <span style="color:var(--muted);">(' + a.size_kb + 'KB)</span></span>';
            html += '<button onclick="window.resetUserFile(\'' + escAttr(a.path) + '\')" style="padding:2px 8px;background:#e74c3c;color:#fff;border:none;border-radius:3px;cursor:pointer;font-size:10px;">删除</button>';
            html += '</div>';
          });
        }

        if (skills.length > 0) {
          html += '<div style="margin:10px 0 6px;font-size:12px;font-weight:600;">自定义 Skill (' + skills.length + ')</div>';
          skills.forEach(function(s) {
            html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:5px 8px;margin-bottom:3px;background:var(--bg);border-radius:4px;">';
            html += '<span style="font-size:11px;">' + escHtml(s.name) + ' <span style="color:var(--muted);">(' + s.size_kb + 'KB)</span></span>';
            html += '<button onclick="window.resetUserFile(\'' + escAttr(s.path) + '\')" style="padding:2px 8px;background:#e74c3c;color:#fff;border:none;border-radius:3px;cursor:pointer;font-size:10px;">删除</button>';
            html += '</div>';
          });
        }

        html += '<button onclick="window.resetUserAll()" style="margin-top:10px;padding:7px 18px;background:#e74c3c;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;">🗑 清空所有自定义</button>';
      }

      html += '<hr style="margin:16px 0;border-color:var(--border);">';
      html += '<h4 style="margin:0 0 8px;font-size:13px;">恢复系统默认</h4>';
      html += '<p style="color:var(--muted);font-size:11px;margin:0 0 10px;">将系统 Agent/Skill 恢复到初始版本（需要 git）。</p>';

      var sysCats = data.system_categories || {};
      var agentCats = sysCats.agents || [];
      var skillCats = sysCats.skills || [];

      if (agentCats.length > 0) {
        html += '<div style="margin-bottom:6px;font-size:12px;font-weight:600;">Agent 分类</div>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;">';
        agentCats.forEach(function(cat) {
          html += '<button onclick="window.resetSystemCategory(\'' + escAttr(cat) + '\',\'agents\')" style="padding:5px 12px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;cursor:pointer;font-size:11px;">' + escHtml(cat) + ' ↩</button>';
        });
        html += '</div>';
      }

      if (skillCats.length > 0) {
        html += '<div style="margin-bottom:6px;font-size:12px;font-weight:600;">Skill 分类</div>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;">';
        skillCats.forEach(function(cat) {
          html += '<button onclick="window.resetSystemCategory(\'' + escAttr(cat) + '\',\'skills\')" style="padding:5px 12px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;cursor:pointer;font-size:11px;">' + escHtml(cat) + ' ↩</button>';
        });
        html += '</div>';
      }

      html += '<hr style="margin:16px 0;border-color:var(--border);">';
      html += '<h4 style="margin:0 0 6px;color:#e74c3c;font-size:13px;">⚠️ 全量恢复出厂设置</h4>';
      html += '<p style="color:var(--muted);font-size:11px;margin:0 0 10px;">清空所有用户自定义 + 恢复所有系统文件到默认。此操作不可撤销。</p>';
      html += '<button onclick="window.fullReset()" style="padding:9px 22px;background:#e74c3c;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;">⚠️ 恢复出厂设置</button>';

      html += '</div>';
      container.innerHTML = html;
    })
    .catch(function() {
      container.innerHTML = '<p style="color:var(--muted);padding:8px;">加载失败，请检查服务是否运行</p>';
    });
}

window.resetUserFile = function(path) {
  if (!confirm('确认删除自定义文件？系统默认版本不受影响。')) return;
  fetch('/api/reset/user-file', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({path: path})
  })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.ok) {
        showToast('已删除', false, 'success');
        var container = document.getElementById('reset-container');
        if (container) renderResetSection(container);
      } else {
        showToast('删除失败: ' + (data.error || '未知'), true);
      }
    });
};

window.resetUserAll = function() {
  if (!confirm('确认清空所有用户自定义内容？此操作不可撤销。')) return;
  fetch('/api/reset/user-all', {method: 'POST'})
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.ok) {
        showToast('已清空 ' + data.count + ' 个自定义文件', false, 'success');
        var container = document.getElementById('reset-container');
        if (container) renderResetSection(container);
      }
    });
};

window.resetSystemCategory = function(category, type) {
  if (!confirm('确认恢复 ' + category + ' 到默认版本？任何修改将丢失。')) return;
  fetch('/api/reset/system-category', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({category: category, type: type})
  })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.ok) {
        showToast('已恢复: ' + category, false, 'success');
      } else {
        showToast('恢复失败: ' + (data.error || '未知'), true);
      }
    });
};

window.fullReset = function() {
  if (!confirm('⚠️ 确认恢复出厂设置？\n\n这将：\n1. 清空所有用户自定义 Agent/Skill\n2. 恢复所有系统文件到默认\n\n此操作不可撤销！')) return;
  fetch('/api/reset/full', {method: 'POST'})
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.ok) {
        showToast('已恢复出厂设置。建议重启 Agency。', false, 'success', 5000);
        location.reload();
      } else if (data.issues) {
        showToast('无法恢复出厂设置: ' + data.issues.join('; '), true);
      } else {
        showToast('恢复失败: ' + (data.error || '未知'), true);
      }
    });
};

export { saveApiKey, toggleDevOverlay, initSettingsAccordion,
         loadMemList, loadRemotePanel, loadIntegrationPanel, loadMCPConfig };
