/* Agency — 开发者设置面板 */
function saveApiKey(){apiKey=$('api-key').value.trim();apiProvider=$('api-provider').value;localStorage.setItem('agency_api_key',apiKey);localStorage.setItem('agency_api_provider',apiProvider);$('api-status').textContent=apiKey?'已保存':'已清除';if(!apiKey){localStorage.removeItem('agency_api_key');localStorage.removeItem('agency_api_provider')}}
function toggleDevOverlay(){devMode=!devMode;var ov=$('devOverlay'),btn=$('devBtn');ov.classList.toggle('on',devMode);btn.classList.toggle('on',devMode);if(devMode){var ak=$('api-key');if(ak&&apiKey)ak.value=apiKey;var ap=$('api-provider');if(ap&&apiProvider)ap.value=apiProvider;loadMemList();loadRemotePanel();loadIntegrationPanel()}}

function loadMemList(){var domEl=$('mem-list');if(!domEl)return;fetch('/api/memory').then(function(r){return r.json()}).then(function(d){var files=d.files||[];domEl.innerHTML=files.length?files.map(function(f){return'<div class="mem-file" onclick="openMemEditor(\''+escHtml(f.path)+'\',\''+escHtml(f.name)+'\')"><span class="icon">📄</span><span>'+escHtml(f.name)+'</span><span style="color:var(--muted);font-size:10px;margin-left:auto">'+(f.size||0)+'B</span></div>'}).join(''):'暂无记忆文件'}).catch(function(){domEl.innerHTML='加载失败'})}
function generateAgent(){var input=$('agent-factory-input'),output=$('agent-factory-output');var req=input.value.trim();if(!req)return;output.innerHTML='生成中…';fetch('/api/agent-generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({requirement:req,api_key:apiKey||undefined,api_provider:apiProvider||undefined})}).then(function(resp){var reader=resp.body.getReader(),decoder=new TextDecoder(),buf='',txt='';function read(){reader.read().then(function(result){if(result.done){finish();return}buf+=decoder.decode(result.value,{stream:!0});buf=buf.replace(/\r\n/g,'\n');var lines=buf.split('\n');buf=lines.pop()||'';for(var i=0;i<lines.length;i++){if(lines[i].indexOf('data: ')!==0)continue;try{var d=JSON.parse(lines[i].slice(6));if(d.content)txt+=d.content;if(d.error){output.innerHTML='<span style=color:var(--danger)>'+escHtml(d.error)+'</span>';return}}catch(_){}}read()})}function finish(){output.innerHTML='<pre style=\"font-size:10px;max-height:200px;overflow:auto;background:var(--bg);padding:8px;border-radius:4px\">'+escHtml(txt)+'</pre><button class=\"new-chat-btn\" style=\"margin-top:4px\" onclick=\"saveAgent()\">保存此 Agent</button>';output._agentContent=txt}read()}).catch(function(){output.innerHTML='生成失败'})}
function saveAgent(){var txt=$('agent-factory-output')._agentContent;if(!txt)return;var m=txt.match(/name:\s*"?([a-z0-9-]+)"?/i);var name=m?m[1]:('agent-'+Date.now().toString(36));fetch('/api/agent-create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,content:txt})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('Agent 已保存: '+name);loadAgents()}else{showToast(d.error||'保存失败',!0)}}).catch(function(){showToast('保存失败',!0)})}
function loadRemotePanel(){
  var domEl=$('remote-panel');if(!domEl){console.debug('remote-panel not found');return}
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
    domEl.innerHTML=html;
  }).catch(function(e){console.error('loadRemotePanel:',e);domEl.innerHTML='加载失败: '+escHtml(e.message)});
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
  }).catch(function(e){showToast('更新失败: '+e.message,!0)});
}
function genRemoteToken(){
  fetch('/api/remote/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:true,token:''})}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){authToken=d.token;localStorage.setItem('agency_auth_token',d.token);$('remote-token-input').value=d.token;showToast('新密码: '+d.token);}
    else showToast(d.error||'生成失败',!0);
  }).catch(function(e){showToast('生成失败: '+e.message,!0)});
}
function copyRemoteUrl(){
  var domEl=$('remote-url');if(!domEl)return;
  domEl.select();document.execCommand('copy');showToast('已复制连接地址');
}
function loadIntegrationPanel(){
  var domEl=$('integration-panel');if(!domEl)return;
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
    domEl.innerHTML=html;
    var btn=document.getElementById('hook-copy-btn');
    if(btn)btn.onclick=function(){copyText(hookUrl)};
  }).catch(function(){domEl.innerHTML='加载失败'});
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
  fetch('/api/memory/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:content.value})}).then(function(r){return r.json()}).then(function(d){if(d.ok){showToast('已保存: '+d.name);document.getElementById('mem-editor').innerHTML='';loadMemList()}else{showToast(d.error||'保存失败',!0)}}).catch(function(e){showToast('保存失败: '+e.message,!0)});
}
