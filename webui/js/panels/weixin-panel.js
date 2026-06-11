/* 从 dashboard.js 拆分 — 微信 Bot 面板 */

/* ── 微信 Bot 面板 ── */
function renderWeixinTab(container) {
  container.innerHTML = '<div id="wx-panel">加载中...</div>';
  loadWeixinStatus();
}

function loadWeixinStatus() {
  api.get('/api/weixin/status')
    .then(function(data) {
      var panel = document.getElementById('wx-panel');
      if (!panel) return;

      var html = '';

      html += '<div class="kpi-row">';
      html += '<div class="kpi-card"><div class="kpi-value" style="color:' + (data.logged_in ? '#27ae60' : '#e74c3c') + '">' + (data.logged_in ? '已连接' : '未连接') + '</div><div class="kpi-label">微信 Bot</div></div>';
      html += '<div class="kpi-card"><div class="kpi-value">' + (data.running ? '运行中' : '已停止') + '</div><div class="kpi-label">消息循环</div></div>';
      html += '<div class="kpi-card"><div class="kpi-value" style="font-size:14px;">' + (data.bot_id ? escHtml(data.bot_id.slice(0,16)+'...') : '-') + '</div><div class="kpi-label">Bot ID</div></div>';
      html += '</div>';

      html += '<div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;">';

      if (!data.logged_in) {
        html += '<button onclick="wxStartLogin()" id="wx-login-btn" style="padding:10px 24px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;">📱 扫码登录</button>';
      } else {
        html += '<button onclick="wxStartBot()" id="wx-start-btn" style="padding:10px 24px;background:' + (data.running ? '#666' : '#27ae60') + ';color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;" ' + (data.running ? 'disabled' : '') + '>' + (data.running ? '⏳ 运行中' : '▶ 启动 Bot') + '</button>';
        html += '<button onclick="wxStopBot()" style="padding:10px 24px;background:#e74c3c;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;" ' + (!data.running ? 'disabled' : '') + '>⏹ 停止</button>';
        html += '<button onclick="wxLogout()" style="padding:10px 24px;background:transparent;color:#e74c3c;border:1px solid #e74c3c;border-radius:6px;cursor:pointer;font-size:14px;">退出登录</button>';
      }

      html += '</div>';

      if (data.login_state === 'waiting_scan' || data.login_state === 'fetching') {
        html += '<div id="wx-qr-area" style="margin-top:16px;padding:16px;background:var(--bg);border:1px solid var(--border);border-radius:8px;text-align:center;">';
        html += '<p style="margin:0 0 12px;">请用微信扫描以下二维码：</p>';
        if (data.qrcode_img_content) {
          html += '<img src="' + escAttr(data.qrcode_img_content) + '" alt="微信登录二维码" style="max-width:200px;border-radius:8px;" onerror="this.onerror=null;this.outerHTML=\'<a href=\\\'' + escAttr(data.qrcode_img_content) + '\\\' target=\\\'_blank\\\' style=\\\'color:var(--accent);\\\'>点击打开二维码链接</a>\'">';
        }
        html += '<p style="font-size:12px;color:var(--muted);margin-top:8px;">扫码后自动连接，请稍候...</p>';
        html += '</div>';
        setTimeout(loadWeixinStatus, 3000);
      }

      if (data.login_state === 'connected') {
        html += '<div style="margin-top:16px;padding:12px;background:#27ae6010;border:1px solid #27ae60;border-radius:8px;color:#27ae60;">✅ ' + escHtml(data.login_message) + '</div>';
        setTimeout(loadWeixinStatus, 1000);
      }

      panel.innerHTML = html;
    })
    .catch(function() {
      var panel = document.getElementById('wx-panel');
      if (panel) panel.innerHTML = '<p style="color:var(--muted)">加载失败，请确保服务已启动</p>';
    });
}

window.wxStartLogin = function() {
  var btn = document.getElementById('wx-login-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ 获取中...'; }
  api.post('/api/weixin/login/start')
    .then(function(data) {
      if (data.ok || data.qrcode_img_content) {
        loadWeixinStatus();
      } else {
        alert('获取二维码失败: ' + (data.error || '未知'));
        if (btn) { btn.disabled = false; btn.textContent = '📱 扫码登录'; }
      }
    });
};

window.wxStartBot = function() {
  api.post('/api/weixin/start')
    .then(function() { loadWeixinStatus(); });
};

window.wxStopBot = function() {
  api.post('/api/weixin/stop')
    .then(function() { loadWeixinStatus(); });
};

window.wxLogout = function() {
  if (!confirm('确认退出微信登录？退出后需要重新扫码。')) return;
  api.post('/api/weixin/logout')
    .then(function() { loadWeixinStatus(); });
};
