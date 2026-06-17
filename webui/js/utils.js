/* Agency — 基础工具函数 (Round 3: 配置剥离到 config/) */

window.safeSetItem = function(key, value) {
  try { localStorage.setItem(key, value); return true; }
  catch(e) { if(e.name==="QuotaExceededError"){console.warn("localStorage full, cannot save "+key); showToast("存储空间已满，请清理旧数据",!1,"warn")} return false }
};

function $(id){return document.getElementById(id)}
function escHtml(s){let d=document.createElement('div');d.textContent=s??'';return d.innerHTML}
function showToast(m,err,level,duration){
  if(typeof m==='object'&&m!==null&&m.undo){
    return showUndoableToast(m.msg||'',m.undo,m.duration||5000,m.commit);
  }
  let t=document.createElement('div');t.className='toast'+(err?' error':'')+(level==='warn'?' warn':'');t.textContent=m;document.body.appendChild(t);duration=duration||3000;setTimeout(function(){t.style.opacity='0';t.style.transition='opacity .3s'},duration-500);setTimeout(function(){t.remove()},duration);return t
}
function apiFetch(url, opts){
  opts=Object.assign({},opts);
  opts.headers=Object.assign({},opts.headers||{});
  if(authToken)opts.headers['Authorization']='Bearer '+authToken;
  return fetch(url,opts).then(function(r){
    if(r.status===401){
      if(authToken){
        authToken='';
        localStorage.removeItem('agency_auth_token');
      }
      showRemoteLogin();
      throw new Error('需要认证');
    }
    return r;
  });
}
function copyText(text){
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function(){showToast('已复制')}).catch(function(){
      let ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showToast('已复制');
    });
  } else {
    let ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showToast('已复制');
  }
}
function getFocusedPanel(){if(focusedPid){let p=panels.find(function(x){return x.id===focusedPid});if(p&&p.dom.wrapper.classList.contains('on'))return p}let start=curPage*perPage;let panel=panels[start]||panels[0];if(!panel)panel=addPanel();return panel}
function highlightCode(domEl){if(!domEl)return;domEl.querySelectorAll('pre code').forEach(function(b){if(window.hljs)try{hljs.highlightElement(b)}catch(_){}})}

/* ── Demo 假数据 ── */
function getDemoAgents(){
  return [
    {name:'coder',model:'deepseek-v4',description:'写代码、修Bug、重构——你的全能编程搭档',keywords:['python','javascript','refactor','debug'],tools:['Read','Write','Edit','Bash','Glob']},
    {name:'reviewer',model:'claude-sonnet',description:'审查代码质量、安全漏洞、性能瓶颈',keywords:['security','performance','code-review','lint'],tools:['Read','Grep','Glob']},
    {name:'explorer',model:'deepseek-v4',description:'搜索项目文件、分析代码结构、回答技术问题',keywords:['search','grep','analysis','docs'],tools:['Read','Grep','Glob','Bash']}
  ];
}
function getDemoSkills(){
  return [
    {name:'pipeline-gate',description:'多阶段任务流水线：研究→规划→实施→审查→验证',category:'编排',enabled:true},
    {name:'code-review',description:'自动化代码审查：安全、性能、风格全方位检查',category:'质量',enabled:true},
    {name:'web-search',description:'联网搜索最新信息，支持多搜索引擎',category:'工具',enabled:true},
    {name:'tdd-guide',description:'测试驱动开发向导：红→绿→重构循环',category:'测试',enabled:true},
    {name:'doc-writer',description:'自动生成和维护项目文档、API 文档',category:'文档',enabled:true}
  ];
}
function getDemoHistory(){
  let now=Date.now();
  return [
    {id:now-3600000,title:'写一个网页爬虫抓取新闻标题',messages:[{role:'user',content:'帮我写一个Python爬虫，抓取Hacker News首页标题'},{role:'assistant',content:'这是基于 requests + BeautifulSoup 的爬虫实现…'}],time:new Date(now-3600000).toLocaleDateString('zh-CN')},
    {id:now-7200000,title:'审查用户认证模块的安全性',messages:[{role:'user',content:'审查这段用户认证代码的安全性'},{role:'assistant',content:'发现3个安全问题：1.密码未加盐 2.SQL注入风险…'}],time:new Date(now-7200000).toLocaleDateString('zh-CN')}
  ];
}

/* ── 删除确认弹窗 (替换原生confirm) ── */
function showDeleteConfirm(message, onConfirm, onCancel){
  let overlay=document.createElement('div');
  overlay.className='confirm-overlay';
  overlay.innerHTML='<div class="confirm-box"><p>'+escHtml(message)+'</p><div class="btn-row"><button class="btn btn-cancel">'+t('cancel')+'</button><button class="btn btn-delete danger-delay">'+t('delete')+'</button></div></div>';
  document.body.appendChild(overlay);
  let cancelBtn=overlay.querySelector('.btn-cancel');
  let deleteBtn=overlay.querySelector('.btn-delete');
  cancelBtn.focus();
  function cleanup(){overlay.remove();}
  cancelBtn.addEventListener('click',function(){cleanup();if(onCancel)onCancel()});
  deleteBtn.addEventListener('click',function(){cleanup();if(onConfirm)onConfirm()});
  overlay.addEventListener('click',function(e){if(e.target===overlay){cleanup();if(onCancel)onCancel()}});
  overlay.addEventListener('keydown',function(e){if(e.key==='Escape'){cleanup();if(onCancel)onCancel()}});
  return overlay;
}

function escAttr(s){ return (s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;'); }

/* ── Tooltip 帮助系统 ── */
function initTooltips(){
  let activeTooltip = null;
  function createTooltip(text, target){
    removeTooltip();
    let tip = document.createElement('div');
    tip.className = 'agency-tooltip';
    tip.textContent = text;
    document.body.appendChild(tip);
    positionTooltip(tip, target);
    tip.style.opacity = '1';
    tip.style.transform = 'translateY(0)';
    activeTooltip = {el: tip, target: target};
    return tip;
  }
  function positionTooltip(tip, target){
    let rect = target.getBoundingClientRect();
    let tw = tip.offsetWidth, th = tip.offsetHeight;
    let vw = window.innerWidth, vh = window.innerHeight;
    let top = rect.bottom + 6, left = rect.left + rect.width / 2 - tw / 2;
    if(top + th > vh - 10){ top = rect.top - th - 6; tip.classList.add('tip-above'); }
    else { tip.classList.remove('tip-above'); }
    if(left < 6){ left = 6; }
    if(left + tw > vw - 6){ left = vw - tw - 6; }
    tip.style.top = top + 'px';
    tip.style.left = left + 'px';
    tip.setAttribute('data-tip-x', (rect.left + rect.width / 2 - left));
  }
  function removeTooltip(){
    if(activeTooltip){ activeTooltip.el.remove(); activeTooltip = null; }
  }
  document.addEventListener('mouseover', function(e){
    let el = e.target.closest('[data-tooltip]');
    if(!el) return;
    if(window.innerWidth < 768) return;
    let text = el.getAttribute('data-tooltip');
    if(text) createTooltip(t(text) || text, el);
  });
  document.addEventListener('mouseout', function(e){
    let el = e.target.closest('[data-tooltip]');
    if(el && window.innerWidth >= 768) removeTooltip();
  });
  document.addEventListener('click', function(e){
    if(window.innerWidth >= 768) return;
    let el = e.target.closest('[data-tooltip]');
    if(!el){removeTooltip();return;}
    if(activeTooltip && activeTooltip.target === el){removeTooltip();return;}
    let text = el.getAttribute('data-tooltip');
    if(text) createTooltip(t(text) || text, el);
    e.stopPropagation();
  });
  window.addEventListener('scroll', function(){ if(activeTooltip) positionTooltip(activeTooltip.el, activeTooltip.target); }, true);
  window.addEventListener('resize', function(){ removeTooltip(); });
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') removeTooltip(); });
}

/* ── 文件路径检测 ── */
function detectFilePath(text){
  if(!text) return null;
  let m = text.match(/^(\/[a-zA-Z0-9_\-\.\/\\]+)/);
  if(m) return m[1];
  m = text.match(/^([A-Za-z]:\\[a-zA-Z0-9_\-\.\/\\]+)/);
  if(m) return m[1];
  m = text.match(/^([A-Za-z]:\/[a-zA-Z0-9_\-\.\/\\]+)/);
  if(m) return m[1];
  return null;
}

/** 侧边栏折叠区切换 (R5 四区布局) */
window.toggleSidebarSection = function(sectionId) {
  let el = document.getElementById(sectionId);
  if (el) el.classList.toggle('collapsed');
};

// ES module bridge — 工具函数
window.$ = $;
window.escHtml = escHtml;
window.showToast = showToast;
window.apiFetch = apiFetch;
window.copyText = copyText;
window.getFocusedPanel = getFocusedPanel;
window.highlightCode = highlightCode;
window.escAttr = escAttr;
window.showDeleteConfirm = showDeleteConfirm;
window.initTooltips = initTooltips;
window.detectFilePath = detectFilePath;
window.getDemoAgents = getDemoAgents;
window.getDemoSkills = getDemoSkills;
window.getDemoHistory = getDemoHistory;
