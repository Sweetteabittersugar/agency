/* 统一 API 客户端 — 集中 fetch、错误处理、缓存 */
(function() {
  'use strict';

  var BASE = '';
  var pendingRequests = {};
  var cache = {};
  var CACHE_TTL = 30000; // 30秒缓存

  function resolveUrl(path) {
    return BASE + (path.startsWith('/') ? path : '/' + path);
  }

  // 请求去重：相同 URL+method 的并发请求合并
  function requestKey(method, url, body) {
    return method + ':' + url + (body ? ':' + JSON.stringify(body) : '');
  }

  function api(method, path, body, opts) {
    opts = opts || {};
    var url = resolveUrl(path);
    var key = requestKey(method, url, body);

    // 去重
    if (pendingRequests[key]) { return pendingRequests[key]; }

    // GET 缓存
    if (method === 'GET' && !opts.noCache) {
      var cached = cache[key];
      if (cached && (Date.now() - cached.ts < CACHE_TTL)) {
        return Promise.resolve(cached.data);
      }
    }

    var fetchOpts = { method: method, headers: {'Content-Type': 'application/json'} };
    if (body) { fetchOpts.body = JSON.stringify(body); }

    var promise = fetch(url, fetchOpts)
      .then(function(r) {
        if (!r.ok) {
          return r.json().then(function(d) { throw new ApiError(r.status, d.error || r.statusText, d); });
        }
        return r.json();
      })
      .then(function(data) {
        if (method === 'GET' && !opts.noCache) {
          cache[key] = { data: data, ts: Date.now() };
        }
        return data;
      })
      .finally(function() {
        delete pendingRequests[key];
      });

    pendingRequests[key] = promise;
    return promise;
  }

  function ApiError(status, message, data) {
    this.status = status;
    this.message = message;
    this.data = data;
  }
  ApiError.prototype = Object.create(Error.prototype);

  // 公共 API
  window.api = {
    get: function(path, opts) { return api('GET', path, null, opts); },
    post: function(path, body, opts) { return api('POST', path, body, opts); },
    del: function(path, opts) { return api('DELETE', path, null, opts); },

    // 清缓存（配置变更后调用）
    clearCache: function() { cache = {}; },

    // 错误判断辅助
    isNotFound: function(err) { return err instanceof ApiError && err.status === 404; },
    isAuthError: function(err) { return err instanceof ApiError && (err.status === 401 || err.status === 403); }
  };
})();

const api = window.api;