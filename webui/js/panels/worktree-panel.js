/* 从 dashboard.js 拆分 — Worktree 管理面板 */

/* ── Worktree 管理 ── */
function renderWorktreeTab(container) {
  container.innerHTML = '<div id="wt-panel"><div class="kpi-row"><div class="kpi-card"><div class="kpi-value" id="wt-count">-</div><div class="kpi-label">活跃 Worktree</div></div></div><div id="wt-list">加载中...</div><div style="margin-top:16px;"><h4>创建新 Worktree</h4><input id="wt-new-name" placeholder="worktree名称 (如 agent-coder)" style="padding:8px;width:200px;margin-right:8px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;"><button onclick="createWorktree()" style="padding:8px 16px;background:var(--accent);color:#fff;border:none;border-radius:4px;cursor:pointer;">创建</button></div></div>';
  loadWorktrees();
}

function loadWorktrees() {
  api.get('/api/worktrees')
    .then(function(data) {
      document.getElementById('wt-count').textContent = data.count || 0;
      var list = document.getElementById('wt-list');
      var agents = data.agents || [];
      if (agents.length === 0) {
        list.innerHTML = '<p style="color:var(--muted)">暂无活跃 Worktree</p>';
        return;
      }
      var html = '<div style="display:flex;flex-direction:column;gap:8px;">';
      agents.forEach(function(wt) {
        html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;">';
        html += '<div><strong>' + escHtml(wt.name) + '</strong><br><span style="font-size:12px;color:var(--muted);">' + escHtml(wt.branch || '') + ' · ' + (wt.size_mb || 0) + ' MB</span></div>';
        html += '<button onclick="removeWorktree(\'' + escAttr(wt.name) + '\')" style="padding:4px 12px;background:#e74c3c;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">删除</button>';
        html += '</div>';
      });
      html += '</div>';
      list.innerHTML = html;
    })
    .catch(function() {
      document.getElementById('wt-list').innerHTML = '<p style="color:var(--muted);">加载失败</p>';
    });
}

function createWorktree() {
  var name = document.getElementById('wt-new-name').value.trim();
  if (!name) return;
  api.post('/api/worktrees/create', {name: name})
    .then(function(data) {
      if (data.ok) {
        document.getElementById('wt-new-name').value = '';
        loadWorktrees();
      } else {
        showToast('创建失败: ' + (data.error || '未知错误'), true);
      }
    })
    .catch(function() { showToast('网络错误', true); });
}

function removeWorktree(name) {
  if (!confirm('确认删除 Worktree: ' + name + '?')) return;
  api.post('/api/worktrees/remove', {name: name, force: true})
    .then(function(data) {
      if (data.ok) loadWorktrees();
      else showToast('删除失败: ' + (data.error || '未知错误'), true);
    })
    .catch(function() { showToast('网络错误', true); });
}

window.createWorktree = createWorktree;
window.removeWorktree = removeWorktree;
export { renderWorktreeTab, loadWorktrees, createWorktree, removeWorktree };
