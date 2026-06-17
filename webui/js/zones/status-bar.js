/* Agency — 状态栏 (Round 5: 底部信息条 — 模型/费用/会话/连接) */
(function() {
  'use strict';

  let _timer = null;
  let POLL_INTERVAL = 30000; // 30s

  function init(container) {
    if (!container) return;
    container.innerHTML = [
      '<span class="status-item" id="sb-model">模型: --</span>',
      '<span class="status-item" id="sb-cost">$ 今日: --</span>',
      '<span class="status-item" id="sb-sessions">会话: --</span>',
      '<span class="status-item" id="sb-connection">● 已连接</span>'
    ].join('');

    updateFromDOM();
    startPolling();
  }

  /** 从现有全局状态更新显示 */
  function updateFromDOM() {
    let modelEl = document.getElementById('sb-model');
    let costEl = document.getElementById('sb-cost');
    let sessEl = document.getElementById('sb-sessions');
    let connEl = document.getElementById('sb-connection');

    if (modelEl && typeof apiProvider !== 'undefined') {
      modelEl.textContent = '模型: ' + (apiProvider || 'deepseek');
    }
    if (sessEl && typeof panels !== 'undefined') {
      sessEl.textContent = '面板: ' + (panels ? panels.length : 0);
    }
    if (connEl) {
      connEl.textContent = navigator.onLine ? '● 已连接' : '● 离线';
      connEl.style.color = navigator.onLine ? 'var(--success)' : 'var(--danger)';
    }
  }

  async function fetchCost() {
    try {
      let d = await api.get('/api/cost/summary');
      let el = document.getElementById('sb-cost');
      if (el && d && d.today_cost !== undefined) {
        el.textContent = '$ 今日: ' + parseFloat(d.today_cost).toFixed(4);
      }
    } catch(e) { /* 静默失败 */ }
  }

  function startPolling() {
    stopPolling();
    fetchCost();
    _timer = setInterval(function() {
      updateFromDOM();
      fetchCost();
    }, POLL_INTERVAL);
  }

  function stopPolling() {
    if (_timer) { clearInterval(_timer); _timer = null; }
  }

  window.addEventListener('online', updateFromDOM);
  window.addEventListener('offline', updateFromDOM);

  window.StatusBar = {
    init: init,
    update: updateFromDOM,
    startPolling: startPolling,
    stopPolling: stopPolling
  };
})();
