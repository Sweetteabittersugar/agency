/* Activity Bar — 四区布局导航中枢 v2.0
   管理活动图标切换 + 侧边栏内容联动 + 扩展注册 */

window.ACTIVITIES = [
  { id: 'chat',      icon: '💬', label: 'Chat',      tooltip: 'Chat — 聊天' },
  { id: 'sessions',  icon: '📋', label: 'Sessions',  tooltip: 'Sessions — 会话历史' },
  { id: 'dashboard', icon: '📊', label: 'Dashboard', tooltip: 'Dashboard — 仪表盘与监控' },
  { id: 'settings',  icon: '⚙️',  label: 'Settings',  tooltip: 'Settings — 配置与偏好' },
];

let _activeActivity = 'chat';

function getActiveActivity() { return _activeActivity; }

function switchActivity(activityId) {
  // Validate
  const act = ACTIVITIES.find(function(a) { return a.id === activityId; });
  if (!act) return;
  _activeActivity = activityId;

  // Persist preference
  try { localStorage.setItem('agency-activity', activityId); } catch(e) {}

  // Update activity bar icons
  let bar = document.getElementById('activityBar');
  if (bar) {
    bar.querySelectorAll('.activity-bar-icon').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.activity === activityId);
    });
  }

  // Switch sidebar view content
  if (typeof renderSidebarView === 'function') {
    renderSidebarView(activityId);
  }
}

function initActivityBar() {
  let topContainer = document.getElementById('activityBarTop');
  if (!topContainer) return;

  // Populate activity icons from ACTIVITIES array
  topContainer.innerHTML = '';
  ACTIVITIES.forEach(function(act) {
    let btn = document.createElement('button');
    btn.className = 'activity-bar-icon';
    btn.dataset.activity = act.id;
    btn.title = act.tooltip;
    btn.setAttribute('aria-label', act.label);
    btn.textContent = act.icon;
    topContainer.appendChild(btn);
  });

  // Event delegation — click on any icon
  topContainer.addEventListener('click', function(e) {
    let btn = e.target.closest('.activity-bar-icon');
    if (!btn) return;
    let activityId = btn.dataset.activity;
    if (activityId) switchActivity(activityId);
  });

  // Restore last active activity
  let saved = null;
  try { saved = localStorage.getItem('agency-activity'); } catch(e) {}
  if (saved && ACTIVITIES.some(function(a) { return a.id === saved; })) {
    switchActivity(saved);
  } else {
    switchActivity('chat');
  }
}

// ── Extension point ──
window.registerActivity = function(activity) {
  if (!activity.id || !activity.icon) return;
  if (ACTIVITIES.some(function(a) { return a.id === activity.id; })) return;
  ACTIVITIES.push(activity);
  initActivityBar(); // rebuild icons
};

// Expose for external use
window.switchActivity = switchActivity;
window.getActiveActivity = getActiveActivity;
