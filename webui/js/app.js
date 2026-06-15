/* Agency — 入口 + 初始化 + 全局变量 */

// ── 全局变量 ──
var panels=[],pidSeq=0,perPage=1,curPage=0,focusedPid=null,orchMode=!1,devMode=!1;
var conversations=[],agents=[];
var projDir='',apiKey='',apiProvider='deepseek',authToken='';
try{projDir=localStorage.getItem('agency_proj_dir')||''}catch(_){}
// 注意：API Key 明文存 localStorage 有 XSS 泄漏风险
// 生产环境建议用 session token 替代，或后端代理持有 Key
/* 2026-06: API Key 优先从服务端加载，防止 pywebview localStorage 不持久化 */
try{apiKey=localStorage.getItem('agency_api_key')||''}catch(_){}
try{apiProvider=localStorage.getItem('agency_api_provider')||'deepseek'}catch(_){}
// 服务端覆盖：后台保存的 Key 优先级最高
try{
  fetch('/api/config/key').then(function(r){return r.json()}).then(function(d){
    if(d.has_key){ apiKey=d.key||apiKey; apiProvider=d.provider||apiProvider; }
  }).catch(function(){});
}catch(_){}
try{authToken=localStorage.getItem('agency_auth_token')||''}catch(_){}

// 2026-06: 从服务端恢复用户偏好（防止 pywebview localStorage 丢失）
(function _restoreServerPrefs(){
  fetch('/api/config/prefs').then(function(r){return r.json()}).then(function(prefs){
    if(!prefs||!Object.keys(prefs).length)return;
    // 只恢复 localStorage 中没有的 key（localStorage 优先）
    var keys=['agency_api_key','agency_api_provider','agency_theme','agency_trust_mode',
              'agency_profile','sticky_agent','custom_shortcuts','agency_unlock_all',
              'agency_custom_templates','agency_output_dir','agency_proj_dir','agency_font_size'];
    keys.forEach(function(k){
      if(prefs[k]&&!localStorage.getItem(k)){
        try{localStorage.setItem(k,prefs[k])}catch(_){}
        if(k==='agency_api_key')apiKey=prefs[k];
        if(k==='agency_api_provider')apiProvider=prefs[k];
        if(k==='agency_profile')agencyProfile=prefs[k];
      }
    });
  }).catch(function(){});
})();

// 通用偏好同步：任何 localStorage 变更后调用，异步上传到服务端
window.syncPrefs = function(key, value){
  try{
    var payload={};payload[key]=value;
    fetch('/api/config/prefs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).catch(function(){});
  }catch(_){}
};

// ── Profile 级别 ──
var agencyProfile='standard';  // minimal | standard | full
try{agencyProfile=localStorage.getItem('agency_profile')||'standard'}catch(_){}
var PROFILE_LABELS={minimal:'省流',standard:'标准',full:'深度'};
var PROFILE_ICONS={minimal:'⚡',standard:'💼',full:'🚀'};
var PROFILE_ROUNDS={minimal:20,standard:80,full:160};
var PROFILE_DESC_FALLBACK={minimal:'日常查询、简单编辑，约支持 20 轮对话',standard:'正常开发、多文件修改，约支持 80 轮对话',full:'复杂重构、架构设计，约支持 160 轮对话'};
var PROFILE_COLORS={minimal:'var(--accent)',standard:'#f0a020',full:'var(--danger)'};
var grid=$('grid'),pageBar=$('pageBar'),agentList=$('agent-list'),historyList=$('history-list');

// ── 窗口拖拽 ──
var dragTarget=null,dragOX=0,dragOY=0;
function onDrag(e){if(!dragTarget)return;dragTarget.style.left=(e.clientX-dragOX)+'px';dragTarget.style.top=(e.clientY-dragOY)+'px'}
function offDrag(){dragTarget=null;document.removeEventListener('mousemove',onDrag);document.removeEventListener('mouseup',offDrag)}
['harnessOverlay','devOverlay'].forEach(function(id){
  var domEl=document.getElementById(id);if(!domEl)return;
  var tab=domEl.querySelector('.harness-overlay-tabs');if(!tab)return;
  tab.addEventListener('mousedown',function(e){if(e.target.tagName==='BUTTON')return;dragTarget=domEl;dragOX=e.clientX-domEl.offsetLeft;dragOY=e.clientY-domEl.offsetTop;document.addEventListener('mousemove',onDrag);document.addEventListener('mouseup',offDrag);e.preventDefault()})
});

// ── API Key 状态显示 ──
if(apiKey){var ak=$('api-key');if(ak)ak.value=apiKey;var ap=$('api-provider');if(ap)ap.value=apiProvider;$('api-status').textContent='已配置'}
// ── 输出目录 ──
var outputDir='';try{outputDir=localStorage.getItem('agency_output_dir')||''}catch(_){}
var odInput=$('output-dir');if(odInput)odInput.value=outputDir;
function saveOutputDir(){var v=($('output-dir')||{}).value||'';localStorage.setItem('agency_output_dir',v);outputDir=v;showToast('输出目录已保存: '+(v||'默认'))}


// ── 项目目录绑定 ──
var pInput=$('proj-dir');if(pInput)pInput.value=projDir;
pInput&&pInput.addEventListener('change',function(){projDir=pInput.value.trim();localStorage.setItem('agency_proj_dir',projDir);loadFileTree(projDir)});

// ── Agent 搜索绑定 ──
var agentSearchEl=$('agent-search');
if(agentSearchEl)agentSearchEl.addEventListener('input',function(){var q=agentSearchEl.value.toLowerCase();renderAgents(agents.filter(function(a){return a.name.includes(q)||(a.description||'').includes(q)||(a.keywords||[]).some(function(k){return k.includes(q)})}))});

// ── 侧边栏导航 ──
(function initSidebarNav(){
  var saved=null;
  try{saved=localStorage.getItem('agency-nav')}catch(e){}
  if(saved&&['chat','agents','dashboard','connect'].indexOf(saved)>=0){
    setTimeout(function(){ if(typeof switchNav==='function') switchNav(saved); }, 200);
  }
})();

// ── Profile 快捷切换 ──
function cycleProfile(){
  var levels=['minimal','standard','full'];
  var idx=levels.indexOf(agencyProfile);
  var next=levels[(idx+1)%levels.length];
  setProfile(next);
}
function setProfile(level){
  if(!PROFILE_LABELS[level]) return;
  agencyProfile = level;
  localStorage.setItem('agency_profile', level);
  localStorage.setItem('profile_manual', 'true');
  updateProfileUI();
  if(typeof loadAgents==='function') loadAgents();  // reload agent list with new profile filter
  fetch('/api/profile', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({level: level})
  }).catch(function(){});
  showToast(t('profileChanged').replace('{name}', PROFILE_LABELS[level]).replace('{rounds}', PROFILE_ROUNDS[level]));
}
function updateProfileUI(){
  var sel = document.getElementById('profile-select');
  if(sel) sel.value = agencyProfile;
  var label = document.getElementById('profile-label');
  if(label && PROFILE_LABELS[agencyProfile]){
    label.textContent = PROFILE_ICONS[agencyProfile] + ' ' + PROFILE_LABELS[agencyProfile];
    label.style.color = PROFILE_COLORS[agencyProfile];
  }
  // 更新 settings 面板描述
  var desc = document.getElementById('profile-desc');
  if(desc){
    desc.textContent = (loadedProfileDescriptions && loadedProfileDescriptions[agencyProfile]) || PROFILE_DESC_FALLBACK[agencyProfile] || '';
  }
  // 更新 header 快捷按钮
  var btn = document.getElementById('profileQuickBtn');
  if(btn){
    btn.textContent = PROFILE_ICONS[agencyProfile];
    btn.title = PROFILE_LABELS[agencyProfile] + ' (点击切换)';
    btn.style.color = PROFILE_COLORS[agencyProfile];
  }
  // 更新 settings 面板按钮
  var btns = document.querySelectorAll('.profile-quick-btn');
  btns.forEach(function(b){
    var lv = b.getAttribute('data-profile');
    b.classList.toggle('active', lv === agencyProfile);
  });
}
var loadedProfileDescriptions = null;
function loadProfileDescriptions(){
  fetch('/api/profile').then(function(r){return r.json()}).then(function(d){
    var profiles = d.profiles || {};
    loadedProfileDescriptions = {};
    Object.keys(profiles).forEach(function(k){
      loadedProfileDescriptions[k] = profiles[k].description || PROFILE_DESC_FALLBACK[k] || '';
    });
    updateProfileUI();
  }).catch(function(){});
}

// ── 初始加载 ──
loadAgents();
// 从服务端恢复会话
api.get('/api/conversations').then(function(d){
  var list=(d&&d.conversations)||[];
  if(list.length>0){
    // 只加载最近 4 条到面板
    list.slice(0,4).forEach(function(summary,i){
      // 加载完整消息
      api.get('/api/conversations/'+summary.id).then(function(full){
        var conv=full.conversation;
        if(!conv||!conv.messages)return;
        conversations.push(conv);
        var p=addPanel(i===0);
        if(p.dom.empty)p.dom.empty.style.display='none';
        p.currentConvo={id:conv.id,title:conv.title||'',messages:[],sessionId:conv.sessionId||''};
        conv.messages.forEach(function(m){
          p.currentConvo.messages.push(m);
          if(m.role==='user'){addMsg(p,'user',m.content)}
          else if(m.role==='assistant'){var bubble=addMsg(p,'assistant',typeof renderMD==='function'?renderMD(m.content):m.content);if(typeof highlightCode==='function')highlightCode(bubble)}
        });
        renderHistory();
      }).catch(function(){});
    });
    if(typeof refreshUI==='function')setTimeout(refreshUI,300);
  }else{
    /* 无历史对话时创建单个常规面板，非全屏空窗 */
    var p=addPanel(false);
    if(p&&p.dom.empty)p.dom.empty.style.display='block';
  }
}).catch(function(){
  /* API 不可用时仍创建基础面板 */
  var p=addPanel(false);
  if(p&&p.dom.empty)p.dom.empty.style.display='block';
});
// 恢复布局偏好（只改每页窗数，不补面板）
var savedLayout = parseInt(localStorage.getItem('agency_layout')) || 1;
if (savedLayout >= 1 && savedLayout <= 4 && savedLayout !== perPage) {
  perPage = savedLayout;
  curPage = 0;
  grid.className = 'grid g' + perPage;
}
if (typeof refreshUI === 'function') setTimeout(refreshUI, 100);
updateProfileUI();
loadProfileDescriptions();
initTheme();
initTooltips();

// ── 功能门控应用 ──
(function applyFeatureGates(){
  // 仪表盘按钮 (Demo 模式下始终显示)
  if(!(typeof _demoMode!=='undefined'&&_demoMode) && !isFeatureUnlocked('dashboard')){
    var dbBtn = document.getElementById('dashboardBtn');
    if(dbBtn){ dbBtn.style.display='none'; }
  }
  // 多面板/分屏 (Demo 模式下允许新建面板)
  var origAddPanel = addPanel;
  addPanel = function(){
    if(!(typeof _demoMode!=='undefined'&&_demoMode) && !isFeatureUnlocked('multipanel') && panels.length >= 1){
      showToast(t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS['multipanel']||3), false, 'warn');
      return panels[0];
    }
    return origAddPanel();
  };
  var origCycleGrid = cycleGrid;
  cycleGrid = function(){
    if(!isFeatureUnlocked('multipanel')){ showToast(t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS['multipanel']||3), false, 'warn'); return; }
    origCycleGrid();
  };
  // 智能调度
  var origToggleOrch = toggleOrchMode;
  toggleOrchMode = function(){
    if(!isFeatureUnlocked('routing')){ showToast(t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS['routing']||3), false, 'warn'); return; }
    origToggleOrch();
  };
  // Profile 切换
  var origCycleProfile = cycleProfile;
  cycleProfile = function(){
    if(!isFeatureUnlocked('profiles')){ showToast(t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS['profiles']||7), false, 'warn'); return; }
    origCycleProfile();
  };
  var origSetProfile = setProfile;
  setProfile = function(level){
    if(!isFeatureUnlocked('profiles') && level !== agencyProfile){ showToast(t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS['profiles']||7), false, 'warn'); return; }
    origSetProfile(level);
  };
  // 设置面板打开时刷新功能解锁 UI
  var origToggleDev = toggleDevOverlay;
  toggleDevOverlay = function(){
    origToggleDev();
    if(devMode){
      renderFeatureUnlock();
      if(typeof renderStickyAgentDropdown === 'function'){
        var sac = document.getElementById('sticky-agent-container');
        if(sac) renderStickyAgentDropdown(sac);
      }
      if(typeof renderShortcutEditor === 'function'){
        var sec = document.getElementById('shortcut-editor-container');
        if(sec) renderShortcutEditor(sec);
      }
      if(!isFeatureUnlocked('agent-factory')){
        var af = document.getElementById('agent-factory-section');
        if(af) af.style.display = 'none';
      }
    }
  };
})();

// ── 检测新解锁功能 ──
setTimeout(function(){ checkNewUnlocks(); }, 1500);

/* ── 帮助覆盖层 ── */
function toggleHelpOverlay(){
  var ov=$('helpOverlay');
  if(!ov)return;
  ov.classList.toggle('on');
  if(ov.classList.contains('on')){switchHelpTab('quickstart')}
}
function switchHelpTab(tab){
  var domEl=$('helpContent');if(!domEl)return;
  document.querySelectorAll('.help-tab').forEach(function(t){t.classList.toggle('active',t.dataset.htab===tab)});
  var detail=function(t,c){return'<details style="margin:0 0 10px"><summary style="cursor:pointer;color:var(--accent);font-size:12px;font-weight:600;padding:5px 0">'+t+'</summary><div style="font-size:11px;color:var(--text2);padding:4px 0 4px 12px;line-height:1.8">'+c+'</div></details>'};
  var item=function(t,c){return'<div style="margin:0 0 10px"><div style="color:var(--accent);font-size:12px;font-weight:600;padding:5px 0">'+t+'</div><div style="font-size:11px;color:var(--text2);padding:0 0 0 12px;line-height:1.8">'+c+'</div></div>'};
  var tabs={
    quickstart:'<div style="font-size:12px;line-height:1.7">'+
      item('1. 首次配置','打开 Agency 后自动弹出配置向导。步骤：输入 API Key → 选择项目文件夹 → 配置远端访问密码 → 完成。Key 仅存本地 .env 文件，不会上传。')+
      item('2. 发送任务','在底部输入框输入自然语言描述的任务，按 Enter 发送。Agency 会自动匹配合适的 Agent 执行。')+
      item('3. 指定 Agent','输入 <code style="font-size:10px;background:var(--surface3);padding:1px 4px;border-radius:2px">@agent名 任务</code> 可以指定特定 Agent 处理。如 <code>@coder 写个排序函数</code>。')+
      item('4. 多面板协作','点击 ＋ 创建新面板，可实现多任务并行。用 ⊞ 切换分屏布局（1/2/4窗）。面板间独立会话，互不干扰。')+
      item('5. 查看结果','Agent 完成后可在聊天区查看。代码块自动语法高亮。任务输出文件路径会在回复中标注。')+
      '</div>',
    features:'<div style="font-size:12px;line-height:1.7">'+
      item('多面板聊天','支持无限面板、1/2/4 分屏布局。每个面板独立会话，可同时执行多个任务。')+
      item('Agent 调度','内置 31 个专业 Agent。智能关键词匹配 + 领域分类器两级路由。支持 @agent名 显式指定。')+
      item('仪表盘监控','实时 Token 窗口、费用趋势图（按日期/模型/Agent 三维）、权限日志、SubAgent 任务树、MCP 状态。')+
      item('Skill 管理','40+ 内置 Skill。侧边栏 Skills 标签可查看、编辑源码、启用/禁用。支持自定义 Skill 草稿。')+
      item('远端访问','开启后可从手机/平板远程操控。密码认证 + token 持久化。Webhook 接口可对接飞书/微信等消息平台。')+
      item('智能调度','点击 🧠 进入调度模式。Orchestrator 自动拆解复杂任务→分派子 Agent→汇总结果。')+
      '</div>',
    faq:'<div style="font-size:12px;line-height:1.7">'+
      detail('Agent 没有回复？','检查：1) API Key 是否正确且未过期 2) 网络是否可访问 API 端点 3) 设置中 Provider 和模型是否正确。如 Key 余额不足请充值。')+
      detail('对话历史存在哪？会丢失吗？','对话历史保存在浏览器 localStorage 中，不会自动删除。即使关闭浏览器或重启电脑也不会丢失。原始会话文件（JSONL格式）位于 ~/.claude/projects/ 目录下。')+
      detail('如何添加自定义 Agent？','设置面板 → Agent 工厂，输入描述 → 点击生成 → Claude 自动创建 Agent 提示词 → 确认保存。新 Agent 自动注册到路由表和侧边栏。')+
      detail('Skills 怎么用？','侧边栏 Skills 标签查看全部 Skill。点击卡片可编辑源码、切换启用状态。Skill 是 Agent 的工作流指导——Agent 接收任务时会自动匹配触发关键词加载对应 Skill。')+
      detail('面板太多怎么关闭？','点击面板右上角 ✕ 关闭。有对话内容时会弹出确认提示。至少保留 1 个面板。关闭的面板消息保存到历史记录中。')+
      detail('仪表盘数据为什么是空的？','权限/SubAgent/Hooks 数据来自运行时——需要 Agent 执行任务后才有记录。概览页的费用和 Token 数据来自 cost.db 任务记录。')+
      '</div>',
    shortcuts:'<div style="font-size:12px;line-height:1.7">'+
      item('发送与编辑','<code>Enter</code> 发送消息 &nbsp; <code>Shift+Enter</code> 换行 &nbsp; <code>Ctrl+/-</code> 调整字号（自动保存）')+
      item('面板与布局','<code>＋</code> 添加面板 &nbsp; <code>⊞</code> 切换分屏 &nbsp; 拖拽侧边栏右边缘调整宽度')+
      item('Agent 交互','<code>@agent名</code> 指定 Agent &nbsp; 点击卡片填入输入框 &nbsp; 右键卡片新面板打开')+
      '</div>'
  };
  domEl.innerHTML=tabs[tab]||'';
}

/* ── 远端登录 ── */
function showRemoteLogin(){
  var ov=$('remoteLoginOverlay');if(!ov)return;
  ov.classList.add('on');
  var inp=$('remote-login-token');if(inp){inp.value='';inp.focus()}
  var err=$('remote-login-error');if(err)err.style.display='none';
}
function submitRemoteLogin(){
  var token=$('remote-login-token').value.trim();
  if(!token){var err=$('remote-login-error');if(err){err.textContent='请输入访问密码';err.style.display='block'}return}
  authToken=token;
  localStorage.setItem('agency_auth_token',token);
  $('remoteLoginOverlay').classList.remove('on');
  showToast('已登录');
}

/* ── 文件浏览器 ── */
function loadFileTree(path){
  var ft=$('file-tree');if(!ft)return;
  var p=path||projDir||'D:/';
  fetch('/api/files?path='+encodeURIComponent(p)).then(function(r){return r.json()}).then(function(d){
    if(d.error){ft.innerHTML=escHtml(d.error);return}
    projDir=d.path;var pd=$('proj-dir');if(pd)pd.value=d.path;localStorage.setItem('agency_proj_dir',projDir);
    var bread=d.path.replace(/\\/g,'/').split('/').filter(Boolean);
    var fbc=$('file-breadcrumb');if(fbc)fbc.innerHTML=bread.map(function(b,i){return'<span style="cursor:pointer;color:var(--accent)" onclick="loadFileTree(\''+bread.slice(0,i+1).join('/')+'\')">'+b+'</span>'}).join(' / ')||'/';
    var h='';
    d.entries.forEach(function(e){h+='<div style="padding:3px 6px;cursor:pointer;display:flex;gap:6px;align-items:center" onclick="'+ (e.is_dir?'loadFileTree('+JSON.stringify((d.path+'/'+e.name).replace(/\\/g,'/'))+')':'openFilePanel('+JSON.stringify((d.path+'/'+e.name).replace(/\\/g,'/'))+')') +'">'+'<span>'+(e.is_dir?'📁':'📄')+'</span>'+'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+e.name+'</span>'+'<span style="font-size:9px;color:var(--muted)">'+(e.is_dir?'':e.size>1024?(e.size/1024).toFixed(1)+'KB':e.size+'B')+'</span>'+'</div>'});
    ft.innerHTML=h||'空目录';
  }).catch(function(){ft.innerHTML='无法加载文件目录。服务可能未启动，请刷新页面重试'});
}
function openFilePanel(fpath){var p=getFocusedPanel();if(p){p.dom.input.value='@explorer 分析这个文件: '+fpath}loadFileTree(projDir)}
function clearProjDir(){projDir='';var pd=$('proj-dir');if(pd)pd.value='';localStorage.removeItem('agency_proj_dir');var ft=$('file-tree');if(ft)ft.innerHTML='';var fbc=$('file-breadcrumb');if(fbc)fbc.textContent='/'}
function onFolderPicked(e){var files=e.target.files;if(!files.length)return;var root={};for(var i=0;i<files.length;i++){var parts=files[i].webkitRelativePath.split('/'),node=root;for(var j=0;j<parts.length;j++){if(j===parts.length-1){if(!node._files)node._files=[];node._files.push({name:parts[j],size:files[i].size})}else{if(!node[parts[j]])node[parts[j]]={};node=node[parts[j]]}}}var html='';function renderNode(node,depth){var keys=Object.keys(node).filter(function(k){return k!=='_files'}).sort();keys.forEach(function(k){html+='<div style="padding:3px 6px;padding-left:'+(6+depth*16)+'px">📁 '+escHtml(k)+'</div>';renderNode(node[k],depth+1)});if(node._files){node._files.sort(function(a,b){return a.name.localeCompare(b.name)}).forEach(function(f){html+='<div style="padding:3px 6px;padding-left:'+(6+depth*16)+'px">📄 '+escHtml(f.name)+' <span style="font-size:9px;color:var(--muted)">'+(f.size>1024?(f.size/1024).toFixed(1)+'KB':f.size+'B')+'</span></div>'})}}renderNode(root,0);var ft=$('file-tree');if(ft)ft.innerHTML=html||'空目录';var rootName=files[0].webkitRelativePath.split('/')[0];var fbc=$('file-breadcrumb');if(fbc)fbc.textContent='📁 '+rootName}

/* ══════════════════════════════════════════
   HCI 增强: tooltip / 侧边栏拖拽 / 字体缩放
   ══════════════════════════════════════════ */

// ── 按钮 tooltip 统一添加 ──
(function(){
  var btnMap={
    'dashboardBtn':'仪表盘 (📊)','devBtn':'开发者设置 (🔧)',
    'orchBtn':'智能调度 (🧠)','gridBtn':'切换布局',
    'helpBtn':'帮助 (❓)'
  };
  Object.keys(btnMap).forEach(function(id){
    var btn=document.getElementById(id);
    if(btn&&!btn.title)btn.title=btnMap[id];
  });
})();

// ── 侧边栏拖拽调整宽度 ──
var _sidebarResizing=false;
var _onSidebarMove=function(e){
  if(!_sidebarResizing)return;
  var sidebar=document.querySelector('.sidebar');
  if(!sidebar)return;
  var w=Math.max(200,Math.min(500,e.clientX));
  sidebar.style.width=w+'px';
  sidebar.style.minWidth=w+'px';
  localStorage.setItem('agency_sidebar_width',w);
};
var _onSidebarUp=function(){_sidebarResizing=false;};
(function(){
  var sidebar=document.querySelector('.sidebar');
  if(sidebar){
    sidebar.addEventListener('mousedown',function(e){
      if(e.offsetX>sidebar.offsetWidth-6){_sidebarResizing=true;e.preventDefault()}
    });
    document.addEventListener('mousemove',_onSidebarMove);
    document.addEventListener('mouseup',_onSidebarUp);
    var saved=localStorage.getItem('agency_sidebar_width');
    if(saved){sidebar.style.width=saved+'px';sidebar.style.minWidth=saved+'px'}
  }
})();
window.addEventListener('beforeunload',function(){
  document.removeEventListener('mousemove',_onSidebarMove);
  document.removeEventListener('mouseup',_onSidebarUp);
});

// ── Ctrl+ +/- 调整字体大小 ──
(function(){
  var savedFont=localStorage.getItem('agency_font_size');
  if(savedFont)document.body.style.fontSize=savedFont;
  document.addEventListener('keydown',function(e){
    if(!e.ctrlKey)return;
    if(e.key==='='||e.key==='+'){
      e.preventDefault();
      var fs=parseInt(getComputedStyle(document.body).fontSize);
      document.body.style.fontSize=Math.min(18,fs+1)+'px';
      localStorage.setItem('agency_font_size',document.body.style.fontSize);
    }
    if(e.key==='-'){
      e.preventDefault();
      var fs=parseInt(getComputedStyle(document.body).fontSize);
      document.body.style.fontSize=Math.max(10,fs-1)+'px';
      localStorage.setItem('agency_font_size',document.body.style.fontSize);
    }
  });
})();

/* ── 响应式：汉堡菜单 ── */
function toggleSidebar(){
  var sb = document.querySelector('.sidebar');
  if(!sb) return;
  sb.classList.toggle('open');
}

/* ── 响应式：移动端底部 Tab ── */
function switchMobileTab(tab){
  var tabs = document.querySelectorAll('.mobile-tab');
  tabs.forEach(function(t){ t.classList.remove('active'); });
  var active = document.querySelector('.mobile-tab[data-mtab="'+tab+'"]');
  if(active) active.classList.add('active');
  switch(tab){
    case 'chat':
      document.querySelector('.sidebar').classList.remove('open');
      document.querySelector('.main').style.display = 'flex';
      break;
    case 'dashboard':
      toggleDashboard();
      break;
    case 'settings':
      if(!devMode) toggleDevOverlay();
      break;
    case 'agents':
      document.querySelector('.sidebar').classList.add('open');
      var atab = document.querySelector('.sidebar-tab[data-tab="agents"]');
      if(atab) atab.click();
      break;
  }
}

/* ── Tooltip + Route/Remplate 动态注入 ── */
(function injectDynamicTooltips(){
  // Route bar tooltip — 监听 DOM 变化为 route bar 添加
  var observer = new MutationObserver(function(mutations){
    mutations.forEach(function(m){
      m.addedNodes.forEach(function(node){
        if(node.nodeType !== 1) return;
        // Template buttons
        var tplBtns = node.querySelectorAll ? node.querySelectorAll('.template-btn') : [];
        if(node.classList && node.classList.contains('template-btn')) tplBtns = [node];
        tplBtns.forEach(function(b){
          if(!b.hasAttribute('data-tooltip')) b.setAttribute('data-tooltip', 'tooltipTemplate');
        });
        // Route bars
        var routes = node.querySelectorAll ? node.querySelectorAll('.panel-route') : [];
        if(node.classList && node.classList.contains('panel-route')) routes = [node];
        routes.forEach(function(r){
          if(!r.hasAttribute('data-tooltip')) r.setAttribute('data-tooltip', 'tooltipRoute');
        });
      });
    });
  });
  observer.observe(document.body, {childList: true, subtree: true});
})();

// 同步全局变量到 Store（供后续渐进迁移）
if (window.Store) setTimeout(function() { Store.syncFromGlobals(); }, 1000);

// ES module — 确保全局变量在模块模式下仍可被其他文件访问
window.panels = panels;
window.pidSeq = pidSeq;
window.perPage = perPage;
window.curPage = curPage;
window.focusedPid = focusedPid;
window.orchMode = orchMode;
window.devMode = devMode;
window.conversations = conversations;
window.agents = agents;
window.projDir = projDir;
window.apiKey = apiKey;
window.apiProvider = apiProvider;
window.authToken = authToken;

window.agencyProfile = agencyProfile;
window.grid = grid;
window.pageBar = pageBar;
window.agentList = agentList;
window.historyList = historyList;
window.outputDir = outputDir;
window.loadedProfileDescriptions = loadedProfileDescriptions;
window.dragTarget = dragTarget;
window.PROFILE_LABELS = PROFILE_LABELS;
window.PROFILE_ICONS = PROFILE_ICONS;
window.PROFILE_ROUNDS = PROFILE_ROUNDS;
window.PROFILE_DESC_FALLBACK = PROFILE_DESC_FALLBACK;
window.PROFILE_COLORS = PROFILE_COLORS;

/* Phase 3: 全局搜索 — 跨会话全文检索 */
window.toggleGlobalSearch = function() {
  var ov = document.getElementById('searchOverlay');
  if (!ov) return;
  ov.classList.toggle('on');
  if (ov.classList.contains('on')) {
    setTimeout(function() { var inp = document.getElementById('global-search-input'); if (inp) inp.focus(); }, 100);
  }
};

window.doGlobalSearch = function() {
  var inp = document.getElementById('global-search-input');
  var res = document.getElementById('global-search-results');
  if (!inp || !res) return;
  var q = inp.value.trim();
  if (!q) { res.innerHTML = ''; return; }
  res.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:12px">搜索中…</div>';
  fetch('/api/search?q=' + encodeURIComponent(q)).then(function(r){ return r.json(); }).then(function(d){
    if (!d.results || !d.results.length) { res.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:12px">未找到匹配结果</div>'; return; }
    res.innerHTML = d.results.map(function(r){
      var icon = r.source === 'session' ? '📝' : '💬';
      return '<div class="search-result-item" style="padding:8px;border-bottom:1px solid var(--border);cursor:pointer;font-size:11px" onclick="openSearchResult(\''+r.id+'\',\''+r.source+'\')">' +
        '<div style="display:flex;justify-content:space-between;margin-bottom:4px">' +
          '<span style="font-weight:600;color:var(--text)">' + icon + ' ' + escHtml(r.title || r.id) + '</span>' +
          '<span style="font-size:9px;color:var(--muted)">' + escHtml(r.source) + '</span>' +
        '</div>' +
        '<div style="color:var(--text2);line-height:1.5">' + (r.snippet || escHtml(r.preview || '').substring(0, 200)) + '</div>' +
      '</div>';
    }).join('');
    res.innerHTML += '<div style="font-size:9px;color:var(--muted);padding:8px;text-align:center">扫描 ' + d.total + ' 个会话，找到 ' + d.results.length + ' 条</div>';
  }).catch(function(e){ res.innerHTML = '<div style="color:var(--danger);font-size:12px;padding:12px">搜索失败: ' + e.message + '</div>'; });
};

/* P1-3: 全局搜索结果点击——根据来源类型执行实际跳转，而非仅弹 toast */
window.openSearchResult = function(id, source) {
  toggleGlobalSearch();
  if (source === 'conversation') {
    /* 对话类型：尝试从侧边栏加载对话 */
    if (typeof loadConversation === 'function') {
      loadConversation(id);
      showToast('已加载对话');
    } else {
      showToast('对话ID: ' + id);
    }
  } else if (source === 'session') {
    /* 会话类型：提示用户可从历史恢复 */
    showToast('会话 ' + id.substring(0,8) + ' — 点击新建面板后可从历史恢复', true, 'info');
  }
};
