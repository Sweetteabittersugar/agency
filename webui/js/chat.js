/* Agency — 聊天面板 + SSE流式 + 分屏 */
var stageStatus={};document.addEventListener('keydown',function(e){if(e.key==='Escape'){panels.forEach(function(p){if(p.dom.templateDropdown)p.dom.templateDropdown.classList.remove('on')})}});
function mkPanel(isOrch){return{id:++pidSeq,isStreaming:!1,abortController:null,_lastAgent:null,isOrchMode:isOrch||!1,currentConvo:{id:Date.now(),title:'',messages:[],sessionId:''},currentAssistantMsg:null,dom:{}}}
function addPanel(isOrch){if(panels.length>=12){showToast("最多12个面板，请先关闭一些再新建",!0,"warn");return null}var s=mkPanel(isOrch);panels.push(s);buildPanelDOM(s);curPage=Math.floor((panels.length-1)/perPage);refreshUI();return s}
function removePanel(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;if(panels.length<=1)return;if(p.isStreaming&&!confirm('面板正在生成回复，确定关闭？'))return;if(p.currentConvo.messages.length>0&&!confirm('关闭面板将丢失当前对话，确定？'))return;var idx=panels.findIndex(function(p){return p.id===pid});if(idx<0)return;if(p.isStreaming&&p.abortController)p.abortController.abort();var savedConvo={id:p.currentConvo.id,title:p.currentConvo.title,messages:p.currentConvo.messages.slice(),sessionId:p.currentConvo.sessionId};var savedRoute=p.dom.route.innerHTML;var savedAgent=p._lastAgent;var savedInput=p.dom.input.value;panels.splice(idx,1);p.dom.wrapper.remove();if(p.currentConvo.sessionId){/*close panel->kill Claude process to prevent zombie*/api.post('/api/sessions/kill',{session_id:p.currentConvo.sessionId}).catch(function(){})}if(window.stopTerminal)stopTerminal(pid);if(focusedPid===pid)focusedPid=null;var total=Math.ceil(panels.length/perPage);if(curPage>=total)curPage=Math.max(0,total-1);refreshUI();showUndoableToast(t('panelClosed'),function(){var np=mkPanel();panels.push(np);buildPanelDOM(np);np.currentConvo=savedConvo;np._lastAgent=savedAgent;np.dom.route.innerHTML=savedRoute;np.dom.input.value=savedInput;np.dom.sendBtn.disabled=!savedInput.trim();if(savedConvo.messages.length>0){np.dom.empty.style.display='none';savedConvo.messages.forEach(function(m){addMsg(np,m.role,m.content)})}refreshUI()},5000)}
function clearAllPanels(){panels.forEach(function(p){if(p.isStreaming&&p.abortController)p.abortController.abort()});while(panels.length>1){var p=panels.pop();p.dom.wrapper&&p.dom.wrapper.remove()}var p=panels[0];p.isOrchMode=true;var mb=document.getElementById('mode-'+p.id);if(mb)mb.textContent='👑';p.currentConvo={id:Date.now(),title:'',messages:[],sessionId:''};p.dom.messages.innerHTML='<div class="empty-panel"><div class="logo">👋</div><h3>'+t('chatEmptyTitle')+'</h3><div class="empty-state-actions"><button class="btn quick-action" onclick="quickAction('+p.id+',1)">'+t('chatEmptyBtn1')+'</button><button class="btn quick-action" onclick="quickAction('+p.id+',2)">'+t('chatEmptyBtn2')+'</button><button class="btn quick-action" onclick="quickAction('+p.id+',3)">'+t('chatEmptyBtn3')+'</button></div></div>';p.dom.route.innerHTML='<span style="color:var(--muted);font-size:9px">👑 总调度</span>';p.dom.agentName.textContent='就绪';curPage=0;refreshUI()}
function buildPanelDOM(s){var w=document.createElement('div');w.className='panel on';var emptyHTML='<div class="empty-panel"><div class="logo">👋</div><h3>'+t('chatEmptyTitle')+'</h3><div class="empty-state-actions"><button class="btn quick-action" onclick="quickAction('+s.id+',1)">'+t('chatEmptyBtn1')+'</button><button class="btn quick-action" onclick="quickAction('+s.id+',2)">'+t('chatEmptyBtn2')+'</button><button class="btn quick-action" onclick="quickAction('+s.id+',3)">'+t('chatEmptyBtn3')+'</button></div></div>';w.innerHTML='<div class="panel-bar"><span class="pinfo"><span class="pdot"></span><span class="pagent">就绪</span></span><select class="panel-agent-select" onchange="onPanelAgentChange('+s.id+',this)"><option value="">Agent...</option></select><button onclick="toggleTerminal(\''+s.id+'\')" title="终端" style="font-size:14px;background:none;border:none;color:var(--muted);cursor:pointer;padding:0 4px">💻</button>'+
  /* Phase 2: 面板级 Provider 切换——每个面板独立选择 AI 供应商 */
  '<select class="panel-provider-select" onchange="onPanelProviderChange(\''+s.id+'\',this.value)" style="font-size:9px;background:var(--bg);color:var(--text);border:1px solid var(--border);padding:1px 4px;border-radius:3px;margin:0 4px;width:auto;max-width:90px">'+
    '<option value="deepseek">DeepSeek</option>'+
    '<option value="anthropic">Anthropic</option>'+
    '<option value="openai">OpenAI</option>'+
    '<option value="google">Google</option>'+
    '<option value="xai">xAI</option>'+
    '<option value="qwen">Qwen</option>'+
    '<option value="zhipu">Zhipu</option>'+
  '</select>'+
  '<span class="panel-tokens" id="tokens-'+s.id+'" title="上下文用量" style="font-size:11px;color:#888;margin-left:auto;cursor:pointer" onclick="showPanelContext(\''+s.id+'\')">📊 --</span><button class="mode-toggle" id="mode-'+s.id+'" onclick="togglePanelMode('+s.id+')" title="空会话时可切换模式" style="background:transparent;border:1px solid var(--border);border-radius:3px;color:var(--muted);cursor:pointer;font-size:10px;padding:1px 5px;margin-right:4px">'+(s.isOrchMode?'👑':'🔀')+'</button><button class="pclose">✕</button></div><div class="panel-msgs">'+emptyHTML+'</div><div class="pipeline-bar" style="display:none"></div><div class="panel-route"><span style="color:var(--muted);font-size:9px">'+t('routeEmpty')+'</span></div><div class="panel-inp"><textarea placeholder="'+t('inputPlaceholder')+'" rows="1" autocomplete="off"></textarea><button class="template-btn" title="模板">📋</button><button disabled>发送</button><div class="template-dropdown"></div></div>';grid.appendChild(w);s.dom={wrapper:w,messages:w.querySelector('.panel-msgs'),pipeline:w.querySelector('.pipeline-bar'),route:w.querySelector('.panel-route'),input:w.querySelector('textarea'),sendBtn:w.querySelector('.panel-inp button:last-of-type'),templateBtn:w.querySelector('.template-btn'),templateDropdown:w.querySelector('.template-dropdown'),dot:w.querySelector('.pdot'),agentName:w.querySelector('.pagent'),empty:w.querySelector('.empty-panel')};w.querySelector('.pclose').addEventListener('click',function(e){e.stopPropagation();removePanel(s.id)});s.dom.input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();handleSend(s.id)}});s.dom.input.addEventListener('focus',function(){focusedPid=s.id;try{var draft=localStorage.getItem('chat_draft_'+s.id);if(draft&&!s.dom.input.value.trim()){s.dom.input.value=draft;s.dom.input.style.height='auto';s.dom.input.style.height=Math.min(s.dom.input.scrollHeight,100)+'px';s.dom.sendBtn.disabled=false}}catch(e){}// 粘性 Agent
var sticky=localStorage.getItem('sticky_agent');if(sticky&&!s._lastAgent&&!s.dom.input.value.trim()){s._lastAgent=sticky;s.dom.route.innerHTML='<span style="color:var(--accent);font-size:9px">📌 '+escHtml(sticky)+'</span>';}});s.dom.input.addEventListener('blur',function(){var v=s.dom.input.value.trim();try{if(v)localStorage.setItem('chat_draft_'+s.id,v);else localStorage.removeItem('chat_draft_'+s.id)}catch(e){}});s.dom.input.addEventListener('input',function(){s.dom.input.style.height='auto';s.dom.input.style.height=Math.min(s.dom.input.scrollHeight,100)+'px';s.dom.sendBtn.disabled=!s.dom.input.value.trim();var v=s.dom.input.value;var fp=typeof detectFilePath==='function'?detectFilePath(v):null;if(fp){if(!s.dom.input.nextElementSibling||!s.dom.input.nextElementSibling.classList.contains('file-path-hint')){var hint=document.createElement('div');hint.className='file-path-hint';hint.textContent=t('filePickerHint');s.dom.input.parentNode.insertBefore(hint,s.dom.input.nextElementSibling)}}else{var existingHint=s.dom.input.parentNode.querySelector('.file-path-hint');if(existingHint)existingHint.remove()}});s.dom.input.addEventListener('paste',function(e){var cd=e.clipboardData||window.clipboardData;var text=cd&&cd.getData?cd.getData('text'):'';if(text&&text.length>5000){if(!confirm(t('pasteLargeText').replace('{N}',text.length))){e.preventDefault()}}});s.dom.sendBtn.addEventListener('click',function(){handleSend(s.id)});
  // 初始化 Agent 下拉
  setTimeout(function(){
    var select = w.querySelector('.panel-agent-select');
    if (select && select.options.length <= 1 && window.agents && window.agents.length) {
      window.agents.forEach(function(a) {
        var opt = document.createElement('option');
        opt.value = a.name;
        opt.textContent = a.name;
        select.appendChild(opt);
      });
    }
  }, 300);
}
function cycleGrid(){var s=[1,2,4];var n=s[(s.indexOf(perPage)+1)%3];if(typeof setLayout==='function'){setLayout(n)}else{perPage=n;curPage=0;refreshUI()}}
function prevPage(){if(curPage>0){curPage--;refreshUI()}}
function nextPage(){if(curPage<Math.ceil(panels.length/perPage)-1){curPage++;refreshUI()}}
function refreshUI(){
var total=Math.ceil(panels.length/perPage),start=curPage*perPage;if(curPage>=total)curPage=Math.max(0,total-1);start=curPage*perPage;// 清除残留内联样式，统一 CSS Grid
grid.style.display='';grid.style.flexWrap='';grid.className='grid g'+perPage;grid.querySelectorAll('.split-gutter').forEach(function(g){g.remove()});panels.forEach(function(p,i){var w=p.dom.wrapper;w.style.flex='';w.style.width='';w.style.height='';w.style.borderRight='';w.classList.toggle('on',i>=start&&i<start+perPage)});var gb=$('gridBtn');if(gb)gb.textContent='⊞';if(total>1){pageBar.style.display='flex';var pn=$('pgNum');if(pn)pn.textContent=(curPage+1)+'/'+total;var pp=$('pgPrev');if(pp)pp.disabled=curPage<=0;var pn2=$('pgNext');if(pn2)pn2.disabled=curPage>=total-1}else{pageBar.style.display='none'}var sum=$('summary');if(sum)sum.textContent=panels.length+'窗'+(total>1?' '+(curPage+1)+'/'+total:'')}
function pickAgent(name){var p=getFocusedPanel();p.dom.input.value='@'+name+' ';p.dom.input.focus()}
function pickAgentNew(name,e){e.preventDefault();var p=addPanel();p.dom.input.value='@'+name+' ';p.dom.input.focus()}
function toggleOrchMode(){orchMode=!orchMode;var btn=$('orchBtn');btn.classList.toggle('on',orchMode);btn.textContent=orchMode?'🧠 调度中':'🧠 调度';if(orchMode&&perPage<4){if(typeof setLayout==='function'){setLayout(4)}else{perPage=4;refreshUI()}}}
function togglePanelMode(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;if(p.currentConvo.messages.length>0){showToast('只能空会话时切换模式',!0,'warn');return}p.isOrchMode=!p.isOrchMode;var btn=document.getElementById('mode-'+pid);if(btn){btn.textContent=p.isOrchMode?'👑':'🔀';btn.title=p.isOrchMode?'总调度模式：Claude 自主处理，可调度其他 Agent':'路由模式：自动匹配专业 Agent'}p.dom.route.innerHTML='<span style="color:var(--muted);font-size:9px">'+(p.isOrchMode?'👑 总调度':'🔀 路由')+'</span>';showToast(p.isOrchMode?'已切换为总调度模式':'已切换为路由模式')}
function setStreaming(p,v){p.isStreaming=v;p.dom.input.disabled=v;p.dom.sendBtn.textContent=v?'停止':'发送';if(v){p.dom.sendBtn.classList.add('stopping');if(p.dom.dot)p.dom.dot.classList.add('busy')}else{p.dom.sendBtn.classList.remove('stopping');if(p.dom.dot)p.dom.dot.classList.remove('busy');p.abortController=null}if(!v)setTimeout(function(){p.dom.input.disabled=!1},50)}
function addMsg(p,role,content){var w=document.createElement('div');w.className='msg '+role;var c=role==='user'?escHtml(content):content;w.innerHTML='<div class="msg-label">'+(role==='user'?'你':'Agency')+'</div><div class="bubble">'+c+'</div>';p.dom.messages.appendChild(w);p.dom.messages.scrollTop=p.dom.messages.scrollHeight;var bubble=w.querySelector('.bubble');if(typeof addForkButton==='function'){addForkButton(bubble,p.currentConvo.messages.length,p.currentConvo.sessionId)}return bubble}
function stopStream(pid){var p=panels.find(function(x){return x.id===pid});if(p){if(p.abortController){p.abortController.abort();p.abortController=null}if(p._reader){try{p._reader.cancel()}catch(_){}p._reader=null}}if(p&&p.currentAssistantMsg&&(!p.currentAssistantMsg.textContent||p.currentAssistantMsg.textContent.trim()==='')){p.currentAssistantMsg.innerHTML='<span style="color:var(--warn)">⏹ 已停止</span>'}}
function retrySend(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;stopStream(pid);setStreaming(p,!1);var lastUser=p.currentConvo.messages.filter(function(m){return m.role==='user'}).pop();if(lastUser){p.dom.input.value=lastUser.content;setTimeout(function(){handleSend(pid)},300)}}
/* ── SSE 自动重连 ── */function sseReconnect(p){if(!p)return;p._sseRetries=(p._sseRetries||0)+1;var MAX_RETRIES=3;if(p._sseRetries>MAX_RETRIES){p.currentAssistantMsg.innerHTML+='<div class="retry-block"><span>⚠ 连接失败，已重试 '+MAX_RETRIES+' 次仍无法恢复。请检查网络或手动重试</span><button onclick="retrySend('+p.id+')" class="retry-btn">🔄 手动重试</button></div>';if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();setStreaming(p,!1);p.dom.agentName.textContent='就绪';setMessageStatus(p.id,p._assistantMsgIndex,'error','连接失败');processQueue(p.id);return}var delays=[2000,5000,15000];var delay=delays[p._sseRetries-1]||15000;showToast('连接中断，'+(delay/1000)+'秒后自动重连 ('+p._sseRetries+'/'+MAX_RETRIES+')');if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}if(p.abortController){p.abortController=null}if(p._reader){try{p._reader.cancel()}catch(_){}p._reader=null}var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentAssistantMsg.innerHTML+='<div style="color:var(--warn);font-size:11px;margin-top:4px">🔄 重连中 ('+p._sseRetries+'/'+MAX_RETRIES+')...</div>';setTimeout(function(){retrySend(p.id)},delay)}
/* ── 路由反馈：用户手动纠正错误路由 ── */
function toggleRouteFix(btn,pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;var dd=btn.parentNode.querySelector('.route-fix-dropdown');if(dd){dd.style.display=dd.style.display==='none'?'block':'none';return}dd=document.createElement('div');dd.className='route-fix-dropdown';dd.style.cssText='display:block;position:absolute;top:100%;left:0;background:var(--bg,#1a1a2e);border:1px solid var(--border,#444);border-radius:8px;max-height:300px;overflow-y:auto;z-index:100;min-width:200px;box-shadow:0 4px 12px rgba(0,0,0,0.3)';btn.parentNode.appendChild(dd);loadAgentDropdown(dd,p);document.addEventListener('click',function h(e){if(!btn.contains(e.target)&&!dd.contains(e.target)){dd.style.display='none';document.removeEventListener('click',h)}})}
function loadAgentDropdown(dd,p){var task=p._lastTask||'';var orig=p._lastAgent||'';var agentsList=typeof agents!=='undefined'&&agents.length?agents:[];function render(list){dd.innerHTML='';if(!list.length){dd.innerHTML='<div style="padding:8px;color:var(--muted)">暂无可用 Agent</div>';return}list.forEach(function(a){var item=document.createElement('div');item.style.cssText='padding:8px 12px;cursor:pointer;font-size:13px;color:var(--text,#e0e0e0)';item.textContent=(a.name===orig?'✓ ':'')+a.name;if(a.name===orig)item.style.color='var(--accent,#4a6cf7)';item.onmouseenter=function(){item.style.background='var(--accent,#4a6cf7)'};item.onmouseleave=function(){item.style.background=''};item.onclick=function(){if(a.name!==orig){api.post('/api/routing/feedback',{task:task,original_agent:orig,corrected_agent:a.name,reason:'用户手动纠正'}).catch(function(){});p.dom.input.value='@'+a.name+' '+task;stopStream(p.id);setStreaming(p,!1);setTimeout(function(){handleSend(p.id)},200)}dd.style.display='none'};dd.appendChild(item)})}if(agentsList.length){render(agentsList)}else{api.get('/api/agents').then(function(d){var arr=Array.isArray(d)?d:(d.agents||d.data||[]);if(arr.length){render(arr)}else{dd.innerHTML='<div style="padding:8px;color:var(--muted)">暂无可用 Agent</div>'}}).catch(function(){dd.innerHTML='<div style="padding:8px;color:var(--muted)">加载失败</div>'})}}
function saveConvoToServer(p){
  if(p.currentConvo.messages.length===0)return;
  if(!p.currentConvo.title||p.currentConvo.title==='新对话'){
    var f=p.currentConvo.messages.find(function(m){return m.role==='user'});
    if(f)p.currentConvo.title=f.content.slice(0,40);
  }
  var entry={id:p.currentConvo.id,title:p.currentConvo.title,messages:p.currentConvo.messages.slice(),sessionId:p.currentConvo.sessionId};
  // 本地缓存更新
  var idx=conversations.findIndex(function(c){return c.id===entry.id});
  if(idx>=0){conversations[idx]=entry}else{conversations.unshift(entry)}
  // 服务端持久化
  api.post('/api/conversations/save',entry).catch(function(){});
  renderHistory();
}
function handleSend(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;if(p._sendLock)return;p._sendLock=true;setTimeout(function(){p._sendLock=false},3000);/*3s lock window matches typical API response time*/if(p.isStreaming){stopStream(pid);return}
/* ── 消息排队 ── */
if(!p._msgQueue)p._msgQueue=[];
if(p.isStreaming||p._pendingRequest){p._msgQueue.push(pid);updateQueueIndicator(p);return}
updateQueueIndicator(p);
/* ── 排队结束 ── */if(orchMode){handleOrchSend(p);return}var task=p.dom.input.value.trim();if(!task)return;if(typeof _demoMode!=='undefined'&&_demoMode&&!apiKey){if(p.dom.empty)p.dom.empty.style.display='none';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task});simulateDemoReply(task,pid);return}var forceAgent='',actualTask=task;var m=task.match(/^@(\S+)\s+/);if(m){forceAgent=m[1];actualTask=task.slice(m[0].length);p._lastAgent=forceAgent}else if(p._lastAgent){forceAgent=p._lastAgent}/* Phase 2: WebSocket 优先，SSE 回退——SocketIO 可用时走 WS，否则保留原 SSE 路径 */var _useWS=typeof io!=='undefined'&&window._wsChatEnabled!==false;if(_useWS){handleSendWS(pid,forceAgent);return}p._pendingRequest=true;setStreaming(p,!0);p.dom.input.value='';p.dom.input.style.height='auto';try{localStorage.removeItem('chat_draft_'+pid)}catch(e){};p.dom.route.innerHTML='<span>🔄 Agent 启动中…</span>';p.dom.agentName.textContent='…';if(p.dom.empty)p.dom.empty.style.display='none';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task});p.currentAssistantMsg=addMsg(p,'assistant','<span class="cursor"></span>');p._assistantMsgIndex=p.currentConvo.messages.length;setMessageStatus(pid,p._assistantMsgIndex,'pending');p._receivedDone=!1;p._timedOut=!1;p.abortController=new AbortController();if(p._timeoutId)clearTimeout(p._timeoutId);p._timeoutId=setTimeout(function(){if(!p._receivedDone&&p.isStreaming){p._timedOut=!0;stopStream(pid);var c2=p.currentAssistantMsg.querySelector('.cursor');if(c2)c2.remove();p.currentAssistantMsg.innerHTML+='<div class="retry-block"><span>⏰ 任务超时（5分钟），是否重试？</span><button onclick="retrySend('+pid+')" class="retry-btn">🔄 重试</button></div>';p.dom.route.innerHTML='<span style="color:var(--warn)">⏰ 超时</span>';setStreaming(p,!1);p.dom.agentName.textContent='超时';setMessageStatus(pid,p._assistantMsgIndex,'error','超时');processQueue(pid)}},300000);
// ── 总调度模式：跳过路由 API，直接走 Chat ──
var _orchMode=p.isOrchMode&&!forceAgent;
var _routePromise=_orchMode?Promise.resolve({agent:'',model:'',confidence:1,source:'orch',category:'👑 总调度',keyword_score:1,semantic_score:0}):apiFetch('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:actualTask,force_agent:forceAgent,proj_dir:projDir||undefined,api_key:apiKey||undefined,api_provider:apiProvider||undefined,profile:agencyProfile||'standard',output_dir:localStorage.getItem('agency_output_dir')||undefined}),signal:p.abortController.signal}).then(function(r){return r.json()});
_routePromise.then(function(route){if(route.error)throw new Error(route.error);
// ── 路由可视化 ──
var category=route.category||'';
var agent=route.agent||'auto';
var confidence=(route.confidence||0)*100;
var source=route.source||'keyword';
var kwScore=(route.keyword_score||0)*100;
var semScore=(route.semantic_score||0)*100;
var color;var statusText;
if(confidence>=80){color='var(--accent)';statusText='高置信'}
else if(confidence>=60){color='var(--warn)';statusText='中置信'}
else{color='var(--danger)';statusText='低置信'}
var routeHTML='';
if(category){routeHTML+='<span>📍 '+escHtml(category)+'</span>';}
routeHTML+=' → <span style="color:'+color+';font-weight:600">🤖 '+escHtml(agent)+' ('+Math.round(confidence)+'% '+statusText+')</span>';
var sourceLabel={'keyword':'🔑 关键词','semantic':'🧠 语义','llm':'🤖 LLM','llm_cached':'💾 LLM缓存','force':'🎯 指定','cache':'📦 缓存','fallback':'⚠ 兜底'};
routeHTML+=' <span style="font-size:9px;color:var(--muted)">'+sourceLabel[source]+'</span>';
if(kwScore>0||semScore>0){routeHTML+=' <span style="font-size:9px;color:var(--text2)">K'+Math.round(kwScore)+'/S'+Math.round(semScore)+'</span>';}
if(confidence<60 && source!=='force'){
  routeHTML+=' <button class="route-pick-btn" onclick="event.stopPropagation();showRoutePicker('+pid+')" style="font-size:9px;padding:1px 6px;margin-left:4px;background:var(--danger);color:#fff;border:none;border-radius:3px;cursor:pointer">换个 Agent</button>';
}
// 路由反馈 — 始终显示"不对，换一个"
p._lastTask=actualTask;
routeHTML+=' <span style="position:relative;display:inline-block"><button class="route-fix-btn" onclick="event.stopPropagation();toggleRouteFix(this,'+pid+')" style="font-size:11px;padding:2px 8px;margin-left:4px;background:transparent;border:1px solid var(--border,#444);border-radius:4px;color:var(--muted,#888);cursor:pointer" title="纠正路由">不对，换一个 ▾</button></span>';
p.dom.route.innerHTML=routeHTML;
p.dom.agentName.textContent=agent;p._lastAgent=agent;setMessageStatus(pid,p._assistantMsgIndex,'executing',agent);
var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();return apiFetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:actualTask,force_agent:forceAgent,model:route.model,proj_dir:projDir||undefined,session_id:p.currentConvo.sessionId||'',api_key:apiKey||undefined,api_provider:apiProvider||undefined,profile:agencyProfile||'standard',output_dir:localStorage.getItem('agency_output_dir')||undefined}),signal:p.abortController.signal})}).then(function(resp){var ct=resp.headers.get('Content-Type')||'';if(!resp.ok||ct.indexOf('text/event-stream')===-1){return resp.json().then(function(d){p._receivedDone=!0;if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}var em=d.error||d.friendly_message||('请求失败 '+resp.status);if(d.action==='open_settings'){showToast(d.friendly_message||em,'warning');if(typeof toggleDevOverlay==='function'&&!devMode)setTimeout(toggleDevOverlay,1500)}else if(d.action==='install_claude'){showToast(d.friendly_message||em,!1)}p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(em)+'</span>'+(d.install_cmd?' <code style="font-size:10px;background:var(--surface2);padding:2px 6px;border-radius:3px">'+escHtml(d.install_cmd)+'</code>':'');setMessageStatus(pid,p._assistantMsgIndex,'error',em);setStreaming(p,!1);p.dom.agentName.textContent='错误';processQueue(pid)}).catch(function(){p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ 请求失败 ('+resp.status+')</span>';setMessageStatus(pid,p._assistantMsgIndex,'error','HTTP '+resp.status);setStreaming(p,!1);p.dom.agentName.textContent='错误';processQueue(pid)})}var reader=resp.body.getReader();p._reader=reader;var decoder=new TextDecoder(),buf='',txt='';function read(){reader.read().then(function(result){if(result.done){p._reader=null;if(!p._receivedDone&&p.isStreaming){if(p._timedOut){p.currentAssistantMsg.innerHTML+='<div class="retry-block"><span>⚠ 任务超时</span><button onclick="retrySend('+pid+')" class="retry-btn">🔄 重试</button></div>';finish()}else if(txt&&txt.trim()){finish()}else{sseReconnect(p)}}else{finish()}return}buf+=decoder.decode(result.value,{stream:!0});buf=buf.replace(/\r\n/g,'\n');var lines=buf.split('\n');buf=lines.pop()||'';var eventType='';for(var i=0;i<lines.length;i++){var line=lines[i];if(line.indexOf('event: ')===0){eventType=line.slice(7);continue}if(line.indexOf('data: ')!==0)continue;try{var d=JSON.parse(line.slice(6));if(d.progress){showProgress(p,d.stage,d.message,d.agent||p._lastAgent)}else if(d.content){if(!p._streamingNotified){p._streamingNotified=true;setMessageStatus(pid,p._assistantMsgIndex,'streaming')}txt+=d.content;p.currentAssistantMsg.innerHTML=renderMD(txt)+'<span class="cursor"></span>';p.dom.messages.scrollTop=p.dom.messages.scrollHeight}else if(eventType==='done'||d.elapsed){p._receivedDone=!0;if(d.session_id){p.currentConvo.sessionId=d.session_id}if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}p.dom.route.innerHTML+='<span>⏱ '+(d.elapsed||0)+'s</span><span>💰 $'+(d.cost||0)+'</span>';
					// 更新面板 token 显示（tokens-{pid} span 初始值为 📊 --，Bug 2 修复）
					var tokEl=document.getElementById('tokens-'+pid);
					if(tokEl&&(d.total_in||d.total_out)){
					  var usedK=d.total_in?Math.round(d.total_in/1000):0;
					  var capacityK=d.compaction?Math.round(d.compaction.capacity/1000):0;
					  var ratioPct=d.compaction?Math.round(d.compaction.ratio*100):0;
					  var color='#888';
					  if(d.compaction&&d.compaction.force)color='#e55';
					  else if(d.compaction&&d.compaction.warn)color='#ea3';
					  tokEl.textContent='📊 '+usedK+'K';
					  if(capacityK)tokEl.textContent+='/'+capacityK+'K';
					  if(ratioPct)tokEl.textContent+=' '+ratioPct+'%';
					  tokEl.style.color=color;
					}}else if(d.error){p._receivedDone=!0;if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}if(d.action==='open_settings'){showToast(d.friendly_message||'请先配置 API Key','warning');if(typeof toggleDevOverlay==='function'&&!devMode)setTimeout(toggleDevOverlay,1500)}else if(d.action==='install_claude'){showToast(d.friendly_message||'Claude CLI 未安装，请在终端运行安装命令',false)}p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(d.error)+'</span>'+(d.install_cmd?' <code style="font-size:10px;background:var(--surface2);padding:2px 6px;border-radius:3px">'+escHtml(d.install_cmd)+'</code>':'');setMessageStatus(pid,p._assistantMsgIndex,'error',d.error);setStreaming(p,!1);p.dom.agentName.textContent='错误';processQueue(pid)}}catch(_){}eventType=''}read()})}function finish(){if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentConvo.messages.push({role:'assistant',content:txt});setMessageStatus(pid,p._assistantMsgIndex,'done');saveConvoToServer(p);setStreaming(p,!1);p.dom.agentName.textContent='就绪';highlightCode(p.currentAssistantMsg);loadCostOverview();processQueue(pid);checkAutoCompact(pid)}read()}).catch(function(e){if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}if(e.name==='AbortError'){if(!p._timedOut){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentAssistantMsg.innerHTML+=' <span style="color:var(--warn)">⏹ 已停止</span>';setMessageStatus(pid,p._assistantMsgIndex,'error','已停止')}var partial=(p.currentAssistantMsg.textContent||'').replace(/⏹\s*已停止/g,'').trim();if(partial){p.currentConvo.messages.push({role:'assistant',content:partial});saveConvoToServer(p)}setStreaming(p,!1);p._reader=null;p.dom.agentName.textContent='就绪';processQueue(pid)}else if(!p._timedOut){if(txt&&txt.trim()){finish()}else{sseReconnect(p)}}else{if(p.currentAssistantMsg)p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(e.message)+'</span>';setMessageStatus(pid,p._assistantMsgIndex,'error',e.message);setStreaming(p,!1);p._reader=null;p.dom.agentName.textContent='就绪';processQueue(pid)}})}
/* Phase 2: WebSocket 聊天 — 替代 SSE，双向通信更稳 */
function handleSendWS(pid,forceAgent){
  var p=panels.find(function(x){return x.id===pid});
  if(!p||!p.dom)return;
  var task=p.dom.input.value.trim();
  if(!task)return;
  if(p._sendLock)return;
  p._sendLock=true;setTimeout(function(){p._sendLock=false;},3000);

  p.dom.sendBtn.disabled=true;
  p.dom.input.value='';
  p.dom.input.style.height='auto';
  try{localStorage.removeItem('chat_draft_'+pid);}catch(e){}

  addMsg(p,'user',task);
  var emptyMsg=addMsg(p,'assistant','⏳ 处理中...');
  var fullText='';
  p.isStreaming=true;
  p.dom.dot.style.background='#fa3';

  /* Phase 2: 构建请求数据——面板级 Provider 优先，否则回退全局设置 */
  var body={
    task:task,
    api_key:apiKey||'',
    api_provider:(p._provider)||apiProvider||'deepseek',  /* B3: 面板级 Provider */
    force_agent:forceAgent||p._lastAgent||'',
    session_id:p.currentConvo.sessionId||'',
    is_first:!p.currentConvo.messages.length||p.currentConvo.messages.length<=1,
    sid:pid+'-'+Date.now()  /* 临时标识——用于后端日志关联 */
  };

  /* Phase 2: 连接 /ws/chat namespace——与 /ws/terminal 独立 */
  var sock=io('/ws/chat');

  sock.on('connect',function(){
    sock.emit('chat_send',body);
  });

  sock.on('chat_event',function(d){
    var evt=d._event;
    if(evt==='content'){
      fullText+=d.content;
      var bubble=p.dom.messages.lastElementChild;
      if(bubble&&bubble.classList.contains('assistant')){
        var contentEl=bubble.querySelector('.bubble-content');
        if(contentEl){
          contentEl.innerHTML=renderMD(fullText);
          p.dom.messages.scrollTop=p.dom.messages.scrollHeight;
          highlightCode(p.dom.messages);
        }
      }
    }else if(evt==='routing'){
      p.dom.route.innerHTML='<span style="color:var(--accent);font-size:9px">🔗 '+escHtml(d.agent||'auto')+'</span>';
    }else if(evt==='error'){
      showToast(d.error,true);
      p.dom.dot.style.background='#e55';
      p.isStreaming=false;
      sock.disconnect();
    }else if(evt==='done'){
      p.currentConvo.sessionId=d.session_id||'';
      /* Phase 2: 更新 token 显示——与 SSE 路径保持一致 */
      var tokEl=document.getElementById('tokens-'+pid);
      if(tokEl&&d.total_in){
        var usedK=Math.round(d.total_in/1000);
        var capK=d.compaction?Math.round(d.compaction.capacity/1000):0;
        var ratio=d.compaction?Math.round(d.compaction.ratio*100):0;
        var color='#888';
        if(d.compaction&&d.compaction.force)color='#e55';
        else if(d.compaction&&d.compaction.warn)color='#ea3';
        tokEl.textContent='📊 '+usedK+'K'+(capK?'/'+capK+'K':'')+(ratio?' '+ratio+'%':'');
        tokEl.style.color=color;
      }
      /* Phase 2: 更新对话记录 */
      if(fullText&&p.currentConvo.messages.length){
        p.currentConvo.messages[p.currentConvo.messages.length-1].content=fullText;
      }
      p.dom.dot.style.background='var(--green)';
      p.isStreaming=false;
      p._receivedDone=true;
      sock.disconnect();
    }
  });

  sock.on('disconnect',function(){
    p.isStreaming=false;
    p.dom.dot.style.background=p._receivedDone?'var(--green)':'#e55';
  });
}
/* Phase 2: 面板级 Provider 切换——每个面板独立选择 AI 供应商 */
window.onPanelProviderChange=function(pid,provider){
  var p=panels.find(function(x){return x.id===parseInt(pid,10);});
  if(!p)return;
  p._provider=provider;
  showToast('已切换 Provider: '+provider,false,'info');
};
function handleOrchSend(p){var task=p.dom.input.value.trim();if(!task)return;if(!p._msgQueue)p._msgQueue=[];if(p.isStreaming||p._pendingRequest){p._msgQueue.push(p.id);updateQueueIndicator(p);return}p._pendingRequest=true;updateQueueIndicator(p);setStreaming(p,!0);p.dom.input.value='';p.dom.input.style.height='auto';p.dom.route.innerHTML='<span>🧠 智能调度</span>';if(p.dom.empty)p.dom.empty.style.display='none';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task});p.currentAssistantMsg=addMsg(p,'assistant','<span class="cursor"></span>');p.abortController=new AbortController();var planReceived=!1;var pipelineStages=null;stageStatus={};fetch('/api/orchestrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:task,proj_dir:projDir||undefined,api_key:apiKey||undefined,api_provider:apiProvider||undefined,profile:agencyProfile||'standard',output_dir:localStorage.getItem('agency_output_dir')||undefined}),signal:p.abortController.signal}).then(function(resp){var reader=resp.body.getReader();p._reader=reader;var decoder=new TextDecoder(),buf='',txt='',planData=null;function read(){reader.read().then(function(result){if(result.done){p._reader=null;finish();return}buf+=decoder.decode(result.value,{stream:!0});buf=buf.replace(/\r\n/g,'\n');var lines=buf.split('\n');buf=lines.pop()||'';for(var i=0;i<lines.length;i++){var line=lines[i],eventType='';if(line.indexOf('event: ')===0){eventType=line.slice(7);continue}if(line.indexOf('data: ')!==0)continue;try{var d=JSON.parse(line.slice(6));if(eventType==='plan'){planData=d;return}if(eventType==='stage'){handleStageEvent(p,d);return}if(eventType==='phase'){if(d.msg){p.dom.route.innerHTML='<span>'+escHtml(d.msg)+'</span>'}return}if(eventType==='done'){if(d.summary)txt+=d.summary;return}if(eventType==='error'){if(d.msg)p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(d.msg)+'</span>';return}if(d.content){txt+=d.content;p.currentAssistantMsg.innerHTML=renderMD(txt)+'<span class="cursor"></span>';p.dom.messages.scrollTop=p.dom.messages.scrollHeight}else if(d.summary){txt+=d.summary}}catch(_){}}read()})}function finish(){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentConvo.messages.push({role:'assistant',content:txt||'调度完成'});saveConvoToServer(p);setStreaming(p,!1);hidePipeline(p);if(planData&&planData.phases){executePlan(planData)}if(planData&&planData.dag_info){renderDAGTree(planData.dag_info,p.currentAssistantMsg)};loadCostOverview();processQueue(p.id)}read()}).catch(function(e){if(e.name==='AbortError'){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentAssistantMsg.innerHTML+=' <span style="color:var(--warn)">⏹ 已停止</span>'}else{if(p.currentAssistantMsg)p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(e.message)+'</span>'}setStreaming(p,!1);p._reader=null;hidePipeline(p);processQueue(p.id)})}
function handleStageEvent(p,d){if(d.pipeline&&!p._pipelineInit){p._pipelineInit=true;p._pipelineStages=d.pipeline;stageStatus={};d.pipeline.forEach(function(s){stageStatus[s.stage]='pending'});renderPipelineBar(p)}if(d.stage){stageStatus[d.stage]=d.status;renderPipelineBar(p);if(d.model_tier){p.dom.route.innerHTML='<span>📋 '+d.stage+'</span><span style="color:var(--accent)">'+d.model_tier+'</span>'}if(d.pass_k){var pk=d.pass_k;var pkSummary='🔍 pass@3: '+(pk.overall?'✅ 通过':'❌ 未通过')+' (';var names=Object.keys(pk.perspectives||{});pkSummary+=names.map(function(n){return (pk.perspectives[n].passed?'✓':'✗')+' '+n}).join(', ');pkSummary+=')';p.dom.route.innerHTML='<span>'+pkSummary+'</span>'}}}
function renderPipelineBar(p){var bar=p.dom.pipeline;if(!bar)return;var stages=p._pipelineStages||[{stage:'research',label:'研究'},{stage:'plan',label:'方案'},{stage:'dry_run',label:'预演'},{stage:'gate',label:'门控'},{stage:'implement',label:'实施'},{stage:'review',label:'审查'},{stage:'verify',label:'验证'}];var iconMap={pending:'⚪',active:'🔵',passed:'✅',failed:'❌',verifying:'🔍'};bar.style.display='flex';bar.innerHTML=stages.map(function(s,i){var st=stageStatus[s.stage]||'pending';var cls='pipeline-dot '+(st==='active'||st==='verifying'?'active':st==='passed'?'done':st==='failed'?'fail':'');return'<div style="display:flex;align-items:center;gap:3px"><span class="'+cls+'" title="'+escHtml(s.label||s.stage)+': '+st+'"></span><span style="font-size:9px;color:var(--muted)">'+escHtml(s.label||s.stage)+'</span>'+(i<stages.length-1?'<span style="color:var(--border2)">—</span>':'')+'</div>'}).join('')}
function hidePipeline(p){var bar=p.dom.pipeline;if(bar){setTimeout(function(){bar.style.display='none'},3000);p._pipelineInit=false;p._pipelineStages=null}}
/* ── Agent 执行进度指示器 ── */
function showProgress(p,stage,message,agent){
  if(!p||!p.dom||!p.dom.messages)return;
  var barId='agent-progress-'+p.id;
  var bar=document.getElementById(barId);
  if(!bar){
    bar=document.createElement('div');
    bar.id=barId;
    bar.style.cssText='padding:6px 12px;background:var(--bg-secondary,var(--surface2));border-bottom:1px solid var(--border);font-size:12px;display:flex;align-items:center;gap:8px;position:sticky;top:0;z-index:10';
    p.dom.messages.insertBefore(bar,p.dom.messages.firstChild);
  }
  var stages={routing:'🔍',dispatching:'📤',executing:'⚙️',done:'✅'};
  var icon=stages[stage]||'⏳';
  if(stage==='done'){
    bar.innerHTML=icon+' '+message;
    bar.style.color='var(--accent,#10b981)';
    setTimeout(function(){if(bar)bar.style.display='none'},3000);
  }else{
    bar.innerHTML=icon+' '+message+' <span style="animation:progressPulse 1s infinite;">...</span>';
    bar.style.color='var(--text)';
    bar.style.display='flex';
  }
}
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

/* ── 消息排队 ── */
function updateQueueIndicator(p){
  if(!p._msgQueue)return;
  var qlen=p._msgQueue.length;
  var rte=p.dom.route;
  if(qlen>0){
    var existing=rte.querySelector('.queue-indicator');
    if(!existing){
      var span=document.createElement('span');span.className='queue-indicator';
      span.style.cssText='color:var(--warn);font-size:10px;margin-left:6px';
      rte.appendChild(span);
    }
    rte.querySelector('.queue-indicator').textContent='排队中（'+qlen+'）…';
  }else{
    var qi=rte.querySelector('.queue-indicator');if(qi)qi.remove();
  }
}
function processQueue(pid){
  var p=panels.find(function(x){return x.id===pid});if(!p)return;
  p._pendingRequest=false;
  if(!p._msgQueue||p._msgQueue.length===0){updateQueueIndicator(p);return}
  var nextPid=p._msgQueue.shift();
  updateQueueIndicator(p);
  var nextP=panels.find(function(x){return x.id===nextPid});
  if(nextP&&nextP!==p){handleSend(nextPid)}
}

/* ── DAG 依赖树渲染 ── */
function renderDAGTree(dagInfo,containerEl){
  if(!dagInfo||!containerEl)return;
  if(!dagInfo.depends_on||!dagInfo.depends_on.length){containerEl.innerHTML='';return}
  var html='<div style="margin-top:6px;padding:6px 8px;background:var(--surface2);border-radius:4px;font-size:10px">';
  html+='<div style="color:var(--accent);font-weight:600;margin-bottom:3px">📊 依赖树</div>';
  html+='<div style="font-family:monospace;line-height:1.8">';
  function renderNode(taskId,indent,isLast){
    var prefix='';
    for(var i=0;i<indent;i++)prefix+='&nbsp;&nbsp;';
    prefix+=isLast?'└─ ':'├─ ';
    html+=prefix+'<span style="color:var(--text2)">'+escHtml(taskId)+'</span><br>';
    // 查找子节点（被此任务依赖的）
    if(dagInfo.children){
      dagInfo.children.forEach(function(child,j){
        renderNode(child.task_id,indent+1,j===dagInfo.children.length-1);
      });
    }
  }
  renderNode(dagInfo.task_id||'任务',0,true);
  if(dagInfo.depends_on&&dagInfo.depends_on.length){
    dagInfo.depends_on.forEach(function(dep,j){
      renderNode(dep,1,j===dagInfo.depends_on.length-1);
    });
  }
  html+='</div></div>';
  containerEl.innerHTML=html;
}

/* ── 会话 Fork ── */
function addForkButton(msgEl,msgIndex,sessionId){if(!sessionId)return;var btn=document.createElement('button');btn.className='fork-btn';btn.title='从这里分叉出新对话';btn.innerHTML='⑂';btn.style.cssText='position:absolute;top:2px;right:2px;padding:1px 5px;background:transparent;border:1px solid var(--border);border-radius:3px;color:var(--muted);cursor:pointer;font-size:10px;opacity:0;transition:opacity 0.15s;';msgEl.style.position='relative';msgEl.appendChild(btn);msgEl.addEventListener('mouseenter',function(){btn.style.opacity='1'});msgEl.addEventListener('mouseleave',function(){btn.style.opacity='0'});btn.addEventListener('touchstart',function(e){e.stopPropagation();btn.style.opacity='1'}, {passive:true});btn.addEventListener('click',function(e){e.stopPropagation();var label=prompt('分叉标签（可选）：','分叉 '+new Date().toLocaleTimeString());if(label===null)return;api.post('/api/sessions/fork',{session_id:sessionId,fork_point:msgIndex,label:label}).then(function(d){if(d.ok){showToast('已分叉: '+d.fork_label);addPanel()}else showToast('分叉失败: '+(d.error||''),!0)})})}
window.addForkButton=addForkButton;

/* ── 空状态快捷操作 ── */
function quickAction(pid,type){var actions={1:t('chatQuickAction1'),2:t('chatQuickAction2'),3:t('chatQuickAction3')};var text=actions[type]||'';var p=panels.find(function(x){return x.id===pid});if(!p)return;p.dom.input.value=text;p.dom.input.focus();p.dom.sendBtn.disabled=false;p.dom.input.style.height='auto';p.dom.input.style.height=Math.min(p.dom.input.scrollHeight,100)+'px'}

/* ── 页面离开保护 ── */
window.addEventListener('beforeunload',function(e){
  // 每个面板先保存到服务端
  /* save moved to after each response - prevent zombie conversations */
  var hasActive=panels.some(function(p){return p.isStreaming});
  if(hasActive){e.preventDefault();e.returnValue=t('sseActiveWarn');return e.returnValue}
});

/* ── Demo 聊天欢迎 ── */
function renderDemoWelcome(){
  if(panels.length===0)addPanel();
  var p=panels[0];
  if(p.dom.empty)p.dom.empty.style.display='none';
  // 清空已有消息
  p.dom.messages.innerHTML='';
  p.currentConvo={id:Date.now(),title:'',messages:[],sessionId:''};

  // 欢迎消息
  addMsg(p,'assistant',
    '<div style="text-align:center;padding:8px 0">'+
    '<div style="font-size:28px;margin-bottom:8px">🎮</div>'+
    '<p style="font-size:13px;color:var(--text);margin-bottom:4px">'+t('demoWelcome')+'</p>'+
    '</div>'
  );

  // 快捷任务卡片
  var tasks=[
    {icon:'🕷️',label:t('demoQuick1')},
    {icon:'🔍',label:t('demoQuick2')},
    {icon:'📋',label:t('demoQuick3')}
  ];
  var taskCards=document.createElement('div');
  taskCards.className='demo-quick-tasks';
  taskCards.style.cssText='display:flex;flex-direction:column;gap:8px;padding:0 12px;max-width:400px;margin:0 auto';
  tasks.forEach(function(task){
    var card=document.createElement('div');
    card.className='demo-task-card';
    card.style.cssText='padding:12px 16px;background:var(--surface2);border-radius:var(--radius);cursor:pointer;border:1px dashed var(--warn);transition:all .15s;text-align:left';
    card.innerHTML='<span style="font-size:14px">'+task.icon+'</span> <span style="font-size:12px;color:var(--text)">'+escHtml(task.label)+'</span><span style="float:right;color:var(--muted);font-size:10px">→</span>';
    card.addEventListener('click',function(){
      showDemoActionPopup(task.label.replace(/^[^\s]+\s/,''));
    });
    card.addEventListener('mouseenter',function(){this.style.borderColor='var(--accent)';this.style.background='var(--surface3)'});
    card.addEventListener('mouseleave',function(){this.style.borderColor='var(--warn)';this.style.background='var(--surface2)'});
    taskCards.appendChild(card);
  });
  p.dom.messages.appendChild(taskCards);
  p.dom.messages.scrollTop=p.dom.messages.scrollHeight;
}
/* ── Demo 模式模拟回复 ── */

function simulateDemoReply(task,pid){
  var demoReplies={"coder":["好的，我来帮你实现这个功能。\n\n```python\ndef hello():\n    print(\"Hello from Agency Demo!\")\n```\n\n这是一个简单的示例。在真实环境中，Claude Code 会生成完整的可用代码。","我来分析一下你的需求...\n\n根据你的描述，这里有几个关键点需要考虑：\n1. **功能需求**：你需要一个完整的实现\n2. **性能考虑**：需要考虑边界情况\n3. **最佳实践**：遵循代码规范\n\n> 提示：配置 API Key 后可以体验真实的 AI 编程助手。"],"reviewer":["我来审查这段代码...\n\n发现以下问题：\n\n| 严重度 | 文件 | 问题 |\n|--------|------|------|\n| 🔴 高 | auth.py:42 | 密码未加盐哈希 |\n| 🟡 中 | api.py:108 | 缺少输入校验 |\n| 🟢 低 | utils.py:23 | 变量命名不够清晰 |\n\n配置 API Key 后可进行真实的代码审查。"],"explorer":["搜索结果显示，项目中有以下相关文件：\n\n- `maestro/main.py` — 路由引擎\n- `maestro/routes/chat.py` — 聊天处理\n- `webui/js/chat.js` — 前端消息管理\n\n配置 API Key 后可以进行真实的代码搜索。"],"security-reviewer":["安全审查结果：\n\n| 严重度 | 问题 | 位置 |\n|--------|------|------|\n| 🔴 高 | 密码未加盐哈希 | auth.py:23 |\n| 🟡 中 | 缺少输入校验 | api.js:45 |\n| 🟢 低 | 注释拼写错误 | main.py:12 |\n\n> 配置 API Key 后可进行真实安全审计。"],"orchestrator":["任务分解完成：\n\n1. **需求分析** → 分配给 architect\n2. **代码实现** → 分配给 coder\n3. **安全审查** → 分配给 security-reviewer\n4. **测试验证** → 分配给 test-runner\n\n📊 预估耗时: 15 分钟\n\n> Demo 展示的是模拟调度流程。真实环境会真正调用多个 Agent 协同。"],"architect":["架构建议：\n\n```\n┌── Web UI (React / Vue)\n├── API Gateway (FastAPI)\n├── Auth Service (JWT)\n├── Database (PostgreSQL)\n└── Cache (Redis)\n```\n\n**技术选型理由：**\n- FastAPI: 高性能异步，自动 OpenAPI\n- PostgreSQL: 成熟稳定，支持 JSON\n- Redis: 会话缓存 + 限流\n\n> 配置 API Key 获取完整的架构设计文档。"],"debugger":["错误分析：\n\n```python\n# 问题代码 (line 42)\nresult = data[\"key\"]  # KeyError\n```\n\n**根因**: `data` 字典缺少 `key` 字段\n\n**修复方案**:\n1. 使用 `data.get(\"key\", default)` 替代直接访问\n2. 在函数入口加参数校验\n\n> 配置 API Key 进行实时调试。"],"data-analyst":["数据洞察：\n\n| 指标 | 当前值 | 趋势 |\n|------|--------|------|\n| DAU | 1,234 | 📈 +12% |\n| 留存 | 67% | 📊 持平 |\n| 转化 | 3.2% | 📉 -0.5% |\n\n建议关注转化率下降，可能与新版本加载时间增加有关。\n\n> 配置 API Key 分析真实数据。"]};
  var p=panels.find(function(px){return px.id===pid});
  var agentName=(p&&p._lastAgent)||"coder";
  var replies=demoReplies[agentName]||demoReplies["coder"];
  var reply=replies[Math.floor(Math.random()*replies.length)];
  var demoBubble=addMsg(p,"assistant","");
  var i=0;
  var timer=setInterval(function(){
    if(i<reply.length){
      var rendered=typeof renderMD==="function"?renderMD(reply.slice(0,i+1)):reply.slice(0,i+1);
      demoBubble.innerHTML=rendered+"<span class=\"cursor\"></span>";
      i+=5;
      p.dom.messages.scrollTop=p.dom.messages.scrollHeight;
    }else{
      clearInterval(timer);
      demoBubble.innerHTML=(typeof renderMD==="function"?renderMD(reply):reply)+
        "<div style=\"margin-top:12px;padding:8px;background:var(--accent);color:#fff;border-radius:6px;font-size:11px;text-align:center;\">"+
        "⚡ Demo — <a href=\"#\" onclick=\"if(typeof toggleDevOverlay==='function')toggleDevOverlay();return false;\" style=\"color:#fff;text-decoration:underline;\">配置 API Key</a> 解锁完整功能"+
        "</div>";
      if(typeof highlightCode==="function")highlightCode(demoBubble);
      p.currentConvo.messages.push({role:"assistant",content:reply});
      saveConvoToServer(p);
      // Demo 完成提示
      setTimeout(function() {
        if (p && p.currentConvo.messages && p.currentConvo.messages.length <= 3) {
          showToast('体验不错？注册个免费 Key 解锁完整功能 →', false);
        }
      }, 3000);
    }
  },15);
}

function toggleTemplateDropdown(pid){
  var p = panels.find(function(x){return x.id===pid});
  if(!p||!p.dom.templateDropdown) return;
  var dd = p.dom.templateDropdown;
  if(dd.classList.contains('on')){ dd.classList.remove('on'); return; }
  // 关闭其他面板的模板下拉
  panels.forEach(function(pp){
    if(pp.dom.templateDropdown && pp.id!==pid) pp.dom.templateDropdown.classList.remove('on');
  });
  dd.classList.add('on');
  renderTemplateList(p, dd);
}
function renderTemplateList(p, dd){
  var templates = getAllTemplates();
  var html = '<div class="template-dropdown-header"><span>'+t('templates')+'</span></div>';
  html += '<div class="template-dropdown-list">';
  for(var i=0;i<templates.length;i++){
    var tpl = templates[i];
    var label = typeof tpl.label==='object'?(tpl.label[_lang]||tpl.label.zh):tpl.label;
    var isCustom = i >= WORKFLOW_TEMPLATES.length;
    html += '<div class="template-item'+(isCustom?' custom':'')+'" onclick="applyTemplate('+p.id+','+i+')">';
    html += '<span class="tpl-icon">'+escHtml(tpl.icon||'📋')+'</span>';
    html += '<span class="tpl-label">'+escHtml(label)+'</span>';
    if(isCustom){
      html += '<span class="tpl-actions">';
      html += '<button class="tpl-act-btn" onclick="event.stopPropagation();editCustomTemplate('+p.id+','+(i-WORKFLOW_TEMPLATES.length)+')" title="'+t('editTemplate')+'">✏</button>';
      html += '<button class="tpl-act-btn del" onclick="event.stopPropagation();deleteCustomTemplate('+p.id+','+(i-WORKFLOW_TEMPLATES.length)+')" title="'+t('delTemplate')+'">✕</button>';
      html += '</span>';
    }
    html += '</div>';
  }
  html += '</div>';
  // 新建模板
  html += '<div class="template-new-row" id="template-new-row-'+p.id+'">';
  html += '<input placeholder="'+t('templateName')+'" id="tpl-name-'+p.id+'">';
  html += '<textarea placeholder="'+t('templateContent')+'" id="tpl-content-'+p.id+'"></textarea>';
  html += '<div class="btn-row"><button class="btn" onclick="saveNewTemplate('+p.id+')" style="font-size:10px;color:var(--accent)">'+t('saveTemplate')+'</button></div>';
  html += '</div>';
  dd.innerHTML = html;
}
function applyTemplate(pid, idx){
  var p = panels.find(function(x){return x.id===pid});
  if(!p) return;
  var templates = getAllTemplates();
  var tpl = templates[idx];
  if(!tpl) return;
  p.dom.input.value = tpl.content;
  p.dom.input.focus();
  p.dom.sendBtn.disabled = false;
  p.dom.input.style.height = 'auto';
  p.dom.input.style.height = Math.min(p.dom.input.scrollHeight, 100) + 'px';
  if(p.dom.templateDropdown) p.dom.templateDropdown.classList.remove('on');
}
function saveNewTemplate(pid){
  var nameEl = document.getElementById('tpl-name-'+pid);
  var contentEl = document.getElementById('tpl-content-'+pid);
  if(!nameEl||!contentEl) return;
  var name = nameEl.value.trim();
  var content = contentEl.value.trim();
  if(!name||!content){ showToast(t('error'), true); return; }
  var templates = getCustomTemplates();
  templates.push({icon:'📋',label:name,content:content});
  saveCustomTemplates(templates);
  showToast(t('templateSaved'));
  var p = panels.find(function(x){return x.id===pid});
  if(p&&p.dom.templateDropdown) renderTemplateList(p, p.dom.templateDropdown);
}
function editCustomTemplate(pid, idx){
  var templates = getCustomTemplates();
  var tpl = templates[idx];
  if(!tpl) return;
  var name = typeof tpl.label==='object'?(tpl.label[_lang]||tpl.label.zh):tpl.label;
  var nameEl = document.getElementById('tpl-name-'+pid);
  var contentEl = document.getElementById('tpl-content-'+pid);
  if(nameEl) nameEl.value = name;
  if(contentEl) contentEl.value = tpl.content;
  // 删除旧模板，等用户重新保存
  templates.splice(idx, 1);
  saveCustomTemplates(templates);
}
function deleteCustomTemplate(pid, idx){
  var templates = getCustomTemplates();
  templates.splice(idx, 1);
  saveCustomTemplates(templates);
  showToast(t('templateDeleted'));
  var p = panels.find(function(x){return x.id===pid});
  if(p&&p.dom.templateDropdown) renderTemplateList(p, p.dom.templateDropdown);
}

/* ── 消息状态生命周期 ── */
window.setMessageStatus=function(panelId,msgIndex,status,detail){var panel=panels.find(function(p){return p.id===panelId});if(!panel||!panel.currentConvo||!panel.currentConvo.messages)return;var msg=panel.currentConvo.messages[msgIndex];if(msg){msg.status=status;msg.statusDetail=detail||''}var bubbles=panel.dom.messages.querySelectorAll('.bubble');var bubble=bubbles[msgIndex];if(!bubble)return;bubble.classList.remove('status-pending','status-routing','status-executing','status-streaming','status-done','status-error');if(status)bubble.classList.add('status-'+status);var indicator=bubble.querySelector('.msg-status');if(!indicator){indicator=document.createElement('span');indicator.className='msg-status';bubble.appendChild(indicator)}var icons={pending:'⏳',routing:'🔍',executing:'⚙️',streaming:'📝',done:'✅',error:'❌'};indicator.textContent=(icons[status]||'')+(detail?' '+detail:'')};

/* ── 自动压缩提醒 ── */
function checkAutoCompact(panelId){var panel=panels.find(function(p){return p.id===panelId});if(!panel||!panel.currentConvo||!panel.currentConvo.messages)return;var key='auto-compact-reminded-'+panelId;if(panel.currentConvo.messages.length>=30&&!localStorage.getItem(key)){showToast('对话较长，建议开启新会话或使用 /compact 压缩上下文以节省 Token',!1,'warn');try{localStorage.setItem(key,'1')}catch(e){}}}
window.checkAutoCompact=checkAutoCompact;

function showPanelContext(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;var sid=p.sessionId||'';api.get('/api/harness/context'+(sid?'?session='+encodeURIComponent(sid):'')).then(function(d){var msg='📊 Token: '+h(d.total_tokens||0)+' | 缓存命中: '+(d.cache_hit_rate||0).toFixed(0)+'% | 费用: $'+(d.cost_est?d.cost_est.total:0).toFixed(4);showToast(msg,'info',5000)}).catch(function(e){showToast('上下文信息不可用','error')})}

// ES module bridge
window.addPanel = addPanel;
window.removePanel = removePanel;
window.clearAllPanels = clearAllPanels;
window.handleSend = handleSend;
window.refreshUI = refreshUI;
window.pickAgent = pickAgent;
window.pickAgentNew = pickAgentNew;
window.toggleOrchMode = toggleOrchMode;
window.stopStream = stopStream;
window.retrySend = retrySend;
window.toggleRouteFix = toggleRouteFix;
window.cycleGrid = cycleGrid;
window.prevPage = prevPage;
window.nextPage = nextPage;
window.quickAction = quickAction;
window.renderDemoWelcome = renderDemoWelcome;
window.toggleTemplateDropdown = toggleTemplateDropdown;
window.applyTemplate = applyTemplate;
window.saveNewTemplate = saveNewTemplate;
window.editCustomTemplate = editCustomTemplate;
window.deleteCustomTemplate = deleteCustomTemplate;
window.showRoutePicker = showRoutePicker;
window.showProgress = showProgress;
