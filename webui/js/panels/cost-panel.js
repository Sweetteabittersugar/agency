/* 从 dashboard.js 拆分 — 费用仪表盘面板 */

/* ── 费用仪表盘 Tab ── */
function loadCostDashboard(){
  var barEl=$('cost-bar-chart'), agentEl=$('cost-agent-bars'), tableEl=$('cost-daily-table');
  api.get('/api/cost/dashboard').then(function(d){
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
