/* Agency — 四区框架 (Round 5: VS Code式 活动栏→侧边栏→主区→底栏→状态栏) */
(function() {
  'use strict';

  let _views = {};

  /**
   * 初始化四区布局
   * 在 DOMContentLoaded 后调用，将旧 DOM 迁移到新框架中
   */
  function init() {
    // 1. 包装现有 body 内容到 .app-wrapper
    let body = document.body;
    let existing = body.innerHTML;

    body.innerHTML = [
      '<div class="app-wrapper">',
      '  <div id="activityBar" class="activity-bar"></div>',
      '  <div id="sidebarView" class="sidebar-view"></div>',
      '  <div class="main-area">',
      '    <div id="mainContent"></div>',
      '  </div>',
      '</div>',
      '<div id="bottomPanel" class="bottom-panel collapsed"></div>',
      '<div id="statusBar" class="status-bar"></div>'
    ].join('');

    // 2. 旧 DOM 放入 mainContent
    let mainContent = document.getElementById('mainContent');
    if (mainContent) {
      mainContent.innerHTML = existing;
    }

    // 3. 初始化各 zone
    let ab = document.getElementById('activityBar');
    if (ab) {
      ActivityBar.init(ab);
      ActivityBar.onViewChange(function(viewId) {
        renderSidebarView(viewId);
      });
    }

    let bp = document.getElementById('bottomPanel');
    if (bp) BottomPanel.init(bp);

    let sb = document.getElementById('statusBar');
    if (sb) StatusBar.init(sb);

    // 4. 默认渲染聊天视图
    renderSidebarView('chat');

    console.log('AppShell: 四区布局初始化完成');
  }

  /** 根据活动 ID 渲染侧边栏内容 */
  function renderSidebarView(activityId) {
    let container = document.getElementById('sidebarView');
    if (!container) return;

    let html = '';
    switch (activityId) {
      case 'chat':
        html = getChatSidebarHTML();
        break;
      case 'sessions':
        html = getSessionsSidebarHTML();
        break;
      case 'dashboard':
        html = getDashboardSidebarHTML();
        break;
      case 'settings':
        html = getSettingsSidebarHTML();
        break;
      default:
        html = '<div style="padding:16px;color:var(--muted);font-size:12px;text-align:center">未知视图</div>';
    }

    container.innerHTML = html;

    // 重新绑定侧边栏交互（导航标签等）
    bindSidebarInteractions(activityId);
  }

  function getChatSidebarHTML() {
    return [
      '<div class="sidebar-section" id="ss-agents">',
      '  <div class="sidebar-section-header" onclick="toggleSidebarSection(\'ss-agents\')">🤖 Agent 列表 <span class="section-toggle">▼</span></div>',
      '  <div class="sidebar-section-body">',
      '    <input class="agent-search" id="agent-search" placeholder="搜索 Agent..." oninput="onAgentSearch(this.value)">',
      '    <div class="agent-list" id="agent-list"></div>',
      '  </div>',
      '</div>',
      '<div class="sidebar-section" id="ss-skills">',
      '  <div class="sidebar-section-header" onclick="toggleSidebarSection(\'ss-skills\')">🧩 Skills <span class="section-toggle">▼</span></div>',
      '  <div class="sidebar-section-body" id="sidebar-skills"></div>',
      '</div>',
      '<div class="sidebar-section" id="ss-history">',
      '  <div class="sidebar-section-header" onclick="toggleSidebarSection(\'ss-history\')">📋 会话历史 <span class="section-toggle">▼</span></div>',
      '  <div class="sidebar-section-body" id="history-list"></div>',
      '</div>'
    ].join('');
  }

  function getSessionsSidebarHTML() {
    return [
      '<div style="padding:12px;font-size:13px;font-weight:600;color:var(--text)">📋 会话历史</div>',
      '<div id="history-list" style="flex:1;overflow-y:auto;padding:0 8px"></div>'
    ].join('');
  }

  function getDashboardSidebarHTML() {
    return [
      '<div style="padding:12px;font-size:13px;font-weight:600;color:var(--text)">📊 概览</div>',
      '<div class="cost-kpis" style="padding:8px">',
      '  <div class="cost-kpi"><span class="kpi-val" id="ds-today">--</span><span class="kpi-label">今日费用</span></div>',
      '  <div class="cost-kpi"><span class="kpi-val" id="ds-sessions">--</span><span class="kpi-label">活跃会话</span></div>',
      '</div>',
      '<div style="padding:8px">',
      '  <button class="btn" onclick="ActivityBar.setActive(\'dashboard\');if(typeof toggleDashboard===\'function\')toggleDashboard()" style="width:100%;margin-top:8px">📊 打开完整仪表盘</button>',
      '</div>'
    ].join('');
  }

  function getSettingsSidebarHTML() {
    let sections = [
      { id: 'api', icon: '🔑', label: 'API 与 Provider' },
      { id: 'appearance', icon: '🎨', label: '外观' },
      { id: 'security', icon: '🛡️', label: '安全' },
      { id: 'data', icon: '💾', label: '数据管理' },
      { id: 'agent-factory', icon: '🤖', label: 'Agent 工厂' },
      { id: 'skills', icon: '🧩', label: 'Skills' },
      { id: 'integrations', icon: '🔌', label: '集成' },
      { id: 'shortcuts', icon: '⌨️', label: '快捷键' },
      { id: 'config', icon: '⚙️', label: '配置管理' }
    ];
    return [
      '<div style="padding:12px;font-size:13px;font-weight:600;color:var(--text)">⚙️ 设置</div>',
      '<nav id="settings-nav">' +
        sections.map(function(s) {
          return '<a class="settings-nav-item" data-section="' + s.id + '" onclick="openSettingsSection(\'' + s.id + '\')">' + s.icon + ' ' + s.label + '</a>';
        }).join('') +
      '</nav>'
    ].join('');
  }

  function bindSidebarInteractions(activityId) {
    // 重定向全局引用：让旧代码渲染到新 sidebarView 容器
    let newAgentList = document.querySelector('#sidebarView #agent-list');
    let newHistoryList = document.querySelector('#sidebarView #history-list');
    if (newAgentList && window.agentList !== newAgentList) {
      window.agentList = newAgentList;   // 覆盖 app.js 的旧引用
    }
    if (newHistoryList && window.historyList !== newHistoryList) {
      window.historyList = newHistoryList;
    }

    // 重新渲染 Agent 列表
    if (activityId === 'chat' && typeof renderAgents === 'function' && window.agents) {
      setTimeout(function() { renderAgents(window.agents); }, 100);
    }
    // 重新渲染历史
    if ((activityId === 'chat' || activityId === 'sessions') && typeof renderHistory === 'function') {
      setTimeout(function() { renderHistory(); }, 100);
    }
    // 隐藏旧 sidebar 的 Agent 搜索框（新 sidebarView 已有）
    let oldSearch = document.querySelector('#mainContent .agent-search');
    if (oldSearch) oldSearch.style.display = 'none';
  }

  function showView(id) {
    ActivityBar.setActive(id);
    renderSidebarView(id);
  }

  function toggleSidebar() {
    let sb = document.getElementById('sidebarView');
    if (sb) sb.classList.toggle('collapsed');
  }

  window.AppShell = {
    init: init,
    showView: showView,
    toggleSidebar: toggleSidebar
  };

  // 兼容：确保旧的 toggleDashboard / toggleDevOverlay 仍可工作
  // 在 main-area 中保留旧 overlay DOM，它们继续通过 CSS 控制显示

  // 启动时自动初始化（在所有脚本加载完成后）
  if (document.readyState === 'complete') {
    setTimeout(init, 50);
  } else {
    window.addEventListener('load', function() { setTimeout(init, 50); });
  }
})();
