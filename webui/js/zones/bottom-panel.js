/* Agency — 底部面板 (Round 5: 终端/输出/记忆 三标签) */
(function() {
  'use strict';

  let TABS = [
    { id: 'terminal', icon: '💻', label: '终端' },
    { id: 'output',   icon: '📋', label: '输出' },
    { id: 'memory',   icon: '🧠', label: '记忆' }
  ];

  let _active = null;
  let _panelEl = null;
  let _contentEls = {};

  function init(container) {
    if (!container) return;
    _panelEl = container;

    // Tabs
    let tabHTML = TABS.map(function(t) {
      return '<button class="bp-tab" data-bpanel="' + t.id + '">' + t.icon + ' ' + t.label + '</button>';
    }).join('');
    container.innerHTML = [
      '<div class="bp-tabs">' + tabHTML + '</div>',
      '<div class="bp-content">',
      '  <div data-bpanel="terminal" class="bp-pane"><div id="global-terminal"></div></div>',
      '  <div data-bpanel="output" class="bp-pane" style="display:none"><div class="bp-placeholder">📋 暂无输出日志</div></div>',
      '  <div data-bpanel="memory" class="bp-pane" style="display:none"><div class="bp-placeholder">🧠 记忆面板</div></div>',
      '</div>'
    ].join('');

    // Cache content panes
    container.querySelectorAll('.bp-pane').forEach(function(p) {
      _contentEls[p.getAttribute('data-bpanel')] = p;
    });

    // Tab click handlers
    container.querySelectorAll('.bp-tab').forEach(function(btn) {
      btn.addEventListener('click', function() {
        let id = btn.getAttribute('data-bpanel');
        toggleTab(id);
      });
    });

    setCollapsed(true);
  }

  function toggleTab(id) {
    if (_active === id) {
      // Clicking active tab collapses
      _active = null;
      setCollapsed(true);
      return;
    }
    _active = id;
    setCollapsed(false);
    // Show active pane, hide others
    Object.keys(_contentEls).forEach(function(k) {
      _contentEls[k].style.display = k === id ? 'flex' : 'none';
    });
    // Update tab active state
    if (_panelEl) {
      _panelEl.querySelectorAll('.bp-tab').forEach(function(b) {
        b.classList.toggle('active', b.getAttribute('data-bpanel') === id);
      });
    }
  }

  function setCollapsed(collapsed) {
    if (_panelEl) _panelEl.classList.toggle('collapsed', collapsed);
  }

  function open(id) {
    toggleTab(id);
  }

  function close() {
    _active = null;
    setCollapsed(true);
  }

  /** 扩展点：动态注册新标签 */
  function register(tab) {
    TABS.push(tab);
  }

  window.BottomPanel = {
    init: init,
    open: open,
    close: close,
    register: register,
    TABS: TABS
  };
})();
