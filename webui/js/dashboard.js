/* Agency — 仪表盘5标签页 + 成本 */
var harnessActive=!1,_lastHarnessTab='overview',_ctxTimer=null,_subTimer=null;
function toggleDashboard(){
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
  if(tab==='overview'){
    domEl.innerHTML='<div class="cost-kpis" style="margin-bottom:10px"><div class="cost-kpi"><span class="kpi-val" id="hov-cost-today">—</span><span class="kpi-label">今日费用</span></div><div class="cost-kpi"><span class="kpi-val" id="hov-cost-30d">—</span><span class="kpi-label">30天</span></div><div class="cost-kpi"><span class="kpi-val" id="hov-calls">—</span><span class="kpi-label">调用</span></div></div><div style="margin-bottom:8px"><span style="font-size:11px;color:var(--muted);font-weight:600">每日费用趋势</span><canvas id="cost-trend-canvas" width="440" height="100" style="width:100%;height:100px;display:block;background:var(--surface2);border-radius:6px;margin-top:4px"></canvas></div><div style="margin-bottom:8px"><span style="font-size:11px;color:var(--muted);font-weight:600">模型费用分布</span><div id="model-bars" style="background:var(--surface2);border-radius:6px;padding:6px 8px;font-size:10px;color:var(--muted);min-height:60px">—</div></div><div style="display:flex;gap:6px;margin-bottom:8px"><div class="cost-kpi" style="flex:1"><span class="kpi-val" id="hov-cache-saved" style="color:var(--warn)">$0</span><span class="kpi-label">缓存节省</span></div><div class="cost-kpi" style="flex:1"><span class="kpi-val" id="hov-cache-tokens" style="font-size:11px">0</span><span class="kpi-label">缓存Token</span></div></div><div id="cost-alerts" style="margin-bottom:6px;font-size:10px"></div><h4 style="font-size:11px;color:var(--muted);margin-bottom:6px">上下文窗口</h4><div class="ctx-gauge" style="height:14px;margin-bottom:4px"><div class="ctx-gauge-fill" id="hctx-fill" style="width:0%"></div></div><div style="font-size:11px;display:flex;justify-content:space-between"><span id="hctx-text">0 / 500K</span><span id="hctx-cache" style="color:var(--muted)">缓存: —</span></div><div id="hctx-detail" style="font-size:10px;color:var(--muted);margin-top:4px"></div>';
    loadContextDetail();loadCostOverview();
  }
  else if(tab==='permission'){domEl.innerHTML='<h3 style="margin-bottom:8px">权限管线</h3><div id="hperm-log" style="font-size:11px">加载中…</div>';loadPermHistory()}
  else if(tab==='subagents'){domEl.innerHTML='<h3 style="margin-bottom:8px">SubAgent 任务树</h3><div id="hsub-tree" style="font-size:11px;color:var(--muted)">加载中…</div>';loadSubagents()}
  else if(tab==='hooks'){domEl.innerHTML='<h3 style="margin-bottom:8px">Hooks 生命周期</h3><div id="hhooks-log" style="font-size:11px;color:var(--muted)">从事件日志中加载…</div>';loadHooksLog()}
  else if(tab==='mcp'){domEl.innerHTML='<h3 style="margin-bottom:8px">MCP 集成</h3><div id="hmcp-list" style="font-size:11px;color:var(--muted)">加载中…</div>';loadMCPDetail()}
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
  var domEl=document.getElementById('model-bars');if(!domEl)return;
  if(!models.length){domEl.innerHTML='暂无数据';return}
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
  }).catch(function(){var domEl=$('hperm-log');if(domEl)domEl.innerHTML='加载失败'});
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
  }).catch(function(){var domEl=$('hctx-detail');if(domEl)domEl.innerHTML='加载失败'});
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
  }).catch(function(){var domEl=$('hsub-tree');if(domEl)domEl.innerHTML='加载失败'});
}
function loadHooksLog(){
  var hlogs=window._hlogs||[];
  fetch('/api/harness/events?limit=50').then(function(r){return r.json()}).then(function(d){
    var events=d.events||[],domEl=$('hhooks-log');if(!domEl)return;
    if(events.length){domEl.innerHTML=events.map(function(e){return'<div style="padding:3px 6px;margin:1px 0;font-size:10px;border-left:2px solid var(--accent);background:var(--surface2)"><strong>'+escHtml(e.type)+'</strong> <span style="color:var(--muted)">'+new Date(e.ts*1000).toLocaleTimeString()+'</span></div>'}).join('')}else{domEl.innerHTML='暂无 Hook 事件'}
  }).catch(function(){var domEl=$('hhooks-log');if(domEl)domEl.innerHTML='加载失败'});
}
function loadMCPDetail(){
  fetch('/api/mcp/status').then(function(r){return r.json()}).then(function(d){
    var domEl=$('hmcp-list'),sel=$('mcp-status');if(!domEl)return;
    var servers=d.servers||[];
    var html=servers.length?servers.map(function(s){return'<div style="padding:8px 10px;margin:4px 0;background:var(--surface2);border-radius:var(--radius-sm)"><div style="font-weight:600;font-size:12px">'+escHtml(s.name)+' <span style="font-size:9px;color:'+(s.running?'var(--accent)':'var(--muted)')+'">● '+(s.running?'活跃':'离线')+'</span></div><div style="font-size:10px;color:var(--muted)">'+escHtml(s.command||'')+(s.args||[]).join(' ')+'</div></div>'}).join(''):'暂无 MCP 服务器';
    domEl.innerHTML=html;if(sel)sel.innerHTML=html;
  }).catch(function(){var domEl=$('hmcp-list');if(domEl)domEl.innerHTML='加载失败'});
}
