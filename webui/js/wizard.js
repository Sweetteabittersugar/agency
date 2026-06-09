/* Agency — 首次配置向导（5步：欢迎 → Key → 项目 → 远端 → 完成） */
var setupData=null,_setupStep=0,_demoMode=false;
fetch('/api/setup/status').then(function(r){return r.json()}).then(function(d){
  setupData=d;
  if(d.needs_setup){showSetupStep(0)}
}).catch(function(){});

function showSetupStep(step){
  _setupStep=step;
  var body=$('setup-body'),footer=$('setup-footer'),ov=$('setupOverlay');
  if(!body||!footer||!ov)return;

  // ── Step 0: 欢迎页 ──
  if(step===0){
    $('setup-title').textContent='Welcome to Agency';
    body.innerHTML=
      '<p style="font-size:13px;color:var(--text);margin-bottom:16px;text-align:center">Claude Code 的 Web 操作面板</p>'+
      '<div style="display:flex;gap:12px;margin-bottom:16px">'+
        '<div style="flex:1;text-align:center;padding:12px 8px;background:var(--surface2);border-radius:var(--radius)">'+
          '<div style="font-size:20px;margin-bottom:4px">🧠</div>'+
          '<div style="font-size:11px;font-weight:600;color:var(--text)">多 Agent 协作</div>'+
          '<div style="font-size:10px;color:var(--muted);margin-top:2px">31 个专业 Agent<br>智能匹配任务</div>'+
        '</div>'+
        '<div style="flex:1;text-align:center;padding:12px 8px;background:var(--surface2);border-radius:var(--radius)">'+
          '<div style="font-size:20px;margin-bottom:4px">📊</div>'+
          '<div style="font-size:11px;font-weight:600;color:var(--text)">实时监控</div>'+
          '<div style="font-size:10px;color:var(--muted);margin-top:2px">Token · 费用 · 权限<br>一目了然</div>'+
        '</div>'+
        '<div style="flex:1;text-align:center;padding:12px 8px;background:var(--surface2);border-radius:var(--radius)">'+
          '<div style="font-size:20px;margin-bottom:4px">📱</div>'+
          '<div style="font-size:11px;font-weight:600;color:var(--text)">手机操控</div>'+
          '<div style="font-size:10px;color:var(--muted);margin-top:2px">远程访问<br>随时随地</div>'+
        '</div>'+
      '</div>'+
      '<p style="font-size:10px;color:var(--muted);text-align:center;margin-bottom:8px">🔒 所有数据仅存本地，永不离开你的设备</p>';
    footer.innerHTML=
      '<button class="btn primary" onclick="enterDemoMode()" style="width:auto;font-size:12px;padding:8px 24px">🚀 跳过，直接体验 Demo</button>'+
      '<button class="btn" onclick="showSetupStep(1)" style="width:auto;font-size:12px;padding:8px 24px">⚙️ 开始配置</button>';
    ov.classList.add('on');
    return;
  }

  // ── Step 1: API Key ──
  if(step===1){
    $('setup-title').textContent='配置 API Key';
    body.innerHTML=
      '<p style="font-size:12px;color:var(--text2);margin-bottom:8px">选择一个 AI 模型供应商，输入你的 API Key</p>'+
      '<select class="proj-input" id="setup-provider" style="margin-bottom:8px">'+
        '<option value="deepseek">DeepSeek ⭐推荐 — 便宜 + 中文好</option>'+
        '<option value="anthropic">Anthropic (Claude)</option>'+
        '<option value="openai">OpenAI (GPT)</option>'+
        '<option value="google">Google (Gemini)</option>'+
        '<option value="xai">xAI (Grok)</option>'+
        '<option value="siliconflow">硅基流动</option>'+
        '<option value="qwen">通义千问</option>'+
        '<option value="kimi">Kimi (月之暗面)</option>'+
        '<option value="glm">智谱 GLM</option>'+
        '<option value="minimax">MiniMax</option>'+
        '<option value="custom">自定义端点</option>'+
      '</select>'+
      '<div style="position:relative">'+
        '<input class="proj-input" id="setup-key" type="password" placeholder="sk-…" autocomplete="off" style="padding-right:80px">'+
        '<button class="btn" onclick="var el=document.getElementById(\'setup-key\');el.type=el.type===\'password\'?\'text\':\'password\'" style="position:absolute;right:4px;top:50%;transform:translateY(-50%);font-size:10px;padding:2px 8px">👁 显示</button>'+
      '</div>'+
      '<p style="font-size:10px;color:var(--muted);margin-top:6px">'+
        '🔒 Key 仅存浏览器本地存储和 .env 文件，<b>永不离开你的设备</b>。'+
        ' 没有 Key？<a href="https://platform.deepseek.com/api_keys" target="_blank" style="color:var(--accent)">去 DeepSeek 免费注册 →</a>'+
      '</p>';
    footer.innerHTML=
      '<button class="btn" onclick="enterDemoMode()" style="font-size:11px">跳过，先进去看看</button>'+
      '<button class="btn primary" onclick="setupNext()" style="width:auto;font-size:11px;padding:6px 20px">下一步 →</button>';
    ov.classList.add('on');
    return;
  }

  // ── Step 2: 项目文件夹 ──
  if(step===2){
    $('setup-title').textContent='项目文件夹（可选）';
    body.innerHTML=
      '<p style="font-size:12px;color:var(--text2);margin-bottom:12px">设置后可在侧边栏浏览项目文件、自动感知上下文</p>'+
      '<input class="proj-input" id="setup-proj-dir" placeholder="例: D:\\projects\\my-app（留空使用当前目录）" value="'+escHtml(projDir)+'">'+
      '<p style="font-size:10px;color:var(--muted);margin-top:4px">可跳过，之后在设置面板随时修改</p>';
    footer.innerHTML=
      '<button class="btn" onclick="showSetupStep(1)" style="font-size:11px">← 上一步</button>'+
      '<button class="btn" onclick="showSetupStep(3)" style="font-size:11px;margin-left:4px">跳过</button>'+
      '<button class="btn primary" onclick="setupNext()" style="width:auto;font-size:11px;padding:6px 20px">下一步 →</button>';
    return;
  }

  // ── Step 3: 远端访问 ──
  if(step===3){
    $('setup-title').textContent='远端访问（可选）';
    body.innerHTML=
      '<p style="font-size:12px;color:var(--text2);margin-bottom:12px">开启后可从手机/平板浏览器远程操控 Agency</p>'+
      '<label style="display:flex;align-items:center;gap:8px;font-size:12px;margin-bottom:8px;cursor:pointer">'+
        '<input type="checkbox" id="setup-remote" onchange="var t=document.getElementById(\'remote-config\');if(t)t.style.display=this.checked?\'block\':\'none\'"> 启用远端访问</label>'+
      '<div id="remote-config" style="display:none">'+
        '<p style="font-size:10px;color:var(--muted);margin-bottom:4px">访问密码（自动生成，可修改）</p>'+
        '<div style="display:flex;gap:4px">'+
          '<input class="proj-input" id="setup-remote-token" style="flex:1;margin:0;font-size:11px;font-family:monospace" value="'+escHtml(setupData&&setupData._remote_token||'')+'">'+
          '<button class="btn" onclick="var t=Array(16).fill(0).map(function(){return\'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\'.charAt(Math.floor(Math.random()*62))}).join(\'\');document.getElementById(\'setup-remote-token\').value=t" style="font-size:10px">🎲 随机</button>'+
        '</div>'+
      '</div>';
    footer.innerHTML=
      '<button class="btn" onclick="showSetupStep(2)" style="font-size:11px">← 上一步</button>'+
      '<button class="btn primary" onclick="setupFinish()" style="width:auto;font-size:11px;padding:6px 20px">✅ 完成配置</button>';
    return;
  }

  // ── Step 4: 完成确认 ──
  if(step===4){
    var providerName=$('setup-provider')?$('setup-provider').selectedOptions[0].text.split(' ')[0]:'DeepSeek';
    body.innerHTML=
      '<div style="text-align:center;padding:16px 0">'+
        '<div style="font-size:32px;margin-bottom:8px">🎉</div>'+
        '<p style="font-size:13px;color:var(--text);margin-bottom:4px">配置完成！</p>'+
        '<p style="font-size:11px;color:var(--text2)">Provider: '+escHtml(providerName)+'</p>'+
        '<p style="font-size:11px;color:var(--text2)">项目: '+escHtml(projDir||'当前目录')+'</p>'+
        '<p style="font-size:10px;color:var(--muted);margin-top:12px">正在启动 Agency…</p>'+
      '</div>';
    footer.innerHTML='';
    return;
  }
}

function setupNext(){
  if(_setupStep===1){
    var key=$('setup-key').value.trim();
    if(!key){showToast('请输入 API Key 或点击"跳过"体验 Demo',true);return}
    setupData._api_key=key;
    setupData._api_provider=$('setup-provider').value;
  } else if(_setupStep===2){
    var dirEl=$('setup-proj-dir');
    if(dirEl){
      var dir=dirEl.value.trim();
      if(dir){projDir=dir;localStorage.setItem('agency_proj_dir',projDir)}
    }
  }
  if(_setupStep===2){showSetupStep(3)}
  else{showSetupStep(_setupStep+1)}
}

function setupFinish(){
  var remoteOn=!!($('setup-remote')&&$('setup-remote').checked);
  var remoteToken=remoteOn?(($('setup-remote-token')&&$('setup-remote-token').value.trim())||(setupData&&setupData._remote_token)||''):'';
  var body={api_key:setupData._api_key||'',api_provider:setupData._api_provider||'deepseek',remote_enabled:remoteOn,remote_token:remoteToken};

  showSetupStep(4); // 先展示完成页

  fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      setTimeout(function(){
        $('setupOverlay').classList.remove('on');
        apiKey=setupData._api_key||'';apiProvider=setupData._api_provider||'deepseek';
        localStorage.setItem('agency_api_key',apiKey);localStorage.setItem('agency_api_provider',apiProvider);
        if(remoteToken){authToken=remoteToken;localStorage.setItem('agency_auth_token',remoteToken)}
        _demoMode=false;
        showToast('配置完成！发送一条消息试试吧 🚀');
      },600);
    } else {
      $('setupOverlay').classList.remove('on');
      showToast(d.error||'保存失败，但你可以先体验 Demo',true);
      _demoMode=true;
    }
  }).catch(function(e){
    $('setupOverlay').classList.remove('on');
    showToast('保存失败，进入 Demo 模式',false);
    _demoMode=true;
  });
}

/* ── Demo 模式 ── */
function enterDemoMode(){
  _demoMode=true;
  $('setupOverlay').classList.remove('on');
  showToast('🎮 Demo 模式 — 无 Key 也能浏览完整界面');
  // 在第一个面板显示欢迎消息
  if(panels.length>0){
    var p=panels[0];
    addMsg(p,'assistant',
      '👋 **欢迎来到 Agency！**\n\n'+
      '这是 Demo 模式 — 你可以浏览所有功能，但 Agent 不会实际执行。\n\n'+
      '**快速上手：**\n'+
      '1. 左侧边栏 — 查看 31 个 Agent 和 40+ Skills\n'+
      '2. 📊 仪表盘 — 费用追踪、权限日志\n'+
      '3. 🔧 设置 — 配置 API Key、Agent 工厂\n'+
      '4. 🧠 智能调度 — 复杂任务自动拆解\n'+
      '5. 📱 远端访问 — 手机也能操控\n\n'+
      '准备好了？点右上角 🔧 → 填入你的 API Key → 开始干活！'
    );
  }
}
