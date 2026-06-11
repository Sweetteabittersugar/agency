/* Agency 前端入口 — ES Modules */
import './state.js';
import './utils.js';
import './api.js';
import './markdown.js';
import './undo.js';
import './command-palette.js';
import './wizard.js';
import './onboarding.js';
import './update-check.js';
import './settings-theme.js';
import './settings-config.js';
import './settings-security.js';
import './settings.js';
import './split-layout.js';
import './sidebar.js';
import './chat.js';
import './app.js';
import './dashboard.js';
import './panels/cost-panel.js';
import './panels/weixin-panel.js';
import './panels/memory-panel.js';
import './panels/operations-panel.js';
import './panels/worktree-panel.js';

// ── 所有模块加载完成后显示引导 ──
setTimeout(function() {
  if (localStorage.getItem('agency-onboarded')) return;
  var overlay = document.getElementById('onboard-overlay');
  if (!overlay) return;
  overlay.style.display = 'flex';

  // 检查是否配置了 API Key
  if (typeof api !== 'undefined' && api.get) {
    api.get('/api/settings').then(function(d) {
      var el = document.getElementById('onboard-key-status');
      if (!el) return;
      if (d.has_api_key) {
        el.innerHTML = '✓ 已检测到 API Key —— 可以直接开始使用';
        el.style.borderLeft = '3px solid #27ae60';
      } else {
        el.innerHTML = '⚡ 尚未配置 API Key —— 可以先体验 Demo，或<a href="#" onclick="dismissOnboard();toggleDevOverlay();return false;" style="color:var(--accent);">点此配置</a>';
        el.style.borderLeft = '3px solid #f39c12';
      }
    }).catch(function() {
      var el = document.getElementById('onboard-key-status');
      if (el) el.innerHTML = '⚡ 无法检测 API Key 状态 —— 请手动配置';
    });
  }
}, 1200);
