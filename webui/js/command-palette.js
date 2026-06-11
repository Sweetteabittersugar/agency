/* Agency — 命令面板 + 全键盘快捷键 */

var KEYBOARD_SHORTCUTS = [
  {keys:'Ctrl+K',desc:'打开命令面板',action:'palette'},
  {keys:'Ctrl+N',desc:'新建面板',action:'newPanel'},
  {keys:'Ctrl+W',desc:'关闭当前面板',action:'closePanel'},
  {keys:'Ctrl+,',desc:'打开设置',action:'settings'},
  {keys:'Ctrl+/',desc:'快捷键帮助',action:'help'},
  {keys:'Ctrl+Enter',desc:'发送消息',action:'send'},
  {keys:'Esc',desc:'停止/关闭',action:'stop'},
  {keys:'1 - 5',desc:'切换仪表盘标签',action:'dashTab',scope:'dashboard'}
];

var _paletteCommands = [];
var _paletteOpen = false;
var _paletteIdx = -1;
var _paletteFiltered = [];

function registerCommand(name, description, category, action, shortcut) {
  _paletteCommands.push({name:name,description:description,category:category,action:action,shortcut:shortcut||''});
}

var commandPalette = {
  _built: false,

  init: function() {
    if (this._built) return;
    this._built = true;
    var self = this;

    // ── DOM 构建 ──
    this.overlay = document.createElement('div');
    this.overlay.className = 'palette-overlay';

    this.box = document.createElement('div');
    this.box.className = 'palette-box';

    this.input = document.createElement('input');
    this.input.className = 'palette-input';
    this.input.type = 'text';
    this.input.placeholder = t('palettePlaceholder');
    this.input.autocomplete = 'off';
    this.input.spellcheck = false;

    this.results = document.createElement('div');
    this.results.className = 'palette-results';

    this.footer = document.createElement('div');
    this.footer.className = 'palette-footer';
    this.footer.textContent = '↑↓ 导航  ↵ 选择  Esc 关闭';

    this.box.appendChild(this.input);
    this.box.appendChild(this.results);
    this.box.appendChild(this.footer);
    this.overlay.appendChild(this.box);
    document.body.appendChild(this.overlay);

    // ── 事件 ──
    this.overlay.addEventListener('click', function(e) {
      if (e.target === self.overlay) self.close();
    });

    this.input.addEventListener('input', function() { self._filter(); });
    this.input.addEventListener('keydown', function(e) { self._onKey(e); });

    this._registerDefaults();
    this._initGlobalKeys();
  },

  open: function() {
    if (!this._built) this.init();
    this.overlay.classList.add('on');
    this.input.value = '';
    this._paletteIdx = -1;
    this._filter();
    setTimeout(function() { commandPalette.input.focus(); }, 50);
  },

  close: function() {
    this.overlay.classList.remove('on');
    this._paletteIdx = -1;
    document.activeElement && document.activeElement.blur();
  },

  // ── 注册默认命令 ──
  _registerDefaults: function() {
    var self = this;
    var cmds = [
      {name:'agent', description:'浏览 Agent 列表，选择后跳转侧边栏', category:'导航', action:function() { self._showAgents(); }},
      {name:'skill', description:'浏览 Skill 列表，选择后跳转侧边栏 Skills', category:'导航', action:function() { self._showSkills(); }},
      {name:'新建面板', description:'创建新聊天面板', category:'面板', action:function() { self.close(); addPanel(); }, shortcut:'Ctrl+N'},
      {name:'关闭面板', description:'关闭当前聊天面板', category:'面板', action:function() { self.close(); removePanel(focusedPid); }, shortcut:'Ctrl+W'},
      {name:'清空对话', description:'清空所有面板聊天历史', category:'面板', action:function() { self.close(); clearAllPanels(); }},
      {name:'设置', description:'打开开发者设置面板', category:'导航', action:function() { self.close(); if (!devMode) toggleDevOverlay(); }, shortcut:'Ctrl+,'},
      {name:'仪表盘', description:'切换仪表盘显示', category:'导航', action:function() { self.close(); toggleDashboard(); }},
      {name:'演示模式', description:'进入 Demo 演示模式', category:'模式', action:function() { self.close(); _demoMode=true; if(typeof switchNav==='function')switchNav('agents'); loadAgents(); renderHistory(); renderDemoWelcome(); showToast('已进入 Demo 模式'); }},
      {name:'主题切换', keywords:['主题','theme','dark','light','颜色'], description:'切换亮色/暗色/高对比度主题', category:'外观', action:function() { self._toggleTheme(); }},
      {name:'导出配置', description:'导出当前配置到 JSON 文件', category:'工具', action:function() { self._exportConfig(); }},
      {name:'快捷键帮助', description:'列出所有键盘快捷键', category:'帮助', action:function() { self._showShortcutsHelp(); }, shortcut:'Ctrl+/'},
      {name:'智能调度', keywords:['调度','路由','route','orchestrate'], description:'分析任务并路由到最优 Agent', category:'导航', action:function() { self.close(); toggleOrchMode(); }},
      {name:'Agent 工厂', keywords:['创建','新建','factory','create','自定义'], description:'打开 Agent 工厂，创建自定义 Agent', category:'工具', action:function() { self.close(); if (!devMode) toggleDevOverlay(); setTimeout(function() { var el = document.getElementById('agent-factory-input'); if (el) { el.scrollIntoView({behavior:'smooth',block:'center'}); el.focus(); } }, 300); }},
      {name:'MCP 管理', description:'管理 MCP 服务器配置', category:'工具', action:function() { self.close(); if (!harnessActive) toggleDashboard(); setTimeout(function() { var tab = document.querySelector('.harness-overlay-tab[data-htab="mcp"]'); if (tab) tab.click(); }, 200); }},
      {name:'帮助文档', keywords:['帮助','help','文档','doc','?'], description:'查看功能帮助与快捷键', category:'帮助', action:function() { self.close(); toggleHelpOverlay(); }},
      {name:'检查更新', keywords:['更新','update','版本','version'], description:'检查 Agency 新版本', category:'工具', action:function() { self.close(); checkUpdate(); }},
      {name:'测试面板', description:'打开 Agent 测试面板', category:'工具', action:function() { self.close(); if (!harnessActive) toggleDashboard(); setTimeout(function() { var tab = document.querySelector('.harness-overlay-tab[data-htab="test"]'); if (tab) tab.click(); }, 200); }},
      {name:'切换标签', description:'在仪表盘标签页间切换', category:'导航', action:function() { self.close(); if (!harnessActive) { toggleDashboard(); } else { var tabs = document.querySelectorAll('.harness-overlay-tab'); var activeIdx = -1; for (var i = 0; i < tabs.length; i++) { if (tabs[i].classList.contains('active')) { activeIdx = i; break; } } var nextIdx = (activeIdx + 1) % tabs.length; if (tabs[nextIdx]) tabs[nextIdx].click(); } }},
      {name:'费用追踪', description:'查看 API 使用费用', category:'工具', action:function() { self.close(); showToast('费用追踪请前往终端执行: python maestro/cost-tracker.py'); }},
    ];
    for (var i = 0; i < cmds.length; i++) {
      registerCommand(cmds[i].name, cmds[i].description, cmds[i].category, cmds[i].action, cmds[i].shortcut);
    }
  },

  // ── 过滤 ──
  _filter: function() {
    var q = this.input.value.toLowerCase().trim();
    this.results.innerHTML = '';

    // 特殊处理：输入 "agent" — 直接列出 Agent
    if (q === 'agent' || q.indexOf('agent ') === 0) {
      this._renderAgentResults(q === 'agent' ? '' : q.slice(6).trim());
      return;
    }
    // 特殊处理：输入 "skill" — 直接列出 Skill
    if (q === 'skill' || q.indexOf('skill ') === 0) {
      this._renderSkillResults(q === 'skill' ? '' : q.slice(6).trim());
      return;
    }
    // 输入 "help" / "?" — 显示快捷键帮助
    if (q === 'help' || q === '?' || q === '快捷键') {
      this._showShortcutsHelp();
      return;
    }
    // 输入 "theme" / "主题" — 直接切换
    if (q === 'theme' || q === '主题') {
      this._toggleTheme();
      this.close();
      return;
    }
    // 输入 "export" / "导出" — 导出
    if (q === 'export' || q === '导出') {
      this._exportConfig();
      this.close();
      return;
    }
    // 输入 "clear" / "清空" — 清空
    if (q === 'clear' || q === '清空') {
      this.close();
      clearAllPanels();
      return;
    }
    // 输入 "demo" / "演示" — 演示模式
    if (q === 'demo' || q === '演示') {
      this.close();
      _demoMode = true;
      if(typeof switchNav==='function')switchNav('agents');
      loadAgents();
      renderHistory();
      renderDemoWelcome();
      showToast('已进入 Demo 模式');
      return;
    }
    // 输入 "dashboard" / "仪表盘" — 仪表盘
    if (q === 'dashboard' || q === '仪表盘') {
      this.close();
      toggleDashboard();
      return;
    }
    // 输入 "settings" / "设置" — 设置
    if (q === 'settings' || q === '设置') {
      this.close();
      if (!devMode) toggleDevOverlay();
      return;
    }
    // 输入 "new panel" / "新建面板"
    if (q === 'new panel' || q === '新建面板') {
      this.close();
      addPanel();
      return;
    }
    // 输入 "close panel" / "关闭面板"
    if (q === 'close panel' || q === '关闭面板') {
      this.close();
      if (panels.length > 1) removePanel(focusedPid);
      else showToast('至少保留一个面板');
      return;
    }

    // 通用模糊搜索
    var matched = [];
    for (var i = 0; i < _paletteCommands.length; i++) {
      var cmd = _paletteCommands[i];
      if (!q || cmd.name.toLowerCase().indexOf(q) >= 0 || cmd.description.toLowerCase().indexOf(q) >= 0 || cmd.category.toLowerCase().indexOf(q) >= 0 || (cmd.keywords || []).some(function(k) { return k.indexOf(q) !== -1; })) {
        matched.push(cmd);
      }
    }
    _paletteFiltered = matched;
    this._renderResults(matched, q);
  },

  // ── 渲染通用命令结果 ──
  _renderResults: function(items, query) {
    if (items.length === 0) {
      this.results.innerHTML = '<div class="palette-empty">' + t('paletteNoResults') + '</div>';
      return;
    }
    var self = this;
    var grouped = {};
    for (var i = 0; i < items.length; i++) {
      var cat = items[i].category || '其他';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(items[i]);
    }
    var cats = Object.keys(grouped);
    var idx = 0;
    for (var c = 0; c < cats.length; c++) {
      var catName = cats[c];
      var header = document.createElement('div');
      header.className = 'palette-category';
      header.textContent = catName;
      this.results.appendChild(header);

      for (var j = 0; j < grouped[catName].length; j++) {
        var item = grouped[catName][j];
        var row = document.createElement('div');
        row.className = 'palette-item';
        row.setAttribute('data-idx', idx);

        var nameHtml = this._highlight(item.name, query);
        var descHtml = this._highlight(item.description, query);
        var shortcutHtml = item.shortcut ? '<span class="palette-shortcut">' + escHtml(item.shortcut) + '</span>' : '';

        row.innerHTML = '<span class="palette-icon">▶</span><span class="palette-name">' + nameHtml + '</span><span class="palette-desc">— ' + descHtml + '</span>' + shortcutHtml;

        (function(item, idxVal) {
          row.addEventListener('click', function() { self._execute(item); });
        })(item, idx);

        this.results.appendChild(row);
        idx++;
      }
    }
  },

  // ── 渲染 Agent 结果 ──
  _renderAgentResults: function(filter) {
    var self = this;
    var list = (typeof agents !== 'undefined' ? agents : []).concat(typeof _demoMode !== 'undefined' && _demoMode ? getDemoAgents() : []);
    if (filter) list = list.filter(function(a) { return a.name.indexOf(filter) >= 0 || (a.description||'').indexOf(filter) >= 0; });
    if (list.length === 0) {
      this.results.innerHTML = '<div class="palette-empty">' + t('paletteNoResults') + '</div>';
      return;
    }
    _paletteFiltered = list;
    var header = document.createElement('div');
    header.className = 'palette-category';
    header.textContent = 'Agents (' + list.length + ')';
    this.results.appendChild(header);
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      var row = document.createElement('div');
      row.className = 'palette-item';
      row.setAttribute('data-idx', i);
      row.innerHTML = '<span class="palette-icon">🤖</span><span class="palette-name">' + escHtml(a.name) + '</span><span class="palette-desc">— ' + escHtml((a.description||'').slice(0, 60)) + '</span>';
      (function(agent) {
        row.addEventListener('click', function() { self.close(); self._jumpToAgent(agent.name); });
      })(a);
      this.results.appendChild(row);
    }
  },

  // ── 渲染 Skill 结果 ──
  _renderSkillResults: function(filter) {
    var self = this;
    var list = typeof allSkills !== 'undefined' ? allSkills : [];
    if (typeof _demoMode !== 'undefined' && _demoMode) list = getDemoSkills();
    if (filter) list = list.filter(function(s) { return s.name.indexOf(filter) >= 0 || (s.description||'').indexOf(filter) >= 0; });
    if (list.length === 0) {
      this.results.innerHTML = '<div class="palette-empty">' + t('paletteNoResults') + '</div>';
      return;
    }
    _paletteFiltered = list;
    var header = document.createElement('div');
    header.className = 'palette-category';
    header.textContent = 'Skills (' + list.length + ')';
    this.results.appendChild(header);
    for (var i = 0; i < list.length; i++) {
      var s = list[i];
      var row = document.createElement('div');
      row.className = 'palette-item';
      row.setAttribute('data-idx', i);
      row.innerHTML = '<span class="palette-icon">🧩</span><span class="palette-name">' + escHtml(s.name) + '</span><span class="palette-desc">— ' + escHtml((s.description||'').slice(0, 60)) + '</span>';
      (function(skill) {
        row.addEventListener('click', function() { self.close(); self._jumpToSkill(skill.name); });
      })(s);
      this.results.appendChild(row);
    }
  },

  // ── 快捷键帮助 ──
  _showShortcutsHelp: function() {
    this.results.innerHTML = '';
    var header = document.createElement('div');
    header.className = 'palette-category';
    header.textContent = '键盘快捷键';
    this.results.appendChild(header);
    for (var i = 0; i < KEYBOARD_SHORTCUTS.length; i++) {
      var ks = KEYBOARD_SHORTCUTS[i];
      var row = document.createElement('div');
      row.className = 'palette-item';
      row.innerHTML = '<span class="palette-icon">⌨</span><span class="palette-shortcut" style="min-width:100px">' + escHtml(ks.keys) + '</span><span class="palette-desc">' + escHtml(ks.desc) + '</span>';
      this.results.appendChild(row);
    }
  },

  // ── 高亮匹配文字 ──
  _highlight: function(text, query) {
    if (!query) return escHtml(text);
    var escaped = escHtml(text);
    var q = escHtml(query).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return escaped.replace(new RegExp('(' + q + ')', 'gi'), '<mark>$1</mark>');
  },

  // ── 键盘导航 ──
  _onKey: function(e) {
    var items = this.results.querySelectorAll('.palette-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this._paletteIdx = Math.min(this._paletteIdx + 1, items.length - 1);
      this._updateSelection(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this._paletteIdx = Math.max(this._paletteIdx - 1, 0);
      this._updateSelection(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      this._selectCurrent(items);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      this.close();
    }
  },

  _updateSelection: function(items) {
    for (var i = 0; i < items.length; i++) items[i].classList.remove('active');
    if (this._paletteIdx >= 0 && items[this._paletteIdx]) {
      items[this._paletteIdx].classList.add('active');
      items[this._paletteIdx].scrollIntoView({block:'nearest'});
    }
  },

  _selectCurrent: function(items) {
    if (this._paletteIdx >= 0 && items[this._paletteIdx]) {
      items[this._paletteIdx].click();
    } else if (this._paletteFiltered.length > 0) {
      // 没有选中项时执行第一个
      items[0] && items[0].click();
    }
  },

  _execute: function(cmd) {
    if (cmd && cmd.action) { this.close(); cmd.action(); }
  },

  // ── 跳转到侧边栏 Agent ──
  _jumpToAgent: function(name) {
    if(typeof switchNav==='function')switchNav('agents');
    // 搜索框中填入 agent 名以过滤
    var searchInput = document.getElementById('agent-search');
    if (searchInput) {
      searchInput.value = name;
      searchInput.dispatchEvent(new Event('input'));
      searchInput.focus();
    }
    // 高亮第一个匹配卡片
    setTimeout(function() {
      var cards = document.querySelectorAll('.agent-card');
      for (var i = 0; i < cards.length; i++) {
        var n = cards[i].querySelector('.name');
        if (n && n.textContent.indexOf(name) === 0) {
          cards[i].style.transition = 'all .3s';
          cards[i].style.borderColor = 'var(--accent)';
          cards[i].style.background = 'rgba(16,185,129,.12)';
          cards[i].scrollIntoView({block:'center'});
          setTimeout(function() { cards[i].style.borderColor = ''; cards[i].style.background = ''; }, 2000);
          break;
        }
      }
    }, 150);
  },

  // ── 跳转到侧边栏 Skill ──
  _jumpToSkill: function(name) {
    if(typeof switchNav==='function')switchNav('agents');
    if (typeof loadSidebarSkills === 'function') loadSidebarSkills();
    setTimeout(function() {
      var cards = document.querySelectorAll('.skill-card');
      for (var i = 0; i < cards.length; i++) {
        var divs = cards[i].querySelectorAll('div');
        if (divs.length > 0 && divs[0].textContent.trim() === name) {
          cards[i].style.transition = 'all .3s';
          cards[i].style.background = 'rgba(16,185,129,.12)';
          cards[i].scrollIntoView({block:'center'});
          setTimeout(function() { cards[i].style.background = ''; }, 2000);
          break;
        }
      }
    }, 300);
  },

  // ── 主题切换 ──
  _toggleTheme: function() {
    var html = document.documentElement;
    var themes = ['dark', 'light', 'high-contrast'];
    var cur = html.getAttribute('data-theme') || 'dark';
    var idx = themes.indexOf(cur);
    var next = themes[(idx + 1) % themes.length];
    html.setAttribute('data-theme', next);
    try { localStorage.setItem('agency_theme', next); } catch(e) {}
    var labels = {dark:'暗色', light:'亮色', 'high-contrast':'高对比度'};
    showToast('主题: ' + (labels[next] || next));
  },

  // ── 导出配置 ──
  _exportConfig: function() {
    var config = {
      theme: document.documentElement.getAttribute('data-theme') || 'dark',
      provider: apiProvider,
      profile: agencyProfile,
      projDir: projDir,
      outputDir: outputDir,
      version: '1.0',
      exportedAt: new Date().toISOString()
    };
    var blob = new Blob([JSON.stringify(config, null, 2)], {type:'application/json'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'agency-config-' + new Date().toISOString().slice(0,10) + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('配置已导出');
  },

  // ── 全局快捷键监听 ──
  _initGlobalKeys: function() {
    var self = this;
    this._keyHandler = function(e) {
      var custom = {};
      try{ custom = JSON.parse(localStorage.getItem('custom_shortcuts') || '{}'); }catch(e){}
      function matchShortcut(action, defaultKeys){
        var keys = custom[action] || defaultKeys;
        var parts = keys.split('+');
        var ctrl = parts.indexOf('Ctrl') >= 0;
        var alt = parts.indexOf('Alt') >= 0;
        var shift = parts.indexOf('Shift') >= 0;
        var keyPart = parts[parts.length-1];
        var eKey = e.key;
        if(eKey === ' ' && keyPart === 'Space') eKey = 'Space';
        if((e.ctrlKey||e.metaKey)===ctrl && e.altKey===alt && e.shiftKey===shift && eKey===keyPart) return true;
        return false;
      }
      // 使用自定义快捷键匹配
      if (matchShortcut('palette', 'Ctrl+K')) {
        e.preventDefault();
        self.open();
        return;
      }
      if (matchShortcut('settings', 'Ctrl+,')) {
        e.preventDefault();
        if (!devMode) toggleDevOverlay();
        return;
      }
      if (matchShortcut('help', 'Ctrl+/')) {
        e.preventDefault();
        self.open();
        self.input.value = '快捷键';
        self._filter();
        return;
      }
      if (matchShortcut('newPanel', 'Ctrl+N') && !e.shiftKey) {
        if (document.activeElement && document.activeElement.tagName === 'TEXTAREA') return;
        e.preventDefault();
        addPanel();
        return;
      }
      if (matchShortcut('closePanel', 'Ctrl+W')) {
        e.preventDefault();
        if (panels.length > 1) removePanel(focusedPid);
        return;
      }
      if (matchShortcut('send', 'Ctrl+Enter')) {
        if (document.activeElement && document.activeElement.tagName === 'TEXTAREA') {
          var panel = getFocusedPanel();
          if (panel && panel.dom && panel.dom.input === document.activeElement) {
            e.preventDefault();
            handleSend(panel.id);
            return;
          }
        }
      }
      // Esc — 关闭弹窗 / 停止 SSE
      if (e.key === 'Escape' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        if (self.overlay.classList.contains('on')) {
          self.close();
          return;
        }
        var overlays = document.querySelectorAll('.agent-prompt-overlay.on, .confirm-overlay');
        if (overlays.length > 0) {
          overlays[overlays.length-1].classList.remove('on');
          var confirmEl = document.querySelector('.confirm-overlay');
          if (confirmEl) confirmEl.remove();
          return;
        }
        if (focusedPid) {
          var fp = panels.find(function(x) { return x.id === focusedPid; });
          if (fp && fp.isStreaming) {
            stopStream(focusedPid);
            return;
          }
        }
      }
    };
    document.addEventListener('keydown', this._keyHandler);
  },

  // ── 供外部调用的快捷方法 ──
  _showAgents: function() {
    this.input.value = 'agent ';
    this._filter();
  },
  _showSkills: function() {
    this.input.value = 'skill ';
    this._filter();
  }
};

/* ── 快捷键绑定更新（供 settings.js 调用）── */
function updateShortcutBindings(){
  if(commandPalette._keyHandler){
    document.removeEventListener('keydown', commandPalette._keyHandler);
  }
  commandPalette._initGlobalKeys();
}

// ── 页面加载后初始化 ──
(function() {
  // 恢复已保存主题
  try {
    var savedTheme = localStorage.getItem('agency_theme');
    if (savedTheme) document.documentElement.setAttribute('data-theme', savedTheme);
  } catch(e) {}
  // 延迟初始化，确保其他模块已就绪
  setTimeout(function() { commandPalette.init(); }, 200);
})();

export { KEYBOARD_SHORTCUTS, registerCommand, commandPalette, updateShortcutBindings };
