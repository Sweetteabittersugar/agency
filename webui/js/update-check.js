/* Agency — 版本更新横幅 */
function checkUpdate(){
  var banner = document.getElementById('update-banner');
  if (banner || sessionStorage.getItem('agency_update_dismissed')) return;
  fetch('/api/check-update').then(function(r){return r.json()}).then(function(d){
    if (!d.has_update) return;
    var el = document.createElement('div');
    el.id = 'update-banner';
    el.style.cssText = 'position:sticky;top:0;z-index:999;width:100%;background:linear-gradient(135deg,#f59e0b,#d97706);color:#1a1a2e;padding:8px 12px;display:flex;align-items:center;justify-content:center;gap:8px;font-size:13px;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,.3)';
    el.innerHTML =
      '<span>⚠️ 新版可用: ' + escHtml(d.current) + ' → ' + escHtml(d.latest) + '</span>' +
      '<code style="background:rgba(0,0,0,.15);padding:2px 8px;border-radius:4px;cursor:pointer;font-size:12px;user-select:all" onclick="copyText(\'' + escAttr(d.upgrade_cmd) + '\')" title="点击复制">' + escHtml(d.upgrade_cmd) + '</code>' +
      '<button onclick="dismissUpdate()" style="background:none;border:none;color:inherit;cursor:pointer;font-size:16px;padding:0 4px;margin-left:8px;opacity:.7" title="关闭">✕</button>';
    document.body.insertBefore(el, document.body.firstChild);
  }).catch(function(){});
}

function dismissUpdate(){
  var el = document.getElementById('update-banner');
  if (el) el.remove();
  sessionStorage.setItem('agency_update_dismissed', '1');
}

document.addEventListener('DOMContentLoaded', function(){
  setTimeout(checkUpdate, 500);
});

export { checkUpdate, dismissUpdate };
