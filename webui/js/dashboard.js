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
    renderDashboardGrid($('harnessContent'));
  }else{
    [_subTimer,_ctxTimer].forEach(function(t){if(t){clearInterval(t)}});_subTimer=_ctxTimer=null;
  }
}

/* —— 仪表盘卡片网格 —— */
function renderDashboardGrid(container){
  if(!container)return;
  if(typeof _demoMode!=='undefined'&&_demoMode){renderDemoDashboardGrid(container);return}
  container.innerHTML=
    '<div class="dash-grid">'+
      buildDashCard('💰','费用','cost','loadCostCard')+
      buildDashCard('⚙️','操作','operations','loadOpsCard')+
      buildDashCard('🧠','上下文','context','loadContextCard')+
      buildDashCard('🌳','工作区','worktree','loadWorktreeCard')+
      buildDashCard('💬','微信','weixin','loadWeixinCard')+
      buildDashCard('🧪','测试','test','loadTestCard')+
      buildDashCard('🔌','MCP','mcp','loadMCPCard')+
      buildDashCard('🧩','记忆','memory','loadMemoryCard')+
    '</div>'+
    '<div id="dash-detail" style="display:none;margin-top:16px;padding:16px;background:var(--surface2);border-radius:12px;"></div>';
  setTimeout(function(){
    document.querySelectorAll('.dash-card[data-card]').forEach(function(card){
      var fn=window[card.getAttribute('data-load')];
      if(fn)fn(card);
    });
  },100);
}

function buildDashCard(icon,title,cardType,loadFn){
  return '<div class="dash-card" data-card="'+cardType+'" data-load="'+loadFn+'" onclick="openDashDetail(\''+cardType+'\')">'+
    '<div class="dash-card-icon">'+icon+'</div>'+
    '<div class="dash-card-title">'+title+'</div>'+
    '<div class="dash-card-body" id="dash-card-'+cardType+'"><div class="skel-row wide"></div><div class="skel-row narrow"></div></div>'+
    '</div>';
}

function loadCostCard(card){api.get('/api/cost/summary').then(function(d){var total=(d.total_cost||(d.total&&d.total.cost)||0);var calls=(d.total_calls||(d.total&&d.total.calls)||0);card.querySelector('.dash-card-body').innerHTML='<div class="dash-stat">$'+Number(total).toFixed(4)+'</div><div class="dash-sub">'+calls+' 次调用</div>';}).catch(function(){card.querySelector('.dash-card-body').textContent='—';});}
function loadOpsCard(card){api.get('/api/operations').then(function(d){var count=(d.operations||[]).length;card.querySelector('.dash-card-body').innerHTML='<div class="dash-stat">'+count+'</div><div class="dash-sub">条记录</div>';}).catch(function(){card.querySelector('.dash-card-body').textContent='—';});}
function loadContextCard(card){api.get('/api/harness/context').then(function(d){card.querySelector('.dash-card-body').innerHTML='<div class="dash-stat">'+(d.token_usage||'—')+'</div><div class="dash-sub">tokens</div>';}).catch(function(){card.querySelector('.dash-card-body').textContent='—';});}
function loadWorktreeCard(card){api.get('/api/worktrees').then(function(d){card.querySelector('.dash-card-body').innerHTML='<div class="dash-stat">'+(d.count||0)+'</div><div class="dash-sub">活跃 worktree</div>';}).catch(function(){card.querySelector('.dash-card-body').textContent='—';});}
function loadWeixinCard(card){api.get('/api/weixin/status').then(function(d){var status=d.logged_in?(d.running?'运行中':'已连接'):'未连接';var color=d.logged_in?'#27ae60':'#888';card.querySelector('.dash-card-body').innerHTML='<div class="dash-stat" style="color:'+color+'">'+status+'</div>';}).catch(function(){card.querySelector('.dash-card-body').textContent='—';});}
function loadTestCard(card){card.querySelector('.dash-card-body').innerHTML='<div class="dash-stat" style="font-size:14px;color:var(--accent);cursor:pointer;" onclick="switchNav(\'dashboard\');toggleDashboard();">▶ 开始测试</div><div class="dash-sub">验证 Agent 功能</div>';}
function loadMCPCard(card){api.get('/api/mcp/status').then(function(d){var servers=d.servers||[];card.querySelector('.dash-card-body').innerHTML='<div class="dash-stat">'+servers.length+'</div><div class="dash-sub">MCP 服务器</div>';}).catch(function(){card.querySelector('.dash-card-body').textContent='—';});}
function loadMemoryCard(card){api.get('/api/memory/timeline').then(function(d){var count=(d.entries||[]).length;card.querySelector('.dash-card-body').innerHTML='<div class="dash-stat">'+count+'</div><div class="dash-sub">条记忆</div>';}).catch(function(){card.querySelector('.dash-card-body').textContent='—';});}

function openDashDetail(cardType){
  var detail=document.getElementById('dash-detail');
  var panelFns={cost:renderCostDetail,worktree:renderWorktreeTab,weixin:renderWeixinTab,operations:renderOperationsTab,memory:renderMemoryTab,mcp:renderMCPDetail,context:renderContextDetail,test:renderTestDetail};
  var fn=panelFns[cardType];
  if(fn){detail.style.display='block';fn(detail);detail.scrollIntoView({behavior:'smooth'});}
}

function renderCostDetail(container){api.get('/api/cost?days=30').then(function(d){if(!d||!d.total){container.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center">暂无费用数据</p>';return}var t=d.total,td=d.today;container.innerHTML='<h3 style="margin-bottom:8px">💰 费用详情</h3><div class="cost-kpis" style="margin-bottom:10px"><div class="cost-kpi"><span class="kpi-val">$'+(td.cost||0).toFixed(4)+'</span><span class="kpi-label">今日</span></div><div class="cost-kpi"><span class="kpi-val">$'+(t.cost||0).toFixed(4)+'</span><span class="kpi-label">30天</span></div><div class="cost-kpi"><span class="kpi-val">'+(t.calls||0)+'</span><span class="kpi-label">调用</span></div></div><div style="margin-bottom:8px"><span style="font-size:11px;color:var(--muted);font-weight:600">每日费用趋势</span><canvas id="cost-trend-canvas" width="440" height="100" style="width:100%;height:100px;display:block;background:var(--bg);border-radius:6px;margin-top:4px"></canvas></div><div style="margin-bottom:8px"><span style="font-size:11px;color:var(--muted);font-weight:600">模型费用分布</span><div id="model-bars" style="background:var(--bg);border-radius:6px;padding:6px 8px;font-size:10px;min-height:60px">—</div></div><div id="cost-alerts" style="margin-bottom:6px;font-size:10px"></div>';loadCostOverview();}).catch(function(){container.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center">无法加载费用数据</p>';});}
function renderMCPDetail(container){api.get('/api/mcp/status').then(function(d){var servers=d.servers||[];if(!servers.length){container.innerHTML='<p style="color:var(--muted);text-align:center;padding:20px">暂无 MCP 服务器</p>';return}container.innerHTML='<h3 style="margin-bottom:8px">🔌 MCP 服务器</h3>'+servers.map(function(s){return'<div style="padding:8px 10px;margin:4px 0;background:var(--bg);border-radius:6px"><div style="font-weight:600;font-size:12px">'+escHtml(s.name)+' <span style="font-size:9px;color:'+(s.running?'var(--accent)':'var(--muted)')+'">● '+(s.running?'活跃':'离线')+'</span></div><div style="font-size:10px;color:var(--muted)">'+escHtml(s.command||'')+'</div></div>'}).join('');}).catch(function(){container.innerHTML='<p style="color:var(--muted);text-align:center;padding:20px">无法加载 MCP 状态</p>';});}
function renderContextDetail(container){api.get('/api/harness/context').then(function(d){var ttl=d.total_tokens||0,pct=ttl>0?Math.min(100,Math.round(ttl/500000*100)):0;container.innerHTML='<h3 style="margin-bottom:8px">🧠 上下文窗口</h3><div class="ctx-gauge" style="height:14px;margin-bottom:4px"><div class="ctx-gauge-fill'+(pct>85?' danger':pct>60?' warn':'')+'" style="width:'+pct+'%"></div></div><div style="font-size:13px;display:flex;justify-content:space-between;margin-bottom:12px"><span>'+ttl.toLocaleString()+' / 500K</span><span style="color:var(--muted)">缓存: '+(d.cache_hit_rate||0)+'%</span></div><div style="font-size:11px;color:var(--text2)">输入 '+(d.input_tokens||0).toLocaleString()+' · 输出 '+(d.output_tokens||0).toLocaleString()+' · 费用 $'+(d.cost_est?d.cost_est.total.toFixed(6):'0')+(d.last_update?' · '+d.last_update:'')+'</div>';}).catch(function(){container.innerHTML='<p style="color:var(--muted);text-align:center;padding:20px">无法加载上下文数据</p>';});}
function renderTestDetail(container){container.innerHTML='<h3 style="margin-bottom:8px">🧪 测试运行器</h3><div style="margin-bottom:8px"><input class="proj-input" id="test-url" type="text" placeholder="输入测试 URL，如 https://example.com" style="width:100%;margin-bottom:4px"><button class="new-chat-btn" onclick="runTest()" style="font-size:11px;padding:6px 16px;width:auto" id="test-run-btn">▶ 开始测试</button><span id="test-status" style="font-size:11px;color:var(--muted);margin-left:8px"></span></div><div id="test-results" style="font-size:11px;color:var(--muted);margin-top:8px"></div><div id="test-screenshot" style="margin-top:8px"></div>';_testPollTimer=null;}

/* —— Demo 仪表盘卡片网格 —— */
function renderDemoDashboardGrid(container){
  container.innerHTML=
    '<div style="margin-bottom:10px;font-size:10px;color:var(--warn);text-align:center;border-bottom:1px dashed var(--warn);padding-bottom:6px;opacity:.7">⚠ '+escHtml(t('demoTooltip'))+'</div>'+
    '<div class="dash-grid">'+
      buildDemoCard('💰','费用','$0.2341','今日 · 42 次调用')+
      buildDemoCard('⚙️','操作','5','条记录')+
      buildDemoCard('🧠','上下文','32%','160K / 500K tokens')+
      buildDemoCard('🌳','工作区','3','活跃 worktree')+
      buildDemoCard('💬','微信','已连接','运行中')+
      buildDemoCard('🧪','测试','—','未运行')+
      buildDemoCard('🔌','MCP','4','MCP 服务器')+
      buildDemoCard('🧩','记忆','12','条记忆')+
    '</div>';
}
function buildDemoCard(icon,title,stat,sub){
  return '<div class="dash-card" style="cursor:default;opacity:.7">'+
    '<div class="dash-card-icon">'+icon+'</div>'+
    '<div class="dash-card-title">'+title+'</div>'+
    '<div class="dash-stat">'+stat+'</div>'+
    '<div class="dash-sub">'+sub+'</div>'+
    '</div>';
}
function loadCostOverview(){
  api.get('/api/cost?days=30').then(function(d){
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
  api.post('/api/permissions/decision',{tool_name:data.tool_name,decision:decision,risk:data.risk||{},reason:decision}).catch(function(){});
}
function addAllowRule(data){
  api.post('/api/permissions/allowlist',{rule:data.tool_name}).then(function(){showToast('已添加规则: '+data.tool_name)}).catch(function(){});
}
function loadPermHistory(){
  api.get('/api/permissions/history?limit=100').then(function(d){
    var domEl=$('hperm-log');if(!domEl)return;
    if(d.history&&d.history.length){domEl.innerHTML=d.history.map(function(e){return'<div class="perm-item '+e.decision+'"><span class="pdec">'+(e.decision==='allow'?'✓':e.decision==='deny'?'✗':'⚠')+'</span> '+escHtml(e.tool||'?')+' <span style="color:var(--muted);font-size:9px">'+e.time+(e.reason?' · '+escHtml(e.reason):'')+'</span></div>'}).join('')}else{domEl.innerHTML='暂无权限记录'}
  }).catch(function(){var domEl=$('hperm-log');if(domEl)domEl.innerHTML='无法加载权限记录。服务可能未启动，请刷新页面重试'});
}
function loadContextDetail(){
  api.get('/api/harness/context').then(function(d){
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
  api.get('/api/harness/subagents').then(function(d){
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
  api.get('/api/harness/events?limit=50').then(function(d){
    var events=d.events||[],domEl=$('hhooks-log');if(!domEl)return;
    if(events.length){domEl.innerHTML=events.map(function(e){return'<div style="padding:3px 6px;margin:1px 0;font-size:10px;border-left:2px solid var(--accent);background:var(--surface2)"><strong>'+escHtml(e.type)+'</strong> <span style="color:var(--muted)">'+new Date(e.ts*1000).toLocaleTimeString()+'</span></div>'}).join('')}else{domEl.innerHTML='暂无 Hook 事件'}
  }).catch(function(){var domEl=$('hhooks-log');if(domEl)domEl.innerHTML='无法加载 Hook 事件。服务可能未启动，请刷新页面重试'});
}
function loadMCPDetail(){
  api.get('/api/mcp/status').then(function(d){
    var domEl=$('hmcp-list'),sel=$('mcp-status');if(!domEl)return;
    var servers=d.servers||[];
    var html=servers.length?servers.map(function(s){return'<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)"><div style="font-weight:600;font-size:12px">'+escHtml(s.name)+' <span style="font-size:9px;color:'+(s.running?'var(--accent)':'var(--muted)')+'">● '+(s.running?'活跃':'离线')+'</span></div><div style="font-size:10px;color:var(--muted)">'+escHtml(s.command||'')+(s.args||[]).join(' ')+'</div></div>'}).join(''):'暂无 MCP 服务器';
    domEl.innerHTML=html;if(sel)sel.innerHTML=html;
  }).catch(function(){var domEl=$('hmcp-list');if(domEl)domEl.innerHTML='无法加载 MCP 状态。服务可能未启动，请刷新页面重试'});
}
function loadDashboardPermissionAudit(){
  api.get('/api/permissions/audit?limit=50').then(function(d){
    var domEl=document.getElementById('perm-audit-list');if(!domEl)return;
    var logs=d.logs||[],stats=d.stats||{};
    if(logs.length){domEl.innerHTML='<div style="margin-bottom:4px;font-size:10px;color:var(--text2)">总计 '+(stats.total||logs.length)+' · 允许 '+(stats.allowed||0)+' · 拒绝 '+(stats.denied||0)+'</div>'+logs.slice(0,20).map(function(l){var color=l.decision==='allow'?'var(--accent)':'var(--danger)';return'<div style="padding:2px 6px;margin:1px 0;font-size:10px;border-left:2px solid '+color+'"><span style="color:'+color+'">'+(l.decision==='allow'?'✓':'✗')+'</span> '+escHtml(l.tool_name||'?')+' <span style="color:var(--muted)">'+escHtml(l.time||'')+'</span></div>'}).join('')}else{domEl.innerHTML='暂无审计记录'}
  }).catch(function(){var domEl=document.getElementById('perm-audit-list');if(domEl)domEl.innerHTML='无法加载审计日志'});
}
function loadEnvStatus(){
  api.get("/api/harness/status").then(function(d){
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

// ES module bridge
window.toggleDashboard = toggleDashboard;
window.renderDashboardGrid = renderDashboardGrid;
window.loadCostOverview = loadCostOverview;
window.openDashDetail = openDashDetail;
