/* 从 settings.js 拆分 — 配置导入导出 */

/* ── 配置导出 ── */
function exportConfig(){
  let config = {
    version: 1,
    exported_at: new Date().toISOString(),
    agents: typeof agents !== 'undefined' ? agents : [],
    skills: typeof allSkills !== 'undefined' ? allSkills : [],
    preferences: {
      theme: localStorage.getItem('agency_theme') || 'dark',
      font_size: localStorage.getItem('agency_font_size') || '14px',
      sidebar_width: localStorage.getItem('agency_sidebar_width') || '280',
      trust_mode: localStorage.getItem('agency_trust_mode') || 'cautious',
      profile: localStorage.getItem('agency_profile') || 'standard',
      output_dir: localStorage.getItem('agency_output_dir') || '',
      unlock_all: localStorage.getItem('agency_unlock_all') || 'false'
    },
    custom_templates: getCustomTemplates()
  };
  // 预览摘要
  let preview = document.getElementById('config-export-preview');
  if(preview){
    let previewHTML = '<div class="config-export-preview"><div style="font-weight:600;margin-bottom:4px">'+t('exportPreview')+'</div>';
    previewHTML += '<div class="preview-row"><span>Agent</span><span class="preview-val">'+(config.agents.length||0)+' 个</span></div>';
    previewHTML += '<div class="preview-row"><span>Skills</span><span class="preview-val">'+(config.skills.length||0)+' 个</span></div>';
    previewHTML += '<div class="preview-row"><span>自定义模板</span><span class="preview-val">'+(config.custom_templates.length||0)+' 个</span></div>';
    previewHTML += '<div class="preview-row"><span>偏好设置</span><span class="preview-val">'+Object.keys(config.preferences).length+' 项</span></div>';
    previewHTML += '</div>';
    preview.innerHTML = previewHTML;
  }
  let blob = new Blob([JSON.stringify(config, null, 2)], {type:'application/json'});
  let url = URL.createObjectURL(blob);
  let a = document.createElement('a');
  a.href = url;
  a.download = 'agency-config.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(t('configExportDone'));
}

/* ── 配置导入 ── */
function importConfig(){
  let input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = function(e){
    let file = e.target.files[0];
    if(!file) return;
    let reader = new FileReader();
    reader.onload = function(ev){
      try{
        let imported = JSON.parse(ev.target.result);
        showImportDiff(imported);
      }catch(err){
        showToast(t('error')+': JSON 格式无效', true);
      }
    };
    reader.readAsText(file);
  };
  input.click();
}
function showImportDiff(imported){
  let current = {
    agents: typeof agents !== 'undefined' ? agents : [],
    skills: typeof allSkills !== 'undefined' ? allSkills : [],
    preferences: {
      theme: localStorage.getItem('agency_theme') || 'dark',
      font_size: localStorage.getItem('agency_font_size') || '14px',
      sidebar_width: localStorage.getItem('agency_sidebar_width') || '280',
      trust_mode: localStorage.getItem('agency_trust_mode') || 'cautious',
      profile: localStorage.getItem('agency_profile') || 'standard',
      output_dir: localStorage.getItem('agency_output_dir') || '',
      unlock_all: localStorage.getItem('agency_unlock_all') || 'false'
    },
    custom_templates: getCustomTemplates()
  };

  let diffs = [];
  // agents
  let impAgents = imported.agents || [];
  let curAgents = current.agents;
  impAgents.forEach(function(ia){
    let ca = curAgents.find(function(a){return a.name===ia.name});
    if(!ca){
      diffs.push({type:'new',section:'Agent',name:ia.name,val:ia.description||''});
    }
  });
  // skills
  let impSkills = imported.skills || [];
  let curSkills = current.skills;
  impSkills.forEach(function(is){
    let cs = curSkills.find(function(s){return s.name===is.name});
    if(!cs){
      diffs.push({type:'new',section:'Skill',name:is.name,val:is.description||''});
    }
  });
  // preferences
  let impPrefs = imported.preferences || {};
  let curPrefs = current.preferences;
  Object.keys(impPrefs).forEach(function(k){
    if(impPrefs[k] !== curPrefs[k]){
      diffs.push({type:'change',section:'偏好',name:k,old:curPrefs[k]||'(空)',val:impPrefs[k]||'(空)'});
    }
  });
  // custom templates
  let impTpls = imported.custom_templates || [];
  let curTpls = current.custom_templates;
  impTpls.forEach(function(it){
    let ct = curTpls.find(function(t){return t.label===it.label});
    if(!ct){
      diffs.push({type:'new',section:'模板',name:it.label||it.content.slice(0,20),val:it.content||''});
    }
  });

  let overlay = document.createElement('div');
  overlay.className = 'config-diff-overlay';
  let html = '<div class="config-diff-modal">';
  html += '<div class="config-diff-header"><span>'+t('importDiff')+' ('+diffs.length+' 项)</span><button class="btn" id="diff-close-btn">✕</button></div>';
  html += '<div class="config-diff-body">';
  if(diffs.length === 0){
    html += '<p style="color:var(--muted);text-align:center;padding:20px">配置无差异，无需导入</p>';
  } else {
    diffs.forEach(function(d,i){
      html += '<div class="config-diff-item" id="diff-item-'+i+'">';
      html += '<div class="diff-name">['+escHtml(d.section)+'] '+escHtml(d.name)+'</div>';
      if(d.type==='change'){
        html += '<div class="diff-row"><span class="diff-old">'+escHtml(d.old)+'</span><span class="diff-arrow">→</span><span class="diff-new">'+escHtml(d.val)+'</span></div>';
        html += '<div class="diff-actions"><button class="replace" onclick="applyDiffItem('+i+',\'replace\')">'+t('replaceWithImport')+'</button><button onclick="applyDiffItem('+i+',\'keep\')">'+t('keepExisting')+'</button></div>';
      } else {
        html += '<div class="diff-row"><span class="diff-new-only">(新增) '+escHtml(d.val)+'</span></div>';
        html += '<div class="diff-actions"><button class="replace" onclick="applyDiffItem('+i+',\'import\')">'+t('importNewItem')+'</button><button onclick="applyDiffItem('+i+',\'skip\')">'+t('skipImport')+'</button></div>';
      }
      html += '</div>';
    });
  }
  html += '</div>';
  html += '<div class="config-diff-actions">';
  if(diffs.length > 0){
    html += '<button class="btn primary" onclick="applyAllDiffs()">'+t('replaceAll')+'</button>';
    html += '<button class="btn" onclick="skipAllDiffs()">'+t('keepAll')+'</button>';
  }
  html += '<button class="btn" id="diff-cancel-btn">'+t('cancel')+'</button>';
  html += '</div></div>';
  overlay.innerHTML = html;
  document.body.appendChild(overlay);

  overlay._diffs = diffs;
  overlay._imported = imported;
  overlay._decisions = {};
  diffs.forEach(function(d,i){ overlay._decisions[i] = 'replace'; });

  function cleanup(){ overlay.remove(); }
  overlay.querySelector('#diff-close-btn').addEventListener('click', cleanup);
  overlay.querySelector('#diff-cancel-btn').addEventListener('click', cleanup);
  overlay.addEventListener('click', function(e){ if(e.target===overlay) cleanup(); });
}

function applyDiffItem(idx, decision){
  let overlay = document.querySelector('.config-diff-overlay');
  if(!overlay) return;
  overlay._decisions[idx] = decision;
  let item = document.getElementById('diff-item-'+idx);
  if(item){
    item.style.opacity = decision==='replace'||decision==='import'?'.6':'.3';
    item.style.borderLeftColor = decision==='replace'||decision==='import'?'var(--accent)':'var(--muted)';
  }
}

function applyAllDiffs(){
  let overlay = document.querySelector('.config-diff-overlay');
  if(!overlay) return;
  let diffs = overlay._diffs;
  for(let i=0;i<diffs.length;i++) overlay._decisions[i]='replace';
  executeImport(overlay._imported, overlay._decisions);
  overlay.remove();
}

function skipAllDiffs(){
  let overlay = document.querySelector('.config-diff-overlay');
  if(!overlay) return;
  overlay.remove();
  showToast(t('configImportCancel'));
}

function executeImport(imported, decisions){
  // Apply preferences
  let impPrefs = imported.preferences || {};
  Object.keys(impPrefs).forEach(function(k){
    let prefKey = {theme:'agency_theme',font_size:'agency_font_size',sidebar_width:'agency_sidebar_width',trust_mode:'agency_trust_mode',profile:'agency_profile',output_dir:'agency_output_dir',unlock_all:'agency_unlock_all'}[k];
    if(prefKey) localStorage.setItem(prefKey, impPrefs[k]);
  });
  showToast(t('configImportDone'));
  setTimeout(function(){ location.reload(); }, 1000);
}

/* ── 配置重置 ── */
function resetConfig(){
  showDeleteConfirm(t('confirmReset'), function(){
    let savedKey = localStorage.getItem('agency_api_key');
    let savedProvider = localStorage.getItem('agency_api_provider');
    localStorage.clear();
    if(savedKey) localStorage.setItem('agency_api_key', savedKey);
    if(savedProvider) localStorage.setItem('agency_api_provider', savedProvider);
    showToast(t('resetDone'));
    setTimeout(function(){ location.reload(); }, 800);
  });
}
