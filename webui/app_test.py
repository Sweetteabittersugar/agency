/* Agency — 前端 JS */
var panels=[],pidSeq=0,perPage=1,curPage=0,focusedPid=null,orchMode=!1,devMode=!1;
var conversations=[],agents=[];try{conversations=JSON.parse(localStorage.getItem('agency_convos')||'[]')}catch(_){}
var projDir='',apiKey='',apiProvider='deepseek',authToken='';
try{projDir=localStorage.getItem('agency_proj_dir')||''}catch(_){}
try{apiKey=localStorage.getItem('agency_api_key')||''}catch(_){}
try{apiProvider=localStorage.getItem('agency_api_provider')||'deepseek'}catch(_){}
try{authToken=localStorage.getItem('agency_auth_token')||''}catch(_){}
var _saveTimer=null,_lastHarnessTab='overview';
/* --- setup guide 4-step --- */
var setupData=null,_setupStep=1;
fetch('/api/setup/status').then(function(r){return r.json()}).then(function(d){
  setupData=d;
  if(d.needs_setup){showSetupStep(1)}
}).catch(function(){});

function showSetupStep(step){
  _setupStep=step;
  var body=,footer=,ov=;
  if(step===1){
    .textContent='Welcome to Agency';
    body.innerHTML='<p style="font-size:12px;color:var(--text2);margin-bottom:12px">Step 1: API Key</p>'+
      '<select class="proj-input" id="setup-provider" style="margin-bottom:8px"><option value="deepseek">DeepSeek</option><option value="anthropic">Anthropic</option><option value="openai">OpenAI</option><option value="google">Google</option><option value="xai">xAI</option><option value="siliconflow">SiliconFlow</option><option value="qwen">Qwen</option><option value="kimi">Kimi</option><option value="glm">GLM</option><option value="minimax">MiniMax</option><option value="custom">Custom</option></select>'+
      '<input class="proj-input" id="setup-key" type="password" placeholder="sk-..." autocomplete="off">'+
      '<p style="font-size:10px;color:var(--muted);margin-top:4px">Key stored in local .env only</p>';
    footer.innerHTML='<button class="btn" onclick=".classList.remove(\'on\')" style="font-size:11px">Skip</button><button class="new-chat-btn" onclick="setupNext()" style="width:auto;font-size:11px;padding:5px 20px">Next</button>';
    ov.classList.add('on');
  } else if(step===2){
    .textContent='Project Folder (optional)';
    body.innerHTML='<p style="font-size:12px;color:var(--text2);margin-bottom:12px">Set project folder for file browsing</p>'+
      '<input class="proj-input" id="setup-proj-dir" placeholder="e.g. D:\ai" value="'+escHtml(projDir)+'">'+
      '<p style="font-size:10px;color:var(--muted);margin-top:4px">Can skip, configurable later</p>';
    footer.innerHTML='<button class="btn" onclick="showSetupStep(1)" style="font-size:11px">Back</button><button class="new-chat-btn" onclick="setupNext()" style="width:auto;font-size:11px;padding:5px 20px">Next</button><button class="btn" onclick="setupNext()" style="font-size:11px;margin-left:4px">Skip</button>';
  } else if(step===3){
    .textContent='Remote Access (optional)';
    body.innerHTML='<p style="font-size:12px;color:var(--text2);margin-bottom:12px">Access from phone/tablet</p>'+
      '<label style="display:flex;align-items:center;gap:8px;font-size:12px;margin-bottom:8px"><input type="checkbox" id="setup-remote"> Enable remote access</label>';
    footer.innerHTML='<button class="btn" onclick="showSetupStep(2)" style="font-size:11px">Back</button><button class="new-chat-btn" onclick="setupNext()" style="width:auto;font-size:11px;padding:5px 20px">Next</button><button class="btn" onclick="setupFinish()" style="font-size:11px;margin-left:4px">Skip</button>';
  } else if(step===4){
    if(!setupData._remote_token){
      setupData._remote_token=Array(16).fill(0).map(function(){return'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'.charAt(Math.floor(Math.random()*62))}).join('');
    }
    body.innerHTML='<p style="font-size:12px;color:var(--text2);margin-bottom:12px">Remote password config</p>'+
      '<p style="font-size:10px;color:var(--muted);margin-bottom:4px">Password (auto-generated)</p>'+
      '<div style="display:flex;gap:4px"><input class="proj-input" id="setup-remote-token" style="flex:1;margin:0;font-size:11px;font-family:monospace" value="'+escHtml(setupData._remote_token)+'"><button class="btn" onclick="setupData._remote_token=Array(16).fill(0).map(function(){return\'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\'.charAt(Math.floor(Math.random()*62))}).join(\'\');.value=setupData._remote_token" style="font-size:10px">Random</button></div>'+
      '<p style="font-size:10px;color:var(--muted);margin-top:8px">Access URL shown in Settings panel after start</p>';
    footer.innerHTML='<button class="btn" onclick="showSetupStep(3)" style="font-size:11px">Back</button><button class="new-chat-btn" onclick="setupFinish()" style="width:auto;font-size:11px;padding:5px 20px">Finish</button>';
  }
}

function setupNext(){
  if(_setupStep===1){
    var key=.value.trim();
    if(!key){showToast('Please enter API Key',!0);return}
    setupData._api_key=key;
    setupData._api_provider=.value;
  } else if(_setupStep===2){
    var dirEl=;
    if(dirEl){
      var dir=dirEl.value.trim();
      if(dir){projDir=dir;localStorage.setItem('agency_proj_dir',projDir)}
    }
  }
  if(_setupStep<4){showSetupStep(_setupStep+1)}
  else{setupFinish()}
}

function setupFinish(){
  var remoteOn=!!(&&.checked);
  var remoteToken=remoteOn?((&&.value.trim())||setupData._remote_token||''):'';
  var body={api_key:setupData._api_key||'',api_provider:setupData._api_provider||'deepseek',remote_enabled:remoteOn,remote_token:remoteToken};
  fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      .classList.remove('on');
      apiKey=setupData._api_key||'';apiProvider=setupData._api_provider||'deepseek';
      localStorage.setItem('agency_api_key',apiKey);localStorage.setItem('agency_api_provider',apiProvider);
      if(remoteToken){authToken=remoteToken;localStorage.setItem('agency_auth_token',remoteToken)}
      showToast('Setup complete!');
    } else showToast(d.error||'Save failed',!0);
  }).catch(function(e){showToast('Save failed: '+e.message,!0)});
}
