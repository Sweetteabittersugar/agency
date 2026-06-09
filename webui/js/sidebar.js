/* Agency — Agent + Skills + 历史 侧边栏 */
var currentPromptAgent='';
var allSkills=[];
async function loadAgents(){
  agentList.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载中…</div>';
  try{agents=await(await fetch('/api/agents')).json();renderAgents(agents)}catch(e){agentList.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">无法加载 Agent 列表。服务可能未启动，请刷新页面重试</div>'}
}
function renderAgents(list){agentList.innerHTML=list.map(function(a){var ns=a.name.replace(/'/g,"\\'"),nh=escHtml(a.name);return'<div class="agent-card" onclick="pickAgent(\''+ns+'\')" oncontextmenu="pickAgentNew(\''+ns+'\',event)"><div style="display:flex;justify-content:space-between;align-items:center"><div class="name">'+nh+'<span class="model">'+(a.model||'auto')+'</span></div><div style="display:flex;gap:2px;flex-shrink:0;margin-left:4px"><button class="btn" style="font-size:10px;padding:1px 5px" onclick="event.stopPropagation();viewAgentPrompt(\''+ns+'\')" title="查看/编辑提示词">📝</button><button class="btn" style="font-size:10px;padding:1px 5px;color:var(--danger)" onclick="event.stopPropagation();deleteAgent(\''+ns+'\')" title="删除 Agent">🗑</button></div></div><div class="desc">'+escHtml(a.description||'')+'</div>'+(a.keywords&&a.keywords.length?'<div class="kw">'+a.keywords.slice(0,5).join(', ')+'</div>':'')+(a.tools&&a.tools.length?'<div class="kw" style="margin-top:2px">'+a.tools.slice(0,6).map(function(t){return'<span class="tool-tag">'+escHtml(t)+'</span>'}).join('')+'</div>':'')+'</div>'}).join('')}
function deleteAgent(name){if(!confirm('确认删除 Agent "'+name+'"？此操作不可撤销。'))return;fetch('/api/agent-delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('Agent 已删除: '+name);loadAgents()}else showToast(d.error||'删除失败',!0)}).catch(function(e){showToast('删除失败: '+e.message,!0)})}
function viewAgentPrompt(name){currentPromptAgent=name;$('apm-title').textContent='编辑: '+name;$('apm-textarea').value='加载中…';$('agentPromptOverlay').classList.add('on');fetch('/api/agents/'+encodeURIComponent(name)).then(function(r){return r.json()}).then(function(d){if(d.error){showToast(d.error,!0);return}$('apm-textarea').value=d.content}).catch(function(e){showToast('无法加载 Agent 内容: '+(e.message||'请检查网络连接后刷新重试'),!0)})}
function closeAgentPrompt(){$('agentPromptOverlay').classList.remove('on');currentPromptAgent=''}
function saveAgentPrompt(){var content=$('apm-textarea').value;if(!currentPromptAgent||!content)return;fetch('/api/agent-update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:currentPromptAgent,content:content})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('已保存: '+currentPromptAgent);closeAgentPrompt();loadAgents()}else{showToast(d.error||'保存失败，请检查文件权限或磁盘空间后重试',!0)}}).catch(function(e){showToast('保存失败: '+(e.message||'请检查网络连接后重试'),!0)})}
function loadSidebarSkills(){
  var domEl=$('sidebar-skills-list');if(!domEl)return;
  domEl.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载中…</div>';
  fetch('/api/skills').then(function(r){return r.json()}).then(function(skills){
    allSkills=skills||[];
    renderSidebarSkills(allSkills);
  }).catch(function(){domEl.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">无法加载 Skills 列表。服务可能未启动，请刷新页面重试</div>'});
}
function renderSidebarSkills(skills){
  var domEl=$('sidebar-skills-list');if(!domEl)return;
  domEl.innerHTML=skills.length?skills.map(function(s){
    var ns=s.name.replace(/'/g,"\\'");
    return'<div class="skill-card" onclick="viewSkillDetail(\''+ns+'\')" style="padding:8px 10px;margin-bottom:4px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px;transition:background .15s;cursor:pointer">'+
      '<div style="font-weight:600;color:var(--text)">'+escHtml(s.name)+'</div>'+
      '<div style="font-size:10px;color:var(--muted);margin-top:2px">'+escHtml((s.description||'').slice(0,80))+'</div>'+
    '</div>';
  }).join(''):'<div style="color:var(--muted);font-size:12px;padding:8px">暂无 Skills</div>';
}
function renderHistory(){historyList.innerHTML=conversations.slice(0,30).map(function(c){return'<div class="history-item" onclick="loadConvo(\''+c.id+'\')"><div style="display:flex;align-items:center"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">'+escHtml(c.title||'新对话')+'</span><button class="del-btn" onclick="delConvo(\''+c.id+'\',event)">×</button></div><div class="time">'+new Date(c.id).toLocaleDateString('zh-CN')+'</div><div class="preview">'+escHtml((c.messages[0]&&c.messages[0].content||'').slice(0,30))+'</div></div>'}).join('')||'<div style="color:var(--muted);font-size:12px;padding:8px">暂无历史</div>'}
function loadConvo(id){var c=conversations.find(function(x){return x.id===Number(id)});if(!c)return;var p=getFocusedPanel();p.currentConvo={id:c.id,title:c.title,messages:c.messages.slice(),sessionId:c.sessionId||''};p.dom.messages.innerHTML='';p.dom.route.innerHTML='';c.messages.forEach(function(m){addMsg(p,m.role,m.content)});p.dom.messages.scrollTop=p.dom.messages.scrollHeight;setTimeout(function(){p.dom.messages.querySelectorAll('.bubble').forEach(highlightCode)},100)}
function delConvo(id,e){e.stopPropagation();if(!confirm('永久删除此对话？\n\n对话将从本地存储中移除，不可恢复。'))return;conversations=conversations.filter(function(c){return c.id!==Number(id)});localStorage.setItem('agency_convos',JSON.stringify(conversations));renderHistory()}
function viewSkillDetail(name){
  var skill=allSkills.find(function(s){return s.name===name});
  if(!skill)return;
  var ov=$('agentPromptOverlay');
  var title=$('apm-title');
  var body=$('apm-body');
  var footer=$('apm-footer');

  title.textContent='Skill: '+name;

  fetch('/api/skills/content/'+name).then(function(r){return r.json()}).then(function(d){
    body.innerHTML=
      '<div style="margin-bottom:12px">'+
      '<p style="font-size:11px"><b>描述：</b>'+escHtml(skill.description||'无')+'</p>'+
      '<p style="font-size:11px"><b>分类：</b>'+escHtml(skill.category||'未分类')+'</p>'+
      '<p style="font-size:11px"><b>状态：</b>'+(skill.enabled?'✅ 已启用':'❌ 已禁用')+'</p>'+
      '</div>'+
      '<p style="font-size:11px;color:var(--muted);margin-bottom:4px">📝 编辑源码：</p>'+
      '<textarea id="skill-editor" style="width:100%;min-height:280px;max-height:55vh;background:var(--bg);border:1px solid var(--border2);border-radius:var(--radius);color:var(--text);font-size:11px;padding:10px;font-family:JetBrains Mono,monospace;outline:none;resize:vertical;line-height:1.5">'+escHtml(d.content||'')+'</textarea>';

    footer.innerHTML=
      '<button class="new-chat-btn" onclick="toggleSkill(\''+name+'\','+(!skill.enabled)+')" style="width:auto;font-size:11px;padding:6px 14px">'+(skill.enabled?'禁用':'启用')+'</button>'+
      '<button class="btn primary" onclick="saveSkillSource(\''+name+'\')" style="width:auto;font-size:11px;padding:6px 14px">💾 保存</button>'+
      '<button class="btn" onclick="deleteSkillDetail(\''+name+'\')" style="width:auto;font-size:11px;padding:6px 14px;color:var(--danger);border-color:var(--danger)">🗑 删除</button>'+
      '<button class="btn" onclick="closeAgentPrompt()" style="width:auto">关闭</button>';

    ov.classList.add('on');
  }).catch(function(){
    body.innerHTML='<p style="color:var(--muted)">无法加载 Skill 源码</p>';
    footer.innerHTML='<button class="btn" onclick="closeAgentPrompt()">关闭</button>';
    ov.classList.add('on');
  });
}
function saveSkillSource(name){
  var content=document.getElementById('skill-editor').value;
  fetch('/api/skills/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,content:content})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.ok){showToast('已保存: '+name);closeAgentPrompt()}else showToast(d.error||'保存失败，请检查文件权限或磁盘空间后重试',!0);
    }).catch(function(e){showToast('保存失败: '+(e.message||'请检查网络连接后重试'),!0)});
}
function toggleSkill(name,enabled){
  fetch('/api/skills/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,enabled:enabled})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.ok){showToast('Skill '+(enabled?'已启用':'已禁用')+': '+name);loadSidebarSkills();viewSkillDetail(name)}
      else showToast(d.error||'Skill 操作失败，请检查配置后重试',!0);
    }).catch(function(e){showToast('Skill 操作失败: '+(e.message||'请检查网络连接后重试'),!0)});
}
function deleteSkillDetail(name){
  if(!confirm('确认删除 Skill "'+name+'"？此操作不可撤销。'))return;
  fetch('/api/skills/'+encodeURIComponent(name),{method:'DELETE'})
    .then(function(r){return r.json()}).then(function(d){
      if(d.ok){showToast('Skill 已删除: '+name);closeAgentPrompt();loadSidebarSkills()}
      else showToast(d.error||'删除失败，可能文件被占用或权限不足，请检查后重试',!0);
    }).catch(function(e){showToast('删除失败: '+(e.message||'请检查网络连接后重试'),!0)});
}

/* ── 路由选择器：用户手动换 Agent ── */
function showRoutePicker(pid) {
  var p = panels.find(function(x){ return x.id === pid; });
  if (!p) return;

  var overlay = document.createElement('div');
  overlay.className = 'agent-prompt-overlay';
  overlay.id = 'routePickerOverlay';
  overlay.style.display = 'flex';

  var lastUserMsg = '';
  var msgs = p.currentConvo.messages || [];
  for (var i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'user') { lastUserMsg = msgs[i].content; break; }
  }

  var html = '<div class="agent-prompt-modal" style="width:420px;max-height:70vh;overflow-y:auto">' +
    '<div class="apm-header"><span>选择 Agent 处理此任务</span><button class="btn" onclick="document.getElementById(\'routePickerOverlay\').remove()">✕</button></div>' +
    '<div class="apm-body" style="max-height:50vh;overflow-y:auto">' +
    '<p style="font-size:10px;color:var(--muted);margin-bottom:8px">任务: ' + escHtml(lastUserMsg.slice(0, 80)) + '</p>';

  if (typeof agents !== 'undefined' && agents.length) {
    html += agents.map(function(a) {
      var ns = a.name.replace(/'/g, "\'");
      return '<div class="agent-card" onclick="pickAgentForRoute(\'' + ns + '\',' + pid + ')" style="cursor:pointer;padding:8px;margin-bottom:4px;background:var(--surface2);border-radius:var(--radius-sm)">' +
        '<div style="font-weight:600;font-size:12px;color:var(--text)">' + escHtml(a.name) + '</div>' +
        '<div style="font-size:10px;color:var(--muted);margin-top:2px">' + escHtml((a.description||'').slice(0,100)) + '</div>' +
      '</div>';
    }).join('');
  } else {
    html += '<div style="color:var(--muted);font-size:12px">Agent 列表未加载</div>';
  }

  html += '</div></div>';
  overlay.innerHTML = html;
  document.body.appendChild(overlay);

  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) overlay.remove();
  });
}

function pickAgentForRoute(agentName, pid) {
  var overlay = document.getElementById('routePickerOverlay');
  if (overlay) overlay.remove();

  var p = panels.find(function(x){ return x.id === pid; });
  if (!p) return;

  var lastUserMsg = '';
  var msgs = p.currentConvo.messages || [];
  for (var i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'user') { lastUserMsg = msgs[i].content; break; }
  }
  if (!lastUserMsg) {
    lastUserMsg = p.dom.input.value || '请执行任务';
  }

  lastUserMsg = lastUserMsg.replace(/^@\S+\s*/, '');

  p.dom.input.value = '@' + agentName + ' ' + lastUserMsg;
  stopStream(pid);
  setStreaming(p, false);
  setTimeout(function(){ handleSend(pid); }, 200);
}
