/* Agency — 聊天 SSE 服务 (Round 4: SSE流式/超时/排队逻辑) */

/**
 * ChatSession — 管理单个面板的 SSE 聊天生命周期
 *
 * Usage:
 *   let session = new ChatSession(panelId, { onContent, onRoute, onDone, onError, onProgress });
 *   session.send(taskText);
 *   session.stop();
 */
(function() {
  'use strict';

  let TIMEOUT_MS = 300000; // 5 分钟超时
  let SSE_MAX_RETRIES = 3;

  /**
   * @param {number} panelId
   * @param {object} callbacks
   * @param {function} callbacks.onRoute - (routeInfo: RouteInfo) => void
   * @param {function} callbacks.onContent - (chunk: string) => void
   * @param {function} callbacks.onDone - (stats: DoneStats) => void
   * @param {function} callbacks.onError - (error: Error) => void
   * @param {function} [callbacks.onProgress] - (stage: string, msg: string, agent?: string) => void
   */
  function ChatSession(panelId, callbacks) {
    this.panelId = panelId;
    this.cb = callbacks || {};
    this.state = 'idle'; // idle | routing | streaming | done | error
    this.abortController = null;
    this._reader = null;
    this._timeoutId = null;
    this._sseRetries = 0;
    this._receivedDone = false;
    this._sendLock = false;
    this._msgQueue = [];
    this._lastTask = '';
  }

  ChatSession.prototype.send = function(task, options) {
    options = options || {};
    let self = this;

    if (self._sendLock) return;
    self._sendLock = true;
    setTimeout(function() { self._sendLock = false; }, 3000);

    if (self.state === 'streaming') {
      self._msgQueue.push(task);
      return;
    }

    if (self.state === 'streaming') {
      self.stop();
      return;
    }

    self._lastTask = task;
    self.state = 'routing';
    self.abortController = new AbortController();
    self._sseRetries = 0;
    self._receivedDone = false;

    // 路由
    let isOrch = options.isOrchMode && !options.forceAgent;
    let routePromise = isOrch
      ? Promise.resolve({ agent: '', model: '', confidence: 100, source: 'orch', category: '总调度', keywordScore: 100, semanticScore: 0 })
      : RoutingService.computeRoute(task, {
          forceAgent: options.forceAgent,
          signal: self.abortController.signal
        });

    routePromise.then(function(route) {
      if (self.cb.onRoute) self.cb.onRoute(route);
      self._startSSE(task, route);
    }).catch(function(err) {
      if (err.name === 'AbortError') return;
      self.state = 'error';
      if (self.cb.onError) self.cb.onError(err);
    });
  };

  ChatSession.prototype._startSSE = function(task, route) {
    let self = this;
    self.state = 'streaming';

    // 超时计时器
    self._timeoutId = setTimeout(function() {
      if (!self._receivedDone && self.state === 'streaming') {
        self.stop();
        self.state = 'error';
        if (self.cb.onError) self.cb.onError(new Error('任务超时（5分钟）'));
      }
    }, TIMEOUT_MS);

    let body = {
      task: task,
      api_key: (typeof apiKey !== 'undefined' ? apiKey : ''),
      api_provider: (typeof apiProvider !== 'undefined' ? apiProvider : 'deepseek'),
      force_agent: route.agent || undefined,
      model: route.model || undefined,
      proj_dir: (typeof projDir !== 'undefined' ? projDir : '') || undefined,
      profile: (typeof agencyProfile !== 'undefined' ? agencyProfile : 'standard') || 'standard'
    };

    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: self.abortController.signal
    }).then(function(response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      self._reader = response.body.getReader();
      return self._readSSEStream();
    }).catch(function(err) {
      if (err.name === 'AbortError') return;
      if (self._sseRetries < SSE_MAX_RETRIES) {
        self._sseRetries++;
        let delay = Math.min(1000 * Math.pow(2, self._sseRetries), 15000);
        setTimeout(function() { self._startSSE(task, route); }, delay);
      } else {
        self.state = 'error';
        if (self.cb.onError) self.cb.onError(err);
      }
    });
  };

  ChatSession.prototype._readSSEStream = function() {
    let self = this;
    let decoder = new TextDecoder();
    let buffer = '';

    function pump() {
      self._reader.read().then(function(result) {
        if (result.done) {
          if (!self._receivedDone) {
            self._receivedDone = true;
            self.state = 'done';
            if (self._timeoutId) clearTimeout(self._timeoutId);
            if (self.cb.onDone) self.cb.onDone({ elapsed: 0 });
          }
          return;
        }

        buffer += decoder.decode(result.value, { stream: true });
        let lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (let i = 0; i < lines.length; i++) {
          let line = lines[i].trim();
          if (!line || !line.startsWith('data: ')) continue;
          let data = line.slice(6);
          if (data === '[DONE]') {
            self._receivedDone = true;
            self.state = 'done';
            if (self._timeoutId) clearTimeout(self._timeoutId);
            // Parse stats from data if available
            if (self.cb.onDone) self.cb.onDone({ elapsed: 0, content: '' });
            return;
          }
          try {
            let parsed = JSON.parse(data);
            if (parsed.type === 'content' || parsed.content) {
              if (self.cb.onContent) self.cb.onContent(parsed.content || parsed.text || data);
            } else if (parsed.type === 'done' || parsed.done) {
              self._receivedDone = true;
              self.state = 'done';
              if (self._timeoutId) clearTimeout(self._timeoutId);
              if (self.cb.onDone) self.cb.onDone(parsed);
              return;
            }
          } catch(e) {
            // Plain text content
            if (self.cb.onContent) self.cb.onContent(data);
          }
        }
        pump();
      }).catch(function(err) {
        if (err.name === 'AbortError') return;
        console.error('SSE 读取错误:', err);
        self.state = 'error';
        if (self.cb.onError) self.cb.onError(err);
      });
    }
    pump();
  };

  ChatSession.prototype.stop = function() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    if (this._reader) {
      try { this._reader.cancel(); } catch(_) {}
      this._reader = null;
    }
    if (this._timeoutId) {
      clearTimeout(this._timeoutId);
      this._timeoutId = null;
    }
    this.state = 'idle';
    this._processQueue();
  };

  ChatSession.prototype._processQueue = function() {
    if (this._msgQueue.length > 0) {
      let next = this._msgQueue.shift();
      setTimeout(function(self, task) { self.send(task); }, 200, this, next);
    }
  };

  ChatSession.prototype.destroy = function() {
    this.stop();
    this.cb = {};
    this._msgQueue = [];
  };

  window.ChatSession = ChatSession;
})();
