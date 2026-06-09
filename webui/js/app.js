/* Agency — 入口 + 初始化 + 全局变量 */

// ── 全局变量 ──
var panels=[],pidSeq=0,perPage=1,curPage=0,focusedPid=null,orchMode=!1,devMode=!1;
var conversations=[],agents=[];try{conversations=JSON.parse(localStorage.getItem('agency_convos')||'[]')}catch(_){}
var projDir='',apiKey='',apiProvider='deepseek',authToken='';
try{projDir=localStorage.getItem('agency_proj_dir')||''}catch(_){}
try{apiKey=localStorage.getItem('agency_api_key')||''}catch(_){}
try{apiProvider=localStorage.getItem('agency_api_provider')||'deepseek'}catch(_){}
try{authToken=localStorage.getItem('agency_auth_token')||''}catch(_){}
var _saveTimer=null;
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

// ── 项目目录绑定 ──
var pInput=$('proj-dir');if(pInput)pInput.value=projDir;
pInput&&pInput.addEventListener('change',function(){projDir=pInput.value.trim();localStorage.setItem('agency_proj_dir',projDir);loadFileTree(projDir)});

// ── Agent 搜索绑定 ──
$('agent-search').addEventListener('input',function(){var q=$('agent-search').value.toLowerCase();renderAgents(agents.filter(function(a){return a.name.includes(q)||(a.description||'').includes(q)||(a.keywords||[]).some(function(k){return k.includes(q)})}))});

// ── 侧边栏标签切换 ──
document.querySelectorAll('.sidebar-tab').forEach(function(tab){tab.addEventListener('click',function(){document.querySelectorAll('.sidebar-tab').forEach(function(t){t.classList.remove('active')});document.querySelectorAll('.sidebar-panel').forEach(function(p){p.classList.remove('active')});tab.classList.add('active');var p=$('panel-'+tab.dataset.tab);if(p)p.classList.add('active');})});
document.querySelector('.sidebar-tab[data-tab="skills"]')&&document.querySelector('.sidebar-tab[data-tab="skills"]').addEventListener('click',function(){loadSidebarSkills()});
document.querySelector('.sidebar-tab[data-tab="project"]')&&document.querySelector('.sidebar-tab[data-tab="project"]').addEventListener('click',function(){loadFileTree(projDir)});

// ── 初始加载 ──
loadAgents();
renderHistory();
addPanel();

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
  var p=path||projDir||'D:/';
  fetch('/api/files?path='+encodeURIComponent(p)).then(function(r){return r.json()}).then(function(d){
    if(d.error){$('file-tree').innerHTML=escHtml(d.error);return}
    projDir=d.path;$('proj-dir').value=d.path;localStorage.setItem('agency_proj_dir',projDir);
    var bread=d.path.replace(/\\/g,'/').split('/').filter(Boolean);
    $('file-breadcrumb').innerHTML=bread.map(function(b,i){return'<span style="cursor:pointer;color:var(--accent)" onclick="loadFileTree(\''+bread.slice(0,i+1).join('/')+'\')">'+b+'</span>'}).join(' / ')||'/';
    var h='';
    d.entries.forEach(function(e){h+='<div style="padding:3px 6px;cursor:pointer;display:flex;gap:6px;align-items:center" onclick="'+ (e.is_dir?'loadFileTree('+JSON.stringify((d.path+'/'+e.name).replace(/\\/g,'/'))+')':'openFilePanel('+JSON.stringify((d.path+'/'+e.name).replace(/\\/g,'/'))+')') +'">'+'<span>'+(e.is_dir?'📁':'📄')+'</span>'+'<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+e.name+'</span>'+'<span style="font-size:9px;color:var(--muted)">'+(e.is_dir?'':e.size>1024?(e.size/1024).toFixed(1)+'KB':e.size+'B')+'</span>'+'</div>'});
    $('file-tree').innerHTML=h||'空目录';
  }).catch(function(){$('file-tree').innerHTML='加载失败'});
}
function openFilePanel(fpath){var p=getFocusedPanel();if(p){p.dom.input.value='@explorer 分析这个文件: '+fpath}loadFileTree(projDir)}
function clearProjDir(){projDir='';$('proj-dir').value='';localStorage.removeItem('agency_proj_dir');$('file-tree').innerHTML='';$('file-breadcrumb').textContent='/'}
function onFolderPicked(e){var files=e.target.files;if(!files.length)return;var root={};for(var i=0;i<files.length;i++){var parts=files[i].webkitRelativePath.split('/'),node=root;for(var j=0;j<parts.length;j++){if(j===parts.length-1){if(!node._files)node._files=[];node._files.push({name:parts[j],size:files[i].size})}else{if(!node[parts[j]])node[parts[j]]={};node=node[parts[j]]}}}var html='';function renderNode(node,depth){var keys=Object.keys(node).filter(function(k){return k!=='_files'}).sort();keys.forEach(function(k){html+='<div style="padding:3px 6px;padding-left:'+(6+depth*16)+'px">📁 '+escHtml(k)+'</div>';renderNode(node[k],depth+1)});if(node._files){node._files.sort(function(a,b){return a.name.localeCompare(b.name)}).forEach(function(f){html+='<div style="padding:3px 6px;padding-left:'+(6+depth*16)+'px">📄 '+escHtml(f.name)+' <span style="font-size:9px;color:var(--muted)">'+(f.size>1024?(f.size/1024).toFixed(1)+'KB':f.size+'B')+'</span></div>'})}}renderNode(root,0);$('file-tree').innerHTML=html||'空目录';var rootName=files[0].webkitRelativePath.split('/')[0];$('file-breadcrumb').textContent='📁 '+rootName}

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
(function(){
  var sidebar=document.querySelector('.sidebar');
  var isResizing=false;
  if(sidebar){
    sidebar.addEventListener('mousedown',function(e){
      if(e.offsetX>sidebar.offsetWidth-6){isResizing=true;e.preventDefault()}
    });
    document.addEventListener('mousemove',function(e){
      if(!isResizing)return;
      var w=Math.max(200,Math.min(500,e.clientX));
      sidebar.style.width=w+'px';
      sidebar.style.minWidth=w+'px';
      localStorage.setItem('agency_sidebar_width',w);
    });
    document.addEventListener('mouseup',function(){isResizing=false});
    var saved=localStorage.getItem('agency_sidebar_width');
    if(saved){sidebar.style.width=saved+'px';sidebar.style.minWidth=saved+'px'}
  }
})();

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
