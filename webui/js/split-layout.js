// 多面板分屏布局管理
(function() {
  'use strict';

  var _currentLayout = 1;

  window.setLayout = function(n) {
    _currentLayout = n;
    perPage = n;

    // 确保面板足够
    while (panels.length < n) { addPanel(); }

    // 清除旧分割条
    grid.querySelectorAll('.split-gutter').forEach(function(g) { g.remove(); });

    if (n === 4) {
      // 田字格: CSS grid 2x2
      grid.style.display = '';
      grid.style.flexWrap = '';
      grid.className = 'grid g4';
      panels.forEach(function(p, i) {
        var w = p.dom.wrapper;
        w.style.width = ''; w.style.height = ''; w.style.flex = '';
        w.style.borderRight = (i % 2 === 0) ? '' : 'none';
        w.classList.toggle('on', i < 4);
      });
    } else if (n === 2) {
      // 双分屏: flex + 分割条
      grid.style.display = 'flex';
      grid.style.flexWrap = 'nowrap';
      grid.className = 'grid';
      panels.forEach(function(p, i) {
        var w = p.dom.wrapper;
        w.style.flex = 'none';
        w.style.width = 'calc(50% - 2px)';
        w.style.height = '';
        w.style.borderRight = 'none';
        w.classList.toggle('on', i < 2);
      });
      // 插入分割条
      var p0 = panels[0] && panels[0].dom.wrapper;
      if (p0 && p0.nextSibling) {
        var g = document.createElement('div');
        g.className = 'split-gutter';
        g.style.display = 'block';
        p0.parentNode.insertBefore(g, p0.nextSibling);
      }
    } else {
      // 单面板
      grid.style.display = 'flex';
      grid.style.flexWrap = 'nowrap';
      grid.className = 'grid';
      panels.forEach(function(p, i) {
        var w = p.dom.wrapper;
        w.style.flex = i === 0 ? '1' : 'none';
        w.style.width = ''; w.style.height = ''; w.style.borderRight = '';
        w.classList.toggle('on', i === 0);
      });
    }

    pageBar.style.display = 'flex';
    curPage = 0;
    updateLayoutButtons(n);
    // 隐藏旧分页按钮（如果还有的话）
    var pgPrev = document.getElementById('pgPrev');
    var pgNext = document.getElementById('pgNext');
    if (pgPrev) pgPrev.style.display = 'none';
    if (pgNext) pgNext.style.display = 'none';
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

    // 恢复上次布局
    var saved = parseInt(localStorage.getItem('agency_layout'));
    if (saved >= 1 && saved <= 4) {
      setLayout(saved);
    }
  }

  // 扩展 addPanel — 新面板也加 Agent 下拉
  var _origAddPanel = window.addPanel;
  window.addPanel = function() {
    var p = _origAddPanel();
    setTimeout(populateAgentSelects, 200);
    return p;
  };

  // 扩展 refreshUI — 不再分页，清理残留分割条，重排面板
  var _origRefreshUI = window.refreshUI;
  window.refreshUI = function() {
    // 面板不足时降级布局
    if (panels.length < _currentLayout && _currentLayout > 1) {
      var fallback = panels.length >= 4 ? 4 : panels.length >= 2 ? 2 : 1;
      _currentLayout = fallback;
      perPage = fallback;
      updateLayoutButtons(fallback);
    }
    // 清理所有分割条，重新应用布局（处理面板增删后的 DOM 残留）
    grid.querySelectorAll('.split-gutter').forEach(function(g) { g.remove(); });
    if (_currentLayout === 2 && panels.length >= 2) {
      var p0w = panels[0] && panels[0].dom.wrapper;
      if (p0w && p0w.parentNode) {
        var gutter = document.createElement('div');
        gutter.className = 'split-gutter';
        gutter.style.display = 'block';
        p0w.parentNode.insertBefore(gutter, p0w.nextSibling);
      }
    }

    pageBar.style.display = 'flex';
    var gb2 = document.getElementById('gridBtn');
    if (gb2) gb2.textContent = '⊞';
    var sumEl = document.getElementById('summary');
    if (sumEl) sumEl.textContent = panels.length + '窗';
    var pgPrev = document.getElementById('pgPrev');
    var pgNext = document.getElementById('pgNext');
    var pgNum = document.getElementById('pgNum');
    if (pgPrev) pgPrev.style.display = 'none';
    if (pgNext) pgNext.style.display = 'none';
    if (pgNum) pgNum.style.display = 'none';
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

const setLayout = window.setLayout;
const onPanelAgentChange = window.onPanelAgentChange;
export { setLayout, onPanelAgentChange };
