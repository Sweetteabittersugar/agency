/* Agency — 首次配置向导（5步：欢迎 → Key → 项目 → 远端 → 完成） */
var setupData=null,_setupStep=0,_demoMode=false,_wizardProvider='',_wizardRegion='',_wizardBudget='';
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
      '<button class="btn" onclick="showSetupStep(1)" style="width:auto;font-size:12px;padding:8px 24px">⚙️ 开始配置</button>'+
      '<button class="btn" onclick="unlockAllFromWizard()" style="font-size:10px;color:var(--muted);margin-top:6px;width:100%;text-align:center;background:transparent;border:1px dashed var(--border2);padding:5px 0">🔓 '+t('wizardUnlockAll')+'</button>';
    ov.classList.add('on');
    return;
  }

  // ── Step 1: Provider 智能推荐（Q&A 引导）──
  if(step===1){
    $('setup-title').textContent='配置 API Key';
    _wizardRegion='';_wizardBudget='';_wizardProvider='';
    renderProviderQ1(body,footer,ov);
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
        '<p style="font-size:11px;color:var(--accent);margin-top:8px;font-weight:600">所有功能已解锁 — 聊天 · 看板 · Agent · 调度 · 多面板</p>'+
        '<p style="font-size:10px;color:var(--muted);margin-top:12px">正在启动 Agency…</p>'+
      '</div>';
    footer.innerHTML='';
    return;
  }
}

/* ── Provider 智能推荐 Step 1 ── */

function renderProviderQ1(body,footer,ov){
  body.innerHTML=
    '<p style="font-size:12px;color:var(--text);margin-bottom:12px;font-weight:600">'+t('providerRegion')+'</p>'+
    '<p style="font-size:10px;color:var(--muted);margin-bottom:12px">💡 '+t('providerRegionHint')+'</p>'+
    '<div style="display:flex;gap:10px;margin-bottom:12px">'+
      '<div class="provider-region-card" onclick="selectRegion(\'cn\')" id="region-cn" style="flex:1;padding:16px 12px;background:var(--surface2);border-radius:var(--radius);text-align:center;cursor:pointer;border:2px solid var(--border2);transition:all .15s">'+
        '<div style="font-size:24px;margin-bottom:6px">🌏</div>'+
        '<div style="font-size:13px;font-weight:600;color:var(--text)">'+t('providerRegionCN')+'</div>'+
        '<div style="font-size:10px;color:var(--muted);margin-top:4px">DeepSeek · 通义千问<br>Kimi · 智谱 · 硅基流动</div>'+
      '</div>'+
      '<div class="provider-region-card" onclick="selectRegion(\'global\')" id="region-global" style="flex:1;padding:16px 12px;background:var(--surface2);border-radius:var(--radius);text-align:center;cursor:pointer;border:2px solid var(--border2);transition:all .15s">'+
        '<div style="font-size:24px;margin-bottom:6px">🌍</div>'+
        '<div style="font-size:13px;font-weight:600;color:var(--text)">'+t('providerRegionGlobal')+'</div>'+
        '<div style="font-size:10px;color:var(--muted);margin-top:4px">Claude · OpenAI · Gemini<br>Grok · 自定义端点</div>'+
      '</div>'+
    '</div>';
  footer.innerHTML=
    '<button class="btn" onclick="enterDemoMode()" style="font-size:11px">跳过</button>'+
    '<button class="btn" onclick="showSetupStep(0)" style="font-size:11px">← 返回</button>';
  ov.classList.add('on');
}

function selectRegion(region){
  _wizardRegion=region;
  // highlight selected
  document.querySelectorAll('.provider-region-card').forEach(function(el){el.style.borderColor='var(--border2)'});
  var sel=document.getElementById('region-'+region);
  if(sel)sel.style.borderColor='var(--accent)';
  // proceed to Q2
  setTimeout(function(){renderProviderQ2($('setup-body'),$('setup-footer'))},200);
}

function renderProviderQ2(body,footer){
  body.innerHTML=
    '<p style="font-size:12px;color:var(--text);margin-bottom:4px;font-weight:600">'+t('providerBudget')+'</p>'+
    '<p style="font-size:10px;color:var(--muted);margin-bottom:12px">当前地区: '+
      (_wizardRegion==='cn'?t('providerRegionCN'):t('providerRegionGlobal'))+'</p>'+
    '<div id="provider-recommendations" style="margin-bottom:12px"></div>'+
    '<div style="margin-bottom:8px">'+
      '<div style="font-size:10px;color:var(--muted);cursor:pointer;padding:6px 0;border-top:1px solid var(--border)" onclick="toggleAllProviders()" id="provider-toggle-all">'+t('providerShowAll')+'</div>'+
      '<div id="all-providers-list" style="display:none;max-height:200px;overflow-y:auto;padding:8px;background:var(--surface2);border-radius:var(--radius-sm)"></div>'+
    '</div>'+
    '<div id="provider-auto-fill" style="font-size:10px;color:var(--muted);margin-bottom:8px;display:none"></div>'+
    '<div style="position:relative">'+
      '<input class="proj-input" id="setup-key" type="password" placeholder="sk-…" autocomplete="off" style="padding-right:80px;margin-bottom:4px">'+
      '<button class="btn" onclick="var el=document.getElementById(\'setup-key\');el.type=el.type===\'password\'?\'text\':\'password\'" style="position:absolute;right:4px;top:4px;font-size:10px;padding:2px 8px">👁 显示</button>'+
    '</div>'+
    '<input class="proj-input" id="setup-provider" value="" type="hidden">'+
    '<p style="font-size:10px;color:var(--muted);margin-top:2px">'+
      '🔒 Key 仅存浏览器本地存储和 .env 文件，<b>永不离开你的设备</b>'+
    '</p>';
  footer.innerHTML=
    '<button class="btn" onclick="enterDemoMode()" style="font-size:11px">跳过</button>'+
    '<button class="btn" onclick="showSetupStep(1)" style="font-size:11px">← 重选地区</button>'+
    '<button class="btn primary" id="setup-next-btn" onclick="setupNext()" style="width:auto;font-size:11px;padding:6px 20px">下一步 →</button>';

  renderBudgetCards();
  renderAllProvidersDropdown();
}

function renderBudgetCards(){
  var container=document.getElementById('provider-recommendations');
  if(!container)return;

  var budgetTiers=[
    {key:'free',icon:'💰',label:t('providerBudgetFree'),descKey:'free'},
    {key:'mid',icon:'💳',label:t('providerBudgetMid'),descKey:'mid'},
    {key:'high',icon:'🚀',label:t('providerBudgetHigh'),descKey:'high'}
  ];

  var html='';
  budgetTiers.forEach(function(tier){
    var providers=getProvidersForRegionBudget(_wizardRegion,tier.key);
    var selectedClass= _wizardBudget===tier.key?' budget-selected':'';
    html+='<div class="budget-tier-card'+selectedClass+'" onclick="selectBudget(\''+tier.key+'\')" id="budget-'+tier.key+'" style="padding:10px 12px;margin-bottom:6px;background:var(--surface2);border-radius:var(--radius);cursor:pointer;border:2px solid var(--border2);transition:all .15s">';
    html+='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">';
    html+='<span style="font-size:12px;font-weight:600;color:var(--text)">'+tier.icon+' '+tier.label+'</span>';
    html+='</div>';
    html+='<div style="display:flex;gap:6px;flex-wrap:wrap">';
    providers.forEach(function(p){
      html+='<div style="flex:1;min-width:100px;padding:6px 8px;background:var(--bg);border-radius:4px;text-align:center">';
      html+='<div style="font-size:11px;font-weight:600;color:var(--text)">'+escHtml(p.name)+'</div>';
      html+='<div style="font-size:9px;color:var(--muted);margin-top:1px">'+escHtml(p.desc.slice(0,20))+'</div>';
      html+='<div style="font-size:9px;color:var(--text2);margin-top:2px">'+t('providerEstimated')+': '+escHtml(p.est_monthly[tier.descKey]||'—')+'</div>';
      if(p.free_credit)html+='<div style="font-size:8px;color:var(--accent);margin-top:1px">'+escHtml(p.free_credit)+'</div>';
      html+='</div>';
    });
    html+='</div></div>';
  });
  container.innerHTML=html;
}

function selectBudget(budget){
  _wizardBudget=budget;
  // highlight
  document.querySelectorAll('.budget-tier-card').forEach(function(el){el.style.borderColor='var(--border2)'});
  var sel=document.getElementById('budget-'+budget);
  if(sel)sel.style.borderColor='var(--accent)';

  // auto-pick best provider
  var providers=getProvidersForRegionBudget(_wizardRegion,budget);
  if(providers.length>0){
    var best=providers[0];
    _wizardProvider=best.key;
    var fillDiv=document.getElementById('provider-auto-fill');
    if(fillDiv){
      fillDiv.style.display='block';
      fillDiv.innerHTML='✅ '+t('providerAutoFilled')+' <b>'+escHtml(best.name)+'</b> — API: <code style="font-size:9px">'+escHtml(best.api_base)+'</code> — 模型: <code style="font-size:9px">'+escHtml(best.default_model)+'</code>'+
        (best.register_url?' <a href="'+escHtml(best.register_url)+'" target="_blank" style="color:var(--accent);font-size:10px">📝 '+t('providerRegister')+'</a>':'');
    }
    // store provider value in hidden input
    var providerInput=document.getElementById('setup-provider');
    if(providerInput)providerInput.value=best.key;
  }
}

function getProvidersForRegionBudget(region,budget){
  var result=[];
  Object.keys(PROVIDER_DB).forEach(function(key){
    var p=PROVIDER_DB[key];
    var regionMatch=(region==='cn')?(p.region==='cn'||p.region==='any'):(p.region==='global'||p.region==='any');
    if(!regionMatch)return;
    if(budget==='free' && p.price_tier!=='free')return;
    if(budget==='mid' && (p.price_tier==='free'||p.price_tier==='mid')){/*pass*/}
    else if(budget==='high'){/*all pass*/}
    else if(budget!=='mid' && p.price_tier!==budget)return;
    result.push(Object.assign({key:key},p));
  });
  // sort: free first, then mid, then high; within same tier, recommended ones first
  result.sort(function(a,b){
    var tierOrder={free:0,mid:1,high:2,any:3};
    return (tierOrder[a.price_tier]||0)-(tierOrder[b.price_tier]||0);
  });
  return result;
}

function renderAllProvidersDropdown(){
  var container=document.getElementById('all-providers-list');
  if(!container)return;
  var html='<select class="proj-input" id="setup-provider-select" style="margin:0;font-size:11px" onchange="onProviderSelect(this.value)">';
  html+='<option value="">— 手动选择 Provider —</option>';
  Object.keys(PROVIDER_DB).forEach(function(key){
    var p=PROVIDER_DB[key];
    var label=(p.price_tier==='free'?'💰 ':p.price_tier==='mid'?'💳 ':'') + p.name + ' — ' + p.desc;
    html+='<option value="'+escHtml(key)+'">'+escHtml(label)+'</option>';
  });
  html+='</select>';
  container.innerHTML=html;
}

function toggleAllProviders(){
  var list=document.getElementById('all-providers-list');
  var toggle=document.getElementById('provider-toggle-all');
  if(!list||!toggle)return;
  if(list.style.display==='none'){
    list.style.display='block';
    toggle.textContent=t('providerHideAll');
  }else{
    list.style.display='none';
    toggle.textContent=t('providerShowAll');
  }
}

function onProviderSelect(key){
  if(!key)return;
  _wizardProvider=key;
  var p=PROVIDER_DB[key];
  if(!p)return;
  var fillDiv=document.getElementById('provider-auto-fill');
  if(fillDiv){
    fillDiv.style.display='block';
    fillDiv.innerHTML='✅ '+t('providerAutoFilled')+' <b>'+escHtml(p.name)+'</b> — API: <code style="font-size:9px">'+escHtml(p.api_base)+'</code> — 模型: <code style="font-size:9px">'+escHtml(p.default_model)+'</code>'+
      (p.register_url?' <a href="'+escHtml(p.register_url)+'" target="_blank" style="color:var(--accent);font-size:10px">📝 '+t('providerRegister')+'</a>':'');
  }
  var providerInput=document.getElementById('setup-provider');
  if(providerInput)providerInput.value=key;
  // clear budget selection
  _wizardBudget='';
  document.querySelectorAll('.budget-tier-card').forEach(function(el){el.style.borderColor='var(--border2)'});
}

/* ── 步骤跳转逻辑 ── */
function setupNext(){
  if(_setupStep===1){
    var key=$('setup-key').value.trim();
    var provider=$('setup-provider').value;
    if(!key){showToast('请输入 API Key 或点击"跳过"体验 Demo',true);return}
    if(!provider){
      // try to get from select dropdown
      var sel=$('setup-provider-select');
      if(sel&&sel.value)provider=sel.value;
    }
    if(!provider){
      showToast('请选择 Provider（点击预算档位或手动选择）',true);return
    }
    setupData._api_key=key;
    setupData._api_provider=provider;
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
        setTimeout(function(){ showToast(t('wizardConfigDone'), false, null, 8000); }, 1500);
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

/* ── 老用户一键解锁 ── */
function unlockAllFromWizard(){
  localStorage.setItem('agency_unlock_all','true');
  $('setupOverlay').classList.remove('on');
  location.reload();
}

/* ── Demo 模式 ── */
function enterDemoMode(){
  _demoMode=true;
  $('setupOverlay').classList.remove('on');
  showToast('🎮 Demo 模式 — 无 Key 也能浏览完整界面');

  // 注入假数据到侧边栏
  if(typeof renderDemoAgentsInSidebar==='function')renderDemoAgentsInSidebar();
  if(typeof renderDemoSkillsInSidebar==='function')renderDemoSkillsInSidebar();
  if(typeof renderDemoHistoryInSidebar==='function')renderDemoHistoryInSidebar();

  // 聊天区显示 Demo 欢迎消息
  if(typeof renderDemoWelcome==='function')renderDemoWelcome();

  // Demo 模式显示仪表盘按钮（绕过门控）
  var dbBtn = document.getElementById('dashboardBtn');
  if(dbBtn) dbBtn.style.display = '';
}

export { setupData, _demoMode, showSetupStep, enterDemoMode, unlockAllFromWizard,
         setupNext, setupFinish, selectRegion, selectBudget,
         renderProviderQ1, renderProviderQ2, renderBudgetCards,
         getProvidersForRegionBudget, renderAllProvidersDropdown,
         toggleAllProviders, onProviderSelect };
