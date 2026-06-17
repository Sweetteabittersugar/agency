/* Agency — 设置面板内嵌视图 (Round 6: 导航树→主区内容) */
(function() {
  'use strict';

  let SECTIONS = [
    { id: 'api',          icon: '🔑', label: 'API 与 Provider', handler: 'renderApiSettings' },
    { id: 'appearance',   icon: '🎨', label: '外观',           handler: 'renderAppearanceSettings' },
    { id: 'security',     icon: '🛡️', label: '安全',           handler: 'renderSecuritySettings' },
    { id: 'data',         icon: '💾', label: '数据管理',       handler: 'renderDataSettings' },
    { id: 'agent-factory',icon: '🤖', label: 'Agent 工厂',     handler: 'renderAgentFactorySettings' },
    { id: 'skills-config',icon: '🧩', label: 'Skills',         handler: 'renderSkillsConfigSettings' },
    { id: 'integrations', icon: '🔌', label: '集成',           handler: 'renderIntegrationsSettings' },
    { id: 'shortcuts',    icon: '⌨️', label: '快捷键',         handler: 'renderShortcutsSettings' },
    { id: 'config',       icon: '⚙️', label: '配置管理',       handler: 'renderConfigManagementSettings' }
  ];

  let _activeSection = null;
  let _detailEl = null;

  function init() {
    // Settings detail rendered in main area, overlay-style but within layout
    ensureDetailContainer();
  }

  function ensureDetailContainer() {
    if (!document.getElementById('settings-detail')) {
      let mainArea = document.querySelector('.main-area');
      if (!mainArea) return;
      let detail = document.createElement('div');
      detail.id = 'settings-detail';
      detail.className = 'settings-detail-view';
      detail.style.display = 'none';
      detail.innerHTML = [
        '<div class="settings-detail-header">',
        '  <span id="settings-detail-title">设置</span>',
        '  <button class="btn" onclick="ZoneSettings.close()">✕ 关闭</button>',
        '</div>',
        '<div class="settings-detail-body" id="settings-detail-body"></div>'
      ].join('');
      mainArea.appendChild(detail);
      _detailEl = detail;
    }
  }

  /**
   * 在侧边栏或主区打开设置 section
   * @param {string} sectionId
   */
  function openSection(sectionId) {
    _activeSection = sectionId;

    // 高亮导航
    document.querySelectorAll('.settings-nav-item').forEach(function(a) {
      a.classList.toggle('active', a.getAttribute('data-section') === sectionId);
    });

    // 渲染到主区详情面板
    renderDetail(sectionId);

    // 也触发旧设置面板 (兼容)
    if (!devMode && typeof toggleDevOverlay === 'function') {
      toggleDevOverlay();
    }
  }

  function renderDetail(sectionId) {
    ensureDetailContainer();
    if (!_detailEl) return;

    let section = SECTIONS.find(function(s) { return s.id === sectionId; });
    if (!section) return;

    _detailEl.style.display = 'flex';
    let title = document.getElementById('settings-detail-title');
    if (title) title.textContent = section.icon + ' ' + section.label;

    let body = document.getElementById('settings-detail-body');
    if (!body) return;

    // 显示加载中
    body.innerHTML = '<div class="loading-text">加载中…</div>';

    // 复用旧设置渲染函数（如果存在）
    switch (sectionId) {
      case 'api':
        renderApiSettings(body);
        break;
      case 'appearance':
        renderThemeSettings(body);
        break;
      case 'security':
        renderTrustModeSettings(body);
        break;
      default:
        // 其他 section 尝试从旧 #devOverlay 提取对应内容
        fallbackRender(body, sectionId);
    }
  }

  function renderApiSettings(container) {
    // 从旧 settings.js 复用 API Key 配置区
    if (typeof renderDevSettings === 'function') {
      // 使用旧面板渲染，但放到我们的容器中
      container.innerHTML = document.getElementById('dev-section-api')?.innerHTML
        || '<div style="padding:16px;text-align:center;color:var(--muted)">请在开发者设置中配置 API Key</div>';
    } else {
      // 手动构建 API 配置 UI
      container.innerHTML = [
        '<div class="settings-section">',
        '  <h3>🔑 API Key</h3>',
        '  <div class="key-input-wrap">',
        '    <input id="settings-api-key" class="proj-input" type="password" placeholder="输入 API Key..." value="' + escHtml(typeof apiKey !== 'undefined' ? apiKey : '') + '" onchange="saveApiKeyFromSettings(this.value)">',
        '    <button class="key-toggle-btn" onclick="toggleKeyVisibility(\'settings-api-key\',this)">👁</button>',
        '  </div>',
        '</div>',
        '<div class="settings-section">',
        '  <h3>🌐 Provider</h3>',
        '  <select id="settings-provider" class="proj-input" onchange="saveProviderFromSettings(this.value)">',
        '    ' + Object.keys(PROVIDER_DB).map(function(k) { let p=PROVIDER_DB[k]; return '<option value="' + k + '"' + ((typeof apiProvider !== 'undefined' ? apiProvider : 'deepseek') === k ? ' selected' : '') + '>' + p.name + '</option>'; }).join(''),
        '  </select>',
        '</div>'
      ].join('');
    }
  }

  function renderThemeSettings(container) {
    container.innerHTML = [
      '<div class="settings-section"><h3>🎨 主题</h3>',
      '<div class="theme-selector">',
      '  <div class="theme-opt' + (getCurrentTheme()==='dark'?' active':'') + '" onclick="setTheme(\'dark\')"><span class="to-icon">🌙</span><span class="to-label">暗色</span></div>',
      '  <div class="theme-opt' + (getCurrentTheme()==='light'?' active':'') + '" onclick="setTheme(\'light\')"><span class="to-icon">☀️</span><span class="to-label">亮色</span></div>',
      '  <div class="theme-opt' + (getCurrentTheme()==='high-contrast'?' active':'') + '" onclick="setTheme(\'high-contrast\')"><span class="to-icon">⬛</span><span class="to-label">高对比</span></div>',
      '</div></div>'
    ].join('');
  }

  function renderTrustModeSettings(container) {
    let modes = ['cautious', 'normal', 'trusted'];
    let labels = {cautious:'🛡️ 谨慎', normal:'⚖️ 正常', trusted:'🤝 信任'};
    let current = localStorage.getItem('agency_trust_mode') || 'cautious';
    container.innerHTML = [
      '<div class="settings-section"><h3>🛡️ 信任模式</h3>',
      modes.map(function(m) {
        return '<button class="btn trust-mode-btn' + (m === current ? ' active' : '') + '" onclick="setTrustMode(\'' + m + '\')" style="margin:4px">' + labels[m] + '</button>';
      }).join(''),
      '</div>'
    ].join('');
  }

  function fallbackRender(container, sectionId) {
    // 尝试从旧 devOverlay 找到对应内容并复制过来
    container.innerHTML = [
      '<div style="padding:16px;text-align:center;color:var(--muted)">',
      '  <div style="font-size:24px;margin-bottom:8px">⚙️</div>',
      '  <div>此设置在开发者面板中配置</div>',
      '  <button class="btn" onclick="if(typeof toggleDevOverlay===\'function\')toggleDevOverlay()" style="margin-top:12px">打开开发者设置</button>',
      '</div>'
    ].join('');
  }

  function close() {
    if (_detailEl) _detailEl.style.display = 'none';
    _activeSection = null;
  }

  function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
  }

  // 全局 API Key 保存
  window.saveApiKeyFromSettings = function(val) {
    apiKey = val;
    localStorage.setItem('agency_api_key', val);
    syncPrefs('agency_api_key', val);
    showToast('API Key 已保存');
  };

  window.saveProviderFromSettings = function(val) {
    apiProvider = val;
    localStorage.setItem('agency_api_provider', val);
    syncPrefs('agency_api_provider', val);
    showToast('Provider 已切换: ' + val);
  };

  window.openSettingsSection = function(id) {
    ZoneSettings.openSection(id);
  };

  window.ZoneSettings = {
    init: init,
    openSection: openSection,
    close: close,
    SECTIONS: SECTIONS
  };

  // Auto-init
  setTimeout(init, 100);
})();
