/* 从 dashboard.js 拆分 — 费用仪表盘面板 */

/* ── 费用仪表盘 Tab ── */
function loadCostDashboard(container) {
  // 先建 HTML 骨架，再填数据
  container.innerHTML =
    '<h3 style="margin-bottom:8px">💰 费用详情</h3>' +
    '<div class="cost-kpis" style="margin-bottom:10px">' +
      '<div class="cost-kpi"><span class="kpi-val" id="cdash-total-cost">--</span><span class="kpi-label">30天总费用</span></div>' +
      '<div class="cost-kpi"><span class="kpi-val" id="cdash-total-tokens">--</span><span class="kpi-label">Token 用量</span></div>' +
      '<div class="cost-kpi"><span class="kpi-val" id="cdash-total-calls">--</span><span class="kpi-label">API 调用</span></div>' +
      '<div class="cost-kpi"><span class="kpi-val" id="cdash-cache-hit">--</span><span class="kpi-label">缓存命中率</span></div>' +
      '<div class="cost-kpi"><span class="kpi-val" id="cdash-cache-saved">--</span><span class="kpi-label">缓存节省</span></div>' +
    '</div>' +
    '<div style="margin-bottom:8px">' +
      '<span style="font-size:11px;color:var(--muted);font-weight:600">模型费用分布</span>' +
      '<div id="cost-model-bars" style="background:var(--bg);border-radius:6px;padding:6px 8px;min-height:30px"></div>' +
    '</div>' +
    '<div style="margin-bottom:8px">' +
      '<span style="font-size:11px;color:var(--muted);font-weight:600">每日费用趋势</span>' +
      '<div id="cost-bar-chart" style="background:var(--bg);border-radius:6px;margin-top:4px;min-height:60px"></div>' +
    '</div>' +
    '<div style="margin-bottom:8px">' +
      '<span style="font-size:11px;color:var(--muted);font-weight:600">Top Agent 费用</span>' +
      '<div id="cost-agent-bars" style="background:var(--bg);border-radius:6px;padding:6px 8px;min-height:30px"></div>' +
    '</div>' +
    '<div style="margin-bottom:8px">' +
      '<span style="font-size:11px;color:var(--muted);font-weight:600">近7天明细</span>' +
      '<div id="cost-daily-table" style="font-size:10px"></div>' +
    '</div>';

  let barEl = document.getElementById('cost-bar-chart');
  let agentEl = document.getElementById('cost-agent-bars');
  let modelEl = document.getElementById('cost-model-bars');
  let tableEl = document.getElementById('cost-daily-table');

  api.get('/api/cost/dashboard').then(function(d){
    if(!d){showEmpty();return}
    let t = d.totals || {};
    let tcEl = document.getElementById('cdash-total-cost');
    let ttEl = document.getElementById('cdash-total-tokens');
    let tclEl = document.getElementById('cdash-total-calls');
    if(tcEl) tcEl.textContent='$'+(t.total_cost||0).toFixed(4);
    if(ttEl) ttEl.textContent=((t.total_tokens||0)).toLocaleString();
    if(tclEl) tclEl.textContent=(t.total_calls||0).toLocaleString();
    // 缓存命中率：cache_read / total_input_tokens
    let totalIn = ((d.daily||[]).reduce(function(s,d){return s+(d.tokens||0)},0)) || (t.total_tokens||0);
    let cacheRead = t.cache_read || 0;
    let hitRate = totalIn > 0 ? (cacheRead / totalIn * 100).toFixed(1) : '0.0';
    let chEl = document.getElementById('cdash-cache-hit');
    let csEl = document.getElementById('cdash-cache-saved');
    if(chEl) chEl.textContent = hitRate + '%';
    if(csEl) csEl.textContent = '$' + ((t.cache_saved||0)).toFixed(4);

    if(barEl) renderBarChart(barEl, d.daily||[], 'cost', 'day');
    if(agentEl) renderHBarChart(agentEl, (d.top_agents||[]).slice(0,5), 'cost', 'agent');
    if(modelEl) renderHBarChart(modelEl, (d.top_models||[]).slice(0,5), 'cost', 'model');
    if(tableEl){
      let daily = d.daily || [];
      let recent = daily.slice(-7).reverse();
      renderDailyTable(tableEl, recent);
    }
  }).catch(function(e){
    console.debug('loadCostDashboard failed', e);
    showEmpty();
  });

  function showEmpty(){
    if(barEl) barEl.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无费用数据</p>';
    if(agentEl) agentEl.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无 Agent 数据</p>';
    if(modelEl) modelEl.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无模型数据</p>';
    if(tableEl) tableEl.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无明细数据</p>';
    let tcEl = document.getElementById('cdash-total-cost');
    let ttEl = document.getElementById('cdash-total-tokens');
    let tclEl = document.getElementById('cdash-total-calls');
    let chEl = document.getElementById('cdash-cache-hit');
    let csEl = document.getElementById('cdash-cache-saved');
    if(tcEl) tcEl.textContent='$0';
    if(ttEl) ttEl.textContent='0';
    if(tclEl) tclEl.textContent='0';
    if(chEl) chEl.textContent='0%';
    if(csEl) csEl.textContent='$0';
  }
}

/* 竖向柱状图 — 纯 CSS/div */
function renderBarChart(container, data, key, labelKey){
  if(!data||!data.length){
    container.innerHTML='<p style="color:var(--muted);padding:12px;text-align:center;font-size:11px">暂无数据</p>';
    return;
  }
  let vals=data.map(function(d){return d[key]||0});
  let max=Math.max.apply(null, vals);
  if(max===0)max=0.01;

  let colors=['#22d3a0','#60a5fa','#fbbf20','#f87171','#a78bfa','#34d399','#f472b6','#818cf8'];
  let html='<div style="display:flex;align-items:flex-end;gap:3px;height:110px;padding:4px 2px;">';
  data.forEach(function(d,i){
    let h=Math.max(3, (vals[i]/max)*106);
    let color=h>80?'#f87171':(h>50?'#fbbf20':'#22d3a0');
    html+='<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;min-width:6px" title="'+escHtml(d[labelKey]||'')+': $'+(vals[i]||0).toFixed(4)+'">';
    html+='<div style="width:100%;max-width:24px;background:'+color+';height:'+h+'px;border-radius:3px 3px 0 0;min-width:4px"></div>';
    html+='</div>';
  });
  html+='</div>';
  html+='<div style="display:flex;gap:3px;font-size:9px;color:var(--muted);padding:2px 2px 0;">';
  data.forEach(function(d,i){
    let lbl=(d[labelKey]||'').slice(5); // 去掉 "YYYY-"
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
  let vals=data.map(function(d){return d[key]||0});
  let max=Math.max.apply(null, vals);
  if(max===0)max=0.01;
  let colors=['#22d3a0','#60a5fa','#fbbf20','#f87171','#a78bfa'];

  let html='';
  data.forEach(function(d,i){
    let pct=(vals[i]/max*100);
    let color=colors[i%colors.length];
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
  let html='<table style="width:100%;border-collapse:collapse;font-size:10px">'+
    '<thead><tr style="border-bottom:1px solid var(--border);color:var(--muted)"><th style="text-align:left;padding:3px 4px">日期</th><th style="text-align:right;padding:3px 4px">调用</th><th style="text-align:right;padding:3px 4px">费用</th><th style="text-align:right;padding:3px 4px">Token</th></tr></thead><tbody>';
  data.forEach(function(d){
    let costClass=(d.cost||0)>5?'color:var(--danger)':(d.cost||0)>1?'color:var(--warn)':'color:var(--text2)';
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
