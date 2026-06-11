/* 从 dashboard.js 拆分 — 操作历史面板 */

/* ── 操作历史 Tab ── */
function renderOperationsTab(container) {
  container.innerHTML = '<div style="padding:4px 0"><h3 style="margin-bottom:8px">📋 操作历史</h3><p style="font-size:10px;color:var(--muted);margin-bottom:8px">Agent 执行的最近 50 条操作记录</p><div id="ops-list" style="font-size:11px;color:var(--muted)">加载中…</div></div>';
  loadOperations();
}
function loadOperations() {
  api.get('/api/operations').then(function(d) {
    var list = document.getElementById('ops-list');
    if (!list) return;
    var ops = d.operations || [];
    if (!ops.length) { list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--muted)">暂无操作记录</div>'; return; }
    var typeLabels = {chat_session:'💬 会话', file_write:'📝 写入文件', file_delete:'🗑 删除文件', command_run:'⚡ 执行命令'};
    var html = '<div style="display:flex;flex-direction:column;gap:4px;max-height:400px;overflow-y:auto">';
    ops.forEach(function(op) {
      var ts = new Date(op.ts * 1000);
      var timeStr = ts.toLocaleString();
      var typeLabel = typeLabels[op.type] || op.type;
      var detail = op.detail ? '<div style="font-size:9px;color:var(--muted);margin-top:2px">' + escHtml(op.detail) + '</div>' : '';
      html += '<div style="padding:8px 10px;background:var(--surface2);border-radius:6px;border-left:3px solid var(--accent)">';
      html += '<div style="display:flex;justify-content:space-between;align-items:center">';
      html += '<span style="font-weight:600;font-size:12px">' + typeLabel + ' <span style="color:var(--accent);font-size:11px">' + escHtml(op.agent) + '</span></span>';
      html += '<span style="font-size:9px;color:var(--muted)">' + escHtml(timeStr) + '</span>';
      html += '</div>';
      html += '<div style="font-size:11px;color:var(--text2);margin-top:3px;word-break:break-all">' + escHtml(op.target) + '</div>';
      html += detail;
      html += '</div>';
    });
    html += '</div>';
    list.innerHTML = html;
  }).catch(function() {
    var list = document.getElementById('ops-list');
    if (list) list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--muted)">加载失败</div>';
  });
}

export { renderOperationsTab, loadOperations };
