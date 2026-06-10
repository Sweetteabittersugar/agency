/* 从 settings.js 拆分 — 信任模式与权限 */

/* ── 全局信任模式 ── */
var TRUST_MODES = {
  cautious: { label: '谨慎模式', desc: '所有需确认操作都询问', icon: '🛡️' },
  normal:   { label: '正常模式', desc: '同类操作只问一次（24h 内记住）', icon: '⚖️' },
  trusted:  { label: '信任模式', desc: '仅拦截高危操作（rm -rf /等）', icon: '🚀' }
};
var trustMode = localStorage.getItem('agency_trust_mode') || 'cautious';

function getTrustMode(){ return trustMode; }

function setTrustMode(mode){
  if(!TRUST_MODES[mode]) return;
  trustMode = mode;
  localStorage.setItem('agency_trust_mode', mode);
  updateTrustModeUI();
  showToast('信任模式已切换: ' + TRUST_MODES[mode].label);
  fetch('/api/permissions/decision', {
    method:'POST',
    headers:{'Content-Type':'application/json','X-Agency-Trust-Mode':mode},
    body:JSON.stringify({decision:'config',tool_name:'trust_mode',risk:mode,reason:'用户切换信任模式'})
  }).catch(function(){});
}

function updateTrustModeUI(){
  var sel = document.getElementById('trust-mode-select');
  if(sel) sel.value = trustMode;
  var desc = document.getElementById('trust-mode-desc');
  if(desc && TRUST_MODES[trustMode]) desc.textContent = TRUST_MODES[trustMode].desc;
  var btns = document.querySelectorAll('.trust-mode-btn');
  btns.forEach(function(b){
    var mode = b.getAttribute('data-mode');
    b.classList.toggle('active', mode === trustMode);
  });
}

/* ── 权限确认弹窗 ── */
function showPermissionConfirm(toolName, risk, reason, args){
  if(trustMode === 'trusted'){
    confirmPermission(toolName, 'allow', args);
    return;
  }
  if(trustMode === 'normal'){
    fetch('/api/permissions/history?limit=10').then(function(r){return r.json()}).then(function(d){
      var hist = d.history || [];
      var found = hist.find(function(h){ return h.tool === toolName && h.decision === 'allow'; });
      if(found){
        confirmPermission(toolName, 'allow', args);
        return;
      }
      _showConfirmDialog(toolName, risk, reason, args);
    }).catch(function(){ _showConfirmDialog(toolName, risk, reason, args); });
    return;
  }
  _showConfirmDialog(toolName, risk, reason, args);
}

function _showConfirmDialog(toolName, risk, reason, args){
  var riskColor = risk === 'high' ? 'var(--danger)' : risk === 'medium' ? '#f0a020' : 'var(--accent)';
  var overlay = document.createElement('div');
  overlay.className = 'agent-prompt-overlay';
  overlay.style.display = 'flex';
  overlay.innerHTML =
    '<div class="agent-prompt-modal" style="width:400px">'+
    '<div class="apm-header"><span>⚡ 权限确认</span></div>'+
    '<div class="apm-body">'+
    '<div style="margin-bottom:12px"><span style="color:var(--text2);font-size:11px">工具:</span> <code style="background:var(--bg);padding:2px 6px;border-radius:3px;font-size:11px">'+escHtml(toolName)+'</code></div>'+
    '<div style="margin-bottom:12px"><span style="color:var(--text2);font-size:11px">风险:</span> <span style="color:'+riskColor+';font-weight:600;font-size:11px">'+escHtml(risk)+'</span></div>'+
    '<div style="margin-bottom:12px;font-size:11px;color:var(--text2)">'+escHtml(reason||'此操作需要你的确认')+'</div>'+
    '<label style="display:flex;align-items:center;gap:6px;font-size:10px;color:var(--muted);margin-bottom:12px;cursor:pointer"><input type="checkbox" id="perm-remember" style="accent-color:var(--accent)"> 24h 内记住此选择</label>'+
    '</div>'+
    '<div class="apm-footer" style="display:flex;gap:8px">'+
    '<button class="btn" style="flex:1;border-color:var(--danger);color:var(--danger)" id="perm-deny-btn">拒绝</button>'+
    '<button class="new-chat-btn" style="flex:1" id="perm-allow-btn">允许执行</button>'+
    '</div>'+
    '</div>';
  document.body.appendChild(overlay);

  document.getElementById('perm-allow-btn').onclick = function(){
    overlay.remove();
    confirmPermission(toolName, 'allow', args);
  };
  document.getElementById('perm-deny-btn').onclick = function(){
    overlay.remove();
    confirmPermission(toolName, 'deny', args);
  };
  overlay.onclick = function(e){
    if(e.target === overlay){ overlay.remove(); confirmPermission(toolName, 'deny', args); }
  };
}

function confirmPermission(toolName, choice, args){
  fetch('/api/permissions/confirm', {
    method:'POST',
    headers:{'Content-Type':'application/json','X-Agency-Trust-Mode':trustMode},
    body:JSON.stringify({tool_name:toolName, choice:choice, trust_mode:trustMode, args:args||''})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      if(choice === 'allow') showToast('已允许: '+toolName);
      else showToast('已拒绝: '+toolName);
    }
  }).catch(function(e){ showToast('权限确认失败: '+(e.message||'网络错误'),!0); });
}

/* ── 权限审计面板 ── */
function loadPermissionAudit(){
  var domEl = document.getElementById('perm-audit-list');
  if(!domEl) return;
  fetch('/api/permissions/audit?limit=50').then(function(r){return r.json()}).then(function(d){
    var logs = d.logs || [];
    var stats = d.stats || {};
    var html = '<div style="margin-bottom:8px;display:flex;gap:12px;font-size:11px">'+
      '<span style="color:var(--accent)">允许: '+stats.allowed+'</span>'+
      '<span style="color:#f0a020">询问: '+stats.asked+'</span>'+
      '<span style="color:var(--danger)">拒绝: '+stats.denied+'</span>'+
      '<span style="color:var(--muted)">总计: '+stats.total+'</span>'+
      '</div>';
    if(logs.length){
      html += '<div style="max-height:300px;overflow-y:auto">';
      logs.forEach(function(l){
        var decColor = l.decision === 'allow' ? 'var(--accent)' : l.decision === 'deny' ? 'var(--danger)' : '#f0a020';
        html += '<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:10px">'+
          '<span style="color:var(--muted)">'+escHtml((l.time||'').slice(-8))+'</span> '+
          '<code style="color:var(--text);font-size:10px">'+escHtml(l.tool)+'</code> '+
          '<span style="color:'+decColor+'">'+escHtml(l.decision)+'</span> '+
          (l.reason ? '<span style="color:var(--muted)"> — '+escHtml(l.reason.slice(0,40))+'</span>' : '')+
          '</div>';
      });
      html += '</div>';
    } else {
      html += '<span style="color:var(--muted);font-size:10px">暂无审计记录</span>';
    }
    domEl.innerHTML = html;
  }).catch(function(){ domEl.innerHTML = '权限审计数据加载失败。请检查服务是否正常运行'; });
}

// 初始化信任模式 UI
document.addEventListener('DOMContentLoaded', function(){
  updateTrustModeUI();
  updateProfileUI();
});
