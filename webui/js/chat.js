/* Agency — 聊天面板 + SSE流式 + 分屏 */
function mkPanel(){return{id:++pidSeq,isStreaming:!1,abortController:null,_lastAgent:null,currentConvo:{id:Date.now(),title:'',messages:[],sessionId:''},currentAssistantMsg:null,dom:{}}}
function addPanel(){var s=mkPanel();panels.push(s);buildPanelDOM(s);curPage=Math.floor((panels.length-1)/perPage);refreshUI();return s}
function removePanel(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;if(panels.length<=1)return;if(p.isStreaming&&!confirm('面板正在生成回复，确定关闭？'))return;if(p.currentConvo.messages.length>0&&!confirm('关闭面板将丢失当前对话，确定？'))return;var idx=panels.findIndex(function(p){return p.id===pid});if(idx<0)return;if(p.isStreaming&&p.abortController)p.abortController.abort();var savedConvo={id:p.currentConvo.id,title:p.currentConvo.title,messages:p.currentConvo.messages.slice(),sessionId:p.currentConvo.sessionId};var savedRoute=p.dom.route.innerHTML;var savedAgent=p._lastAgent;var savedInput=p.dom.input.value;panels.splice(idx,1);p.dom.wrapper.remove();if(focusedPid===pid)focusedPid=null;var total=Math.ceil(panels.length/perPage);if(curPage>=total)curPage=Math.max(0,total-1);refreshUI();showUndoableToast(t('panelClosed'),function(){var np=mkPanel();panels.push(np);buildPanelDOM(np);np.currentConvo=savedConvo;np._lastAgent=savedAgent;np.dom.route.innerHTML=savedRoute;np.dom.input.value=savedInput;np.dom.sendBtn.disabled=!savedInput.trim();if(savedConvo.messages.length>0){np.dom.empty.style.display='none';savedConvo.messages.forEach(function(m){addMsg(np,m.role,m.content)})}refreshUI()},5000)}
function clearAllPanels(){panels.forEach(function(p){if(p.isStreaming&&p.abortController)p.abortController.abort()});while(panels.length>1){var p=panels.pop();p.dom.wrapper&&p.dom.wrapper.remove()}var p=panels[0];p.currentConvo={id:Date.now(),title:'',messages:[],sessionId:''};p.dom.messages.innerHTML='<div class="empty-panel"><div class="logo">👋</div><h3>'+t('chatEmptyTitle')+'</h3><div class="empty-state-actions"><button class="btn quick-action" onclick="quickAction('+p.id+',1)">'+t('chatEmptyBtn1')+'</button><button class="btn quick-action" onclick="quickAction('+p.id+',2)">'+t('chatEmptyBtn2')+'</button><button class="btn quick-action" onclick="quickAction('+p.id+',3)">'+t('chatEmptyBtn3')+'</button></div></div>';p.dom.route.innerHTML='<span style="color:var(--muted);font-size:9px">'+t('routeEmpty')+'</span>';p.dom.agentName.textContent='就绪';curPage=0;refreshUI()}
function buildPanelDOM(s){var w=document.createElement('div');w.className='panel on';var emptyHTML='<div class="empty-panel"><div class="logo">👋</div><h3>'+t('chatEmptyTitle')+'</h3><div class="empty-state-actions"><button class="btn quick-action" onclick="quickAction('+s.id+',1)">'+t('chatEmptyBtn1')+'</button><button class="btn quick-action" onclick="quickAction('+s.id+',2)">'+t('chatEmptyBtn2')+'</button><button class="btn quick-action" onclick="quickAction('+s.id+',3)">'+t('chatEmptyBtn3')+'</button></div></div>';w.innerHTML='<div class="panel-bar"><span class="pinfo"><span class="pdot"></span><span class="pagent">就绪</span></span><button class="pclose">✕</button></div><div class="panel-msgs">'+emptyHTML+'</div><div class="pipeline-bar" style="display:none"></div><div class="panel-route"><span style="color:var(--muted);font-size:9px">'+t('routeEmpty')+'</span></div><div class="panel-inp"><textarea placeholder="'+t('inputPlaceholder')+'" rows="1"></textarea><button class="template-btn" title="模板">📋</button><button disabled>发送</button><div class="template-dropdown"></div></div>';grid.appendChild(w);s.dom={wrapper:w,messages:w.querySelector('.panel-msgs'),pipeline:w.querySelector('.pipeline-bar'),route:w.querySelector('.panel-route'),input:w.querySelector('textarea'),sendBtn:w.querySelector('.panel-inp button:last-of-type'),templateBtn:w.querySelector('.template-btn'),templateDropdown:w.querySelector('.template-dropdown'),dot:w.querySelector('.pdot'),agentName:w.querySelector('.pagent'),empty:w.querySelector('.empty-panel')};w.querySelector('.pclose').addEventListener('click',function(e){e.stopPropagation();removePanel(s.id)});s.dom.input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();handleSend(s.id)}});s.dom.input.addEventListener('focus',function(){focusedPid=s.id;try{var draft=localStorage.getItem('chat_draft_'+s.id);if(draft&&!s.dom.input.value.trim()){s.dom.input.value=draft;s.dom.input.style.height='auto';s.dom.input.style.height=Math.min(s.dom.input.scrollHeight,100)+'px';s.dom.sendBtn.disabled=false}}catch(e){}// 粘性 Agent
var sticky=localStorage.getItem('sticky_agent');if(sticky&&!s._lastAgent&&!s.dom.input.value.trim()){s._lastAgent=sticky;s.dom.route.innerHTML='<span style="color:var(--accent);font-size:9px">📌 '+escHtml(sticky)+'</span>';}});s.dom.input.addEventListener('blur',function(){var v=s.dom.input.value.trim();try{if(v)localStorage.setItem('chat_draft_'+s.id,v);else localStorage.removeItem('chat_draft_'+s.id)}catch(e){}});s.dom.input.addEventListener('input',function(){s.dom.input.style.height='auto';s.dom.input.style.height=Math.min(s.dom.input.scrollHeight,100)+'px';s.dom.sendBtn.disabled=!s.dom.input.value.trim();var v=s.dom.input.value;var fp=typeof detectFilePath==='function'?detectFilePath(v):null;if(fp){if(!s.dom.input.nextElementSibling||!s.dom.input.nextElementSibling.classList.contains('file-path-hint')){var hint=document.createElement('div');hint.className='file-path-hint';hint.textContent=t('filePickerHint');s.dom.input.parentNode.insertBefore(hint,s.dom.input.nextElementSibling)}}else{var existingHint=s.dom.input.parentNode.querySelector('.file-path-hint');if(existingHint)existingHint.remove()}});s.dom.input.addEventListener('paste',function(e){var cd=e.clipboardData||window.clipboardData;var text=cd&&cd.getData?cd.getData('text'):'';if(text&&text.length>5000){if(!confirm(t('pasteLargeText').replace('{N}',text.length))){e.preventDefault()}}});s.dom.sendBtn.addEventListener('click',function(){handleSend(s.id)});}
function cycleGrid(){var s=[1,2,4];perPage=s[(s.indexOf(perPage)+1)%3];curPage=0;refreshUI()}
function prevPage(){if(curPage>0){curPage--;refreshUI()}}
function nextPage(){if(curPage<Math.ceil(panels.length/perPage)-1){curPage++;refreshUI()}}
function refreshUI(){var total=Math.ceil(panels.length/perPage),start=curPage*perPage;grid.className='grid g'+perPage;$('gridBtn').textContent='⊞';if(total>1){pageBar.style.display='flex';$('pgNum').textContent=(curPage+1)+'/'+total;$('pgPrev').disabled=curPage<=0;$('pgNext').disabled=curPage>=total-1}else{pageBar.style.display='none'}panels.forEach(function(p,i){p.dom.wrapper.classList.toggle('on',i>=start&&i<start+perPage)});$('summary').textContent=panels.length+'窗'+(total>1?' '+(curPage+1)+'/'+total:'')}
function pickAgent(name){var p=getFocusedPanel();p.dom.input.value='@'+name+' ';p.dom.input.focus()}
function pickAgentNew(name,e){e.preventDefault();var p=addPanel();p.dom.input.value='@'+name+' ';p.dom.input.focus()}
function toggleOrchMode(){orchMode=!orchMode;var btn=$('orchBtn');btn.classList.toggle('on',orchMode);btn.textContent=orchMode?'🧠 调度中':'🧠 调度';if(orchMode&&perPage<4){perPage=4;refreshUI()}}
function setStreaming(p,v){p.isStreaming=v;p.dom.input.disabled=v;p.dom.sendBtn.textContent=v?'停止':'发送';if(v){p.dom.sendBtn.classList.add('stopping');if(p.dom.dot)p.dom.dot.classList.add('busy')}else{p.dom.sendBtn.classList.remove('stopping');if(p.dom.dot)p.dom.dot.classList.remove('busy');p.abortController=null}if(!v)setTimeout(function(){p.dom.input.disabled=!1},50)}
function addMsg(p,role,content){var w=document.createElement('div');w.className='msg '+role;w.innerHTML='<div class="msg-label">'+(role==='user'?'你':'Agency')+'</div><div class="bubble">'+content+'</div>';p.dom.messages.appendChild(w);p.dom.messages.scrollTop=p.dom.messages.scrollHeight;return w.querySelector('.bubble')}
function stopStream(pid){var p=panels.find(function(x){return x.id===pid});if(p){if(p.abortController){p.abortController.abort();p.abortController=null}if(p._reader){try{p._reader.cancel()}catch(_){}p._reader=null}}if(p&&p.currentAssistantMsg&&(!p.currentAssistantMsg.textContent||p.currentAssistantMsg.textContent.trim()==='')){p.currentAssistantMsg.innerHTML='<span style="color:var(--warn)">⏹ 已停止</span>'}}
function retrySend(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;stopStream(pid);setStreaming(p,!1);var lastUser=p.currentConvo.messages.filter(function(m){return m.role==='user'}).pop();if(lastUser){p.dom.input.value=lastUser.content;setTimeout(function(){handleSend(pid)},300)}}
function saveAllConvos(){
  if(_saveTimer)clearTimeout(_saveTimer);
  _saveTimer=setTimeout(function(){
    _saveTimer=null;
    panels.forEach(function(p){if(p.currentConvo.messages.length===0)return;if(!p.currentConvo.title||p.currentConvo.title==='新对话'){var f=p.currentConvo.messages.find(function(m){return m.role==='user'});if(f)p.currentConvo.title=f.content.slice(0,40)}var idx=conversations.findIndex(function(c){return c.id===p.currentConvo.id});if(idx>=0){conversations[idx]={id:p.currentConvo.id,title:p.currentConvo.title,messages:p.currentConvo.messages,sessionId:p.currentConvo.sessionId}}else{conversations.unshift({id:p.currentConvo.id,title:p.currentConvo.title,messages:p.currentConvo.messages,sessionId:p.currentConvo.sessionId})}});
    try{localStorage.setItem('agency_convos',JSON.stringify(conversations))}catch(e){}
    renderHistory();
  },500);
}
function handleSend(pid){var p=panels.find(function(x){return x.id===pid});if(!p)return;if(p._sendLock)return;p._sendLock=true;setTimeout(function(){p._sendLock=false},500);if(p.isStreaming){stopStream(pid);return}
/* ── 消息排队 ── */
if(!p._msgQueue)p._msgQueue=[];
if(p.isStreaming||p._pendingRequest){p._msgQueue.push(pid);updateQueueIndicator(p);return}
updateQueueIndicator(p);
/* ── 排队结束 ── */if(orchMode){handleOrchSend(p);return}var task=p.dom.input.value.trim();if(!task)return;if(typeof _demoMode!=='undefined'&&_demoMode&&!apiKey){if(p.dom.empty)p.dom.empty.style.display='none';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task});var demoBubble=addMsg(p,'assistant','<div style="padding:8px 0">🔧 <b>Demo 模式</b> — 需要配置 API Key 才能发送任务。<br><br>👉 点右上角 <b>🔧 设置</b> → 填入 API Key → 开始干活！<br>💡 推荐 <a href="https://platform.deepseek.com/api_keys" target="_blank" style="color:var(--accent)">DeepSeek（免费注册）</a></div>');highlightCode(demoBubble);saveAllConvos();return}var isNew=!p.currentConvo.sessionId;if(isNew)p.currentConvo.sessionId='xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0,v=c==='x'?r:(r&0x3|0x8);return v.toString(16)});var forceAgent='',actualTask=task;var m=task.match(/^@(\S+)\s+/);if(m){forceAgent=m[1];actualTask=task.slice(m[0].length);p._lastAgent=forceAgent}else if(p._lastAgent){forceAgent=p._lastAgent}p._pendingRequest=true;setStreaming(p,!0);p.dom.input.value='';p.dom.input.style.height='auto';p.dom.sendBtn.disabled=true;p.dom.route.innerHTML='<span>🔄 Agent 启动中…</span>';p.dom.agentName.textContent='…';if(p.dom.empty)p.dom.empty.style.display='none';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task});p.currentAssistantMsg=addMsg(p,'assistant','<span class="cursor"></span>');p._receivedDone=!1;p._timedOut=!1;p.abortController=new AbortController();if(p._timeoutId)clearTimeout(p._timeoutId);p._timeoutId=setTimeout(function(){if(!p._receivedDone&&p.isStreaming){p._timedOut=!0;stopStream(pid);var c2=p.currentAssistantMsg.querySelector('.cursor');if(c2)c2.remove();p.currentAssistantMsg.innerHTML+='<div class="retry-block"><span>⏰ 任务超时（5分钟），是否重试？</span><button onclick="retrySend('+pid+')" class="retry-btn">🔄 重试</button></div>';p.dom.route.innerHTML='<span style="color:var(--warn)">⏰ 超时</span>';setStreaming(p,!1);p.dom.agentName.textContent='超时';processQueue(pid)}},300000);apiFetch('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:actualTask,force_agent:forceAgent,proj_dir:projDir||undefined,api_key:apiKey||undefined,api_provider:apiProvider||undefined,profile:agencyProfile||'standard',output_dir:localStorage.getItem('agency_output_dir')||undefined}),signal:p.abortController.signal}).then(function(r){return r.json()}).then(function(route){if(route.error)throw new Error(route.error);
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
p.dom.route.innerHTML=routeHTML;
p.dom.agentName.textContent=agent;p._lastAgent=agent;
var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();return apiFetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:actualTask,force_agent:forceAgent,model:route.model,proj_dir:projDir||undefined,session_id:p.currentConvo.sessionId,is_new_session:isNew,api_key:apiKey||undefined,api_provider:apiProvider||undefined,profile:agencyProfile||'standard',output_dir:localStorage.getItem('agency_output_dir')||undefined}),signal:p.abortController.signal})}).then(function(resp){var reader=resp.body.getReader();p._reader=reader;var decoder=new TextDecoder(),buf='',txt='';function read(){reader.read().then(function(result){if(result.done){p._reader=null;if(!p._receivedDone&&p.isStreaming){var reason=p._timedOut?'任务超时':'连接中断';p.currentAssistantMsg.innerHTML+='<div class="retry-block"><span>⚠ '+reason+'</span><button onclick="retrySend('+pid+')" class="retry-btn">🔄 重试</button></div>'}finish();return}buf+=decoder.decode(result.value,{stream:!0});buf=buf.replace(/\r\n/g,'\n');var lines=buf.split('\n');buf=lines.pop()||'';for(var i=0;i<lines.length;i++){var line=lines[i];if(line.indexOf('event:')===0)continue;if(line.indexOf('data: ')!==0)continue;try{var d=JSON.parse(line.slice(6));if(d.content){txt+=d.content;p.currentAssistantMsg.innerHTML=renderMD(txt)+'<span class="cursor"></span>';p.dom.messages.scrollTop=p.dom.messages.scrollHeight}else if(d.elapsed){p._receivedDone=!0;if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}p.dom.route.innerHTML+='<span>⏱ '+d.elapsed+'s</span><span>💰 $'+d.cost+'</span>'+(d.via==='pool'?'<span>⚡池</span>':'')}else if(d.error){p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(d.error)+'</span>'}}catch(_){}}read()})}function finish(){if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentConvo.messages.push({role:'assistant',content:txt});saveAllConvos();setStreaming(p,!1);p.dom.agentName.textContent='就绪';highlightCode(p.currentAssistantMsg);loadCostOverview();processQueue(pid)}read()}).catch(function(e){if(p._timeoutId){clearTimeout(p._timeoutId);p._timeoutId=null}if(e.name==='AbortError'){if(!p._timedOut){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentAssistantMsg.innerHTML+=' <span style="color:var(--warn)">⏹ 已停止</span>'}var partial=(p.currentAssistantMsg.textContent||'').replace(/⏹\s*已停止/g,'').trim();if(partial){p.currentConvo.messages.push({role:'assistant',content:partial});saveAllConvos()}}else{if(p.currentAssistantMsg)p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(e.message)+'</span>'}setStreaming(p,!1);p._reader=null;p.dom.agentName.textContent='就绪';processQueue(pid)})}
function handleOrchSend(p){var task=p.dom.input.value.trim();if(!task)return;if(!p._msgQueue)p._msgQueue=[];if(p.isStreaming||p._pendingRequest){p._msgQueue.push(p.id);updateQueueIndicator(p);return}p._pendingRequest=true;updateQueueIndicator(p);setStreaming(p,!0);p.dom.input.value='';p.dom.input.style.height='auto';p.dom.sendBtn.disabled=true;p.dom.route.innerHTML='<span>🧠 智能调度</span>';if(p.dom.empty)p.dom.empty.style.display='none';addMsg(p,'user',task);p.currentConvo.messages.push({role:'user',content:task});p.currentAssistantMsg=addMsg(p,'assistant','<span class="cursor"></span>');p.abortController=new AbortController();var planReceived=!1;var pipelineStages=null;var stageStatus={};fetch('/api/orchestrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:task,proj_dir:projDir||undefined,api_key:apiKey||undefined,api_provider:apiProvider||undefined,profile:agencyProfile||'standard',output_dir:localStorage.getItem('agency_output_dir')||undefined}),signal:p.abortController.signal}).then(function(resp){var reader=resp.body.getReader();p._reader=reader;var decoder=new TextDecoder(),buf='',txt='',planData=null;function read(){reader.read().then(function(result){if(result.done){p._reader=null;finish();return}buf+=decoder.decode(result.value,{stream:!0});buf=buf.replace(/\r\n/g,'\n');var lines=buf.split('\n');buf=lines.pop()||'';for(var i=0;i<lines.length;i++){var line=lines[i],eventType='';if(line.indexOf('event: ')===0){eventType=line.slice(7);continue}if(line.indexOf('data: ')!==0)continue;try{var d=JSON.parse(line.slice(6));if(eventType==='plan'){planData=d;return}if(eventType==='stage'){handleStageEvent(p,d);return}if(eventType==='phase'){if(d.msg){p.dom.route.innerHTML='<span>'+escHtml(d.msg)+'</span>'}return}if(eventType==='done'){if(d.summary)txt+=d.summary;return}if(eventType==='error'){if(d.msg)p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(d.msg)+'</span>';return}if(d.content){txt+=d.content;p.currentAssistantMsg.innerHTML=renderMD(txt)+'<span class="cursor"></span>';p.dom.messages.scrollTop=p.dom.messages.scrollHeight}else if(d.summary){txt+=d.summary}}catch(_){}}read()})}function finish(){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentConvo.messages.push({role:'assistant',content:txt||'调度完成'});saveAllConvos();setStreaming(p,!1);hidePipeline(p);if(planData&&planData.phases){executePlan(planData)}if(planData&&planData.dag_info){renderDAGTree(planData.dag_info,p.currentAssistantMsg)};loadCostOverview();processQueue(p.id)}read()}).catch(function(e){if(e.name==='AbortError'){var c=p.currentAssistantMsg.querySelector('.cursor');if(c)c.remove();p.currentAssistantMsg.innerHTML+=' <span style="color:var(--warn)">⏹ 已停止</span>'}else{if(p.currentAssistantMsg)p.currentAssistantMsg.innerHTML='<span style="color:var(--danger)">❌ '+escHtml(e.message)+'</span>'}setStreaming(p,!1);p._reader=null;hidePipeline(p);processQueue(p.id)})}
function handleStageEvent(p,d){if(d.pipeline&&!p._pipelineInit){p._pipelineInit=true;p._pipelineStages=d.pipeline;stageStatus={};d.pipeline.forEach(function(s){stageStatus[s.stage]='pending'});renderPipelineBar(p)}if(d.stage){stageStatus[d.stage]=d.status;renderPipelineBar(p);if(d.model_tier){p.dom.route.innerHTML='<span>📋 '+d.stage+'</span><span style="color:var(--accent)">'+d.model_tier+'</span>'}if(d.pass_k){var pk=d.pass_k;var pkSummary='🔍 pass@3: '+(pk.overall?'✅ 通过':'❌ 未通过')+' (';var names=Object.keys(pk.perspectives||{});pkSummary+=names.map(function(n){return (pk.perspectives[n].passed?'✓':'✗')+' '+n}).join(', ');pkSummary+=')';p.dom.route.innerHTML='<span>'+pkSummary+'</span>'}}}
function renderPipelineBar(p){var bar=p.dom.pipeline;if(!bar)return;var stages=p._pipelineStages||[{stage:'research',label:'研究'},{stage:'plan',label:'方案'},{stage:'dry_run',label:'预演'},{stage:'gate',label:'门控'},{stage:'implement',label:'实施'},{stage:'review',label:'审查'},{stage:'verify',label:'验证'}];var iconMap={pending:'⚪',active:'🔵',passed:'✅',failed:'❌',verifying:'🔍'};bar.style.display='flex';bar.innerHTML=stages.map(function(s,i){var st=stageStatus[s.stage]||'pending';var cls='pipeline-dot '+(st==='active'||st==='verifying'?'active':st==='passed'?'done':st==='failed'?'fail':'');return'<div style="display:flex;align-items:center;gap:3px"><span class="'+cls+'" title="'+escHtml(s.label||s.stage)+': '+st+'"></span><span style="font-size:9px;color:var(--muted)">'+escHtml(s.label||s.stage)+'</span>'+(i<stages.length-1?'<span style="color:var(--border2)">—</span>':'')+'</div>'}).join('')}
function hidePipeline(p){var bar=p.dom.pipeline;if(bar){setTimeout(function(){bar.style.display='none'},3000);p._pipelineInit=false;p._pipelineStages=null}}
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

/* ── 空状态快捷操作 ── */
function quickAction(pid,type){var actions={1:t('chatQuickAction1'),2:t('chatQuickAction2'),3:t('chatQuickAction3')};var text=actions[type]||'';var p=panels.find(function(x){return x.id===pid});if(!p)return;p.dom.input.value=text;p.dom.input.focus();p.dom.sendBtn.disabled=false;p.dom.input.style.height='auto';p.dom.input.style.height=Math.min(p.dom.input.scrollHeight,100)+'px'}

/* ── 页面离开保护 ── */
window.addEventListener('beforeunload',function(e){var hasActive=panels.some(function(p){return p.isStreaming});if(hasActive){e.preventDefault();e.returnValue=t('sseActiveWarn');return e.returnValue}});

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

/* ── 模板下拉选择器 ── */
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
