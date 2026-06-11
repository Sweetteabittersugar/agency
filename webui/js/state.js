/* 集中状态管理 — 与现有全局变量共存，供新代码使用 */
(function() {
  'use strict';

  // ===== 状态定义 =====
  var _state = {
    // 面板
    panels: [],
    perPage: 4,
    curPage: 1,
    focusedPid: null,

    // Agent
    agents: [],
    allSkills: [],
    selectedAgents: [],
    multiSelectMode: false,

    // 会话
    conversations: {},

    // API
    apiKey: '',
    apiProvider: 'deepseek',
    authToken: '',

    // UI
    theme: 'dark',
    devMode: false,
    orchMode: false,
    demoMode: false,
    sidebarTab: 'agents',
    layout: 1,

    // 设置
    agencyProfile: 'balanced',
    outputDir: '',
    lang: 'zh',

    // 功能门控
    unlockOverrides: {}
  };

  // ===== 订阅者 =====
  var _listeners = {};

  /**
   * 获取状态（返回副本，不可直接修改）
   */
  function getState(key) {
    if (key) {
      var val = _state[key];
      return (val && typeof val === 'object' && !Array.isArray(val))
        ? Object.assign({}, val)
        : (Array.isArray(val) ? val.slice() : val);
    }
    return JSON.parse(JSON.stringify(_state));
  }

  /**
   * 更新状态（合并模式）
   * Store.set('theme', 'light')
   * Store.set({theme: 'light', layout: 2})
   */
  function setState(key, value) {
    var changes = {};

    if (typeof key === 'object') {
      changes = key;
    } else {
      changes[key] = value;
    }

    var changedKeys = [];
    for (var k in changes) {
      if (changes.hasOwnProperty(k) && _state.hasOwnProperty(k)) {
        var oldVal = _state[k];
        var newVal = changes[k];
        if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
          _state[k] = newVal;
          changedKeys.push(k);

          // 同步到现有全局变量（向后兼容）
          if (window[k] !== undefined && k !== 'theme' && k !== 'layout') {
            try { window[k] = newVal; } catch(e) {}
          }
        }
      }
    }

    // 通知订阅者
    changedKeys.forEach(function(k) {
      if (_listeners[k]) {
        _listeners[k].forEach(function(fn) {
          try { fn(_state[k], k); } catch(e) { console.warn('Store listener error:', k, e); }
        });
      }
      if (_listeners['*']) {
        _listeners['*'].forEach(function(fn) {
          try { fn(_state, k); } catch(e) {}
        });
      }
    });

    // 持久化到 localStorage
    _persist(changedKeys);
  }

  /**
   * 订阅状态变化
   * Store.on('theme', function(newVal, key) { ... })
   * Store.on('*', function(fullState, changedKey) { ... })  // 监听所有变化
   */
  function on(key, fn) {
    if (!_listeners[key]) _listeners[key] = [];
    _listeners[key].push(fn);
    return function unsubscribe() {
      var idx = _listeners[key].indexOf(fn);
      if (idx >= 0) _listeners[key].splice(idx, 1);
    };
  }

  /**
   * 一次性监听
   */
  function once(key, fn) {
    var unsub = on(key, function(val, k) {
      unsub();
      fn(val, k);
    });
  }

  // ===== 持久化 =====
  var PERSIST_KEYS = ['theme', 'lang', 'layout', 'agencyProfile', 'devMode', 'apiProvider', 'outputDir'];

  function _persist(keys) {
    keys.forEach(function(k) {
      if (PERSIST_KEYS.indexOf(k) >= 0) {
        try {
          var val = _state[k];
          localStorage.setItem('agency-' + k, typeof val === 'object' ? JSON.stringify(val) : String(val));
        } catch(e) {}
      }
    });
  }

  /**
   * 从 localStorage 恢复持久化状态
   */
  function restore() {
    PERSIST_KEYS.forEach(function(k) {
      try {
        var raw = localStorage.getItem('agency-' + k);
        if (raw !== null) {
          try { _state[k] = JSON.parse(raw); } catch(e) { _state[k] = raw; }
        }
      } catch(e) {}
    });
  }

  /**
   * 与现有全局变量同步（页面加载时调用一次）
   */
  function syncFromGlobals() {
    var keys = ['panels', 'agents', 'apiKey', 'apiProvider', 'authToken',
                'outputDir', 'agencyProfile', 'devMode', 'orchMode'];
    keys.forEach(function(k) {
      if (window[k] !== undefined) {
        _state[k] = window[k];
      }
    });
  }

  // ===== 导出 =====
  window.Store = {
    get: getState,
    set: setState,
    on: on,
    once: once,
    restore: restore,
    syncFromGlobals: syncFromGlobals,
    // 调试：打印当前全部状态
    dump: function() { console.table(_state); }
  };

  // 启动时恢复
  restore();

})();

const Store = window.Store;