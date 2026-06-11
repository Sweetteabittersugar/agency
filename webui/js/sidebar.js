/* Agency — Agent + Skills + 历史 侧边栏 */
var currentPromptAgent='';
var allSkills=[];
var _multiSelectMode = false;
var _selectedAgents = {};
var STARTER_AGENTS = ['coder', 'explorer', 'general-worker', 'orchestrator'];
var currentNav = 'chat';

/* ── 导航切换 ── */
window.switchNav = function(nav) {
  currentNav = nav;
  document.querySelectorAll('#sidebar-nav .nav-item').forEach(function(el) {
    el.classList.toggle('active', el.getAttribute('data-nav') === nav);
  });
  document.querySelectorAll('#sidebar-content .nav-panel').forEach(function(el) {
    el.style.display = 'none';
  });
  var panel = document.getElementById('nav-' + nav);
  if (panel) panel.style.display = 'block';
  if (nav === 'agents') { loadSidebarAgents(); loadSidebarSkills(); }
  if (nav === 'dashboard') { loadSidebarDashboard(); }
  if (nav === 'connect') { loadSidebarConnect(); }
  try { localStorage.setItem('agency-nav', nav); } catch(e) {}
};

function loadSidebarAgents() {
  if (window.agents && window.agents.length) {
    renderAgents(window.agents);
  } else {
    loadAgents();
  }
}

function loadSidebarDashboard() {
  api.get('/api/cost/summary').then(function(d) {
    var total = d.total_cost || (d.total && d.total.cost) || 0;
    var el = document.getElementById('sidebar-cost-summary');
    if (el) el.innerHTML = '<div style="display:flex;justify-content:space-between;padding:8px;"><span>今日费用</span><strong>$' + Number(total).toFixed(4) + '</strong></div>';
  }).catch(function() {
    var el = document.getElementById('sidebar-cost-summary');
    if (el) el.textContent = '无法加载';
  });
  api.get('/api/operations').then(function(d) {
    var ops = (d.operations || []).slice(0, 3);
    var html = ops.map(function(o) {
      var ts = o.ts || o.timestamp || 0;
      return '<div style="padding:2px 8px;font-size:10px;color:var(--muted);">' +
        new Date(ts * 1000).toLocaleTimeString('zh-CN') + ' ' + escHtml((o.type || '') + ' ' + (o.target || '')).slice(0, 40) + '</div>';
    }).join('');
    var el = document.getElementById('sidebar-ops-summary');
    if (el) el.innerHTML = html || '<div style="padding:8px;color:var(--muted);font-size:11px;">暂无操作</div>';
  }).catch(function() {
    var el = document.getElementById('sidebar-ops-summary');
    if (el) el.textContent = '无法加载';
  });
}

function loadSidebarConnect() {
  api.get('/api/weixin/status').then(function(d) {
    var el = document.getElementById('sidebar-wx-status');
    if (el) el.innerHTML =
      '<span style="color:' + (d.logged_in ? 'var(--success)' : 'var(--muted)') + '">' + (d.logged_in ? '✅ 已连接' : '⚪ 未连接') + '</span>' +
      (d.logged_in ? '' : '<br><a href="#" onclick="toggleDashboard();return false" style="font-size:11px;color:var(--accent);">去登录 →</a>');
  }).catch(function() {
    var el = document.getElementById('sidebar-wx-status');
    if (el) el.textContent = '加载失败';
  });
  api.get('/api/mcp/status').then(function(d) {
    var servers = d.servers || [];
    var el = document.getElementById('sidebar-mcp-status');
    if (el) el.innerHTML = servers.length + ' 个服务器' + (servers.length ? '' : ' (未配置)');
  }).catch(function() {
    var el = document.getElementById('sidebar-mcp-status');
    if (el) el.textContent = '无法加载';
  });
}

/* ── Demo 模式横幅 ── */
function checkDemoBanner() {
  api.get('/api/settings')
    .then(function(config) {
      var hasKey = config.has_api_key;
      var banner = document.getElementById('demo-banner');
      if (!hasKey && banner) {
        banner.style.display = 'block';
      }
    })
    .catch(function() {});
}

window.dismissDemoBanner = function() {
  var banner = document.getElementById('demo-banner');
  if (banner) banner.style.display = 'none';
  try { localStorage.setItem('demo-banner-dismissed', '1'); } catch(e) {}
};

// 页面加载后检测（延迟等 API 就绪）
if (!localStorage.getItem('demo-banner-dismissed')) {
  setTimeout(checkDemoBanner, 1200);
}

function toggleMultiSelect(){
  _multiSelectMode = !_multiSelectMode;
  _selectedAgents = {};
  if(_multiSelectMode){
    renderAgents(agents);
    renderBatchBar();
  } else {
    renderAgents(agents);
    removeBatchBar();
  }
}

function toggleAgentSelect(name, e){
  e.stopPropagation();
  if(_selectedAgents[name]){
    delete _selectedAgents[name];
  } else {
    _selectedAgents[name] = true;
  }
  renderAgents(agents);
  updateBatchBar();
}

function selectAllAgents(){
  if(typeof agents === 'undefined' || !agents.length) return;
  var all = Object.keys(_selectedAgents).length === agents.length;
  if(all){
    _selectedAgents = {};
  } else {
    agents.forEach(function(a){ _selectedAgents[a.name] = true; });
  }
  renderAgents(agents);
  updateBatchBar();
}

function batchDeleteAgents(){
  var names = Object.keys(_selectedAgents);
  if(!names.length) return;
  if(agents.length - names.length < 3){
    showToast(t('minAgents'), false, 'warn');
    return;
  }
  var msg = t('confirmBatchDelete').replace('{n}', names.length);
  showDeleteConfirm(msg, function(){
    var removed = [];
    names.forEach(function(n){
      var agent = agents.find(function(a){ return a.name === n; });
      if(agent){
        var idx = agents.indexOf(agent);
        agents.splice(idx, 1);
        removed.push({agent: agent, idx: idx});
      }
    });
    _selectedAgents = {};
    _multiSelectMode = false;
    renderAgents(agents);
    removeBatchBar();
    showUndoableToast(t('agentDeleted') + ' ' + names.length + ' 个', function(){
      removed.reverse().forEach(function(item){
        agents.splice(item.idx, 0, item.agent);
      });
      renderAgents(agents);
    }, 5000, function(){
      names.forEach(function(n){
        api.post('/api/agent-delete', {name: n}).catch(function(){});
      });
    });
  });
}

function renderBatchBar(){
  var existing = document.getElementById('batch-action-bar');
  if(existing) existing.remove();
  var bar = document.createElement('div');
  bar.id = 'batch-action-bar';
  bar.className = 'batch-action-bar';
  bar.innerHTML = '<span id="batch-count">' + t('batchSelectedCount').replace('{n}', Object.keys(_selectedAgents).length) + '</span>' +
    '<button class="btn" onclick="selectAllAgents()">' + t('batchSelectAll') + '</button>' +
    '<button class="btn danger" onclick="batchDeleteAgents()">' + t('batchDeleteSelected') + '</button>' +
    '<button class="btn" onclick="toggleMultiSelect()">' + t('batchCancel') + '</button>';
  document.body.appendChild(bar);
}

function updateBatchBar(){
  var bar = document.getElementById('batch-action-bar');
  if(!bar) return;
  var span = bar.querySelector('#batch-count');
  if(span) span.textContent = t('batchSelectedCount').replace('{n}', Object.keys(_selectedAgents).length);
}

function removeBatchBar(){
  var bar = document.getElementById('batch-action-bar');
  if(bar) bar.remove();
}

async function loadAgents(){
  if(!isFeatureUnlocked('agents')){
    agentList.innerHTML='<div style="text-align:center;padding:30px 16px;color:var(--muted)"><div style="font-size:28px;margin-bottom:8px">🔒</div><p style="font-size:12px">'+t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS['agents']||1)+'</p></div>';
    return;
  }
  if(typeof _demoMode!=='undefined'&&_demoMode){renderDemoAgentsInSidebar();return}
  agentList.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载中…</div>';
  try{agents=await api.get('/api/agents');renderAgents(agents)}catch(e){agentList.innerHTML='<div class="empty-state"><div class="es-icon">🔌</div><div class="es-text">'+t('agentsLoadFail')+'</div><div class="es-actions"><button class="btn" onclick="loadAgents()">'+t('retry')+'</button><button class="btn" onclick="checkServiceStatus()">'+t('checkService')+'</button></div></div>'}
}
function renderAgents(list){
  // 多选切换按钮
  var multiToggleBtn = _multiSelectMode
    ? '<button class="btn on" onclick="toggleMultiSelect()" style="font-size:10px;padding:3px 8px;margin-bottom:6px;display:block;width:100%">' + t('batchCancel') + '</button>'
    : '<button class="btn" onclick="toggleMultiSelect()" style="font-size:10px;padding:3px 8px;margin-bottom:6px;display:block;width:100%">☑ ' + t('batchSelect') + '</button>';

  // 单卡片渲染
  function cardHTML(a) {
    var ns = a.name.replace(/'/g, "\\'"), nh = escHtml(a.name);
    var isSelected = _multiSelectMode && _selectedAgents[a.name];
    var cardClass = 'agent-card' + (isSelected ? ' agent-selected' : '');
    var checkboxCol = _multiSelectMode
      ? '<div style="flex-shrink:0;margin-right:8px;display:flex;align-items:center"><input type="checkbox" style="accent-color:var(--accent);width:16px;height:16px;cursor:pointer"' + (isSelected ? ' checked' : '') + ' onclick="toggleAgentSelect(\'' + ns + '\',event)"></div>'
      : '';
    var actionBtns = _multiSelectMode
      ? ''
      : '<div style="display:flex;gap:2px;flex-shrink:0;margin-left:4px"><button class="btn" style="font-size:10px;padding:1px 5px" onclick="event.stopPropagation();viewAgentPrompt(\'' + ns + '\')" title="查看/编辑提示词">📝</button><button class="btn" style="font-size:10px;padding:1px 5px;color:var(--danger)" onclick="event.stopPropagation();deleteAgent(\'' + ns + '\')" title="删除 Agent">🗑</button></div>';
    var clickHandler = _multiSelectMode
      ? 'onclick="toggleAgentSelect(\'' + ns + '\',event)"'
      : 'onclick="pickAgent(\'' + ns + '\')" oncontextmenu="pickAgentNew(\'' + ns + '\',event)"';
    return '<div class="' + cardClass + '" ' + clickHandler + '><div style="display:flex;align-items:center">' +
      checkboxCol +
      '<div style="flex:1;min-width:0"><div style="display:flex;justify-content:space-between;align-items:center"><div class="name">' + nh + '<span class="model">' + (a.model || 'auto') + '</span></div>' + actionBtns + '</div>' +
      '<div class="desc">' + escHtml(a.description || '') + '</div>' +
      (a.keywords && a.keywords.length ? '<div class="kw">' + a.keywords.slice(0, 5).join(', ') + '</div>' : '') +
      (a.tools && a.tools.length ? '<div class="kw" style="margin-top:2px">' + a.tools.slice(0, 6).map(function(t) { return '<span class="tool-tag">' + escHtml(t) + '</span>'; }).join('') + '</div>' : '') +
      '</div></div></div>';
  }

  // 分组：推荐 vs 全部
  var starters = list.filter(function(a) { return STARTER_AGENTS.indexOf(a.name) !== -1; });
  var others = list.filter(function(a) { return STARTER_AGENTS.indexOf(a.name) === -1; });
  var collapsed = localStorage.getItem('agent-list-collapsed') === '1';

  var html = multiToggleBtn;
  if (starters.length) {
    html += '<div style="font-size:11px;color:var(--warn);padding:6px 0 4px;">⭐ 推荐</div>';
    html += starters.map(cardHTML).join('');
  }
  if (others.length) {
    html += '<div id="agent-toggle-bar" style="display:flex;align-items:center;padding:8px 0;cursor:pointer;font-size:11px;color:var(--muted);border-top:1px solid var(--border);margin-top:4px;" onclick="toggleAgentList()">';
    html += '<span id="agent-toggle-icon">' + (collapsed ? '▶' : '▼') + '</span> 📂 全部 Agent (' + others.length + ')</div>';
    html += '<div id="agent-full-list" style="display:' + (collapsed ? 'none' : 'block') + ';">';
    html += others.map(cardHTML).join('');
    html += '</div>';
  } else if (!starters.length) {
    html += list.map(cardHTML).join('');
  }

  agentList.innerHTML = html;
}

window.toggleAgentList = function() {
  var list = document.getElementById('agent-full-list');
  var icon = document.getElementById('agent-toggle-icon');
  if (!list || !icon) return;
  var isCollapsed = list.style.display === 'none';
  list.style.display = isCollapsed ? 'block' : 'none';
  icon.textContent = isCollapsed ? '▼' : '▶';
  try { localStorage.setItem('agent-list-collapsed', isCollapsed ? '0' : '1'); } catch(e) {}
};
function renderDemoAgentsInSidebar(){
  var agents=getDemoAgents();
  var html='<div style="padding:4px 0 6px;font-size:10px;color:var(--warn);text-align:center;border-bottom:1px dashed var(--warn);margin-bottom:6px;opacity:.7">⚠ '+t('demoTooltip')+'</div>';
  html+=agents.map(function(a){
    return'<div class="agent-card demo-agent" onclick="showDemoActionPopup(\''+escHtml(a.name)+'\')"><div style="display:flex;justify-content:space-between;align-items:center"><div class="name">'+escHtml(a.name)+'<span class="model">'+(a.model||'auto')+'</span></div></div><div class="desc">'+escHtml(a.description||'')+'</div>'+(a.keywords&&a.keywords.length?'<div class="kw">'+a.keywords.slice(0,5).join(', ')+'</div>':'')+(a.tools&&a.tools.length?'<div class="kw" style="margin-top:2px">'+a.tools.slice(0,6).map(function(t){return'<span class="tool-tag">'+escHtml(t)+'</span>'}).join('')+'</div>':'')+'</div>';
  }).join('');
  agentList.innerHTML=html;
}
function renderDemoSkillsInSidebar(){
  var skills=getDemoSkills();
  var domEl=$('sidebar-skills-list');if(!domEl)return;
  var html='<div style="padding:4px 0 6px;font-size:10px;color:var(--warn);text-align:center;border-bottom:1px dashed var(--warn);margin-bottom:6px;opacity:.7">⚠ '+t('demoTooltip')+'</div>';
  html+=skills.map(function(s){
    return'<div class="skill-card demo-skill" onclick="showDemoActionPopup(\''+escHtml(s.name)+'\')" style="padding:8px 10px;margin-bottom:4px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px;transition:background .15s;cursor:pointer;border:1px dashed var(--border2)">'+
      '<div style="font-weight:600;color:var(--text)">'+escHtml(s.name)+'</div>'+
      '<div style="font-size:10px;color:var(--muted);margin-top:2px">'+escHtml((s.description||'').slice(0,80))+'</div>'+
    '</div>';
  }).join('');
  domEl.innerHTML=html;
}
function renderDemoHistoryInSidebar(){
  var items=getDemoHistory();
  var html='<div style="padding:4px 0 6px;font-size:10px;color:var(--warn);text-align:center;border-bottom:1px dashed var(--warn);margin-bottom:6px;opacity:.7">⚠ '+t('demoTooltip')+'</div>';
  html+=items.map(function(c){
    return'<div class="history-item demo-history" onclick="showDemoActionPopup(\'history\')"><div style="display:flex;align-items:center"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">'+escHtml(c.title||'新对话')+'</span></div><div class="time">'+escHtml(c.time)+'</div><div class="preview">'+escHtml((c.messages[0]&&c.messages[0].content||'').slice(0,30))+'</div></div>';
  }).join('');
  historyList.innerHTML=html;
}
function showDemoActionPopup(label){
  var ov=document.createElement('div');
  ov.className='agent-prompt-overlay';
  ov.id='demoPopupOverlay';
  ov.style.display='flex';
  ov.innerHTML='<div class="agent-prompt-modal" style="width:360px;text-align:center">'+
    '<div class="apm-header"><span>'+t('demoPopup')+'</span><button class="btn" onclick="document.getElementById(\'demoPopupOverlay\').remove()">✕</button></div>'+
    '<div class="apm-body" style="padding:24px 16px">'+
      '<div style="font-size:40px;margin-bottom:12px">🔧</div>'+
      '<p style="font-size:13px;color:var(--text);margin-bottom:4px">'+t('demoPopup')+'</p>'+
      '<p style="font-size:10px;color:var(--muted);margin-bottom:16px">当前为 Demo 模式，点击 "'+escHtml(label||'')+'" 需要真实 API Key</p>'+
    '</div>'+
    '<div class="apm-footer" style="justify-content:center">'+
      '<button class="btn" onclick="document.getElementById(\'demoPopupOverlay\').remove()" style="font-size:11px">稍后</button>'+
      '<button class="btn primary" onclick="document.getElementById(\'demoPopupOverlay\').remove();toggleDevOverlay()" style="font-size:11px;padding:6px 20px">'+t('demoGotoSettings')+'</button>'+
    '</div>'+
  '</div>';
  document.body.appendChild(ov);
  ov.addEventListener('click',function(e){if(e.target===ov)ov.remove()});
}
function deleteAgent(name){if(agents.length<=3){showToast(t('minAgents'),false,'warn');return}showDeleteConfirm(t('confirmDelete')+' ('+escHtml(name)+')',function(){var agentData=agents.find(function(a){return a.name===name});if(!agentData)return;var idx=agents.indexOf(agentData);agents.splice(idx,1);renderAgents(agents);showUndoableToast(t('agentDeleted')+' '+name,function(){agents.splice(idx,0,agentData);renderAgents(agents)},5000,function(){api.post('/api/agent-delete',{name:name}).then(function(d){if(!d.ok){showToast(d.error||t('error'),true);loadAgents()}}).catch(function(e){showToast(t('error')+': '+e.message,true);loadAgents()})})})}
function viewAgentPrompt(name){currentPromptAgent=name;$('apm-title').textContent='编辑: '+name;$('apm-textarea').value='加载中…';$('apm-footer').innerHTML='<button class="new-chat-btn" onclick="saveAgentPrompt()" style="font-size:11px;padding:5px 14px;width:auto">💾 保存</button><button class="btn" onclick="clearAgentPromptText()" style="font-size:11px;padding:5px 8px">🗑 清空</button><button class="btn" onclick="closeAgentPrompt()">取消</button>';$('agentPromptOverlay').classList.add('on');api.get('/api/agents/'+encodeURIComponent(name)).then(function(d){if(d.error){showToast(d.error,!0);return}$('apm-textarea').value=d.content;$('apm-textarea')._originalContent=d.content}).catch(function(e){showToast('无法加载 Agent 内容: '+(e.message||'请检查网络连接后刷新重试'),!0)})}
function closeAgentPrompt(){$('agentPromptOverlay').classList.remove('on');currentPromptAgent='';$('apm-footer').innerHTML='<button class="new-chat-btn" onclick="saveAgentPrompt()" style="font-size:11px;padding:5px 14px;width:auto">💾 保存</button><button class="btn" onclick="closeAgentPrompt()">取消</button>'}
function saveAgentPrompt(){var content=$('apm-textarea').value;var oldContent=$('apm-textarea')._originalContent||'';if(!currentPromptAgent||!content)return;api.post('/api/agent-update',{name:currentPromptAgent,content:content}).then(function(d){if(d.ok){$('apm-textarea')._originalContent=content;closeAgentPrompt();loadAgents();showUndoableToast(t('promptSaved'),function(){api.post('/api/agent-update',{name:currentPromptAgent,content:oldContent}).then(function(){loadAgents()}).catch(function(){})},5000)}else{showToast(d.error||t('saveFail'),true)}}).catch(function(e){showToast(t('saveFail')+': '+(e.message||''),true)})}
function loadSidebarSkills(){
  if(!isFeatureUnlocked('skills')){
    var domEl=$('sidebar-skills-list');if(domEl)domEl.innerHTML='<div style="text-align:center;padding:30px 16px;color:var(--muted)"><div style="font-size:28px;margin-bottom:8px">🔒</div><p style="font-size:12px">'+t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS['skills']||7)+'</p></div>';
    return;
  }
  if(typeof _demoMode!=='undefined'&&_demoMode){renderDemoSkillsInSidebar();return}
  var domEl=$('sidebar-skills-list');if(!domEl)return;
  domEl.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载中…</div>';
  api.get('/api/skills').then(function(skills){
    allSkills=skills||[];
    renderSidebarSkills(allSkills);
  }).catch(function(){domEl.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">无法加载 Skills 列表。服务可能未启动，请刷新页面重试</div>'});
}
function renderSidebarSkills(skills){
  var domEl=$('sidebar-skills-list');if(!domEl)return;
  var enabled=skills.filter(function(s){return s.enabled!==false;});
  var disabled=skills.filter(function(s){return s.enabled===false;});

  var statsHtml='<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0 6px;font-size:10px;color:var(--muted);border-bottom:1px solid var(--border);margin-bottom:6px;gap:8px">'+
    '<span>' + enabled.length + ' 个已启用 / ' + skills.length + ' 个可用</span>'+
    '<span style="display:flex;gap:4px;flex-shrink:0">'+
      (disabled.length?'<button class="btn skill-enable-all-btn" onclick="event.stopPropagation();enableAllSkills()" style="font-size:9px;padding:2px 6px;border-color:#2e7d32;color:#2e7d32">全部启用</button>':'')+
      (enabled.length?'<button class="btn" onclick="event.stopPropagation();disableAllSkills()" style="font-size:9px;padding:2px 6px">全部禁用</button>':'')+
    '</span></div>';

  var cardsHtml='';
  enabled.forEach(function(s){
    var ns=s.name.replace(/'/g,"\\'");
    cardsHtml+='<div class="skill-card" onclick="viewSkillDetail(\''+ns+'\')" style="padding:8px 10px;margin-bottom:4px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px;transition:background .15s;cursor:pointer">'+
      '<div style="font-weight:600;color:var(--text)">'+escHtml(s.name)+'</div>'+
      '<div style="font-size:10px;color:var(--muted);margin-top:2px">'+escHtml((s.description||'').slice(0,80))+'</div>'+
    '</div>';
  });
  disabled.forEach(function(s){
    var ns=s.name.replace(/'/g,"\\'");
    cardsHtml+='<div class="skill-card disabled" style="padding:8px 10px;margin-bottom:4px;background:var(--surface2);border-radius:var(--radius-sm);font-size:12px;transition:background .15s;display:flex;align-items:center;justify-content:space-between">'+
      '<div style="flex:1;min-width:0;cursor:pointer" onclick="viewSkillDetail(\''+ns+'\')">'+
        '<div style="font-weight:600;color:var(--text)">⏸ '+escHtml(s.name)+'</div>'+
        '<div style="font-size:10px;color:var(--muted);margin-top:2px">'+escHtml((s.description||'').slice(0,80))+'</div>'+
      '</div>'+
      '<button class="skill-enable-btn" onclick="event.stopPropagation();enableSkill(\''+ns+'\')" style="flex-shrink:0;margin-left:8px" title="启用此 Skill">启用</button>'+
    '</div>';
  });

  domEl.innerHTML=skills.length?statsHtml+cardsHtml:'<div class="empty-state"><div class="es-icon">🧩</div><div class="es-text">'+t('skillsEmptyTitle')+'</div><div class="es-actions"><a href="#" onclick="toggleHelpOverlay();return false" class="btn">'+t('learnMore')+'</a></div></div>';
}
function renderHistory(){historyList.innerHTML=conversations.slice(0,30).map(function(c){return'<div class="history-item" onclick="loadConvo(\''+c.id+'\')"><div style="display:flex;align-items:center"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">'+escHtml(c.title||'新对话')+'</span><button class="del-btn" onclick="delConvo(\''+c.id+'\',event)">×</button></div><div class="time">'+new Date(c.id).toLocaleDateString('zh-CN')+'</div><div class="preview">'+escHtml((c.messages[0]&&c.messages[0].content||'').slice(0,30))+'</div></div>'}).join('')||'<div class="empty-state"><div class="es-icon">💬</div><div class="es-text">'+t('historyEmpty')+'</div></div>'}
window.searchHistory=function(q){if(!q||!q.trim()){renderHistory();return}api.get('/api/sessions/search?q='+encodeURIComponent(q.trim())).then(function(d){var results=d.results||[];if(!results.length){historyList.innerHTML='<div class="empty-state"><div class="es-icon">🔍</div><div class="es-text">未找到匹配的对话</div></div>';return}var html='';results.forEach(function(r){var ts=new Date(r.ts*1000).toLocaleString('zh-CN');html+='<div class="history-item" onclick="loadSessionSearch(\''+r.session_id+'\')" style="cursor:pointer"><div style="display:flex;align-items:center"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">📄 '+escHtml(r.session_id)+'</span></div><div class="time">'+escHtml(ts)+' · '+escHtml(r.type)+'</div><div class="preview">'+escHtml(r.snippet)+'</div></div>'});historyList.innerHTML=html}).catch(function(){historyList.innerHTML='<div class="empty-state"><div class="es-icon">⚠</div><div class="es-text">搜索失败</div></div>'})}
window.loadSessionSearch=function(sessionId){api.get('/api/sessions/'+sessionId).then(function(data){if(!data.events||!data.events.length){showToast('会话为空');return}var p=getFocusedPanel();p.currentConvo={id:Date.now(),title:'搜索: '+sessionId.slice(0,8),messages:[],sessionId:sessionId};p.dom.messages.innerHTML='';p.dom.route.innerHTML='';data.events.forEach(function(evt){if(evt.type==='user_message'){var task=evt.data.task||'';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task})}else if(evt.type==='agent_response'){var resp=evt.data.response||'';var b=addMsg(p,'assistant',typeof renderMD==='function'?renderMD(resp):resp);if(typeof renderMD==='function')highlightCode(b);p.currentConvo.messages.push({role:'assistant',content:resp})}else if(evt.type==='route_decision'){if(evt.data.agent){p._lastAgent=evt.data.agent;p.dom.route.innerHTML='<span style="color:var(--accent);font-size:9px">📌 '+escHtml(evt.data.agent)+'</span>'}}});p.dom.messages.scrollTop=p.dom.messages.scrollHeight}).catch(function(){showToast('加载会话失败')})}
function loadConvo(id){var c=conversations.find(function(x){return x.id===Number(id)});if(!c)return;var p=getFocusedPanel();p.currentConvo={id:c.id,title:c.title,messages:c.messages.slice(),sessionId:c.sessionId||''};p.dom.messages.innerHTML='';p.dom.route.innerHTML='';c.messages.forEach(function(m){addMsg(p,m.role,m.content)});p.dom.messages.scrollTop=p.dom.messages.scrollHeight;setTimeout(function(){p.dom.messages.querySelectorAll('.bubble').forEach(highlightCode)},100)}
function delConvo(id,e){e.stopPropagation();var convo=conversations.find(function(c){return c.id===Number(id)});if(!convo)return;showDeleteConfirm(t('confirmDelete'),function(){var idx=conversations.indexOf(convo);conversations.splice(idx,1);localStorage.setItem('agency_convos',JSON.stringify(conversations));renderHistory();showUndoableToast(t('convDeleted'),function(){conversations.splice(idx,0,convo);localStorage.setItem('agency_convos',JSON.stringify(conversations));renderHistory()},5000)})}
function viewSkillDetail(name){
  var skill=allSkills.find(function(s){return s.name===name});
  if(!skill)return;
  var ov=$('agentPromptOverlay');
  var title=$('apm-title');
  var body=$('apm-body');
  var footer=$('apm-footer');

  title.textContent='Skill: '+name;

  api.get('/api/skills/content/'+name).then(function(d){
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
  api.post('/api/skills/save',{name:name,content:content})
    .then(function(d){
      if(d.ok){showToast('已保存: '+name);closeAgentPrompt()}else showToast(d.error||'保存失败，请检查文件权限或磁盘空间后重试',!0);
    }).catch(function(e){showToast('保存失败: '+(e.message||'请检查网络连接后重试'),!0)});
}
function toggleSkill(name,enabled){
  var skill=allSkills.find(function(s){return s.name===name});
  var oldEnabled=skill?skill.enabled:!enabled;
  if(skill)skill.enabled=enabled;
  loadSidebarSkills();
  showUndoableToast(t('skillToggled')+' '+name,function(){
    if(skill)skill.enabled=oldEnabled;loadSidebarSkills();
    var ov=$('agentPromptOverlay');if(ov.classList.contains('on'))viewSkillDetail(name);
  },5000,function(){
    api.post('/api/skills/toggle',{name:name,enabled:enabled})
      .then(function(d){
        if(!d.ok){showToast(d.error||'Skill 操作失败',true);loadSidebarSkills()}
      }).catch(function(e){showToast('Skill 操作失败',true);loadSidebarSkills()});
  });
}
function enableSkill(name){
  toggleSkill(name,true);
}
function enableAllSkills(){
  var disabled=allSkills.filter(function(s){return s.enabled===false;});
  if(!disabled.length) return;
  if(!confirm('确认启用全部 '+disabled.length+' 个已禁用的 Skill？')) return;
  disabled.forEach(function(s){ toggleSkill(s.name,true); });
}
function disableAllSkills(){
  var enabled=allSkills.filter(function(s){return s.enabled!==false;});
  if(!enabled.length) return;
  if(!confirm('确认禁用全部 '+enabled.length+' 个已启用的 Skill？\n\n注意：禁用的 Skill 不会出现在 AI 匹配列表中。')) return;
  enabled.forEach(function(s){ toggleSkill(s.name,false); });
}
function deleteSkillDetail(name){
  showDeleteConfirm(t('confirmDelete')+' ('+escHtml(name)+')',function(){
    api.del('/api/skills/'+encodeURIComponent(name))
      .then(function(d){
        if(d.ok){showToast(t('deleteOk')+': '+name);closeAgentPrompt();loadSidebarSkills()}
        else showToast(d.error||t('error'),true);
      }).catch(function(e){showToast(t('error')+': '+e.message,true)});
  });
}

/* ── 清空提示词（可撤销）── */
function clearAgentPromptText(){var ta=$('apm-textarea');if(!ta||!ta.value.trim())return;var savedText=ta.value;ta.value='';ta.style.height='auto';showUndoableToast(t('promptCleared'),function(){ta.value=savedText;ta.style.height='auto';ta.style.height=Math.min(ta.scrollHeight,55*16)+'px'},5000)}

/* ── 服务状态检查 ── */
function checkServiceStatus(){showToast('正在检查服务状态…',false,'warn',2000);api.get('/api/version').then(function(d){showToast('服务正常: '+escHtml(d.version||'OK'));loadAgents()}).catch(function(){showToast('服务未响应，请确认 Agency 是否已启动',true)})}

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

// ES module bridge
window.loadAgents = loadAgents;
window.renderAgents = renderAgents;
window.loadSidebarSkills = loadSidebarSkills;
window.renderHistory = renderHistory;
window.delConvo = delConvo;
window.loadConvo = loadConvo;
window.switchNav = switchNav;
window.toggleAgentList = toggleAgentList;
window.toggleMultiSelect = toggleMultiSelect;
window.deleteAgent = deleteAgent;
window.viewAgentPrompt = viewAgentPrompt;
window.closeAgentPrompt = closeAgentPrompt;
window.saveAgentPrompt = saveAgentPrompt;
window.viewSkillDetail = viewSkillDetail;
window.saveSkillSource = saveSkillSource;
window.toggleSkill = toggleSkill;
window.enableSkill = enableSkill;
window.checkServiceStatus = checkServiceStatus;
window.showRoutePicker = showRoutePicker;
window.showDemoActionPopup = showDemoActionPopup;
window.clearAgentPromptText = clearAgentPromptText;
window.enableAllSkills = enableAllSkills;
window.disableAllSkills = disableAllSkills;

export { currentPromptAgent, allSkills, STARTER_AGENTS, currentNav,
         switchNav, loadAgents, renderAgents, loadSidebarAgents, loadSidebarDashboard,
         loadSidebarConnect, loadSidebarSkills, renderSidebarSkills, renderHistory,
         delConvo, loadConvo, toggleMultiSelect, deleteAgent, viewAgentPrompt,
         closeAgentPrompt, saveAgentPrompt, viewSkillDetail, saveSkillSource,
         toggleSkill, enableSkill, checkServiceStatus, showRoutePicker,
         renderDemoAgentsInSidebar, renderDemoSkillsInSidebar, renderDemoHistoryInSidebar,
         showDemoActionPopup, pickAgentForRoute, clearAgentPromptText,
         enableAllSkills, disableAllSkills };
