/* Agency — 前端 JS */
var panels=[],pidSeq=0,perPage=1,curPage=0,focusedPid=null,orchMode=!1,devMode=!1;
var conversations=[],agents=[];try{conversations=JSON.parse(localStorage.getItem('agency_convos')||'[]')}catch(_){}
var projDir='',apiKey='',apiProvider='deepseek',authToken='';
try{projDir=localStorage.getItem('agency_proj_dir')||''}catch(_){}
try{apiKey=localStorage.getItem('agency_api_key')||''}catch(_){}
try{apiProvider=localStorage.getItem('agency_api_provider')||'deepseek'}catch(_){}
try{authToken=localStorage.getItem('agency_auth_token')||''}catch(_){}
/* ── 首次配置向导 ── */
var setupData=null;
fetch('/api/setup/status').then(function(r){return r.json()}).then(function(d){
  setupData=d;
  if(d.needs_setup){showSetupStep(1)}
}).catch(function(){});
function showSetupStep(step){
  var body=$('setup-body'),footer=$('setup-footer'),ov=$('setupOverlay');
  if(step===1){
    $('setup-title').textContent='欢迎使用 Agency';
    body.innerHTML='<p style=\"font-size:12px;color:var(--text2);margin-bottom:12px\">第一步：配置 API Key 以连接 AI 模型</p>'+
      '<select class=\"proj-input\" id=\"setup-provider\" style=\"margin-bottom:8px\"><option value=\"deepseek\">DeepSeek（推荐，便宜）</option><option value=\"anthropic\">Anthropic</option><option value=\"openai\">OpenAI 兼容</option></select>'+
      '<input class=\"proj-input\" id=\"setup-key\" type=\"password\" placeholder=\"sk-…\" autocomplete=\"off\">'+
      '<p style=\"font-size:10px;color:var(--muted);margin-top:4px\">Key 仅存在本地 .env 文件，不会上传</p>';
    footer.innerHTML='<button class=\"btn\" onclick=\"$(\'setupOverlay\').classList.remove(\'on\')\" style=\"font-size:11px\">跳过</button><button class=\"new-chat-btn\" onclick=\"setupNext()\" style=\"width:auto;font-size:11px;padding:5px 20px\">下一步</button>';
    ov.classList.add('on');
  } else if(step===2){
    $('setup-title').textContent='远端访问（可选）';
    // 自动生成密码（只生成一次）
    if(!setupData._remote_token){
      setupData._remote_token=Array(16).fill(0).map(function(){return'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'.charAt(Math.floor(Math.random()*62))}).join('');
    }
    body.innerHTML='<p style=\"font-size:12px;color:var(--text2);margin-bottom:12px\">开启后可从手机/平板远程操作</p>'+
      '<label style=\"display:flex;align-items:center;gap:8px;font-size:12px;margin-bottom:8px\"><input type=\"checkbox\" id=\"setup-remote\" onchange=\"document.getElementById(\"setup-remote-info\").style.display=this.checked?\"block\":\"none\"\"> 启用远端访问</label>'+
      '<div id=\"setup-remote-info\" style=\"display:none\">'+
      '<p style=\"font-size:10px;color:var(--muted);margin-bottom:4px\">访问密码（已自动生成，可修改）</p>'+
      '<div style=\"display:flex;gap:4px\"><input class=\"proj-input\" id=\"setup-remote-token\" style=\"flex:1;margin:0;font-size:11px;font-family:monospace\" value=\"'+escHtml(setupData._remote_token)+'\"><button class=\"btn\" onclick=\"setupData._remote_token=Array(16).fill(0).map(function(){return\"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\".charAt(Math.floor(Math.random()*62))}).join(\"\");$(\"setup-remote-token\").value=setupData._remote_token\" style=\"font-size:10px\">随机</button></div>'+
      '</div>';
    footer.innerHTML='<button class=\"btn\" onclick=\"showSetupStep(1)\" style=\"font-size:11px\">上一步</button><button class=\"new-chat-btn\" onclick=\"setupFinish()\" style=\"width:auto;font-size:11px;padding:5px 20px\">完成</button>';
  }
}
function setupNext(){
  var key=$('setup-key').value.trim();
  if(!key){showToast('请输入 API Key',!0);return}
  setupData._api_key=key;
  setupData._api_provider=$('setup-provider').value;
  showSetupStep(2);
}
function setupFinish(){
  var remoteOn=$('setup-remote')&&$('setup-remote').checked;
  var remoteToken=remoteOn?($('setup-remote-token').value.trim()||setupData._remote_token||''):'';
  var body={api_key:setupData._api_key||'',api_provider:setupData._api_provider||'deepseek',remote_enabled:remoteOn,remote_token:remoteToken};
  fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      $('setupOverlay').classList.remove('on');
      apiKey=setupData._api_key||'';apiProvider=setupData._api_provider||'deepseek';
      localStorage.setItem('agency_api_key',apiKey);localStorage.setItem('agency_api_provider',apiProvider);
      if(remoteToken){authToken=remoteToken;localStorage.setItem('agency_auth_token',remoteToken)}
      showToast('配置完成！');
    } else showToast(d.error||'保存失败',!0);
  });
}
// API 请求包装：自动注入认证头
function apiFetch(url, opts){
  opts = opts || {};
  opts.headers = opts.headers || {};
  if (authToken) opts.headers['Authorization'] = 'Bearer ' + authToken;
  return fetch(url, opts).then(function(r){
    if (r.status === 401 && authToken) {
      // token 过期或无效，提示重新输入
      var nt = prompt('认证令牌无效，请输入新的访问令牌:');
      if (nt) {
        authToken = nt.trim();
        localStorage.setItem('agency_auth_token', authToken);
        opts.headers['Authorization'] = 'Bearer ' + authToken;
        return fetch(url, opts);
      }
    }
    return r;
  });
}
if(apiKey){var ak=$('api-key');if(ak)ak.value=apiKey;var ap=$('api-provider');if(ap)ap.value=apiProvider;$('api-status').textContent='已配置'}
function saveApiKey(){apiKey=$('api-key').value.trim();apiProvider=$('api-provider').value;localStorage.setItem('agency_api_key',apiKey);localStorage.setItem('agency_api_provider',apiProvider);$('api-status').textContent=apiKey?'已保存':'已清除';if(!apiKey){localStorage.removeItem('agency_api_key');localStorage.removeItem('agency_api_provider')}}
function $(id){return document.getElementById(id)}
var grid=$('grid'),pageBar=$('pageBar'),agentList=$('agent-list'),historyList=$('history-list');
document.querySelectorAll('.sidebar-tab').forEach(function(tab){tab.addEventListener('click',function(){document.querySelectorAll('.sidebar-tab').forEach(function(t){t.classList.remove('active')});document.querySelectorAll('.sidebar-panel').forEach(function(p){p.classList.remove('active')});tab.classList.add('active');var p=$('panel-'+tab.dataset.tab);if(p)p.classList.add('active');})});
async function loadAgents(){try{agents=await(await fetch('/api/agents')).json();renderAgents(agents)}catch(e){agentList.innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">加载失败</div>'}}
loadAgents();
function renderAgents(list){agentList.innerHTML=list.map(function(a){return'<div class="agent-card" onclick="pickAgent(\''+a.name+'\')" oncontextmenu="pickAgentNew(\''+a.name+'\',event)"><div style="display:flex;justify-content:space-between;align-items:center"><div class="name">'+a.name+'<span class="model">'+(a.model||'auto')+'</span></div><button class="btn" style="font-size:10px;padding:1px 5px;flex-shrink:0;margin-left:4px" onclick="event.stopPropagation();viewAgentPrompt(\''+a.name+'\')" title="查看/编辑提示词">📝</button></div><div class="desc">'+escHtml(a.description||'')+'</div>'+(a.keywords&&a.keywords.length?'<div class="kw">'+a.keywords.slice(0,5).join(', ')+'</div>':'')+'</div>'}).join('')}
$('agent-search').addEventListener('input',function(){var q=$('agent-search').value.toLowerCase();renderAgents(agents.filter(function(a){return a.name.includes(q)||(a.description||'').includes(q)||(a.keywords||[]).some(function(k){return k.includes(q)})}))});
function pickAgent(name){var p=getFocusedPanel();p.dom.input.value='@'+name+' ';p.dom.input.focus()}
function pickAgentNew(name,e){e.preventDefault();var p=addPanel();p.dom.input.value='@'+name+' ';p.dom.input.focus()}
function getFocusedPanel(){if(focusedPid){var p=panels.find(function(x){return x.id===focusedPid});if(p&&p.dom.wrapper.classList.contains('on'))return p}var start=curPage*perPage;return panels[start]||panels[0]}
var pInput=$('proj-dir');if(pInput)pInput.value=projDir;
pInput&&pInput.addEventListener('change',function(){projDir=pInput.value.trim();localStorage.setItem('agency_proj_dir',projDir);loadFileTree(projDir)});
function mkPanel(){return{id:++pidSeq,isStreaming:!1,abortController:null,currentConvo:{id:Date.now(),title:'',messages:[],sessionId:''},currentAssistantMsg:null,dom:{}}}
function addPanel(){var s=mkPanel();panels.push(s);buildPanelDOM(s);curPage=Math.floor((panels.length-1)/perPage);refreshUI();setTimeout(function(){s.dom.input&&s.dom.input.focus()},80);return s}
function removePanel(pid){if(panels.length<=1)return;var idx=panels.findIndex(function(p){return p.id===pid});if(idx<0)return;var p=panels[idx];if(p.isStreaming&&p.abortController)p.abortController.abort();panels.splice(idx,1);p.dom.wrapper.remove();if(focusedPid===pid)focusedPid=null;var total=Math.ceil(panels.length/perPage);if(curPage>=total)curPage=Math.max(0,total-1);refreshUI()}
function clearAllPanels(){panels.forEach(function(p){if(p.isStreaming&&p.abortController)p.abortController.abort()});while(panels.length>1){var p=panels.pop();p.dom.wrapper&&p.dom.wrapper.remove()}var p=panels[0];p.currentConvo={id:Date.now(),title:'',messages:[],sessionId:''};p.dom.messages.innerHTML='<div class="empty-panel"><div class="logo">⚡</div><h3>就绪</h3></div>';p.dom.route.innerHTML='';p.dom.agentName.textContent='就绪';curPage=0;refreshUI()}
function buildPanelDOM(s){var w=document.createElement('div');w.className='panel on';w.innerHTML='<div class="panel-bar"><span class="pinfo"><span class="pdot"></span><span class="pagent">就绪</span></span><button class="pclose">✕</button></div><div class="panel-msgs"><div class="empty-panel"><div class="logo">⚡</div><h3>就绪</h3></div></div><div class="panel-route"></div><div class="panel-inp"><textarea placeholder="输入任务或 @agent名…" rows="1"></textarea><button>发送</button></div>';grid.appendChild(w);s.dom={wrapper:w,messages:w.querySelector('.panel-msgs'),route:w.querySelector('.panel-route'),input:w.querySelector('textarea'),sendBtn:w.querySelector('.panel-inp button'),dot:w.querySelector('.pdot'),agentName:w.querySelector('.pagent'),empty:w.querySelector('.empty-panel')};w.querySelector('.pclose').addEventListener('click',function(e){e.stopPropagation();removePanel(s.id)});s.dom.input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();handleSend(s.id)}});s.dom.input.addEventListener('focus',function(){focusedPid=s.id});s.dom.input.addEventListener('input',function(){s.dom.input.style.height='auto';s.dom.input.style.height=Math.min(s.dom.input.scrollHeight,100)+'px'});s.dom.sendBtn.addEventListener('click',function(){handleSend(s.id)});}
function cycleGrid(){var s=[1,2,4];perPage=s[(s.indexOf(perPage)+1)%3];curPage=0;refreshUI()}
function prevPage(){if(curPage>0){curPage--;refreshUI()}}
function nextPage(){if(curPage<Math.ceil(panels.length/perPage)-1){curPage++;refreshUI()}}
function refreshUI(){var total=Math.ceil(panels.length/perPage),start=curPage*perPage;grid.className='grid g'+perPage;$('gridBtn').textContent='⊞';if(total>1){pageBar.style.display='flex';$('pgNum').textContent=(curPage+1)+'/'+total;$('pgPrev').disabled=curPage<=0;$('pgNext').disabled=curPage>=total-1}else{pageBar.style.display='none'}panels.forEach(function(p,i){p.dom.wrapper.classList.toggle('on',i>=start&&i<start+perPage)});$('summary').textContent=panels.length+'窗'+(total>1?' '+(curPage+1)+'/'+total:'')}
function handleSend(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;if(p.isStreaming){stopStream(pid);return}if(orchMode){handleOrchSend(p);return}var task=p.dom.input.value.trim();if(!task)return;var isNew=!p.currentConvo.sessionId;if(isNew)p.currentConvo.sessionId='xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0,v=c==='x'?r:(r&0x3|0x8);return v.toString(16)});var forceAgent='',actualTask=task;var m=task.match(/^@(\S+)\s+/);if(m){forceAgent=m[1];actualTask=task.slice(m[0].length)}setStreaming(p,!0);p.dom.input.value='';p.dom.input.style.height='auto';p.dom.route.innerHTML='<span>…</span>';p.dom.agentName.textContent='…';if(p.dom.empty)p.dom.empty.style.display='none';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task});p.currentAssistantMsg=addMsg(p,'assistant','<span class="cursor"></span>');p._receivedDone=!1;p.abortController=new AbortController();apiFetch('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:actualTask,force_agent:forceAgent,proj_dir:projDir||undefined,api_key:apiKey||undefined,api_provider:apiProvider||undefined}),signal:p.abortController.signal}).then(function(r){return r.json()}).then(function(route){if(route.error)throw new Error(route.error);p.dom.route.innerHTML='<span>🤖 '+route.agent+'</span><span>🧠 '+route.model+'</span>';p.dom.agentName.textContent=route.agent;var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();return apiFetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:actualTask,force_agent:forceAgent,model:route.model,proj_dir:projDir||undefined,session_id:p.currentConvo.sessionId,is_new_session:isNew,api_key:apiKey||undefined,api_provider:apiProvider||undefined}),signal:p.abortController.signal})}).then(function(resp){var reader=resp.body.getReader();p._reader=reader;var decoder=new TextDecoder(),buf='',txt='';function read(){reader.read().then(function(result){if(result.done){p._reader=null;if(!p._receivedDone&&p.isStreaming){p.currentAssistantMsg.innerHTML+='<div style="color:var(--warn);margin-top:4px;font-size:11px;cursor:pointer" onclick="retrySend('+pid+')">⚠ 连接中断 — 点击重试</div>'}finish();return}buf+=decoder.decode(result.value,{stream:!0});var lines=buf.split('\n');buf=lines.pop()||'';for(var i=0;i<lines.length;i++){var line=lines[i];if(line.indexOf('event:')===0)continue;if(line.indexOf('data: ')!==0)continue;try{var d=JSON.parse(line.slice(6));if(d.content){txt+=d.content;p.currentAssistantMsg.innerHTML=renderMD(txt)+'<span class="cursor"></span>';p.dom.messages.scrollTop=p.dom.messages.scrollHeight}else if(d.elapsed){p._receivedDone=!0;p.dom.route.innerHTML+='<span>⏱ '+d.elapsed+'s</span><span>💰 $'+d.cost+'</span>'}else if(d.error){p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(d.error)+'</span>'}}catch(_){}}read()})}function finish(){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentConvo.messages.push({role:'assistant',content:txt});saveAllConvos();setStreaming(p,!1);p.dom.agentName.textContent='就绪';highlightCode(p.currentAssistantMsg);loadCostOverview()}read()}).catch(function(e){if(e.name==='AbortError'){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentAssistantMsg.innerHTML+=' <span style="color:var(--warn)">⏹ 已停止</span>';var partial=(p.currentAssistantMsg.textContent||'').replace('⏹ 已停止','').trim();if(partial){p.currentConvo.messages.push({role:'assistant',content:partial});saveAllConvos()}}else{if(p.currentAssistantMsg)p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(e.message)+'</span>'}setStreaming(p,!1);p._reader=null;p.dom.agentName.textContent='就绪'})}
function handleOrchSend(p){var task=p.dom.input.value.trim();if(!task)return;setStreaming(p,!0);p.dom.input.value='';p.dom.input.style.height='auto';p.dom.route.innerHTML='<span>🧠 智能调度</span>';if(p.dom.empty)p.dom.empty.style.display='none';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task});p.currentAssistantMsg=addMsg(p,'assistant','<span class="cursor"></span>');p.abortController=new AbortController();var planReceived=!1;fetch('/api/orchestrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:task,proj_dir:projDir||undefined,api_key:apiKey||undefined,api_provider:apiProvider||undefined}),signal:p.abortController.signal}).then(function(resp){var reader=resp.body.getReader();p._reader=reader;var decoder=new TextDecoder(),buf='',txt='',planData=null;function read(){reader.read().then(function(result){if(result.done){p._reader=null;finish();return}buf+=decoder.decode(result.value,{stream:!0});var lines=buf.split('\n');buf=lines.pop()||'';for(var i=0;i<lines.length;i++){var line=lines[i],eventType='';if(line.indexOf('event: ')===0){eventType=line.slice(7);continue}if(line.indexOf('data: ')!==0)continue;try{var d=JSON.parse(line.slice(6));if(eventType==='plan'){planData=d;return}if(d.content){txt+=d.content;p.currentAssistantMsg.innerHTML=renderMD(txt)+'<span class="cursor"></span>';p.dom.messages.scrollTop=p.dom.messages.scrollHeight}else if(d.summary){txt+=d.summary}}catch(_){}}read()})}function finish(){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentConvo.messages.push({role:'assistant',content:txt||'调度完成'});saveAllConvos();setStreaming(p,!1);if(planData&&planData.phases){executePlan(planData)};loadCostOverview()}read()}).catch(function(e){if(e.name==='AbortError'){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentAssistantMsg.innerHTML+=' <span style="color:var(--warn)">⏹ 已停止</span>'}else{if(p.currentAssistantMsg)p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(e.message)+'</span>'}setStreaming(p,!1);p._reader=null})}
function executePlan(plan){
  if(!plan||!plan.phases)return;
  showToast('调度计划: '+plan.title+' ('+plan.phases.length+'阶段)');
  var allTasks=[];
  plan.phases.forEach(function(phase){
    (phase.tasks||[]).forEach(function(t){
      allTasks.push({agent:t.agent,task:t.task,phase:phase.phase,parallel:phase.parallel});
    });
  });
  if(allTasks.length===0)return;
  if(perPage<4){perPage=4;curPage=0}
  while(panels.length<Math.min(allTasks.length+1,8))addPanel();
  refreshUI();
  var phaseIdx=0;
  function runNextPhase(){
    if(phaseIdx>=plan.phases.length)return;
    var phase=plan.phases[phaseIdx],tasks=phase.tasks||[];
    showToast('阶段'+phase.phase+': '+phase.description);
    if(phase.parallel){
      tasks.forEach(function(t,i){
        var panel=panels[i+1];if(!panel)return;
        panel.dom.input.value='@'+t.agent+' '+t.task;
        setTimeout(function(){handleSend(panel.id)},i*200);
      });
    }else{
      var ti=0;
      function runNext(){
        if(ti>=tasks.length){phaseIdx++;setTimeout(runNextPhase,500);return}
        var t=tasks[ti],panel=panels[ti+1];
        if(panel){panel.dom.input.value='@'+t.agent+' '+t.task;handleSend(panel.id)}
        ti++;setTimeout(runNext,15000);
      }
      runNext();
      return;
    }
    phaseIdx++;setTimeout(runNextPhase,20000);
  }
  setTimeout(runNextPhase,1000);
}
function stopStream(pid){var p=panels.find(function(x){return x.id===pid});if(p){if(p.abortController){p.abortController.abort();p.abortController=null}if(p._reader){try{p._reader.cancel()}catch(_){}p._reader=null}}}
function retrySend(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;stopStream(pid);setStreaming(p,!1);var lastUser=p.currentConvo.messages.filter(function(m){return m.role==='user'}).pop();if(lastUser){p.dom.input.value=lastUser.content;setTimeout(function(){handleSend(pid)},300)}}
function setStreaming(p,v){p.isStreaming=v;p.dom.input.disabled=v;p.dom.sendBtn.textContent=v?'停止':'发送';if(v){p.dom.sendBtn.classList.add('stopping');if(p.dom.dot)p.dom.dot.classList.add('busy')}else{p.dom.sendBtn.classList.remove('stopping');if(p.dom.dot)p.dom.dot.classList.remove('busy');p.abortController=null}if(!v)setTimeout(function(){p.dom.input.focus();p.dom.input.disabled=!1},50)}
function addMsg(p,role,content){var w=document.createElement('div');w.className='msg '+role;w.innerHTML='<div class="msg-label">'+(role==='user'?'你':'Agency')+'</div><div class="bubble">'+content+'</div>';p.dom.messages.appendChild(w);p.dom.messages.scrollTop=p.dom.messages.scrollHeight;return w.querySelector('.bubble')}
function saveAllConvos(){panels.forEach(function(p){if(p.currentConvo.messages.length===0)return;if(!p.currentConvo.title||p.currentConvo.title==='新对话'){var f=p.currentConvo.messages.find(function(m){return m.role==='user'});if(f)p.currentConvo.title=f.content.slice(0,40)}var idx=conversations.findIndex(function(c){return c.id===p.currentConvo.id});if(idx>=0){conversations[idx]={id:p.currentConvo.id,title:p.currentConvo.title,messages:p.currentConvo.messages,sessionId:p.currentConvo.sessionId}}else{conversations.unshift({id:p.currentConvo.id,title:p.currentConvo.title,messages:p.currentConvo.messages,sessionId:p.currentConvo.sessionId})}});var json=JSON.stringify(conversations);if(json.length>4*1024*1024){while(json.length>4*1024*1024&&conversations.length>0){conversations.pop();json=JSON.stringify(conversations)}showToast('存储空间不足，已清理旧会话',!1,'warn')}try{localStorage.setItem('agency_convos',json)}catch(e){showToast('存储空间不足，请清理历史会话',!0)}renderHistory()}
function renderHistory(){historyList.innerHTML=conversations.slice(0,30).map(function(c){return'<div class="history-item" onclick="loadConvo(\''+c.id+'\')"><div style="display:flex;align-items:center"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">'+escHtml(c.title||'新对话')+'</span><button class="del-btn" onclick="delConvo(\''+c.id+'\',event)">×</button></div><div class="time">'+new Date(c.id).toLocaleDateString('zh-CN')+'</div><div class="preview">'+escHtml((c.messages[0]&&c.messages[0].content||'').slice(0,30))+'</div></div>'}).join('')||'<div style="color:var(--muted);font-size:12px;padding:8px">暂无历史</div>'}
renderHistory();
function loadConvo(id){var c=conversations.find(function(x){return x.id===Number(id)});if(!c)return;var p=getFocusedPanel();p.currentConvo={id:c.id,title:c.title,messages:c.messages.slice(),sessionId:c.sessionId||''};p.dom.messages.innerHTML='';p.dom.route.innerHTML='';c.messages.forEach(function(m){addMsg(p,m.role,m.content)});p.dom.messages.scrollTop=p.dom.messages.scrollHeight;setTimeout(function(){p.dom.messages.querySelectorAll('.bubble').forEach(highlightCode)},100)}
function delConvo(id,e){e.stopPropagation();conversations=conversations.filter(function(c){return c.id!==Number(id)});localStorage.setItem('agency_convos',JSON.stringify(conversations));renderHistory()}
function toggleDevOverlay(){devMode=!devMode;var ov=$('devOverlay'),btn=$('devBtn');ov.classList.toggle('on',devMode);btn.classList.toggle('on',devMode);if(devMode){var ak=$('api-key');if(ak&&apiKey)ak.value=apiKey;var ap=$('api-provider');if(ap&&apiProvider)ap.value=apiProvider;loadSkillsList();loadMemList();loadRemotePanel();loadIntegrationPanel()}}
function loadSkillsList(){var el=$('skills-list');if(!el)return;fetch('/api/skills').then(function(r){return r.json()}).then(function(skills){el.innerHTML=skills.length?skills.map(function(s){return'<div style="padding:4px 0;font-size:11px"><span>'+escHtml(s.name)+'</span> <span style="color:var(--muted);font-size:10px">'+escHtml(s.description||'').slice(0,40)+'</span></div>'}).join(''):'暂无 Skills'}).catch(function(){el.innerHTML='加载失败'})}
function loadMemList(){var el=$('mem-list');if(!el)return;fetch('/api/memory').then(function(r){return r.json()}).then(function(d){var files=d.files||[];el.innerHTML=files.length?files.map(function(f){return'<div class="mem-file" onclick="openMemEditor(\''+escHtml(f.path)+'\',\''+escHtml(f.name)+'\')"><span class="icon">📄</span><span>'+escHtml(f.name)+'</span><span style="color:var(--muted);font-size:10px;margin-left:auto">'+(f.size||0)+'B</span></div>'}).join(''):'暂无记忆文件'}).catch(function(){el.innerHTML='加载失败'})}
function generateAgent(){var input=$('agent-factory-input'),output=$('agent-factory-output');var req=input.value.trim();if(!req)return;output.innerHTML='生成中…';fetch('/api/agent-generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({requirement:req,api_key:apiKey||undefined,api_provider:apiProvider||undefined})}).then(function(resp){var reader=resp.body.getReader(),decoder=new TextDecoder(),buf='',txt='';function read(){reader.read().then(function(result){if(result.done){finish();return}buf+=decoder.decode(result.value,{stream:!0});var lines=buf.split('\n');buf=lines.pop()||'';for(var i=0;i<lines.length;i++){if(lines[i].indexOf('data: ')!==0)continue;try{var d=JSON.parse(lines[i].slice(6));if(d.content)txt+=d.content;if(d.error){output.innerHTML='<span style=color:var(--danger)>'+escHtml(d.error)+'</span>';return}}catch(_){}}read()})}function finish(){output.innerHTML='<pre style=\"font-size:10px;max-height:200px;overflow:auto;background:var(--bg);padding:8px;border-radius:4px\">'+escHtml(txt)+'</pre><button class=\"new-chat-btn\" style=\"margin-top:4px\" onclick=\"saveAgent()\">保存此 Agent</button>';output._agentContent=txt}read()}).catch(function(){output.innerHTML='生成失败'})}
function saveAgent(){var txt=$('agent-factory-output')._agentContent;if(!txt)return;var m=txt.match(/name:\s*"?([a-z0-9-]+)"?/i);var name=m?m[1]:('agent-'+Date.now().toString(36));fetch('/api/agent-create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,content:txt})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('Agent 已保存: '+name);loadAgents()}else{showToast(d.error||'保存失败',!0)}}).catch(function(){showToast('保存失败',!0)})}
function toggleOrchMode(){orchMode=!orchMode;var btn=$('orchBtn');btn.classList.toggle('on',orchMode);btn.textContent=orchMode?'🧠 调度中':'🧠 调度';if(orchMode&&perPage<4){perPage=4;refreshUI()}}
document.addEventListener('keydown',function(e){if(e.key==='Escape'){panels.forEach(function(p){if(p.isStreaming)stopStream(p.id)})}if(e.ctrlKey&&e.key==='n'){e.preventDefault();addPanel()}if(e.ctrlKey&&e.key==='ArrowLeft'){e.preventDefault();prevPage()}if(e.ctrlKey&&e.key==='ArrowRight'){e.preventDefault();nextPage()}if(e.ctrlKey&&e.key==='g'){e.preventDefault();cycleGrid()}});
function renderMD(t){if(!t)return'';var h=t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');var p=0,o='';while(p<h.length){if(h.charAt(p)==='['){var e=h.indexOf(']',p);if(e!==-1&&h.charAt(e+1)==='('){var ue=h.indexOf(')',e+2);if(ue!==-1){o+='<a href="'+h.substring(e+2,ue)+'" target="_blank">'+h.substring(p+1,e)+'</a>';p=ue+1;continue}}}o+=h.charAt(p++)}h=o;h=h.replace(/\[Thinking\]([\s\S]*?)\[\/Thinking\]/gi,'<details class="think"><summary>思考过程</summary>$1</details>');h=h.replace(/```(\w*)\n([\s\S]*?)```/g,function(_,lang,code){return'<pre><code class="language-'+(lang||'plaintext')+'">'+escHtml(code)+'</code></pre>'});h=h.replace(/(\|.+\|\n?)+/gm,function(m){var r=m.trim().split('\n'),o='<table>';for(var i=0;i<r.length;i++){var c=r[i].split('|').filter(function(x){return!!x.trim()});var t=i?'td':'th';o+='<tr>'+c.map(function(x){return'<'+t+'>'+x.trim()+'</'+t+'>'}).join('')+'</tr>'}return o+'</table>'});h=h.replace(/`([^`]+)`/g,'<code>$1</code>');h=h.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');h=h.replace(/\*(.+?)\*/g,'<em>$1</em>');h=h.replace(/^### (.+)$/gm,'<h3>$1</h3>');h=h.replace(/^## (.+)$/gm,'<h2>$1</h2>');h=h.replace(/^# (.+)$/gm,'<h1>$1</h1>');h=h.replace(/^(\d+)\. (.+)$/gm,'<li style="margin-left:16px;list-style-type:decimal">$2</li>');h=h.replace(/^- (.+)$/gm,'<li style="margin-left:16px">$1</li>');h=h.replace(/\n/g,'<br>');return h}
function highlightCode(el){if(!el)return;el.querySelectorAll('pre code').forEach(function(b){if(window.hljs)try{hljs.highlightElement(b)}catch(_){}})}
function escHtml(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML}
function showToast(m,err,level){var t=document.createElement('div');t.className='toast'+(err?' error':'')+(level==='warn'?' warn':'');t.textContent=m;document.body.appendChild(t);setTimeout(function(){t.style.opacity='0';t.style.transition='opacity .3s'},2500);setTimeout(function(){t.remove()},3000)}
/* ── Harness: 仪表盘 ── */
var harnessActive=!1;
function toggleDashboard(){
  harnessActive=!harnessActive;
  var ov=$('harnessOverlay'),btn=$('dashboardBtn');
  ov.classList.toggle('on',harnessActive);
  btn.classList.toggle('on',harnessActive);
  if(harnessActive){renderHarnessTab('overview')}
  else{[_subTimer,_ctxTimer].forEach(function(t){if(t){clearInterval(t)}});_subTimer=_ctxTimer=null}
}
var dragTarget=null,dragOX=0,dragOY=0;
function onDrag(e){if(!dragTarget)return;dragTarget.style.left=(e.clientX-dragOX)+'px';dragTarget.style.top=(e.clientY-dragOY)+'px'}
function offDrag(){dragTarget=null;document.removeEventListener('mousemove',onDrag);document.removeEventListener('mouseup',offDrag)}
['harnessOverlay','devOverlay'].forEach(function(id){
  var el=document.getElementById(id);if(!el)return;
  var tab=el.querySelector('.harness-overlay-tabs');if(!tab)return;
  tab.addEventListener('mousedown',function(e){if(e.target.tagName==='BUTTON')return;dragTarget=el;dragOX=e.clientX-el.offsetLeft;dragOY=e.clientY-el.offsetTop;document.addEventListener('mousemove',onDrag);document.addEventListener('mouseup',offDrag);e.preventDefault()})
});
document.querySelectorAll('.harness-overlay-tab').forEach(function(t){t.addEventListener('click',function(){document.querySelectorAll('.harness-overlay-tab').forEach(function(x){x.classList.remove('active')});t.classList.add('active');renderHarnessTab(t.dataset.htab)})});
function renderHarnessTab(tab){
  var el=$('harnessContent');if(!el)return;
  if(tab==='overview'){
    el.innerHTML='<div class="cost-kpis" style="margin-bottom:10px"><div class="cost-kpi"><span class="kpi-val" id="hov-cost-today">—</span><span class="kpi-label">今日费用</span></div><div class="cost-kpi"><span class="kpi-val" id="hov-cost-30d">—</span><span class="kpi-label">30天</span></div><div class="cost-kpi"><span class="kpi-val" id="hov-calls">—</span><span class="kpi-label">调用</span></div></div><div style="margin-bottom:8px"><span style="font-size:11px;color:var(--muted);font-weight:600">每日费用趋势</span><canvas id="cost-trend-canvas" width="440" height="100" style="width:100%;height:100px;display:block;background:var(--surface2);border-radius:6px;margin-top:4px"></canvas></div><div style="margin-bottom:8px"><span style="font-size:11px;color:var(--muted);font-weight:600">模型费用分布</span><div id="model-bars" style="background:var(--surface2);border-radius:6px;padding:6px 8px;font-size:10px;color:var(--muted);min-height:60px">—</div></div><div style="display:flex;gap:6px;margin-bottom:8px"><div class="cost-kpi" style="flex:1"><span class="kpi-val" id="hov-cache-saved" style="color:var(--warn)">$0</span><span class="kpi-label">缓存节省</span></div><div class="cost-kpi" style="flex:1"><span class="kpi-val" id="hov-cache-tokens" style="font-size:11px">0</span><span class="kpi-label">缓存Token</span></div></div><div id="cost-alerts" style="margin-bottom:6px;font-size:10px"></div><h4 style="font-size:11px;color:var(--muted);margin-bottom:6px">上下文窗口</h4><div class="ctx-gauge" style="height:14px;margin-bottom:4px"><div class="ctx-gauge-fill" id="hctx-fill" style="width:0%"></div></div><div style="font-size:11px;display:flex;justify-content:space-between"><span id="hctx-text">0 / 500K</span><span id="hctx-cache" style="color:var(--muted)">缓存: —</span></div><div id="hctx-detail" style="font-size:10px;color:var(--muted);margin-top:4px"></div>';
    loadContextDetail();loadCostOverview();
  }
  else if(tab==='permission'){el.innerHTML='<h3 style="margin-bottom:8px">权限管线</h3><div id="hperm-log" style="font-size:11px">加载中…</div>';loadPermHistory()}
  else if(tab==='subagents'){el.innerHTML='<h3 style="margin-bottom:8px">SubAgent 任务树</h3><div id="hsub-tree" style="font-size:11px;color:var(--muted)">加载中…</div>';loadSubagents()}
  else if(tab==='hooks'){el.innerHTML='<h3 style="margin-bottom:8px">Hooks 生命周期</h3><div id="hhooks-log" style="font-size:11px;color:var(--muted)">从事件日志中加载…</div>';loadHooksLog()}
  else if(tab==='mcp'){el.innerHTML='<h3 style="margin-bottom:8px">MCP 集成</h3><div id="hmcp-list" style="font-size:11px;color:var(--muted)">加载中…</div>';loadMCPDetail()}
}
function loadCostOverview(){
  fetch('/api/cost?days=30').then(function(r){return r.json()}).then(function(d){
    if(!d||!d.total)return;
    var t=d.total,td=d.today;
    var el=function(id){return document.getElementById(id)};
    if(el('hov-cost-today'))el('hov-cost-today').textContent='$'+(td.cost||0).toFixed(4);
    if(el('hov-cost-30d'))el('hov-cost-30d').textContent='$'+(t.cost||0).toFixed(4);
    if(el('hov-calls'))el('hov-calls').textContent=t.calls||0;
    var cache=d.cache||{};
    if(el('hov-cache-saved'))el('hov-cache-saved').textContent='$'+(cache.saved||0).toFixed(4);
    if(el('hov-cache-tokens'))el('hov-cache-tokens').textContent=((cache.read_tok||0)+(cache.write_tok||0)).toLocaleString();
    drawCostTrend(d.by_date||[]);
    drawModelBars(d.by_model||[]);
    renderCostAlerts(d.alerts||[]);
  }).catch(function(e){console.debug('loadCostOverview failed',e)});
}
function drawCostTrend(byDate){
  var c=document.getElementById('cost-trend-canvas');if(!c)return;
  var ctx=c.getContext('2d'),W=c.width,H=c.height,pad=28;
  ctx.clearRect(0,0,W,H);
  if(!byDate.length){ctx.fillStyle='#5f6877';ctx.font='10px sans-serif';ctx.fillText('暂无数据',W/2-20,H/2);return}
  var maxCost=0;byDate.forEach(function(d){maxCost=Math.max(maxCost,d.cost||0)});
  if(maxCost===0)maxCost=0.01;
  var barW=(W-pad*2)/byDate.length-2;if(barW<1)barW=1;
  var dailyWarn=5.0;
  ctx.strokeStyle='rgba(251,191,32,.3)';ctx.setLineDash([3,3]);
  var warnY=H-pad-(dailyWarn/maxCost*(H-pad*2));
  ctx.beginPath();ctx.moveTo(pad,warnY);ctx.lineTo(W-pad,warnY);ctx.stroke();
  ctx.setLineDash([]);
  byDate.forEach(function(d,i){
    var h=d.cost?((d.cost||0)/maxCost*(H-pad*2)):0;
    var x=pad+i*((W-pad*2)/byDate.length),y=H-pad-h;
    ctx.fillStyle=(d.cost||0)>dailyWarn?'#f87171':'#22d3a0';
    ctx.fillRect(x,y,barW,h);
    if(byDate.length<=14){
      ctx.fillStyle='#9ca3b4';ctx.font='8px sans-serif';
      ctx.fillText((d.date||'').slice(5),x-2,H-6);
    }
  });
}
function drawModelBars(models){
  var el=document.getElementById('model-bars');if(!el)return;
  if(!models.length){el.innerHTML='暂无数据';return}
  var totalCost=0;models.forEach(function(m){totalCost+=m.cost||0});
  el.innerHTML=models.map(function(m,i){
    var pct=totalCost>0?((m.cost||0)/totalCost*100):0;
    var colors=['#22d3a0','#60a5fa','#fbbf20','#f87171','#a78bfa','#34d399'];
    return'<div style="display:flex;align-items:center;margin:3px 0;gap:6px">'+
      '<span style="min-width:80px;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+escHtml(m.model||'?')+'</span>'+
      '<div style="flex:1;height:12px;background:var(--bg);border-radius:6px;overflow:hidden">'+
        '<div style="height:100%;width:'+pct+'%;background:'+(colors[i%colors.length])+';border-radius:6px;min-width:2px"></div>'+
      '</div>'+
      '<span style="font-size:9px;min-width:44px;text-align:right">$'+(m.cost||0).toFixed(4)+'</span>'+
    '</div>';
  }).join('');
}
function renderCostAlerts(alerts){
  var el=document.getElementById('cost-alerts');if(!el)return;
  if(!alerts||!alerts.length){el.innerHTML='';return}
  el.innerHTML=alerts.slice(0,5).map(function(a){
    var bg=a.level==='danger'?'rgba(248,113,113,.15)':'rgba(251,191,32,.12)';
    var border=a.level==='danger'?'#f87171':'#fbbf20';
    return'<div style="padding:4px 8px;margin:2px 0;background:'+bg+';border-left:2px solid '+border+';border-radius:3px;font-size:10px">'+
      (a.level==='danger'?'🔴 ':'⚠️ ')+escHtml(a.msg)+'</div>';
  }).join('');
}
/* ── 权限 Toast ── */
function showPermToast(data){
  var t=document.createElement('div');t.className='toast warn';
  var riskLabel=data.risk&&data.risk.level==='high'?'🔴 高风险':'🟡 中风险';
  t.innerHTML='<div><strong>'+riskLabel+'</strong> · '+escHtml(data.tool_name)+'</div><div style="font-size:10px;color:var(--muted);margin-top:2px">'+escHtml((data.tool_input||'').slice(0,100))+'</div><div class="toast-acts"><button class="allow">允许</button><button class="deny">拒绝</button><button class="always">总是允许此模式</button></div>';
  document.body.appendChild(t);
  t.querySelector('.allow').onclick=function(){sendPermDecision(data,'allow');t.remove()};
  t.querySelector('.deny').onclick=function(){sendPermDecision(data,'deny');t.remove()};
  t.querySelector('.always').onclick=function(){addAllowRule(data);sendPermDecision(data,'allow');t.remove()};
  setTimeout(function(){if(document.body.contains(t)){sendPermDecision(data,'deny');t.remove()}},30000);
}
function sendPermDecision(data,decision){
  fetch('/api/permissions/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool_name:data.tool_name,decision:decision,risk:data.risk||{},reason:decision})});
}
function addAllowRule(data){
  fetch('/api/permissions/allowlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rule:data.tool_name})});
  showToast('已添加规则: '+data.tool_name);
}
function loadPermHistory(){
  fetch('/api/permissions/history?limit=100').then(function(r){return r.json()}).then(function(d){
    var el=$('hperm-log');if(!el)return;
    if(d.history&&d.history.length){el.innerHTML=d.history.map(function(e){return'<div class="perm-item '+e.decision+'"><span class="pdec">'+(e.decision==='allow'?'✓':e.decision==='deny'?'✗':'⚠')+'</span> '+escHtml(e.tool||'?')+' <span style="color:var(--muted);font-size:9px">'+e.time+(e.reason?' · '+escHtml(e.reason):'')+'</span></div>'}).join('')}else{el.innerHTML='暂无权限记录'}
  }).catch(function(){var el=$('hperm-log');if(el)el.innerHTML='加载失败'});
}
/* ── 上下文工程 ── */
var _ctxTimer=null;
function loadContextDetail(){
  fetch('/api/harness/context').then(function(r){return r.json()}).then(function(d){
    var ttl=d.total_tokens||0,pct=ttl>0?Math.min(100,Math.round(ttl/500000*100)):0;
    var fill=$('hctx-fill'),text=$('hctx-text'),cache=$('hctx-cache'),detail=$('hctx-detail');
    if(fill){fill.style.width=pct+'%';fill.className='ctx-gauge-fill'+(pct>85?' danger':pct>60?' warn':'')}
    if(text)text.textContent=ttl.toLocaleString()+' / 500K';
    if(cache)cache.textContent='缓存命中: '+(d.cache_hit_rate||0)+'% · 省 $'+(d.cost_est?d.cost_est.cache_saved.toFixed(6):'0');
    if(detail){
      var comp=d.composition||{};
      detail.innerHTML='输入 '+(d.input_tokens||0).toLocaleString()+' · 输出 '+(d.output_tokens||0).toLocaleString()+'<br>'+
        '组成: 系统 ~'+comp.system_pct+'% · 对话 ~'+comp.conversation_pct+'% · 工具 ~'+comp.tool_pct+'%<br>'+
        '会话: '+d.messages+'条消息 · '+d.tool_calls+'次工具 · 费用 $'+(d.cost_est?d.cost_est.total.toFixed(6):'0')+
        (d.duration_s?' · '+d.duration_s+'s':'')+(d.last_update?' · '+d.last_update:'');
    }
  }).catch(function(){var el=$('hctx-detail');if(el)el.innerHTML='加载失败'});
  if(_ctxTimer)clearInterval(_ctxTimer);
  _ctxTimer=setInterval(function(){if($('harnessOverlay').classList.contains('on'))loadContextDetail()},10000);
}
/* ── SubAgent 任务树 ── */
var _subTimer=null;
function loadSubagents(){
  fetch('/api/harness/subagents').then(function(r){return r.json()}).then(function(d){
    var el=$('hsub-tree');if(!el)return;
    if(d.tree&&d.tree.length){var html='<div style="margin-bottom:6px;color:var(--text2);font-size:11px">'+d.stats.total+' 个 · '+d.stats.done+' 完成 '+(d.stats.running||0)+' 运行中 '+(d.stats.failed||0)+' 失败</div>';
    d.tree.forEach(function(a,i){
      var icon=a.hasOutput?'✅':(a.status==='running'?'🔄':'⬤');
      var color=a.hasOutput?'var(--accent)':(a.status==='running'?'var(--warn)':'var(--muted)');
      html+='<details style="margin:2px 0;background:var(--surface2);border-radius:4px;font-size:11px"><summary style="padding:4px 8px;cursor:pointer"><span style="color:'+color+'">'+icon+'</span> '+escHtml(a.name)+' <span style="color:var(--muted);font-size:10px">'+escHtml(a.type||'')+'</span></summary><div style="padding:4px 12px 8px;font-size:10px;color:var(--text2)">'+escHtml(a.description||'无描述')+'<br>项目: '+escHtml(a.project||'')+'</div></details>';
    });
    el.innerHTML=html}else{el.innerHTML='<span style="color:var(--muted)">暂无 SubAgent 记录</span>'}
    // 自动刷新
    if(_subTimer)clearInterval(_subTimer);
    _subTimer=setInterval(function(){if($('harnessOverlay').classList.contains('on'))loadSubagents()},5000);
  }).catch(function(){var el=$('hsub-tree');if(el)el.innerHTML='加载失败'});
}
/* ── Hooks 日志 ── */
function loadHooksLog(){
  var hlogs=window._hlogs||[];
  fetch('/api/harness/events?limit=50').then(function(r){return r.json()}).then(function(d){
    var events=d.events||[],el=$('hhooks-log');if(!el)return;
    if(events.length){el.innerHTML=events.map(function(e){return'<div style="padding:3px 6px;margin:1px 0;font-size:10px;border-left:2px solid var(--accent);background:var(--surface2)"><strong>'+escHtml(e.type)+'</strong> <span style="color:var(--muted)">'+new Date(e.ts*1000).toLocaleTimeString()+'</span></div>'}).join('')}else{el.innerHTML='暂无 Hook 事件'}
  }).catch(function(){var el=$('hhooks-log');if(el)el.innerHTML='加载失败'});
}
/* ── MCP 详情 ── */
function loadMCPDetail(){
  fetch('/api/mcp/status').then(function(r){return r.json()}).then(function(d){
    var el=$('hmcp-list'),sel=$('mcp-status');if(!el)return;
    var servers=d.servers||[];
    var html=servers.length?servers.map(function(s){return'<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)"><div style="font-weight:600;font-size:12px">'+escHtml(s.name)+' <span style="font-size:9px;color:'+(s.running?'var(--accent)':'var(--muted)')+'">● '+(s.running?'活跃':'离线')+'</span></div><div style="font-size:10px;color:var(--muted)">'+escHtml(s.command||'')+(s.args||[]).join(' ')+'</div></div>'}).join(''):'暂无 MCP 服务器';
    el.innerHTML=html;if(sel)sel.innerHTML=html;
  }).catch(function(){var el=$('hmcp-list');if(el)el.innerHTML='加载失败'});
}
function openMemEditor(path,name){
  var fname=name.split('\\').pop().split('/').pop();
  fetch('/api/memory/'+encodeURIComponent(fname)).then(function(r){return r.json()}).then(function(d){
    if(d.error){showToast(d.error,!0);return}
    var ed=$('mem-editor');
    ed.innerHTML='<div style="margin-bottom:4px;font-size:11px;color:var(--text2)">编辑: '+escHtml(d.name)+'</div><textarea class="mem-editor" id="mem-edit-area">'+escHtml(d.content)+'</textarea><div style="margin-top:6px;display:flex;gap:6px"><button class="btn" onclick="saveMemFile(\''+escHtml(fname)+'\')">💾 保存</button><button class="btn" onclick="document.getElementById(\'mem-editor\').innerHTML=\'\';loadMemList()">取消</button></div>';
  }).catch(function(){showToast('加载文件失败',!0)});
}
function saveMemFile(name){
  var content=document.getElementById('mem-edit-area');if(!content)return;
  fetch('/api/memory/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:content.value})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('已保存: '+d.name);document.getElementById('mem-editor').innerHTML='';loadMemList()}else{showToast(d.error||'保存失败',!0)}});
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
/* ── Agent 提示词查看/编辑 ── */
var currentPromptAgent='';
function viewAgentPrompt(name){currentPromptAgent=name;$('apm-title').textContent='编辑: '+name;$('apm-textarea').value='加载中…';$('agentPromptOverlay').classList.add('on');fetch('/api/agents/'+encodeURIComponent(name)).then(function(r){return r.json()}).then(function(d){if(d.error){showToast(d.error,!0);return}$('apm-textarea').value=d.content}).catch(function(){showToast('加载失败',!0)})}
function closeAgentPrompt(){$('agentPromptOverlay').classList.remove('on');currentPromptAgent=''}
function saveAgentPrompt(){var content=$('apm-textarea').value;if(!currentPromptAgent||!content)return;fetch('/api/agent-update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:currentPromptAgent,content:content})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('已保存: '+currentPromptAgent);closeAgentPrompt();loadAgents()}else{showToast(d.error||'保存失败',!0)}}).catch(function(){showToast('保存失败',!0)})}
document.querySelector('.sidebar-tab[data-tab=\"project\"]')&&document.querySelector('.sidebar-tab[data-tab=\"project\"]').addEventListener('click',function(){loadFileTree(projDir)});
/* ── 集成面板 ── */
function loadIntegrationPanel(){
  var el=$('integration-panel');if(!el)return;
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
    el.innerHTML=html;
    var btn=document.getElementById('hook-copy-btn');
    if(btn)btn.onclick=function(){copyText(hookUrl)};
  }).catch(function(){el.innerHTML='加载失败'});
}
function copyText(text){
  var ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showToast('已复制');
}
/* ── 远端访问面板 ── */
function loadRemotePanel(){
  var el=$('remote-panel');if(!el){console.debug('remote-panel not found');return}
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
    el.innerHTML=html;
  }).catch(function(e){console.error('loadRemotePanel:',e);el.innerHTML='加载失败: '+escHtml(e.message)});
}
function toggleRemote(on){
  fetch('/api/remote/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:on})}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      if(d.token){authToken=d.token;localStorage.setItem('agency_auth_token',d.token);showToast('远端已开启')}
      else showToast('远端已关闭');
      loadRemotePanel();
    } else showToast(d.error||'操作失败',!0);
  }).catch(function(e){showToast('操作失败: '+e.message,!0);console.error(e)});
}
function setRemoteToken(){
  var t=$('remote-token-input').value.trim();if(!t)return;
  fetch('/api/remote/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:true,token:t})}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){authToken=d.token;localStorage.setItem('agency_auth_token',d.token);$('remote-token-input').value='';showToast('密码已更新');}
    else showToast(d.error||'更新失败',!0);
  });
}
function genRemoteToken(){
  fetch('/api/remote/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:true,token:''})}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){authToken=d.token;localStorage.setItem('agency_auth_token',d.token);$('remote-token-input').value=d.token;showToast('新密码: '+d.token);}
    else showToast(d.error||'生成失败',!0);
  });
}
function copyRemoteUrl(){
  var el=$('remote-url');if(!el)return;
  el.select();document.execCommand('copy');showToast('已复制连接地址');
}
addPanel();
