/* Agency — 首次配置向导（4步） */
var setupData=null,_setupStep=1;
fetch('/api/setup/status').then(function(r){return r.json()}).then(function(d){
  setupData=d;
  if(d.needs_setup){showSetupStep(1)}
}).catch(function(){});
function showSetupStep(step){
  _setupStep=step;
  var body=$('setup-body'),footer=$('setup-footer'),ov=$('setupOverlay');
  if(step===1){
    $('setup-title').textContent='欢迎使用 Agency';
    body.innerHTML='<p style=\"font-size:12px;color:var(--text2);margin-bottom:12px\">第一步：配置 API Key 以连接 AI 模型</p>'+
      '<select class=\"proj-input\" id=\"setup-provider\" style=\"margin-bottom:8px\"><option value=\"deepseek\">DeepSeek（推荐，便宜）</option><option value=\"anthropic\">Anthropic</option><option value=\"openai\">OpenAI</option><option value=\"google\">Google</option><option value=\"xai\">xAI (Grok)</option><option value=\"siliconflow\">硅基流动</option><option value=\"qwen\">通义千问</option><option value=\"kimi\">Kimi</option><option value=\"glm\">智谱 GLM</option><option value=\"minimax\">MiniMax</option><option value=\"custom\">自定义</option></select>'+
      '<input class=\"proj-input\" id=\"setup-key\" type=\"password\" placeholder=\"sk-…\" autocomplete=\"off\">'+
      '<p style=\"font-size:10px;color:var(--muted);margin-top:4px\">Key 仅存在本地 .env 文件，不会上传</p>';
    footer.innerHTML='<button class=\"btn\" onclick=\"$(\'setupOverlay\').classList.remove(\'on\')\" style=\"font-size:11px\">跳过</button><button class=\"new-chat-btn\" onclick=\"setupNext()\" style=\"width:auto;font-size:11px;padding:5px 20px\">下一步</button>';
    ov.classList.add('on');
  } else if(step===2){
    $('setup-title').textContent='项目文件夹（可选）';
    body.innerHTML='<p style=\"font-size:12px;color:var(--text2);margin-bottom:12px\">设置项目文件夹后可浏览文件、自动感知上下文</p>'+
      '<input class=\"proj-input\" id=\"setup-proj-dir\" placeholder=\"例: D:\\ai\" value=\"'+escHtml(projDir)+'\">'+
      '<p style=\"font-size:10px;color:var(--muted);margin-top:4px\">可跳过，之后在设置面板随时修改</p>';
    footer.innerHTML='<button class=\"btn\" onclick=\"showSetupStep(1)\" style=\"font-size:11px\">上一步</button><button class=\"new-chat-btn\" onclick=\"setupNext()\" style=\"width:auto;font-size:11px;padding:5px 20px\">下一步</button><button class=\"btn\" onclick=\"setupNext()\" style=\"font-size:11px;margin-left:4px\">跳过</button>';
  } else if(step===3){
    $('setup-title').textContent='远端访问（可选）';
    body.innerHTML='<p style=\"font-size:12px;color:var(--text2);margin-bottom:12px\">开启后可从手机/平板远程操作</p>'+
      '<label style=\"display:flex;align-items:center;gap:8px;font-size:12px;margin-bottom:8px\"><input type=\"checkbox\" id=\"setup-remote\"> 启用远端访问</label>';
    footer.innerHTML='<button class=\"btn\" onclick=\"showSetupStep(2)\" style=\"font-size:11px\">上一步</button><button class=\"new-chat-btn\" onclick=\"setupNext()\" style=\"width:auto;font-size:11px;padding:5px 20px\">下一步</button><button class=\"btn\" onclick=\"setupFinish()\" style=\"font-size:11px;margin-left:4px\">跳过</button>';
  } else if(step===4){
    if(!setupData._remote_token){
      setupData._remote_token=Array(16).fill(0).map(function(){return'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'.charAt(Math.floor(Math.random()*62))}).join('');
    }
    body.innerHTML='<p style=\"font-size:12px;color:var(--text2);margin-bottom:12px\">配置远端密码与连接信息</p>'+
      '<p style=\"font-size:10px;color:var(--muted);margin-bottom:4px\">访问密码（已自动生成，可修改）</p>'+
      '<div style=\"display:flex;gap:4px\"><input class=\"proj-input\" id=\"setup-remote-token\" style=\"flex:1;margin:0;font-size:11px;font-family:monospace\" value=\"'+escHtml(setupData._remote_token)+'\"><button class=\"btn\" onclick=\"setupData._remote_token=Array(16).fill(0).map(function(){return\"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\".charAt(Math.floor(Math.random()*62))}).join(\"\");$(\"setup-remote-token\").value=setupData._remote_token\" style=\"font-size:10px\">随机</button></div>'+
      '<p style=\"font-size:10px;color:var(--muted);margin-top:8px\">启动后访问地址将在设置面板「远端访问」中显示</p>';
    footer.innerHTML='<button class=\"btn\" onclick=\"showSetupStep(3)\" style=\"font-size:11px\">上一步</button><button class=\"new-chat-btn\" onclick=\"setupFinish()\" style=\"width:auto;font-size:11px;padding:5px 20px\">完成</button>';
  }
}
function setupNext(){
  if(_setupStep===1){
    var key=$('setup-key').value.trim();
    if(!key){showToast('请输入 API Key',!0);return}
    setupData._api_key=key;
    setupData._api_provider=$('setup-provider').value;
  } else if(_setupStep===2){
    var dirEl=$('setup-proj-dir');
    if(dirEl){
      var dir=dirEl.value.trim();
      if(dir){projDir=dir;localStorage.setItem('agency_proj_dir',projDir)}
    }
  }
  if(_setupStep<4){showSetupStep(_setupStep+1)}
  else{setupFinish()}
}
function setupFinish(){
  var remoteOn=!!($('setup-remote')&&$('setup-remote').checked);
  var remoteToken=remoteOn?(($('setup-remote-token')&&$('setup-remote-token').value.trim())||setupData._remote_token||''):'';
  var body={api_key:setupData._api_key||'',api_provider:setupData._api_provider||'deepseek',remote_enabled:remoteOn,remote_token:remoteToken};
  fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      $('setupOverlay').classList.remove('on');
      apiKey=setupData._api_key||'';apiProvider=setupData._api_provider||'deepseek';
      localStorage.setItem('agency_api_key',apiKey);localStorage.setItem('agency_api_provider',apiProvider);
      if(remoteToken){authToken=remoteToken;localStorage.setItem('agency_auth_token',remoteToken)}
      showToast('配置完成！');
    } else showToast(d.error||'保存失败',!0);
  }).catch(function(e){showToast('保存失败: '+e.message,!0)});
}
