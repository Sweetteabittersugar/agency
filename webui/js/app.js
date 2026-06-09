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
  document.querySelectorAll('.help-tab').forEach(function(t){t.classList.toggle('active',t.textContent.includes(tab))});
  var tabs={
    quickstart:'<h3>快速入门</h3><p style="font-size:11px;color:var(--text2)">1. 输入 API Key 完成配置<br>2. 在底部输入框输入任务<br>3. 按 Enter 发送<br>4. 使用 @agent名 指定 Agent</p>',
    features:'<h3>功能介绍</h3><p style="font-size:11px;color:var(--text2)">多面板聊天 · Agent 调度 · 仪表盘监控 · Skill 管理 · 远端访问</p>',
    faq:'<h3>常见问题</h3><p style="font-size:11px;color:var(--text2)"><b>Q: Agent 没有回复？</b><br>A: 检查 API Key 是否正确<br><b>Q: 对话历史存在哪？</b><br>A: 浏览器 localStorage，不会丢失<br><b>Q: 如何添加 Agent？</b><br>A: 设置面板 → Agent 工厂</p>',
    shortcuts:'<h3>快捷键</h3><p style="font-size:11px;color:var(--text2)">Enter = 发送<br>Shift+Enter = 换行</p>'
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
