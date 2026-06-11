// 首次使用引导
(function() {
  'use strict';

  function showOnboarding() {
    var overlay = document.getElementById('onboard-overlay');
    if (overlay) overlay.style.display = 'flex';
  }

  window.dismissOnboard = function() {
    var overlay = document.getElementById('onboard-overlay');
    if (overlay) overlay.style.display = 'none';
    try { localStorage.setItem('agency-onboarded', '1'); } catch(e) {}
  };

  window.startDemo = function() {
    if (typeof _demoMode !== 'undefined') _demoMode = true;
    if (typeof renderDemoAgentsInSidebar === 'function') renderDemoAgentsInSidebar();
    if (typeof renderDemoSkillsInSidebar === 'function') renderDemoSkillsInSidebar();
    if (typeof renderDemoHistoryInSidebar === 'function') renderDemoHistoryInSidebar();
    if (typeof renderDemoWelcome === 'function') renderDemoWelcome();
    showToast('🎮 Demo 模式 — 无 Key 也能浏览完整界面', false);
  };

  // 不再自动触发：改由 main.js 在所有模块加载后控制
  // document.addEventListener('DOMContentLoaded', function() { ... });

  // dismiss 按钮绑定保留（不依赖 DOMContentLoaded，因为覆盖层已经是 DOM 的一部分）
  document.addEventListener('DOMContentLoaded', function() {
    var btn = document.getElementById('onboard-dismiss');
    if (btn) btn.addEventListener('click', dismissOnboard);
  });
})();

// 输入框示例任务轮播
(function() {
  var examples = [
    '试试「帮我写一个 Python 爬虫脚本」',
    '试试「审查这段代码的安全性」',
    '试试「帮我设计一个用户登录系统」',
    '试试「优化这个 SQL 查询的性能」',
    '试试「用 TDD 方式实现一个栈」',
    '试试「帮我写 Dockerfile 部署这个项目」',
    '试试「搜索项目中所有 API 端点」'
  ];
  var idx = 0;

  function rotatePlaceholder() {
    var input = document.querySelector('textarea[placeholder*="输入"]')
             || document.querySelector('[placeholder*="输入"]')
             || document.querySelector('textarea');
    if (input && !input._hasCustomPlaceholder) {
      input._hasCustomPlaceholder = true;
      input.setAttribute('data-orig-placeholder', input.placeholder || '');
    }
    if (input) {
      input.placeholder = examples[idx];
      idx = (idx + 1) % examples.length;
    }
  }

  setInterval(rotatePlaceholder, 4000);
  setTimeout(rotatePlaceholder, 500);
})();

const dismissOnboard = window.dismissOnboard;
const startDemo = window.startDemo;