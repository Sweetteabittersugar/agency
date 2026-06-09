/* Agency — 基础工具函数 */
function $(id){return document.getElementById(id)}
function escHtml(s){var d=document.createElement('div');d.textContent=s??'';return d.innerHTML}
function showToast(m,err,level,duration){var t=document.createElement('div');t.className='toast'+(err?' error':'')+(level==='warn'?' warn':'');t.textContent=m;document.body.appendChild(t);duration=duration||3000;setTimeout(function(){t.style.opacity='0';t.style.transition='opacity .3s'},duration-500);setTimeout(function(){t.remove()},duration);return t}
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
      var ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showToast('已复制');
    });
  } else {
    var ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showToast('已复制');
  }
}
function getFocusedPanel(){if(focusedPid){var p=panels.find(function(x){return x.id===focusedPid});if(p&&p.dom.wrapper.classList.contains('on'))return p}var start=curPage*perPage;var panel=panels[start]||panels[0];if(!panel)panel=addPanel();return panel}
function highlightCode(domEl){if(!domEl)return;domEl.querySelectorAll('pre code').forEach(function(b){if(window.hljs)try{hljs.highlightElement(b)}catch(_){}})}

/* ── i18n 轻量国际化 ── */
var _lang=(navigator.language||'zh').slice(0,2)==='zh'?'zh':'en';
var L={
  loading:{zh:'加载中…',en:'Loading…'},
  error:{zh:'出错了',en:'Error'},
  empty:{zh:'暂无数据',en:'No data'},
  saveOk:{zh:'已保存',en:'Saved'},
  saveFail:{zh:'保存失败',en:'Save failed'},
  deleteOk:{zh:'已删除',en:'Deleted'},
  copied:{zh:'已复制',en:'Copied'},
  confirmDelete:{zh:'确认删除？此操作不可撤销。',en:'Delete? This cannot be undone.'},
  networkError:{zh:'网络异常，请检查连接后重试',en:'Network error. Check your connection'},
  apiKeyHint:{zh:'🔒 Key 仅存本地，永不上传',en:'🔒 Key stored locally only'},
};
function t(key){var entry=L[key];return entry?(_lang==='zh'?entry.zh:entry.en):key}

