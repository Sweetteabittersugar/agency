/* Agency — 编排服务 (Round 4: 多阶段编排管线) */
(function() {
  'use strict';

  /**
   * 执行编排任务
   * @param {string} task - 任务描述
   * @param {object} callbacks
   * @param {function} callbacks.onPlan - (plan: object) => void
   * @param {function} callbacks.onStage - (stage: string, progress: number) => void
   * @param {function} callbacks.onContent - (chunk: string) => void
   * @param {function} callbacks.onDone - (result: object) => void
   * @param {function} callbacks.onError - (error: Error) => void
   * @param {AbortSignal} [options.signal]
   */
  function executeOrchestrate(task, callbacks, options) {
    options = options || {};
    callbacks = callbacks || {};

    let fetchOpts = {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        task: task,
        api_key: (typeof apiKey !== 'undefined' ? apiKey : ''),
        api_provider: (typeof apiProvider !== 'undefined' ? apiProvider : 'deepseek'),
        proj_dir: (typeof projDir !== 'undefined' ? projDir : '') || undefined,
        profile: (typeof agencyProfile !== 'undefined' ? agencyProfile : 'standard') || 'standard'
      })
    };
    if (options.signal) fetchOpts.signal = options.signal;

    return fetch('/api/orchestrate', fetchOpts)
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.body.getReader();
      })
      .then(function(reader) {
        let decoder = new TextDecoder();
        let buffer = '';

        function pump() {
          return reader.read().then(function(result) {
            if (result.done) {
              if (callbacks.onDone) callbacks.onDone({});
              return;
            }
            buffer += decoder.decode(result.value, {stream: true});
            let lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (let i = 0; i < lines.length; i++) {
              let line = lines[i].trim();
              if (!line || !line.startsWith('data: ')) continue;
              let data = line.slice(6);
              if (data === '[DONE]') {
                if (callbacks.onDone) callbacks.onDone({});
                return;
              }
              try {
                let evt = JSON.parse(data);
                if (evt.type === 'plan' && callbacks.onPlan) {
                  callbacks.onPlan(evt);
                } else if (evt.type === 'stage' && callbacks.onStage) {
                  callbacks.onStage(evt.stage, evt.progress || 0);
                } else if ((evt.type === 'content' || evt.content) && callbacks.onContent) {
                  callbacks.onContent(evt.content || evt.text || data);
                } else if (evt.type === 'done' || evt.done) {
                  if (callbacks.onDone) callbacks.onDone(evt);
                  return;
                }
              } catch(e) {
                if (callbacks.onContent) callbacks.onContent(data);
              }
            }
            return pump();
          });
        }
        return pump();
      })
      .catch(function(err) {
        if (err.name === 'AbortError') return;
        if (callbacks.onError) callbacks.onError(err);
      });
  }

  window.OrchestrationService = {
    execute: executeOrchestrate
  };
})();
