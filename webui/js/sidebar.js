/* Agency — Agent + Skills + 历史 侧边栏 */
var currentPromptAgent='';
async function loadAgents(){
  agentList.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载中…</div>';
  try{agents=await(await fetch('/api/agents')).json();renderAgents(agents)}catch(e){agentList.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载失败</div>'}
}
function renderAgents(list){agentList.innerHTML=list.map(function(a){var ns=a.name.replace(/'/g,"\\'"),nh=escHtml(a.name);return'<div class="agent-card" onclick="pickAgent(\''+ns+'\')" oncontextmenu="pickAgentNew(\''+ns+'\',event)"><div style="display:flex;justify-content:space-between;align-items:center"><div class="name">'+nh+'<span class="model">'+(a.model||'auto')+'</span></div><div style="display:flex;gap:2px;flex-shrink:0;margin-left:4px"><button class="btn" style="font-size:10px;padding:1px 5px" onclick="event.stopPropagation();viewAgentPrompt(\''+ns+'\')" title="查看/编辑提示词">📝</button><button class="btn" style="font-size:10px;padding:1px 5px;color:var(--danger)" onclick="event.stopPropagation();deleteAgent(\''+ns+'\')" title="删除 Agent">🗑</button></div></div><div class="desc">'+escHtml(a.description||'')+'</div>'+(a.keywords&&a.keywords.length?'<div class="kw">'+a.keywords.slice(0,5).join(', ')+'</div>':'')+(a.tools&&a.tools.length?'<div class="kw" style="margin-top:2px">'+a.tools.slice(0,6).map(function(t){return'<span class="tool-tag">'+escHtml(t)+'</span>'}).join('')+'</div>':'')+'</div>'}).join('')}
function deleteAgent(name){if(!confirm('确认删除 Agent "'+name+'"？此操作不可撤销。'))return;fetch('/api/agent-delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('Agent 已删除: '+name);loadAgents()}else showToast(d.error||'删除失败',!0)}).catch(function(e){showToast('删除失败: '+e.message,!0)})}
function viewAgentPrompt(name){currentPromptAgent=name;$('apm-title').textContent='编辑: '+name;$('apm-textarea').value='加载中…';$('agentPromptOverlay').classList.add('on');fetch('/api/agents/'+encodeURIComponent(name)).then(function(r){return r.json()}).then(function(d){if(d.error){showToast(d.error,!0);return}$('apm-textarea').value=d.content}).catch(function(){showToast('加载失败',!0)})}
function closeAgentPrompt(){$('agentPromptOverlay').classList.remove('on');currentPromptAgent=''}
function saveAgentPrompt(){var content=$('apm-textarea').value;if(!currentPromptAgent||!content)return;fetch('/api/agent-update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:currentPromptAgent,content:content})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('已保存: '+currentPromptAgent);closeAgentPrompt();loadAgents()}else{showToast(d.error||'保存失败',!0)}}).catch(function(){showToast('保存失败',!0)})}
function loadSidebarSkills(){
  var domEl=$('sidebar-skills-list');if(!domEl)return;
  domEl.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载中…</div>';
  fetch('/api/skills').then(function(r){return r.json()}).then(function(skills){
    renderSidebarSkills(skills||[]);
  }).catch(function(){domEl.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载失败</div>'});
}
function renderSidebarSkills(skills){
  var domEl=$('sidebar-skills-list');if(!domEl)return;
  domEl.innerHTML=skills.length?skills.map(function(s){
    return'<div style="padding:8px 10px;margin-bottom:4px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px;transition:background .15s;cursor:default">'+
      '<div style="font-weight:600;color:var(--text)">'+escHtml(s.name)+'</div>'+
      '<div style="font-size:10px;color:var(--muted);margin-top:2px">'+escHtml((s.description||'').slice(0,80))+'</div>'+
    '</div>';
  }).join(''):'<div style="color:var(--muted);font-size:12px;padding:8px">暂无 Skills</div>';
}
function renderHistory(){historyList.innerHTML=conversations.slice(0,30).map(function(c){return'<div class="history-item" onclick="loadConvo(\''+c.id+'\')"><div style="display:flex;align-items:center"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">'+escHtml(c.title||'新对话')+'</span><button class="del-btn" onclick="delConvo(\''+c.id+'\',event)">×</button></div><div class="time">'+new Date(c.id).toLocaleDateString('zh-CN')+'</div><div class="preview">'+escHtml((c.messages[0]&&c.messages[0].content||'').slice(0,30))+'</div></div>'}).join('')||'<div style="color:var(--muted);font-size:12px;padding:8px">暂无历史</div>'}
function loadConvo(id){var c=conversations.find(function(x){return x.id===Number(id)});if(!c)return;var p=getFocusedPanel();p.currentConvo={id:c.id,title:c.title,messages:c.messages.slice(),sessionId:c.sessionId||''};p.dom.messages.innerHTML='';p.dom.route.innerHTML='';c.messages.forEach(function(m){addMsg(p,m.role,m.content)});p.dom.messages.scrollTop=p.dom.messages.scrollHeight;setTimeout(function(){p.dom.messages.querySelectorAll('.bubble').forEach(highlightCode)},100)}
function delConvo(id,e){e.stopPropagation();conversations=conversations.filter(function(c){return c.id!==Number(id)});localStorage.setItem('agency_convos',JSON.stringify(conversations));renderHistory()}
