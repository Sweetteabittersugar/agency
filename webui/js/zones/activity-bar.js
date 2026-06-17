/* Agency — 活动栏 (Round 5: 48px 左侧图标列) */
(function() {
  'use strict';

  let ACTIVITIES = [
    { id: 'chat',       icon: '💬', label: '聊天', title: '聊天与 Agent 列表' },
    { id: 'sessions',   icon: '📋', label: '会话', title: '会话历史' },
    { id: 'dashboard',  icon: '📊', label: '仪表盘', title: '费用与监控仪表盘' },
    { id: 'settings',   icon: '⚙️', label: '设置', title: '开发者设置' }
  ];

  let _current = 'chat';
  let _onChange = null;

  function init(container) {
    if (!container) return;
    container.innerHTML = ACTIVITIES.map(function(a) {
      let cls = a.id === _current ? 'activity-btn active' : 'activity-btn';
      return '<button class="' + cls + '" data-activity="' + a.id + '" title="' + a.title + '">' + a.icon + '</button>';
    }).join('');

    container.querySelectorAll('.activity-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        let id = btn.getAttribute('data-activity');
        setActive(id);
      });
    });
  }

  function setActive(id) {
    _current = id;
    let container = document.getElementById('activityBar');
    if (container) {
      container.querySelectorAll('.activity-btn').forEach(function(b) {
        b.classList.toggle('active', b.getAttribute('data-activity') === id);
      });
    }
    if (_onChange) _onChange(id);
  }

  function getCurrent() { return _current; }

  function onViewChange(cb) { _onChange = cb; }

  /** 扩展点：动态注册新活动 */
  function register(activity) {
    ACTIVITIES.push(activity);
  }

  window.ActivityBar = {
    init: init,
    setActive: setActive,
    getCurrent: getCurrent,
    onViewChange: onViewChange,
    register: register,
    ACTIVITIES: ACTIVITIES
  };
})();
