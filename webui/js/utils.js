/* Agency — 基础工具函数 */
function $(id){return document.getElementById(id)}
function escHtml(s){var d=document.createElement('div');d.textContent=s??'';return d.innerHTML}
function showToast(m,err,level,duration){
  if(typeof m==='object'&&m!==null&&m.undo){
    return showUndoableToast(m.msg||'',m.undo,m.duration||5000,m.commit);
  }
  var t=document.createElement('div');t.className='toast'+(err?' error':'')+(level==='warn'?' warn':'');t.textContent=m;document.body.appendChild(t);duration=duration||3000;setTimeout(function(){t.style.opacity='0';t.style.transition='opacity .3s'},duration-500);setTimeout(function(){t.remove()},duration);return t
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
      var ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showToast('已复制');
    });
  } else {
    var ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);showToast('已复制');
  }
}
function getFocusedPanel(){if(focusedPid){var p=panels.find(function(x){return x.id===focusedPid});if(p&&p.dom.wrapper.classList.contains('on'))return p}var start=curPage*perPage;var panel=panels[start]||panels[0];if(!panel)panel=addPanel();return panel}
function highlightCode(domEl){if(!domEl)return;domEl.querySelectorAll('pre code').forEach(function(b){if(window.hljs)try{hljs.highlightElement(b)}catch(_){}})}

/* ── Provider 数据库 ── */
var PROVIDER_DB={
  deepseek:{name:'DeepSeek',desc:'性价比极高，中文能力强',region:'cn',price_tier:'free',api_base:'https://api.deepseek.com',default_model:'deepseek-chat',register_url:'https://platform.deepseek.com/api_keys',free_credit:'500万 Token 免费额度',est_monthly:{free:'$0',mid:'$2-10',high:'$10-50'}},
  qwen:{name:'通义千问',desc:'阿里云出品，生态完善',region:'cn',price_tier:'free',api_base:'https://dashscope.aliyuncs.com/compatible-mode/v1',default_model:'qwen-max',register_url:'https://dashscope.console.aliyun.com/',free_credit:'新用户百万 Token 免费',est_monthly:{free:'$0',mid:'$3-15',high:'$15-80'}},
  kimi:{name:'Kimi (月之暗面)',desc:'超长上下文，阅读能力强',region:'cn',price_tier:'free',api_base:'https://api.moonshot.cn/v1',default_model:'moonshot-v1-8k',register_url:'https://platform.moonshot.cn/',free_credit:'注册送 15 元',est_monthly:{free:'$0',mid:'$5-20',high:'$20-100'}},
  glm:{name:'智谱 GLM',desc:'清华系，学术背景深厚',region:'cn',price_tier:'free',api_base:'https://open.bigmodel.cn/api/paas/v4',default_model:'glm-4-flash',register_url:'https://open.bigmodel.cn/',free_credit:'注册送额度',est_monthly:{free:'$0',mid:'$3-15',high:'$15-60'}},
  minimax:{name:'MiniMax',desc:'语音+文本多模态',region:'cn',price_tier:'free',api_base:'https://api.minimax.chat/v1',default_model:'abab7-chat',register_url:'https://platform.minimaxi.com/',free_credit:'新用户有额度',est_monthly:{free:'$0',mid:'$5-20',high:'$20-80'}},
  siliconflow:{name:'硅基流动',desc:'聚合多家模型，灵活切换',region:'cn',price_tier:'free',api_base:'https://api.siliconflow.cn/v1',default_model:'deepseek-ai/DeepSeek-V3',register_url:'https://siliconflow.cn/',free_credit:'新用户赠送额度',est_monthly:{free:'$0',mid:'$3-12',high:'$12-50'}},
  anthropic:{name:'Anthropic Claude',desc:'最强推理，安全可靠',region:'global',price_tier:'mid',api_base:'https://api.anthropic.com',default_model:'claude-sonnet-4-20250514',register_url:'https://console.anthropic.com/',free_credit:'无免费额度',est_monthly:{free:'—',mid:'$10-30',high:'$50-200'}},
  openai:{name:'OpenAI (GPT)',desc:'生态最成熟，模型最全',region:'global',price_tier:'mid',api_base:'https://api.openai.com/v1',default_model:'gpt-4o',register_url:'https://platform.openai.com/',free_credit:'无免费额度',est_monthly:{free:'—',mid:'$10-30',high:'$50-200'}},
  google:{name:'Google Gemini',desc:'多模态能力强，免费额度慷慨',region:'global',price_tier:'free',api_base:'https://generativelanguage.googleapis.com/v1beta/openai',default_model:'gemini-2.5-flash',register_url:'https://aistudio.google.com/apikey',free_credit:'免费层额度充足',est_monthly:{free:'$0',mid:'$5-20',high:'$20-80'}},
  xai:{name:'xAI (Grok)',desc:'Musk 出品，实时信息',region:'global',price_tier:'mid',api_base:'https://api.x.ai/v1',default_model:'grok-beta',register_url:'https://x.ai/api',free_credit:'每月有免费额度',est_monthly:{free:'$0',mid:'$5-25',high:'$25-100'}},
  custom:{name:'自定义端点',desc:'兼容 OpenAI 格式的任意服务',region:'any',price_tier:'any',api_base:'https://your-api-endpoint.com/v1',default_model:'gpt-3.5-turbo',register_url:'',free_credit:'取决于你的服务商',est_monthly:{free:'—',mid:'—',high:'—'}}
};

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
  var now=Date.now();
  return [
    {id:now-3600000,title:'写一个网页爬虫抓取新闻标题',messages:[{role:'user',content:'帮我写一个Python爬虫，抓取Hacker News首页标题'},{role:'assistant',content:'这是基于 requests + BeautifulSoup 的爬虫实现…'}],time:new Date(now-3600000).toLocaleDateString('zh-CN')},
    {id:now-7200000,title:'审查用户认证模块的安全性',messages:[{role:'user',content:'审查这段用户认证代码的安全性'},{role:'assistant',content:'发现3个安全问题：1.密码未加盐 2.SQL注入风险…'}],time:new Date(now-7200000).toLocaleDateString('zh-CN')}
  ];
}

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
  demoWelcome:{zh:'👋 欢迎体验 Agency！这是 Demo 模式，试试下面的功能 👇',en:'👋 Welcome to Agency! Demo mode — try the features below 👇'},
  demoQuick1:{zh:'🕷️ 帮我写网页爬虫',en:'🕷️ Write a web scraper'},
  demoQuick2:{zh:'🔍 审查这段代码的安全性',en:'🔍 Security review this code'},
  demoQuick3:{zh:'📋 搜索项目中所有 TODO',en:'📋 Find all TODOs in project'},
  demoPopup:{zh:'🔧 配置 API Key 即可执行真实任务',en:'🔧 Configure API Key to execute real tasks'},
  demoGotoSettings:{zh:'⚙️ 前往设置',en:'⚙️ Go to Settings'},
  demoTooltip:{zh:'Demo 模拟数据 — 配置 Key 后替换为真实数据',en:'Demo data — replace with real data after configuring Key'},
  providerRegion:{zh:'你在哪个地区？',en:'Which region are you in?'},
  providerBudget:{zh:'你的预算？',en:'Your budget?'},
  providerRegionCN:{zh:'🌏 中国大陆',en:'🌏 Mainland China'},
  providerRegionGlobal:{zh:'🌍 海外',en:'🌍 Overseas'},
  providerBudgetFree:{zh:'💰 免费优先',en:'💰 Free tier first'},
  providerBudgetMid:{zh:'💳 中等预算 (~$10-20/月)',en:'💳 Moderate budget (~$10-20/mo)'},
  providerBudgetHigh:{zh:'🚀 性能优先 (不计成本)',en:'🚀 Performance first (unlimited budget)'},
  providerRecommended:{zh:'推荐',en:'Recommended'},
  providerEstimated:{zh:'预估月费',en:'Est. monthly'},
  providerShowAll:{zh:'查看全部 11 个 Provider ▼',en:'Show all 11 providers ▼'},
  providerHideAll:{zh:'收起 ▲',en:'Collapse ▲'},
  providerRegionHint:{zh:'根据地区推荐延迟最低的服务商',en:'Recommended providers with lowest latency for your region'},
  providerAutoFilled:{zh:'已自动填入：',en:'Auto-filled: '},
  providerRegister:{zh:'注册',en:'Register'},
  // 空状态引导
  chatEmptyTitle:{zh:'👋 试试：帮我写个网页爬虫',en:'👋 Try: Write me a web scraper'},
  chatEmptyBtn1:{zh:'📝 写文案',en:'📝 Copywriting'},
  chatEmptyBtn2:{zh:'🔍 查资料',en:'🔍 Research'},
  chatEmptyBtn3:{zh:'💻 写代码',en:'💻 Code'},
  chatQuickAction1:{zh:'帮我写一段产品文案',en:'Write me some product copy'},
  chatQuickAction2:{zh:'帮我查一下相关资料',en:'Research some information for me'},
  chatQuickAction3:{zh:'帮我写一个实用工具',en:'Write me a utility tool'},
  agentsLoadFail:{zh:'无法连接服务器',en:'Cannot connect to server'},
  retry:{zh:'重试',en:'Retry'},
  checkService:{zh:'检查服务状态',en:'Check service'},
  dashboardEmpty:{zh:'还没有数据。发一个任务后这里会有实时统计 📊',en:'No data yet. Send a task to see live stats here 📊'},
  historyEmpty:{zh:'对话会出现在这里。试试发第一条消息 👆',en:'Conversations appear here. Try sending your first message 👆'},
  skillsEmptyTitle:{zh:'Skills 是给 Agent 的工作流模板',en:'Skills are workflow templates for Agents'},
  learnMore:{zh:'了解更多 →',en:'Learn more →'},
  createSkill:{zh:'创建 →',en:'Create →'},
  routeEmpty:{zh:'输入任务后自动匹配最佳 Agent',en:'Type a task to auto-match the best Agent'},
  // 撤销系统
  undo:{zh:'撤销',en:'Undo'},
  restore:{zh:'恢复',en:'Restore'},
  enable:{zh:'启用',en:'Enable'},
  rollback:{zh:'回滚',en:'Rollback'},
  convDeleted:{zh:'对话已删除',en:'Conversation deleted'},
  panelClosed:{zh:'面板已关闭',en:'Panel closed'},
  promptCleared:{zh:'提示词已清空',en:'Prompt cleared'},
  promptSaved:{zh:'提示词已保存',en:'Prompt saved'},
  skillToggled:{zh:'已切换',en:'Toggled'},
  configSaved:{zh:'配置已保存',en:'Config saved'},
  agentDeleted:{zh:'已删除',en:'Deleted'},
  // 输入保护
  inputPlaceholder:{zh:'输入任务或 @agent名…',en:'Type a task or @agent…'},
  pasteLargeText:{zh:'内容较长(约{N}字)，是否发送？',en:'Content is long (~{N} chars). Send anyway?'},
  providerSwitchWarn:{zh:'切换后可能需要重新输入 API Key',en:'Switching may require re-entering API Key'},
  minAgents:{zh:'至少保留3个Agent',en:'Keep at least 3 Agents'},
  sseActiveWarn:{zh:'有正在执行的任务，确定离开？',en:'Active tasks running. Leave anyway?'},
  cancel:{zh:'取消',en:'Cancel'},
  delete:{zh:'删除',en:'Delete'},
  // 渐进式功能暴露
  featureUnlock:{zh:'功能解锁',en:'Feature Unlock'},
  featureLocked:{zh:'🔒 Day {day} 解锁',en:'🔒 Unlocks Day {day}'},
  currentDay:{zh:'当前：Day {day}',en:'Current: Day {day}'},
  newFeatureUnlocked:{zh:'🎉 新功能解锁：{name}！',en:'🎉 New feature unlocked: {name}!'},
  unlockAll:{zh:'🔓 解锁全部功能',en:'🔓 Unlock All Features'},
  // 工作流模板
  templates:{zh:'📋 模板',en:'📋 Templates'},
  saveTemplate:{zh:'💾 保存模板',en:'💾 Save Template'},
  editTemplate:{zh:'编辑',en:'Edit'},
  delTemplate:{zh:'删除',en:'Delete'},
  newTemplate:{zh:'+ 新建模板',en:'+ New Template'},
  templateName:{zh:'模板名称',en:'Template Name'},
  templateContent:{zh:'模板内容',en:'Template Content'},
  templateSaved:{zh:'模板已保存',en:'Template saved'},
  templateDeleted:{zh:'模板已删除',en:'Template deleted'},
  // 配置导入导出
  exportConfig:{zh:'📤 导出配置',en:'📤 Export Config'},
  importConfig:{zh:'📥 导入配置',en:'📥 Import Config'},
  resetConfig:{zh:'🔄 重置为默认',en:'🔄 Reset to Default'},
  exportPreview:{zh:'导出预览',en:'Export Preview'},
  importDiff:{zh:'配置差异',en:'Config Diff'},
  keepExisting:{zh:'保留',en:'Keep'},
  replaceWithImport:{zh:'替换',en:'Replace'},
  importNewItem:{zh:'导入',en:'Import'},
  skipImport:{zh:'跳过',en:'Skip'},
  replaceAll:{zh:'全部替换',en:'Replace All'},
  keepAll:{zh:'全部保留',en:'Keep All'},
  confirmReset:{zh:'确定重置所有配置？API Key 将保留，其他所有配置将恢复默认。',en:'Reset all config? API Key will be kept, everything else will be reset to default.'},
  resetDone:{zh:'配置已重置，即将刷新…',en:'Config reset. Refreshing…'},
  configExportDone:{zh:'配置已导出',en:'Config exported'},
  configImportDone:{zh:'配置已导入，即将刷新…',en:'Config imported. Refreshing…'},
  configImportCancel:{zh:'已取消导入',en:'Import cancelled'},
  // 主题
  themeDark:{zh:'暗色',en:'Dark'},
  themeLight:{zh:'亮色',en:'Light'},
  themeHighContrast:{zh:'高对比度',en:'High Contrast'},
  contrastHint:{zh:'💡 检测到系统偏好高对比度，已自动推荐高对比度主题',en:'💡 System prefers high contrast. High contrast theme recommended.'},
  palettePlaceholder:{zh:'输入命令…',en:'Type a command…'},
  paletteNoResults:{zh:'无匹配结果',en:'No matching results'},
  // 批量操作
  batchSelect:{zh:'多选',en:'Multi-select'},
  batchCancel:{zh:'取消',en:'Cancel'},
  batchSelectAll:{zh:'全选',en:'Select All'},
  batchDeleteSelected:{zh:'删除选中',en:'Delete Selected'},
  batchSelectedCount:{zh:'已选 {n} 个',en:'{n} selected'},
  confirmBatchDelete:{zh:'确认删除 {n} 个 Agent？此操作不可撤销。',en:'Delete {n} agents? This cannot be undone.'},
  clearAllHistory:{zh:'🗑 清空全部对话历史',en:'🗑 Clear All History'},
  clearAllHistoryConfirm:{zh:'确认清空所有对话历史？5秒内可撤销。',en:'Clear all history? Undo available for 5 seconds.'},
  clearAllHistoryDone:{zh:'对话历史已清空',en:'All history cleared'},
  historyCleared:{zh:'所有对话历史已清空',en:'All conversation history cleared'},
  stickyAgent:{zh:'默认 Agent',en:'Default Agent'},
  stickyAgentDesc:{zh:'选中的 Agent 将在所有新面板中优先使用',en:'Selected agent will be used by default in all new panels'},
  stickyAgentNone:{zh:'无（自动路由）',en:'None (auto route)'},
  filePickerHint:{zh:'💡 输入文件路径：从文件管理器复制路径后粘贴到这里',en:'💡 Enter file path: copy and paste path from your file manager'},
  // Tooltip 文案
  tooltipSend:{zh:'Ctrl+Enter 发送，支持 @agent 指定助手',en:'Ctrl+Enter to send. @agent to specify assistant'},
  tooltipProfile:{zh:'轻量=快+便宜；标准=智能路由；全功能=最强能力。随时切换',en:'Minimal=fast+cheap; Standard=smart routing; Full=maximum power. Switch anytime'},
  tooltipRoute:{zh:'Agency 自动选择最适合的 Agent，点击可手动更换',en:'Agency auto-selects the best Agent. Click to manually change'},
  tooltipMCP:{zh:'MCP 让 Agent 能操作浏览器、搜索网络。需要先安装对应服务',en:'MCP enables Agent to control browsers and search. Install services first'},
  tooltipSkill:{zh:'Skill 是给 Agent 的工作流模板，开启后 Agent 在合适场景自动调用',en:'Skills are workflow templates. Agents auto-use them in relevant scenarios'},
  tooltipOpus:{zh:'Opus 是最强推理模型，比例过高建议优化路由规则降低成本',en:'Opus is the strongest. High ratio? Optimize routing to reduce cost'},
  tooltipTemplate:{zh:'一键填入常用任务模板，可自定义保存',en:'One-click task templates. Customizable and savable'},
  // Profile 自动升级
  profileAutoUpgraded:{zh:'📈 已使用 Agency {n}天，已自动升级为标准模式。路由和 Agent 列表已解锁 [设置]',en:'📈 Used Agency for {n} days. Auto-upgraded to Standard. Routing & Agent list unlocked [Settings]'},
  profileRecommendFull:{zh:'📈 已使用 Agency {n}天，推荐升级全功能模式。解锁全部能力 [设置]',en:'📈 Used Agency for {n} days. Full mode recommended. Unlock all features [Settings]'},
  // 快捷键编辑
  shortcuts:{zh:'⌨️ 快捷键',en:'⌨️ Shortcuts'},
  editShortcut:{zh:'编辑',en:'Edit'},
  resetShortcuts:{zh:'重置为默认',en:'Reset to Default'},
  pressNewShortcut:{zh:'请按下新的快捷键组合…',en:'Press new shortcut keys…'},
  shortcutConflict:{zh:'快捷键冲突："{key}" 已被 "{action}" 使用',en:'Shortcut conflict: "{key}" already used by "{action}"'},
  shortcutSaved:{zh:'快捷键已保存',en:'Shortcut saved'},
  shortcutsReset:{zh:'快捷键已重置为默认',en:'Shortcuts reset to default'},
  shortcutCapture:{zh:'正在监听按键… 按 Esc 取消',en:'Listening for keys… Esc to cancel'},
  // 移动端
  mobileChat:{zh:'💬 聊天',en:'💬 Chat'},
  mobileDashboard:{zh:'📊 仪表盘',en:'📊 Dashboard'},
  mobileSettings:{zh:'⚙️ 设置',en:'⚙️ Settings'},
  mobileAgents:{zh:'👤 Agent',en:'👤 Agents'},
  // 引导解锁
  wizardUnlockAll:{zh:'我是老用户，解锁全部功能',en:"I'm a returning user, unlock all features"},
  wizardConfigDone:{zh:'🎉 配置完成！功能会随使用天数逐步解锁。在设置→功能解锁可提前开启全部。',en:'🎉 Setup complete! Features unlock gradually. Settings → Feature Unlock to enable all early.'},
  featureUnlockHint:{zh:'💡 功能随使用天数逐步解锁。需要提前使用全部功能？→ 开启上方"解锁全部功能"开关',en:'💡 Features unlock gradually as you use Agency. Want everything now? → Turn on "Unlock All Features" above'},
};
function t(key){var entry=L[key];return entry?(_lang==='zh'?entry.zh:entry.en):key}

/* ── 删除确认弹窗 (替换原生confirm) ── */
function showDeleteConfirm(message, onConfirm, onCancel){
  var overlay=document.createElement('div');
  overlay.className='confirm-overlay';
  overlay.innerHTML='<div class="confirm-box"><p>'+escHtml(message)+'</p><div class="btn-row"><button class="btn btn-cancel">'+t('cancel')+'</button><button class="btn btn-delete danger-delay">'+t('delete')+'</button></div></div>';
  document.body.appendChild(overlay);
  var cancelBtn=overlay.querySelector('.btn-cancel');
  var deleteBtn=overlay.querySelector('.btn-delete');
  cancelBtn.focus();
  function cleanup(){overlay.remove();}
  cancelBtn.addEventListener('click',function(){cleanup();if(onCancel)onCancel()});
  deleteBtn.addEventListener('click',function(){cleanup();if(onConfirm)onConfirm()});
  overlay.addEventListener('click',function(e){if(e.target===overlay){cleanup();if(onCancel)onCancel()}});
  overlay.addEventListener('keydown',function(e){if(e.key==='Escape'){cleanup();if(onCancel)onCancel()}});
  return overlay;
}

/* ── 渐进式功能暴露 ── */
var FEATURE_SCHEDULE = {
  day0:       { minDay:0,  features:['chat','settings'],                           desc:{zh:'基础聊天 + Key 配置',en:'Basic chat + Key config'} },
  day1_2:     { minDay:1,  features:['dashboard','agents'],                        desc:{zh:'仪表盘 + Agent 列表',en:'Dashboard + Agent list'} },
  day3_5:     { minDay:3,  features:['routing','multipanel'],                      desc:{zh:'智能调度 + 多面板',en:'Smart routing + Multi-panel'} },
  day7:       { minDay:7,  features:['agent-factory','skills','profiles'],         desc:{zh:'Agent 工厂 + Skill 编辑 + Profile',en:'Agent factory + Skill edit + Profile'} },
};
var FEATURE_UNLOCK_DAYS = {};
(function(){
  var ks = Object.keys(FEATURE_SCHEDULE);
  for(var i=0;i<ks.length;i++){
    var s = FEATURE_SCHEDULE[ks[i]];
    for(var j=0;j<s.features.length;j++){
      FEATURE_UNLOCK_DAYS[s.features[j]] = s.minDay;
    }
  }
})();
function getUserDay(){
  var first = localStorage.getItem('agency_first_visit');
  if(!first){
    var now = new Date().toISOString().slice(0,10);
    localStorage.setItem('agency_first_visit', now);
    first = now;
  }
  var diff = Math.floor((Date.now() - new Date(first).getTime()) / 86400000);
  return Math.max(0, diff);
}
function isFeatureUnlocked(name){
  if(localStorage.getItem('agency_unlock_all') === 'true') return true;
  var minDay = FEATURE_UNLOCK_DAYS[name];
  if(minDay === undefined) return true;
  return getUserDay() >= minDay;
}
function checkNewUnlocks(){
  var day = getUserDay();
  var seen = {};
  try{ seen = JSON.parse(localStorage.getItem('agency_unlock_seen') || '{}'); }catch(e){}
  var newUnlocks = [];
  var ks = Object.keys(FEATURE_SCHEDULE);
  for(var i=0;i<ks.length;i++){
    var s = FEATURE_SCHEDULE[ks[i]];
    if(day >= s.minDay && !seen[ks[i]]){
      for(var j=0;j<s.features.length;j++){ newUnlocks.push(s.features[j]); }
      seen[ks[i]] = true;
    }
  }
  if(newUnlocks.length > 0){
    localStorage.setItem('agency_unlock_seen', JSON.stringify(seen));
    var labelMap = {chat:'基础聊天',settings:'设置面板',dashboard:'仪表盘',agents:'Agent列表',routing:'智能调度',multipanel:'多面板','agent-factory':'Agent工厂',skills:'Skill编辑',profiles:'Profile切换'};
    var names = newUnlocks.map(function(f){ return labelMap[f] || f; });
    showToast(t('newFeatureUnlocked').replace('{name}', names.join('、')));
  }
  // Profile 自动选择
  autoSelectProfile(day);
}

/* ── Profile 自动选择 ── */
function autoSelectProfile(day){
  if(localStorage.getItem('profile_manual') === 'true') return;
  var cur = localStorage.getItem('agency_profile') || 'standard';
  if(day >= 7 && cur !== 'full'){
    showToast(t('profileRecommendFull').replace('{n}', day), false, 'warn', 5000);
  } else if(day >= 3 && cur === 'minimal'){
    localStorage.setItem('agency_profile', 'standard');
    if(typeof agencyProfile !== 'undefined') agencyProfile = 'standard';
    if(typeof updateProfileUI === 'function') updateProfileUI();
    showToast(t('profileAutoUpgraded').replace('{n}', day), false, 'warn', 6000);
  }
}

/* ── 工作流模板 ── */
var WORKFLOW_TEMPLATES = [
  {icon:'🆕',label:{zh:'写新功能',en:'New Feature'},content:'@coder 请帮我实现以下功能：\n功能描述：\n技术栈：\n具体要求：'},
  {icon:'🐛',label:{zh:'修 Bug',en:'Fix Bug'},content:'@coder 请修复以下 Bug：\nBug 描述：\n复现步骤：\n期望行为：'},
  {icon:'🔍',label:{zh:'代码审查',en:'Code Review'},content:'@reviewer 请审查以下代码，重点关注：\n1. 安全问题\n2. 性能问题\n3. 代码规范'},
  {icon:'🧪',label:{zh:'写测试',en:'Write Tests'},content:'@test 请为以下代码编写测试：\n测试框架：\n覆盖要求：'},
  {icon:'📚',label:{zh:'搜索资料',en:'Search'},content:'@explorer 请搜索以下内容：\n关键词：\n范围：\n格式要求：'},
  {icon:'⚡',label:{zh:'性能分析',en:'Performance'},content:'@coder 请分析以下代码的性能瓶颈：\n场景：\n数据量：'}
];
function getCustomTemplates(){
  try{ return JSON.parse(localStorage.getItem('agency_custom_templates') || '[]'); }catch(e){ return []; }
}
function saveCustomTemplates(list){
  localStorage.setItem('agency_custom_templates', JSON.stringify(list));
}
function getAllTemplates(){
  return WORKFLOW_TEMPLATES.concat(getCustomTemplates());
}
function escAttr(s){ return (s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;'); }

/* ── Tooltip 帮助系统 ── */
function initTooltips(){
  var activeTooltip = null;
  function createTooltip(text, target){
    removeTooltip();
    var tip = document.createElement('div');
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
    var rect = target.getBoundingClientRect();
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var vw = window.innerWidth, vh = window.innerHeight;
    var top = rect.bottom + 6, left = rect.left + rect.width / 2 - tw / 2;
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
  // Desktop: hover
  document.addEventListener('mouseover', function(e){
    var el = e.target.closest('[data-tooltip]');
    if(!el) return;
    if(window.innerWidth < 768) return; // mobile uses click
    var text = el.getAttribute('data-tooltip');
    if(text) createTooltip(t(text) || text, el);
  });
  document.addEventListener('mouseout', function(e){
    var el = e.target.closest('[data-tooltip]');
    if(el && window.innerWidth >= 768) removeTooltip();
  });
  // Mobile: click
  document.addEventListener('click', function(e){
    if(window.innerWidth >= 768) return;
    var el = e.target.closest('[data-tooltip]');
    if(!el){
      removeTooltip();
      return;
    }
    if(activeTooltip && activeTooltip.target === el){
      removeTooltip();
      return;
    }
    var text = el.getAttribute('data-tooltip');
    if(text) createTooltip(t(text) || text, el);
    e.stopPropagation();
  });
  // Close on scroll/resize
  window.addEventListener('scroll', function(){ if(activeTooltip) positionTooltip(activeTooltip.el, activeTooltip.target); }, true);
  window.addEventListener('resize', function(){ removeTooltip(); });
  // Close on Escape
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') removeTooltip(); });
}

/* ── 文件路径检测 ── */
function detectFilePath(text){
  if(!text) return null;
  var m = text.match(/^(\/[a-zA-Z0-9_\-\.\/\\]+)/);
  if(m) return m[1];
  m = text.match(/^([A-Za-z]:\\[a-zA-Z0-9_\-\.\/\\]+)/);
  if(m) return m[1];
  m = text.match(/^([A-Za-z]:\/[a-zA-Z0-9_\-\.\/\\]+)/);
  if(m) return m[1];
  return null;
}
