/* Agency — 仪表盘5标签页 + 成本 */
var harnessActive=!1,_lastHarnessTab='overview',_ctxTimer=null,_subTimer=null;
function toggleDashboard(){
  if(!(typeof _demoMode!=='undefined'&&_demoMode) && !isFeatureUnlocked('dashboard')){
    showToast(t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS['dashboard']||1), false, 'warn');
    return;
  }
  harnessActive=!harnessActive;
  var ov=$('harnessOverlay'),btn=$('dashboardBtn');
  ov.classList.toggle('on',harnessActive);
  btn.classList.toggle('on',harnessActive);
  if(harnessActive){
    var activeTab=document.querySelector('.harness-overlay-tab[data-htab="'+_lastHarnessTab+'"]');
    if(activeTab){
      document.querySelectorAll('.harness-overlay-tab').forEach(function(x){x.classList.remove('active')});
      activeTab.classList.add('active');
    }
    renderHarnessTab(_lastHarnessTab);
  }else{
    var cur=document.querySelector('.harness-overlay-tab.active');
    if(cur)_lastHarnessTab=cur.dataset.htab;
    [_subTimer,_ctxTimer].forEach(function(t){if(t){clearInterval(t)}});_subTimer=_ctxTimer=null;
  }
}
document.querySelectorAll('.harness-overlay-tab').forEach(function(t){t.addEventListener('click',function(){document.querySelectorAll('.harness-overlay-tab').forEach(function(x){x.classList.remove('active')});t.classList.add('active');_lastHarnessTab=t.dataset.htab;renderHarnessTab(t.dataset.htab)})});
function renderHarnessTab(tab){
  var domEl=$('harnessContent');if(!domEl)return;
  // 功能门控：某些仪表盘标签页需要更高解锁等级 (Demo 模式下跳过)
  var gatedTabs = {subagents:'routing',hooks:'routing'};
  if(!(typeof _demoMode!=='undefined'&&_demoMode) && gatedTabs[tab] && !isFeatureUnlocked(gatedTabs[tab])){
    domEl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted)"><div style="font-size:24px;margin-bottom:8px">🔒</div><p>'+t('featureLocked').replace('{day}', FEATURE_UNLOCK_DAYS[gatedTabs[tab]]||3)+'</p></div>';
    return;
  }
  if(typeof _demoMode!=='undefined'&&_demoMode){renderDemoDashboard(tab,domEl);return}
  if(tab==='overview'){
    domEl.innerHTML='<div class="cost-kpis" style="margin-bottom:10px"><div class="cost-kpi"><span class="kpi-val" id="hov-cost-today">—</span><span class="kpi-label">今日费用</span></div><div class="cost-kpi"><span class="kpi-val" id="hov-cost-30d">—</span><span class="kpi-label">30天</span></div><div class="cost-kpi"><span class="kpi-val" id="hov-calls">—</span><span class="kpi-label">调用</span></div></div><div style="margin-bottom:8px"><span style="font-size:11px;color:var(--muted);font-weight:600">每日费用趋势</span><canvas id="cost-trend-canvas" width="440" height="100" style="width:100%;height:100px;display:block;background:var(--surface2);border-radius:6px;margin-top:4px"></canvas></div><div style="margin-bottom:8px"><span style="font-size:11px;color:var(--muted);font-weight:600">模型费用分布</span><div id="model-bars" style="background:var(--surface2);border-radius:6px;padding:6px 8px;font-size:10px;color:var(--muted);min-height:60px">—</div></div><div style="margin-bottom:8px;padding:8px 10px;background:var(--surface2);border-radius:6px" id="opus-panel"><span style="font-size:11px;color:var(--muted);font-weight:600">Opus 调用占比 <span data-tooltip="tooltipOpus" style="cursor:help">?</span></span><div id="opus-ratio" style="margin-top:4px;font-size:10px;color:var(--muted)">加载中…</div></div><div style="display:flex;gap:6px;margin-bottom:8px"><div class="cost-kpi" style="flex:1"><span class="kpi-val" id="hov-cache-saved" style="color:var(--warn)">$0</span><span class="kpi-label">缓存节省</span></div><div class="cost-kpi" style="flex:1"><span class="kpi-val" id="hov-cache-tokens" style="font-size:11px">0</span><span class="kpi-label">缓存Token</span></div></div><div id="cost-alerts" style="margin-bottom:6px;font-size:10px"></div><h4 style="font-size:11px;color:var(--muted);margin-bottom:6px">上下文窗口</h4><div class="ctx-gauge" style="height:14px;margin-bottom:4px"><div class="ctx-gauge-fill" id="hctx-fill" style="width:0%"></div></div><div style="font-size:11px;display:flex;justify-content:space-between"><span id="hctx-text">0 / 500K</span><span id="hctx-cache" style="color:var(--muted)">缓存: —</span></div><div id="hctx-detail" style="font-size:10px;color:var(--muted);margin-top:4px"></div>';
    loadContextDetail();loadCostOverview();
  }
  else if(tab==='cost'){
    domEl.innerHTML='<div style="padding:4px 0"><div id="cost-dash-totals" class="cost-kpis" style="margin-bottom:10px"><div class="cost-kpi"><span class="kpi-val" id="cdash-total-cost">—</span><span class="kpi-label">30天总费用</span></div><div class="cost-kpi"><span class="kpi-val" id="cdash-total-tokens">—</span><span class="kpi-label">总Token</span></div><div class="cost-kpi"><span class="kpi-val" id="cdash-total-calls">—</span><span class="kpi-label">总调用</span></div></div><div style="margin-bottom:10px"><span style="font-size:11px;color:var(--muted);font-weight:600">📈 每日费用趋势</span><div id="cost-bar-chart" style="background:var(--surface2);border-radius:6px;padding:6px 8px;min-height:80px;margin-top:4px">加载中…</div></div><div style="display:flex;gap:10px;margin-bottom:10px;flex-wrap:wrap"><div style="flex:1;min-width:200px"><span style="font-size:11px;color:var(--muted);font-weight:600">🏆 Top Agent 消费</span><div id="cost-agent-bars" style="background:var(--surface2);border-radius:6px;padding:6px 8px;min-height:60px;margin-top:4px">加载中…</div></div><div style="flex:1;min-width:200px"><span style="font-size:11px;color:var(--muted);font-weight:600">📋 近7天明细</span><div id="cost-daily-table" style="background:var(--surface2);border-radius:6px;padding:6px 8px;min-height:60px;margin-top:4px;font-size:10px">加载中…</div></div></div></div>';
    loadCostDashboard();
  }
  else if(tab==='permission'){domEl.innerHTML='<h3 style="margin-bottom:8px">权限管线</h3><div id="hperm-log" style="font-size:11px">加载中…</div><h4 style="margin-top:12px;margin-bottom:6px;font-size:11px;color:var(--muted)">审计日志</h4><div id="perm-audit-list" style="font-size:11px">加载中…</div>';loadPermHistory();loadDashboardPermissionAudit()}
  else if(tab==='subagents'){domEl.innerHTML='<h3 style="margin-bottom:8px">SubAgent 任务树</h3><div id="hsub-tree" style="font-size:11px;color:var(--muted)">加载中…</div>';loadSubagents()}
  else if(tab==='hooks'){domEl.innerHTML='<h3 style="margin-bottom:8px">Hooks 生命周期</h3><div id="hhooks-log" style="font-size:11px;color:var(--muted)">从事件日志中加载…</div>';loadHooksLog()}
  else if(tab==='mcp'){domEl.innerHTML='<h3 style="margin-bottom:8px">MCP 集成</h3><div id="hmcp-list" style="font-size:11px;color:var(--muted)">加载中…</div>';loadMCPDetail()}
  else if(tab==='env'){domEl.innerHTML='<h3 style="margin-bottom:8px">环境状态</h3><div id="henv-status" style="font-size:11px;color:var(--muted)">加载中…</div>';loadEnvStatus()}
  else if(tab==='test'){domEl.innerHTML='<h3 style="margin-bottom:8px">🧪 测试运行器</h3><div style="margin-bottom:8px"><input class="proj-input" id="test-url" type="text" placeholder="输入测试 URL，如 https://example.com" style="width:100%;margin-bottom:4px"><button class="new-chat-btn" onclick="runTest()" style="font-size:11px;padding:6px 16px;width:auto" id="test-run-btn">▶ 开始测试</button><span id="test-status" style="font-size:11px;color:var(--muted);margin-left:8px"></span></div><div id="test-results" style="font-size:11px;color:var(--muted);margin-top:8px"></div><div id="test-screenshot" style="margin-top:8px"></div>';_testPollTimer=null}
}
function loadCostOverview(){
  fetch('/api/cost?days=30').then(function(r){return r.json()}).then(function(d){
    if(!d||!d.total)return;
    var t=d.total,td=d.today;
    if($('hov-cost-today'))$('hov-cost-today').textContent='$'+(td.cost||0).toFixed(4);
    if($('hov-cost-30d'))$('hov-cost-30d').textContent='$'+(t.cost||0).toFixed(4);
    if($('hov-calls'))$('hov-calls').textContent=t.calls||0;
    var cache=d.cache||{};
    if($('hov-cache-saved'))$('hov-cache-saved').textContent='$'+(cache.saved||0).toFixed(4);
    if($('hov-cache-tokens'))$('hov-cache-tokens').textContent=((cache.read_tok||0)+(cache.write_tok||0)).toLocaleString();
    drawCostTrend(d.by_date||[]);
    drawModelBars(d.by_model||[]);
    drawOpusRatio(d.by_model||[]);
    renderCostAlerts(d.alerts||[]);
  }).catch(function(e){console.debug('loadCostOverview failed',e)});
}
function drawCostTrend(byDate){
  var c=document.getElementById('cost-trend-canvas');if(!c)return;
  var ctx=c.getContext('2d'),W=c.width,H=c.height,pad=28;
  ctx.clearRect(0,0,W,H);
  if(!byDate.length){ctx.fillStyle='#5f6877';ctx.font='10px sans-serif';var txt=t('dashboardEmpty');ctx.fillText(txt,W/2-ctx.measureText(txt).width/2,H/2);return}
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
  var domEl=document.getElementById('model-bars');if(!domEl)return;
  if(!models.length){domEl.innerHTML='<div class="empty-state"><div class="es-icon">📊</div><div class="es-text">'+t('dashboardEmpty')+'</div></div>';return}
  var totalCost=0;models.forEach(function(m){totalCost+=m.cost||0});
  domEl.innerHTML=models.map(function(m,i){
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
function drawOpusRatio(models){
  var domEl=document.getElementById('opus-ratio');if(!domEl)return;
  if(!models||!models.length){domEl.innerHTML='<div class="empty-state"><div class="es-text">'+t('dashboardEmpty')+'</div></div>';return}
  var totalCost=0,opusCost=0,opusCalls=0,totalCalls=0;
  models.forEach(function(m){
    totalCost+=m.cost||0;totalCalls+=m.calls||0;
    if(/opus/i.test(m.model||'')){opusCost+=m.cost||0;opusCalls+=m.calls||0}
  });
  if(totalCost===0){domEl.innerHTML='无费用数据';return}
  var pct=totalCost>0?(opusCost/totalCost*100):0;
  var color=pct>10?'var(--danger)':pct>5?'var(--warn)':'var(--accent)';
  var warning=pct>10?'<span style="color:var(--danger);font-weight:600"> ⚠ 超10%告警</span>':'';
  domEl.innerHTML='<div style="display:flex;align-items:center;gap:10px;margin-top:4px">'+
    '<div style="font-size:18px;font-weight:700;color:'+color+'">'+(opusCost>0?'$'+opusCost.toFixed(4):'$0')+'</div>'+
    '<div style="flex:1">'+
      '<div style="display:flex;justify-content:space-between;font-size:9px;margin-bottom:2px">'+
        '<span>占比</span><span style="color:'+color+'">'+pct.toFixed(1)+'%</span>'+
      '</div>'+
      '<div style="height:8px;background:var(--bg);border-radius:4px;overflow:hidden">'+
        '<div style="height:100%;width:'+Math.min(pct,100)+'%;background:'+color+';border-radius:4px;min-width:2px"></div>'+
      '</div>'+
      '<div style="font-size:9px;color:var(--muted);margin-top:2px">调用 '+opusCalls+' 次 / 共 '+totalCalls+' 次</div>'+
    '</div>'+
  '</div>'+warning;
}
function renderCostAlerts(alerts){
  var domEl=document.getElementById('cost-alerts');if(!domEl)return;
  if(!alerts||!alerts.length){domEl.innerHTML='';return}
  domEl.innerHTML=alerts.slice(0,5).map(function(a){
    var bg=a.level==='danger'?'rgba(248,113,113,.15)':'rgba(251,191,32,.12)';
    var border=a.level==='danger'?'#f87171':'#fbbf20';
    return'<div style="padding:4px 8px;margin:2px 0;background:'+bg+';border-left:2px solid '+border+';border-radius:3px;font-size:10px">'+
      (a.level==='danger'?'🔴 ':'⚠️ ')+escHtml(a.msg)+'</div>';
  }).join('');
}
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
  fetch('/api/permissions/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool_name:data.tool_name,decision:decision,risk:data.risk||{},reason:decision})}).catch(function(){});
}
function addAllowRule(data){
  fetch('/api/permissions/allowlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rule:data.tool_name})}).then(function(){showToast('已添加规则: '+data.tool_name)}).catch(function(){});
}
function loadPermHistory(){
  fetch('/api/permissions/history?limit=100').then(function(r){return r.json()}).then(function(d){
    var domEl=$('hperm-log');if(!domEl)return;
    if(d.history&&d.history.length){domEl.innerHTML=d.history.map(function(e){return'<div class="perm-item '+e.decision+'"><span class="pdec">'+(e.decision==='allow'?'✓':e.decision==='deny'?'✗':'⚠')+'</span> '+escHtml(e.tool||'?')+' <span style="color:var(--muted);font-size:9px">'+e.time+(e.reason?' · '+escHtml(e.reason):'')+'</span></div>'}).join('')}else{domEl.innerHTML='暂无权限记录'}
  }).catch(function(){var domEl=$('hperm-log');if(domEl)domEl.innerHTML='无法加载权限记录。服务可能未启动，请刷新页面重试'});
}
function loadContextDetail(){
  fetch('/api/harness/context').then(function(r){return r.json()}).then(function(d){
    var ttl=d.total_tokens||0,pct=ttl>0?Math.min(100,Math.round(ttl/500000*100)):0;
    var fill=$('hctx-fill'),text=$('hctx-text'),cache=$('hctx-cache'),detail=$('hctx-detail');
    if(fill){fill.style.width=pct+'%';fill.className='ctx-gauge-fill'+(pct>85?' danger':pct>60?' warn':'')}
    if(text)text.textContent=ttl.toLocaleString()+' / 500K';
    if(cache)cache.textContent='缓存命中: '+(d.cache_hit_rate||0)+'% · 省 $'+(d.cost_est?d.cost_est.cache_saved.toFixed(6):'0');
    if(detail){
      var sessions=d.sessions||[];
      var html='';
      if(sessions.length){
        sessions.forEach(function(s){
          var spct=s.tokens>0?Math.min(100,Math.round(s.tokens/(s.max||500000)*100)):0;
          html+='<div style="margin-bottom:4px">'+
            '<div style="display:flex;justify-content:space-between;font-size:9px;margin-bottom:1px"><span style="color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px">'+escHtml(s.name||s.id||'会话')+'</span><span style="color:var(--muted)">'+(s.tokens||0).toLocaleString()+'/'+Math.round((s.max||500000)/1000)+'K</span></div>'+
            '<div class="ctx-gauge" style="height:5px;margin-bottom:2px"><div class="ctx-gauge-fill'+(spct>85?' danger':spct>60?' warn':'')+'" style="width:'+spct+'%"></div></div>'+
          '</div>';
        });
      }
      html+='输入 '+(d.input_tokens||0).toLocaleString()+' · 输出 '+(d.output_tokens||0).toLocaleString()+' · 费用 $'+(d.cost_est?d.cost_est.total.toFixed(6):'0')+(d.last_update?' · '+d.last_update:'');
      detail.innerHTML=html;
    }
  }).catch(function(){var domEl=$('hctx-detail');if(domEl)domEl.innerHTML='无法加载上下文数据。服务可能未启动，请刷新页面重试'});
  if(_ctxTimer)clearInterval(_ctxTimer);
  _ctxTimer=setInterval(function(){if($('harnessOverlay').classList.contains('on'))loadContextDetail()},10000);
}
function loadSubagents(){
  fetch('/api/harness/subagents').then(function(r){return r.json()}).then(function(d){
    var domEl=$('hsub-tree');if(!domEl)return;
    if(d.tree&&d.tree.length){var html='<div style="margin-bottom:6px;color:var(--text2);font-size:11px">'+d.stats.total+' 个 · '+d.stats.done+' 完成 '+(d.stats.running||0)+' 运行中 '+(d.stats.failed||0)+' 失败</div>';
    d.tree.forEach(function(a,i){
      var icon=a.hasOutput?'✅':(a.status==='running'?'🔄':'⬤');
      var color=a.hasOutput?'var(--accent)':(a.status==='running'?'var(--warn)':'var(--muted)');
      html+='<details style="margin:2px 0;background:var(--surface2);border-radius:4px;font-size:11px"><summary style="padding:4px 8px;cursor:pointer"><span style="color:'+color+'">'+icon+'</span> '+escHtml(a.name)+' <span style="color:var(--muted);font-size:10px">'+escHtml(a.type||'')+'</span></summary><div style="padding:4px 12px 8px;font-size:10px;color:var(--text2)">'+escHtml(a.description||'无描述')+'<br>项目: '+escHtml(a.project||'')+'</div></details>';
    });
    domEl.innerHTML=html}else{domEl.innerHTML='<span style="color:var(--muted)">暂无 SubAgent 记录</span>'}
    if(_subTimer)clearInterval(_subTimer);
    _subTimer=setInterval(function(){if($('harnessOverlay').classList.contains('on'))loadSubagents()},5000);
  }).catch(function(){var domEl=$('hsub-tree');if(domEl)domEl.innerHTML='无法加载子任务列表。服务可能未启动，请刷新页面重试'});
}
function loadHooksLog(){
  var hlogs=window._hlogs||[];
  fetch('/api/harness/events?limit=50').then(function(r){return r.json()}).then(function(d){
    var events=d.events||[],domEl=$('hhooks-log');if(!domEl)return;
    if(events.length){domEl.innerHTML=events.map(function(e){return'<div style="padding:3px 6px;margin:1px 0;font-size:10px;border-left:2px solid var(--accent);background:var(--surface2)"><strong>'+escHtml(e.type)+'</strong> <span style="color:var(--muted)">'+new Date(e.ts*1000).toLocaleTimeString()+'</span></div>'}).join('')}else{domEl.innerHTML='暂无 Hook 事件'}
  }).catch(function(){var domEl=$('hhooks-log');if(domEl)domEl.innerHTML='无法加载 Hook 事件。服务可能未启动，请刷新页面重试'});
}
function loadMCPDetail(){
  fetch('/api/mcp/status').then(function(r){return r.json()}).then(function(d){
    var domEl=$('hmcp-list'),sel=$('mcp-status');if(!domEl)return;
    var servers=d.servers||[];
    var html=servers.length?servers.map(function(s){return'<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)"><div style="font-weight:600;font-size:12px">'+escHtml(s.name)+' <span style="font-size:9px;color:'+(s.running?'var(--accent)':'var(--muted)')+'">● '+(s.running?'活跃':'离线')+'</span></div><div style="font-size:10px;color:var(--muted)">'+escHtml(s.command||'')+(s.args||[]).join(' ')+'</div></div>'}).join(''):'暂无 MCP 服务器';
    domEl.innerHTML=html;if(sel)sel.innerHTML=html;
  }).catch(function(){var domEl=$('hmcp-list');if(domEl)domEl.innerHTML='无法加载 MCP 状态。服务可能未启动，请刷新页面重试'});
}
function loadDashboardPermissionAudit(){
  fetch('/api/permissions/audit?limit=50').then(function(r){return r.json()}).then(function(d){
    var domEl=document.getElementById('perm-audit-list');if(!domEl)return;
    var logs=d.logs||[],stats=d.stats||{};
    if(logs.length){domEl.innerHTML='<div style="margin-bottom:4px;font-size:10px;color:var(--text2)">总计 '+(stats.total||logs.length)+' · 允许 '+(stats.allowed||0)+' · 拒绝 '+(stats.denied||0)+'</div>'+logs.slice(0,20).map(function(l){var color=l.decision==='allow'?'var(--accent)':'var(--danger)';return'<div style="padding:2px 6px;margin:1px 0;font-size:10px;border-left:2px solid '+color+'"><span style="color:'+color+'">'+(l.decision==='allow'?'✓':'✗')+'</span> '+escHtml(l.tool_name||'?')+' <span style="color:var(--muted)">'+escHtml(l.time||'')+'</span></div>'}).join('')}else{domEl.innerHTML='暂无审计记录'}
  }).catch(function(){var domEl=document.getElementById('perm-audit-list');if(domEl)domEl.innerHTML='无法加载审计日志'});
}
function loadEnvStatus(){
  fetch("/api/harness/status").then(function(r){return r.json()}).then(function(d){
    var domEl=document.getElementById("henv-status");if(!domEl)return;
    var html="";
    var apiOk=d.api_key_valid!==undefined?d.api_key_valid:false;
    var apiProvider=d.api_provider||"未知";
    html+='<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)">';
    html+='<div style="font-weight:600;font-size:12px;margin-bottom:4px">API Key</div>';
    html+='<div style="font-size:11px"><span style="color:'+(apiOk?"var(--accent)":"var(--danger)")+'">'+(apiOk?"✅ 有效":"❌ 无效")+'</span>';
    html+=' · 提供商: <span style="color:var(--text2)">'+escHtml(apiProvider)+'</span></div>';
    html+='</div>';
    var mcpServers=d.mcp_servers||{};
    html+='<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)">';
    html+='<div style="font-weight:600;font-size:12px;margin-bottom:6px">MCP 服务</div>';
    var mcpNames=Object.keys(mcpServers);
    if(mcpNames.length){
      mcpNames.forEach(function(name){
        var ok=mcpServers[name];
        html+='<div style="display:flex;align-items:center;gap:6px;padding:2px 0;font-size:11px">';
        html+='<span style="width:8px;height:8px;border-radius:50%;display:inline-block;background:'+(ok?"var(--accent)":"var(--danger)")+'"></span>';
        html+='<span>'+escHtml(name)+'</span>';
        html+='<span style="color:'+(ok?"var(--accent)":"var(--danger)")+';font-size:10px">'+(ok?"可用":"不可用")+'</span>';
        html+='</div>';
      });
    }else{html+='<span style="color:var(--muted);font-size:10px">无 MCP 服务配置</span>'}
    html+='</div>';
    html+='<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)">';
    html+='<div style="font-weight:600;font-size:12px;margin-bottom:2px">项目目录</div>';
    html+='<div style="font-size:10px;color:var(--muted);word-break:break-all">'+escHtml(d.project_dir||"—")+'</div>';
    html+='</div>';
    html+='<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)">';
    html+='<div style="font-weight:600;font-size:12px;margin-bottom:2px">最后检查</div>';
    html+='<div style="font-size:10px;color:var(--muted)">'+escHtml(d.checked_at||"未检查")+'</div>';
    html+='</div>';
    var hooksReg=d.hooks_registered||[];
    html+='<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)">';
    html+='<div style="font-weight:600;font-size:12px;margin-bottom:6px">Hook 注册</div>';
    if(hooksReg.length){
      hooksReg.forEach(function(h){
        html+='<div style="display:flex;align-items:center;gap:6px;padding:1px 0;font-size:11px">';
        html+='<span style="color:var(--accent)">●</span>';
        html+='<span>'+escHtml(h.event)+'</span>';
        html+='<span style="color:var(--muted);font-size:10px">'+h.scripts+' 个脚本</span>';
        html+='</div>';
      });
    }else{html+='<span style="color:var(--muted);font-size:10px">未注册 Hook</span>'}
    html+='</div>';
    if(d.error)html+='<div style="padding:6px 10px;margin:4px 0;background:rgba(248,113,113,.1);border-left:2px solid var(--danger);border-radius:3px;font-size:10px;color:var(--danger)">'+escHtml(d.error)+'</div>';
    domEl.innerHTML=html;
  }).catch(function(){var domEl=document.getElementById("henv-status");if(domEl)domEl.innerHTML="无法加载环境状态。服务可能未启动，请刷新页面重试"});
}

/* ── 测试运行器 ── */
var _testPollTimer=null,_testRunId=null;
function runTest(){
  var url=($('test-url')||{}).value;if(!url){showToast('请输入测试 URL',false,'warn');return}
  var btn=$('test-run-btn');if(btn){btn.disabled=true;btn.textContent='⏳ 测试中…'}
  var statusEl=$('test-status');if(statusEl)statusEl.textContent='启动中…';
  _testRunId=null;
  var body={url:url};
  var od=localStorage.getItem('agency_output_dir');if(od)body.output_dir=od;
  apiFetch('/api/test/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(d){
    if(d.error){showToast(d.error,true);if(btn){btn.disabled=false;btn.textContent='▶ 开始测试'};return}
    _testRunId=d.run_id;if(statusEl)statusEl.textContent='运行中: '+_testRunId;
    pollTestStatus();
  }).catch(function(e){showToast('启动测试失败: '+e.message,true);if(btn){btn.disabled=false;btn.textContent='▶ 开始测试'}});
}
function pollTestStatus(){
  if(!_testRunId)return;
  if(_testPollTimer)clearTimeout(_testPollTimer);
  apiFetch('/api/test/status/'+_testRunId).then(function(r){return r.json()}).then(function(d){
    var results=$('test-results'),screenshot=$('test-screenshot'),statusEl=$('test-status'),btn=$('test-run-btn');
    if(d.error){showToast(d.error,true);if(btn){btn.disabled=false;btn.textContent='▶ 开始测试'};return}
    if(d.status==='running'){
      if(statusEl)statusEl.textContent='运行中…';
      _testPollTimer=setTimeout(pollTestStatus,2000);
      return;
    }
    if(statusEl)statusEl.textContent=d.status==='completed'?'✅ 完成':'❌ '+(d.status||'失败');
    if(btn){btn.disabled=false;btn.textContent='▶ 重新测试'}
    var tests=d.tests||[];
    var passed=tests.filter(function(t){return t.passed}).length;
    var total=tests.length||1;
    var html='<div style="display:flex;gap:12px;margin-bottom:8px">';
    html+='<div class="cost-kpi"><span class="kpi-val" style="color:'+(passed===total?'var(--accent)':'var(--warn)')+'">'+passed+'/'+total+'</span><span class="kpi-label">通过</span></div>';
    html+='<div class="cost-kpi"><span class="kpi-val" style="color:'+(passed<total?'var(--danger)':'var(--muted)')+'">'+(total-passed)+'</span><span class="kpi-label">失败</span></div>';
    html+='</div>';
    if(tests.length){
      html+='<div style="font-size:10px;max-height:150px;overflow-y:auto">';
      tests.forEach(function(t){
        html+='<div style="padding:3px 6px;margin:2px 0;border-radius:3px;background:'+(t.passed?'rgba(34,211,160,.1)':'rgba(248,113,113,.1)')+'">';
        html+='<span style="color:'+(t.passed?'var(--accent)':'var(--danger)')+'">'+(t.passed?'✅':'❌')+'</span> ';
        html+=escHtml(t.name||'测试');
        if(t.duration_ms)html+=' <span style="color:var(--muted);font-size:9px">'+t.duration_ms+'ms</span>';
        if(t.error)html+='<div style="color:var(--danger);font-size:9px;margin-left:18px">'+escHtml(t.error)+'</div>';
        html+='</div>';
      });
      html+='</div>';
    }
    if(d.summary)html+='<div style="font-size:10px;color:var(--text2);margin-top:4px;padding:4px 8px;background:var(--surface2);border-radius:4px">📋 '+escHtml(d.summary)+'</div>';
    if(results)results.innerHTML=html;
    if(d.screenshot&&screenshot){
      screenshot.innerHTML='<div style="margin-top:8px"><span style="font-size:10px;color:var(--muted)">截图预览：</span><br><img src="/api/files?path='+encodeURIComponent(d.screenshot)+'" style="max-width:100%;max-height:220px;border-radius:4px;border:1px solid var(--border);margin-top:4px" onerror="this.style.display=\'none\'"></div>';
    }
  }).catch(function(e){var statusEl=$('test-status');if(statusEl)statusEl.textContent='查询失败';var btn=$('test-run-btn');if(btn){btn.disabled=false;btn.textContent='▶ 开始测试'}});
}

/* ── Demo 仪表盘 ── */
function renderDemoDashboard(tab,domEl){
  if(tab==='overview'){
    domEl.innerHTML=
      '<div style="margin-bottom:10px;font-size:10px;color:var(--warn);text-align:center;border-bottom:1px dashed var(--warn);padding-bottom:6px;opacity:.7">⚠ '+escHtml(t('demoTooltip'))+'</div>'+
      '<div class="cost-kpis demo-block" style="margin-bottom:10px"><div class="cost-kpi"><span class="kpi-val" style="color:var(--accent)">$0.2341</span><span class="kpi-label">今日费用</span></div><div class="cost-kpi"><span class="kpi-val" style="color:var(--text2)">$3.1240</span><span class="kpi-label">30天</span></div><div class="cost-kpi"><span class="kpi-val" style="color:var(--text2)">42</span><span class="kpi-label">调用</span></div></div>'+
      '<div style="margin-bottom:8px" class="demo-block">'+
        '<span style="font-size:11px;color:var(--muted);font-weight:600">每日费用趋势</span>'+
        '<canvas id="cost-trend-canvas" width="440" height="100" style="width:100%;height:100px;display:block;background:var(--surface2);border-radius:6px;margin-top:4px"></canvas>'+
      '</div>'+
      '<div style="margin-bottom:8px" class="demo-block">'+
        '<span style="font-size:11px;color:var(--muted);font-weight:600">模型费用分布</span>'+
        '<div id="model-bars" style="background:var(--surface2);border-radius:6px;padding:6px 8px;font-size:10px;color:var(--muted);min-height:60px">'+
          buildDemoModelBars()+
        '</div>'+
      '</div>'+
      '<div style="margin-bottom:8px;padding:8px 10px;background:var(--surface2);border-radius:6px" class="demo-block">'+
        '<span style="font-size:11px;color:var(--muted);font-weight:600">Opus 调用占比 <span data-tooltip="tooltipOpus" style="cursor:help">?</span></span>'+
        '<div style="margin-top:4px;font-size:10px;color:var(--muted)"><div style="height:8px;background:var(--bg);border-radius:4px;overflow:hidden"><div style="height:100%;width:42%;background:var(--accent);border-radius:4px"></div></div><div style="font-size:9px;color:var(--text2);margin-top:2px">$0.98 / 占总费用 31%</div></div>'+
      '</div>'+
      '<div style="margin-bottom:8px;padding:8px 10px;background:var(--surface2);border-radius:6px" class="demo-block">'+
        '<span style="font-size:11px;color:var(--muted);font-weight:600">上下文窗口</span>'+
        '<div class="ctx-gauge" style="height:14px;margin:6px 0 4px"><div class="ctx-gauge-fill" style="width:32%"></div></div>'+
        '<div style="font-size:11px;display:flex;justify-content:space-between"><span>160,000 / 500K</span><span style="color:var(--muted)">缓存: 78%</span></div>'+
      '</div>'+
      '<div style="display:flex;gap:6px;margin-bottom:8px" class="demo-block"><div class="cost-kpi" style="flex:1"><span class="kpi-val" style="color:var(--warn)">$0.8560</span><span class="kpi-label">缓存节省</span></div><div class="cost-kpi" style="flex:1"><span class="kpi-val" style="font-size:11px">12,500</span><span class="kpi-label">缓存Token</span></div></div>';
    setTimeout(function(){drawDemoCostTrend()},100);
  } else {
    domEl.innerHTML=
      '<div style="margin-bottom:10px;font-size:10px;color:var(--warn);text-align:center;border-bottom:1px dashed var(--warn);padding-bottom:6px;opacity:.7">⚠ '+escHtml(t('demoTooltip'))+'</div>'+
      '<div style="text-align:center;padding:40px 16px;color:var(--muted);font-size:12px">Demo 模式 — 此面板需配置 API Key 后加载真实数据</div>';
  }
}

function buildDemoModelBars(){
  var models=[
    {model:'deepseek-v4',cost:1.52,calls:18},
    {model:'claude-sonnet',cost:0.98,calls:10},
    {model:'gpt-4o',cost:0.35,calls:6},
    {model:'gemini-flash',cost:0.18,calls:5},
    {model:'claude-haiku',cost:0.09,calls:3}
  ];
  var totalCost=models.reduce(function(s,m){return s+m.cost},0);
  var colors=['#22d3a0','#60a5fa','#fbbf20','#f87171','#a78bfa'];
  return models.map(function(m,i){
    var pct=totalCost>0?(m.cost/totalCost*100):0;
    return'<div style="display:flex;align-items:center;margin:3px 0;gap:6px">'+
      '<span style="min-width:80px;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+escHtml(m.model)+'</span>'+
      '<div style="flex:1;height:12px;background:var(--bg);border-radius:6px;overflow:hidden">'+
        '<div style="height:100%;width:'+pct+'%;background:'+colors[i%colors.length]+';border-radius:6px;min-width:2px"></div>'+
      '</div>'+
      '<span style="font-size:9px;min-width:44px;text-align:right">$'+m.cost.toFixed(4)+'</span>'+
    '</div>';
  }).join('');
}

function drawDemoCostTrend(){
  var c=document.getElementById('cost-trend-canvas');if(!c)return;
  var ctx=c.getContext('2d'),W=c.width,H=c.height,pad=28;
  ctx.clearRect(0,0,W,H);
  var data=[0.02,0.15,0.08,0.04,0.01,0.06,0.12,0.18,0.09,0.03,0.07,0.14,0.22,0.05];
  var maxCost=0.25;
  var barW=(W-pad*2)/data.length-2;
  ctx.strokeStyle='rgba(251,191,32,.3)';ctx.setLineDash([3,3]);
  var warnY=H-pad-(0.2/maxCost*(H-pad*2));
  ctx.beginPath();ctx.moveTo(pad,warnY);ctx.lineTo(W-pad,warnY);ctx.stroke();
  ctx.setLineDash([]);
  data.forEach(function(cost,i){
    var h=cost/maxCost*(H-pad*2);
    var x=pad+i*((W-pad*2)/data.length),y=H-pad-h;
    ctx.fillStyle=cost>0.2?'#f87171':'#22d3a0';
    ctx.fillRect(x,y,barW,h);
    if(i%3===0){
      ctx.fillStyle='#9ca3b4';ctx.font='8px sans-serif';
      ctx.fillText('06-'+(9+i),x-2,H-6);
    }
  });
}

/* ── 费用仪表盘 Tab ── */
function loadCostDashboard(){
  var barEl=$('cost-bar-chart'), agentEl=$('cost-agent-bars'), tableEl=$('cost-daily-table');
  fetch('/api/cost/dashboard').then(function(r){return r.json()}).then(function(d){
    if(!d){showEmpty();return}
    // KPIs
    var t=d.totals||{};
    var tcEl=$('cdash-total-cost'), ttEl=$('cdash-total-tokens'), tclEl=$('cdash-total-calls');
    if(tcEl)tcEl.textContent='$'+(t.total_cost||0).toFixed(4);
    if(ttEl)ttEl.textContent=((t.total_tokens||0)).toLocaleString();
    if(tclEl)tclEl.textContent=(t.total_calls||0).toLocaleString();

    // 每日趋势柱状图
    if(barEl)renderBarChart(barEl, d.daily||[], 'cost', 'day');

    // Top Agent 横向条形图
    if(agentEl)renderHBarChart(agentEl, (d.top_agents||[]).slice(0,5), 'cost', 'agent');

    // 近7天明细表
    if(tableEl){
      var daily=d.daily||[];
      var recent=daily.slice(-7).reverse();
      renderDailyTable(tableEl, recent);
    }
  }).catch(function(e){
    console.debug('loadCostDashboard failed', e);
    showEmpty();
  });

  function showEmpty(){
    if(barEl)barEl.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无费用数据</p>';
    if(agentEl)agentEl.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无 Agent 数据</p>';
    if(tableEl)tableEl.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无明细数据</p>';
    var tcEl=$('cdash-total-cost'),ttEl=$('cdash-total-tokens'),tclEl=$('cdash-total-calls');
    if(tcEl)tcEl.textContent='$0';
    if(ttEl)ttEl.textContent='0';
    if(tclEl)tclEl.textContent='0';
  }
}

/* 竖向柱状图 — 纯 CSS/div */
function renderBarChart(container, data, key, labelKey){
  if(!data||!data.length){
    container.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无数据</p>';
    return;
  }
  var vals=data.map(function(d){return d[key]||0});
  var max=Math.max.apply(null, vals);
  if(max===0)max=0.01;

  var colors=['#22d3a0','#60a5fa','#fbbf20','#f87171','#a78bfa','#34d399','#f472b6','#818cf8'];
  var html='<div style="display:flex;align-items:flex-end;gap:3px;height:110px;padding:4px 2px;">';
  data.forEach(function(d,i){
    var h=Math.max(3, (vals[i]/max)*106);
    var color=h>80?'#f87171':(h>50?'#fbbf20':'#22d3a0');
    html+='<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;min-width:6px" title="'+escHtml(d[labelKey]||'')+': $'+(vals[i]||0).toFixed(4)+'">';
    html+='<div style="width:100%;max-width:24px;background:'+color+';height:'+h+'px;border-radius:3px 3px 0 0;min-width:4px"></div>';
    html+='</div>';
  });
  html+='</div>';
  html+='<div style="display:flex;gap:3px;font-size:9px;color:var(--muted);padding:2px 2px 0;">';
  data.forEach(function(d,i){
    var lbl=(d[labelKey]||'').slice(5); // 去掉 "YYYY-"
    html+='<div style="flex:1;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:6px" title="'+escHtml(d[labelKey]||'')+'">'+(i%Math.ceil(data.length/14)===0||data.length<=14?escHtml(lbl):'')+'</div>';
  });
  html+='</div>';
  container.innerHTML=html;
}

/* 横向条形图 — 纯 CSS/div (Top Agent) */
function renderHBarChart(container, data, key, labelKey){
  if(!data||!data.length){
    container.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无数据</p>';
    return;
  }
  var vals=data.map(function(d){return d[key]||0});
  var max=Math.max.apply(null, vals);
  if(max===0)max=0.01;
  var colors=['#22d3a0','#60a5fa','#fbbf20','#f87171','#a78bfa'];

  var html='';
  data.forEach(function(d,i){
    var pct=(vals[i]/max*100);
    var color=colors[i%colors.length];
    html+='<div style="display:flex;align-items:center;margin:3px 0;gap:8px">'+
      '<span style="min-width:70px;font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:right" title="'+escHtml(d[labelKey]||'')+'">'+escHtml(d[labelKey]||d.agent||'—')+'</span>'+
      '<div style="flex:1;height:14px;background:var(--bg);border-radius:7px;overflow:hidden">'+
        '<div style="height:100%;width:'+pct+'%;background:'+color+';border-radius:7px;min-width:2px"></div>'+
      '</div>'+
      '<span style="font-size:9px;min-width:50px;text-align:right;color:var(--text2)">$'+(vals[i]||0).toFixed(4)+'</span>'+
    '</div>';
  });
  container.innerHTML=html;
}

/* 近7天明细表 */
function renderDailyTable(container, data){
  if(!data||!data.length){
    container.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无数据</p>';
    return;
  }
  var html='<table style="width:100%;border-collapse:collapse;font-size:10px">'+
    '<thead><tr style="border-bottom:1px solid var(--border);color:var(--muted)"><th style="text-align:left;padding:3px 4px">日期</th><th style="text-align:right;padding:3px 4px">调用</th><th style="text-align:right;padding:3px 4px">费用</th><th style="text-align:right;padding:3px 4px">Token</th></tr></thead><tbody>';
  data.forEach(function(d){
    var costClass=(d.cost||0)>5?'color:var(--danger)':(d.cost||0)>1?'color:var(--warn)':'color:var(--text2)';
    html+='<tr style="border-bottom:1px solid var(--surface2)">'+
      '<td style="padding:3px 4px">'+escHtml(d.day||d.date||'')+'</td>'+
      '<td style="text-align:right;padding:3px 4px;color:var(--text2)">'+(d.calls||0)+'</td>'+
      '<td style="text-align:right;padding:3px 4px;'+costClass+'">$'+(d.cost||0).toFixed(4)+'</td>'+
      '<td style="text-align:right;padding:3px 4px;color:var(--text2)">'+((d.tokens||0)).toLocaleString()+'</td>'+
    '</tr>';
  });
  html+='</tbody></table>';
  container.innerHTML=html;
}
