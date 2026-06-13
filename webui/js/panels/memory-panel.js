/* 从 dashboard.js 拆分 — 记忆面板 */

/* ── 记忆面板 ── */
function renderMemoryTab(container) {
  container.innerHTML = '<div id="memory-panel" style="padding:12px;">' +
    '<div style="display:flex;gap:8px;margin-bottom:12px;">' +
    '<input id="mem-search-input" placeholder="搜索记忆..." style="flex:1;padding:8px 12px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:13px;" onkeyup="if(event.key===\'Enter\') searchMemory()">' +
    '<button onclick="searchMemory()" style="padding:8px 16px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;">搜索</button>' +
    '</div>' +
    '<div style="display:flex;gap:8px;margin-bottom:12px;">' +
    '<button onclick="loadMemoryTimeline()" style="padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;cursor:pointer;font-size:12px;">时间线</button>' +
    '<button onclick="loadMemoryFiles()" style="padding:6px 14px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;cursor:pointer;font-size:12px;">记忆文件</button>' +
    '</div>' +
    '<div id="mem-content" style="max-height:500px;overflow-y:auto;"><p style="color:var(--muted);">选择上方按钮查看记忆</p></div>' +
    '</div>';
}

function searchMemory() {
  var q = document.getElementById('mem-search-input').value.trim();
  if (!q) return;
  var content = document.getElementById('mem-content');
  content.innerHTML = '<p style="color:var(--muted);">搜索中...</p>';

  api.get('/api/memory/search?q=' + encodeURIComponent(q))
    .then(function(data) {
      if (!data.ok) { content.innerHTML = '<p style="color:#e74c3c;">搜索失败</p>'; return; }
      var results = data.results || [];
      if (results.length === 0) {
        content.innerHTML = '<p style="color:var(--muted);">未找到匹配结果</p>';
        return;
      }
      var totalMatches = results.reduce(function(s,r){return s+r.total_matches;},0);
      var html = '<div style="font-size:12px;color:var(--muted);margin-bottom:8px;">找到 ' + data.total_files + ' 个文件，共 ' + totalMatches + ' 处匹配</div>';
      results.forEach(function(r) {
        html += '<div style="margin-bottom:12px;padding:10px;background:var(--bg);border-radius:8px;">';
        html += '<div style="font-weight:600;margin-bottom:6px;">' + escHtml(r.name) + ' <span style="color:var(--muted);font-weight:400;">(' + r.total_matches + '处)</span></div>';
        (r.matches||[]).forEach(function(m) {
          html += '<div style="font-size:12px;padding:3px 8px;margin:2px 0;background:rgba(255,255,0,0.05);border-radius:3px;">' +
            '<span style="color:var(--muted);">L' + m.line + ':</span> ' + escHtml(m.text) + '</div>';
        });
        html += '</div>';
      });
      content.innerHTML = html;
    })
    .catch(function() {
      content.innerHTML = '<p style="color:#e74c3c;">搜索失败，请检查服务</p>';
    });
}

function loadMemoryTimeline() {
  var content = document.getElementById('mem-content');
  content.innerHTML = '<p style="color:var(--muted);">加载时间线...</p>';

  api.get('/api/memory/timeline')
    .then(function(data) {
      var entries = data.entries || [];
      if (entries.length === 0) {
        content.innerHTML = '<p style="color:var(--muted);">暂无记忆记录</p>';
        return;
      }
      var html = '<div style="font-size:12px;color:var(--muted);margin-bottom:8px;">最近 ' + entries.length + ' 条记录</div>';
      var typeEmoji = {user_message:'💬', agent_response:'🤖', route_decision:'🎯', task_complete:'✅', feedback:'📝', routing_correction:'🔄', operation:'⚙️'};
      entries.forEach(function(e) {
        var emoji = typeEmoji[e.type] || '📌';
        var time = new Date(e.ts * 1000).toLocaleString('zh-CN');
        html += '<div style="padding:8px 10px;margin-bottom:4px;background:var(--bg);border-radius:6px;display:flex;gap:8px;align-items:flex-start;">' +
          '<span style="font-size:16px;">' + emoji + '</span>' +
          '<div style="flex:1;">' +
          '<div style="font-size:12px;color:var(--muted);">' + time + ' · ' + e.type + (e.session ? ' · ' + e.session.slice(0,12) : '') + '</div>' +
          '<div style="font-size:13px;margin-top:2px;">' + escHtml(e.summary) + '</div>' +
          '</div></div>';
      });
      content.innerHTML = html;
    })
    .catch(function() {
      content.innerHTML = '<p style="color:#e74c3c;">加载失败</p>';
    });
}

function loadMemoryFiles() {
  var content = document.getElementById('mem-content');
  content.innerHTML = '<p style="color:var(--muted);">加载中...</p>';

  api.get('/api/memory')
    .then(function(data) {
      var files = data.files || [];
      if (files.length === 0) {
        content.innerHTML = '<p style="color:var(--muted);">暂无记忆文件</p>';
        return;
      }
      var html = '';
      files.forEach(function(f) {
        html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 10px;margin-bottom:4px;background:var(--bg);border-radius:6px;cursor:pointer;" onclick="openMemoryFile(\'' + escAttr(f.path) + '\',\'' + escAttr(f.name) + '\')">' +
          '<div style="display:flex;align-items:center;gap:8px;">' +
          '<span>📄</span>' +
          '<div><div style="font-size:13px;">' + escHtml(f.name) + '</div><div style="font-size:10px;color:var(--muted);">' + (f.size||0) + 'B</div></div>' +
          '</div>' +
          '<span style="color:var(--accent);font-size:12px;">查看 →</span>' +
          '</div>';
      });
      content.innerHTML = html;
    })
    .catch(function() {
      content.innerHTML = '<p style="color:#e74c3c;">加载失败</p>';
    });
}

window.openMemoryFile = function(path, name, targetId) {/*targetId: sidebar=>"sidebar-mem-content", dashboard=>"mem-content"(default)*/
  targetId = targetId || 'mem-content';
  var backFn = targetId === 'sidebar-mem-content' ? 'sidebarLoadMemoryFiles' : 'loadMemoryFiles';
  api.get('/api/memory/' + encodeURIComponent(path))
    .then(function(data) {
      var content = document.getElementById(targetId);
      if (!content) { console.error('openMemoryFile: #'+targetId+' not found'); return; }
      if (data.error) { content.innerHTML = '<span style="color:var(--danger)">'+escHtml(data.error)+'</span>'; return; }
      content.innerHTML =
        '<div style="margin-bottom:8px;"><button onclick="'+backFn+'()" style="padding:4px 10px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;cursor:pointer;font-size:11px;">← 返回</button></div>' +
        '<div style="font-size:12px;color:var(--muted);margin-bottom:8px;">📄 ' + escHtml(name || path) + '</div>' +
        '<pre style="padding:12px;background:var(--bg);border-radius:8px;font-size:12px;color:var(--text);white-space:pre-wrap;max-height:400px;overflow-y:auto;">' + escHtml(data.content || '') + '</pre>';
    }).catch(function(e) {
      var content = document.getElementById(targetId);
      if (content) content.innerHTML = '<span style="color:var(--danger)">加载失败: '+escHtml(e.message||'未知错误')+'</span>';
    });
};

window.openMemoryFile = openMemoryFile;

/* ── 侧边栏记忆入口 ── */
function sidebarSearchMemory(){
  var q = (document.getElementById('sidebar-mem-search') || {}).value || '';
  if (!q.trim()) { sidebarLoadMemoryTimeline(); return; }
  var content = document.getElementById('sidebar-mem-content');
  if (!content) return;
  content.innerHTML = '<span style="color:var(--muted)">搜索中…</span>';
  api.get('/api/memory/search?q=' + encodeURIComponent(q.trim())).then(function(d) {
    var results = d.results || [];
    if (!results.length) { content.innerHTML = '<span style="color:var(--muted)">无匹配结果</span>'; return; }
    var html = '';
    results.forEach(function(r) {
      html += '<div style="padding:4px 0;border-bottom:1px solid var(--border);cursor:pointer;font-size:11px" onclick="openMemoryFile(\'' + escAttr(r.name||r.path||r.file||'') + '\',\'' + escAttr(r.name||r.path||'') + '\')">📄 ' + escHtml(r.name||r.path||'?') + '<br><span style="color:var(--muted);font-size:10px">' + escHtml((r.snippet||r.preview||'').slice(0,60)) + '</span></div>';
    });
    content.innerHTML = html;
  }).catch(function(e) { content.innerHTML = '<span style="color:var(--danger)">搜索失败</span>'; });
}
function sidebarLoadMemoryTimeline(){
  var content = document.getElementById('sidebar-mem-content');
  if (!content) return;
  content.innerHTML = '<span style="color:var(--muted)">加载中…</span>';
  api.get('/api/memory/timeline').then(function(d) {
    var entries = d.entries || d.timeline || [];
    if (!entries.length) { content.innerHTML = '<span style="color:var(--muted)">暂无记忆记录</span>'; return; }
    var html = '';
    entries.slice(0, 20).forEach(function(e) {
      var time = (e.time||e.timestamp||'').slice(0,16) || '?';
      html += '<div style="padding:3px 0;border-bottom:1px solid var(--border);font-size:10px"><span style="color:var(--muted)">' + escHtml(time) + '</span> ' + escHtml(e.msg||e.event||e.summary||'?') + '</div>';
    });
    content.innerHTML = html;
  }).catch(function(e) { content.innerHTML = '<span style="color:var(--danger)">加载失败</span>'; });
}
function sidebarLoadMemoryFiles(){
  var content = document.getElementById('sidebar-mem-content');
  if (!content) return;
  content.innerHTML = '<span style="color:var(--muted)">加载中…</span>';
  api.get('/api/memory').then(function(d) {
    var files = d.files || d.memories || [];
    if (!files.length) { content.innerHTML = '<span style="color:var(--muted)">暂无记忆文件</span>'; return; }
    var html = '';
    files.forEach(function(f) {
      var name = f.name || f.path || f;
      if (typeof f === 'string') name = f;
      html += '<div style="padding:3px 0;border-bottom:1px solid var(--border);cursor:pointer;font-size:11px" onclick="openMemoryFile(\'' + escAttr(f.name||f.path||f) + '\',\'' + escAttr(name) + '\',\'sidebar-mem-content\')">📄 ' + escHtml(name) + '</div>';
    });
    content.innerHTML = html;
  }).catch(function(e) { content.innerHTML = '<span style="color:var(--danger)">加载失败</span>'; });
}
window.sidebarSearchMemory = sidebarSearchMemory;
window.sidebarLoadMemoryTimeline = sidebarLoadMemoryTimeline;
window.sidebarLoadMemoryFiles = sidebarLoadMemoryFiles;