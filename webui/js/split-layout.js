// 多面板分屏布局管理
(function() {
  'use strict';

  var _currentLayout = 1;

  window.setLayout = function(n) {
    _currentLayout = n;
    perPage = n;
    curPage = 0;

    // 清除旧分割条 + 内联样式，统一用 CSS Grid 管理布局
    grid.querySelectorAll('.split-gutter').forEach(function(g) { g.remove(); });
    grid.style.display = '';
    grid.style.flexWrap = '';
    grid.className = 'grid g' + n;
    panels.forEach(function(p) {
      var w = p.dom.wrapper;
      w.style.flex = ''; w.style.width = ''; w.style.height = ''; w.style.borderRight = '';
    });

    // 面板可见性统一由 refreshUI 管理
    if (typeof refreshUI === 'function') refreshUI();
    try { localStorage.setItem('agency_layout', n); } catch(e) {}
  };

  function updateLayoutButtons(active) {
    var btns = pageBar.querySelectorAll('.layout-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle('active', parseInt(btns[i].dataset.layout) === active);
    }
  }

  // 填充 Agent 下拉框
  function populateAgentSelects() {
    function fill(arr) {
      var opts = arr.map(function(a) {
        return '<option value="' + escAttr(a.name) + '">' + escHtml(a.name) + '</option>';
      }).join('');
      for (var i = 0; i < panels.length; i++) {
        var sel = panels[i].dom.wrapper.querySelector('.panel-agent-select');
        if (sel) { sel.innerHTML = '<option value="">Agent...</option>' + opts; }
      }
    }
    if (typeof agents !== 'undefined' && agents.length) {
      fill(agents);
    } else {
      fetch('/api/agents')
        .then(function(r) { return r.json(); })
        .then(function(d) {
          var arr = Array.isArray(d) ? d : (d.agents || d.data || []);
          if (arr.length) fill(arr);
        }).catch(function() {});
    }
  }

  // Agent 选择变更 — 填入 @agent 前缀
  window.onPanelAgentChange = function(pid, selectEl) {
    var v = selectEl.value;
    if (!v) return;
    var p = panels.find(function(x) { return x.id === pid; });
    if (!p) return;
    p.dom.input.value = '@' + v + ' ' + p.dom.input.value.replace(/^@\S+\s*/, '');
    p.dom.input.focus();
    p.dom.sendBtn.disabled = !p.dom.input.value.trim();
    selectEl.value = '';
  };

  // 分割条拖拽
  function initGutterDrag() {
    grid.addEventListener('mousedown', function(e) {
      var gutter = e.target.closest('.split-gutter');
      if (!gutter) return;
      e.preventDefault();
      gutter.classList.add('dragging');

      var startX = e.clientX;
      var prev = gutter.previousElementSibling;
      var next = gutter.nextElementSibling;
      if (!prev || !next) return;
      var prevW = prev.getBoundingClientRect().width;
      var nextW = next.getBoundingClientRect().width;
      var totalW = prevW + nextW;

      function onMove(ev) {
        var dx = ev.clientX - startX;
        var newPrev = Math.max(200, Math.min(totalW - 200, prevW + dx));
        var newNext = totalW - newPrev;
        prev.style.width = newPrev + 'px';
        next.style.width = newNext + 'px';
      }
      function onUp() {
        gutter.classList.remove('dragging');
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      }
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  // 初始化
  function init() {
    initGutterDrag();

    // 延迟填充 Agent 下拉框
    setTimeout(function() {
      populateAgentSelects();
      // 监听 agents 加载完成后重新填充
      var origRenderAgents = window.renderAgents;
      if (typeof origRenderAgents === 'function') {
        var wrapped = function(list) {
          origRenderAgents(list);
          agents = list;
          populateAgentSelects();
        };
        window.renderAgents = wrapped;
      }
    }, 800);

    // 布局偏好暂存，等 app.js 会话恢复完成后再应用
    // 直接恢复布局会与会话恢复冲突，导致多面板内容丢失
    window._pendingLayout = parseInt(localStorage.getItem('agency_layout')) || 1;

    // 首次使用多面板提示（仅提示一次）
    var hintShown = localStorage.getItem('split-hint-shown');
    if (!hintShown && _currentLayout === 1) {
      setTimeout(function() {
        showToast('💡 试试多面板分屏？点击工具栏 ⊞ 切换布局', false);
        try { localStorage.setItem('split-hint-shown', '1'); } catch(e) {}
      }, 10000);
    }
  }

  // 扩展 addPanel — 新面板也加 Agent 下拉
  var _origAddPanel = window.addPanel;
  window.addPanel = function() {
    var p = _origAddPanel();
    setTimeout(populateAgentSelects, 200);
    return p;
  };


  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

const setLayout = window.setLayout;
const onPanelAgentChange = window.onPanelAgentChange;