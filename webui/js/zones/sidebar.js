/* Agency — 新版侧边栏渲染 (替换旧 sidebar.js 的渲染逻辑) */
/* 接管 renderAgents / renderHistory / loadAgents 写到新 #sidebarView 容器 */

(function() {
  'use strict';

  // ── 覆盖旧 sidebar.js 的核心函数 ──

  /** 渲染 Agent 卡片到 sidebarView 内的 agent-list */
  window.renderAgents = function(list) {
    let container = document.querySelector('#sidebarView #agent-list');
    if (!container) return;
    if (!list || !list.length) {
      container.innerHTML = '<div style="padding:16px;color:var(--muted);text-align:center;font-size:11px">' + t('agentsLoadFail') + '</div>';
      return;
    }

    function cardHTML(a) {
      let ns = a.name.replace(/'/g, "\\'"), nh = escHtml(a.name);
      return '<div class="agent-card" onclick="pickAgent(\'' + ns + '\')" oncontextmenu="pickAgentNew(\'' + ns + '\',event)">' +
        '<div class="name">' + nh + '<span class="model">' + (a.model || 'auto') + '</span></div>' +
        '<div class="desc">' + escHtml(a.description || '') + '</div>' +
        (a.keywords && a.keywords.length ? '<div class="kw">' + a.keywords.slice(0, 5).join(', ') + '</div>' : '') +
      '</div>';
    }

    let starters = list.filter(function(a) { return ['coder', 'explorer', 'general-worker', 'orchestrator'].indexOf(a.name) !== -1; });
    let others = list.filter(function(a) { return ['coder', 'explorer', 'general-worker', 'orchestrator'].indexOf(a.name) === -1; });

    let html = '';
    if (starters.length) {
      html += '<div style="font-size:11px;color:var(--warn);padding:6px 0 4px">⭐ 推荐</div>';
      html += starters.map(cardHTML).join('');
    }
    if (others.length) {
      html += '<div style="font-size:11px;color:var(--muted);padding:8px 0 4px;border-top:1px solid var(--border);margin-top:4px">📂 全部 Agent (' + others.length + ')</div>';
      html += others.map(cardHTML).join('');
    }
    container.innerHTML = html;
  };

  /** 渲染对话历史 */
  window.renderHistory = function() {
    let container = document.querySelector('#sidebarView #history-list');
    if (!container) return;
    if (!window.conversations || !window.conversations.length) {
      container.innerHTML = '<div style="padding:16px;color:var(--muted);text-align:center;font-size:11px">' + t('historyEmpty') + '</div>';
      return;
    }
    let html = '';
    window.conversations.slice(0, 20).forEach(function(c) {
      html += '<div class="history-item" onclick="loadConvo(' + c.id + ')" style="padding:8px;cursor:pointer;border-radius:6px;font-size:11px">' +
        '<div style="font-weight:500;color:var(--text)">' + escHtml(c.title || '未命名') + '</div>' +
        '<div style="font-size:9px;color:var(--muted);margin-top:2px">' + (c.time || '') + '</div>' +
      '</div>';
    });
    container.innerHTML = html || '<div style="padding:16px;color:var(--muted);text-align:center;font-size:11px">暂无对话</div>';
  };

  window.delConvo = function(id) {
    let idx = (window.conversations || []).findIndex(function(c) { return c.id === Number(id); });
    if (idx < 0) return;
    window.conversations.splice(idx, 1);
    window.renderHistory();
    showToast(t('convDeleted'));
  };

  window.loadConvo = function(id) {
    let c = (window.conversations || []).find(function(x) { return x.id === Number(id); });
    if (!c) return;
    let p = getFocusedPanel();
    if (!p) return;
    p.currentConvo = {id: c.id, title: c.title, messages: c.messages.slice(), sessionId: c.sessionId || ''};
    p.dom.messages.innerHTML = '';
    p.dom.route.innerHTML = '';
    c.messages.forEach(function(m) { addMsg(p, m.role, m.content); });
    p.dom.messages.scrollTop = p.dom.messages.scrollHeight;
    setTimeout(function() { if (p.dom.messages) p.dom.messages.querySelectorAll('.bubble').forEach(highlightCode); }, 100);
  };

  /** 加载 Agent 列表 */
  window.loadAgents = function() {
    api.get('/api/agents').then(function(d) {
      let arr = Array.isArray(d) ? d : (d.agents || d.data || []);
      window.agents = arr;
      if (typeof renderAgents === 'function') renderAgents(arr);
      // 同时填充面板内 Agent 下拉
      setTimeout(function() {
        document.querySelectorAll('.panel-agent-select').forEach(function(sel) {
          if (sel.options.length <= 1 && window.agents.length) {
            window.agents.forEach(function(a) {
              let opt = document.createElement('option');
              opt.value = a.name;
              opt.textContent = a.name;
              sel.appendChild(opt);
            });
          }
        });
      }, 200);
    }).catch(function(e) {
      console.error('加载 Agent 列表失败:', e);
      let container = document.querySelector('#sidebarView #agent-list');
      if (container) container.innerHTML = '<div style="padding:16px;color:var(--muted);text-align:center;font-size:11px">' + t('agentsLoadFail') + '</div>';
    });
  };

  /** 切换导航 — 转发到 ActivityBar */
  window.switchNav = function(nav) {
    let map = { chat: 'chat', agents: 'chat', dashboard: 'dashboard', connect: 'sessions' };
    let activity = map[nav] || nav;
    if (window.ActivityBar) ActivityBar.setActive(activity);
  };

  console.log('zones/sidebar: 已接管 renderAgents/renderHistory/loadAgents/loadConvo/delConvo/switchNav');
})();
