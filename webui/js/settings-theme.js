/* 从 settings.js 拆分 — 主题管理 */

/* ── 主题切换 ── */
function setTheme(theme){
  localStorage.setItem('agency_theme', theme);
  document.documentElement.setAttribute('data-theme', theme==='dark'?null:theme);
  document.body.className = theme==='high-contrast'?'theme-high-contrast':'';
  var sel = document.getElementById('theme-selector');
  if(sel){
    sel.querySelectorAll('.theme-opt').forEach(function(o){
      o.classList.toggle('active', o.getAttribute('data-theme-val')===theme);
    });
  }
  showToast(t('configSaved'));
}
function initTheme(){
  var saved = localStorage.getItem('agency_theme') || '';
  // 检测系统高对比度偏好
  if(window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches){
    var hint = document.getElementById('contrast-hint');
    if(hint) hint.classList.add('show');
    if(!saved){
      saved = 'high-contrast';
    }
  }
  if(saved && saved !== 'dark'){
    document.documentElement.setAttribute('data-theme', saved);
    document.body.className = saved==='high-contrast'?'theme-high-contrast':'';
    var sel = document.getElementById('theme-selector');
    if(sel){
      sel.querySelectorAll('.theme-opt').forEach(function(o){
        o.classList.toggle('active', o.getAttribute('data-theme-val')===saved);
      });
    }
  }

  // 监听系统对比度变化
  if(window.matchMedia){
    window.matchMedia('(prefers-contrast: more)').addEventListener('change', function(e){
      var hint = document.getElementById('contrast-hint');
      if(e.matches){
        if(hint) hint.classList.add('show');
        if(!localStorage.getItem('agency_theme')) setTheme('high-contrast');
      } else {
        if(hint) hint.classList.remove('show');
      }
    });
  }
}

window.setTheme = setTheme;

export { setTheme, initTheme };
