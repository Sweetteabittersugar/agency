/* Agency — 基础工具函数 */
function $(id){return document.getElementById(id)}
function escHtml(s){var d=document.createElement('div');d.textContent=s??'';return d.innerHTML}
function showToast(m,err,level){var t=document.createElement('div');t.className='toast'+(err?' error':'')+(level==='warn'?' warn':'');t.textContent=m;document.body.appendChild(t);setTimeout(function(){t.style.opacity='0';t.style.transition='opacity .3s'},2500);setTimeout(function(){t.remove()},3000)}
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
  var ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showToast('已复制');
}
function getFocusedPanel(){if(focusedPid){var p=panels.find(function(x){return x.id===focusedPid});if(p&&p.dom.wrapper.classList.contains('on'))return p}var start=curPage*perPage;var panel=panels[start]||panels[0];if(!panel)panel=addPanel();return panel}
function highlightCode(domEl){if(!domEl)return;domEl.querySelectorAll('pre code').forEach(function(b){if(window.hljs)try{hljs.highlightElement(b)}catch(_){}})}
