/* Agency — 路由服务 (Round 4: 从 chat.js 抽取路由调用) */
(function() {
  'use strict';

  /**
   * 调用 /api/route 获取路由决策
   * @param {string} task - 用户任务文本
   * @param {object} options
   * @param {string} [options.forceAgent] - 强制指定 Agent
   * @param {string} [options.projDir] - 项目目录
   * @param {AbortSignal} [options.signal] - 取消信号
   * @returns {Promise<RouteInfo>}
   */
  function computeRoute(task, options) {
    options = options || {};
    let fetchOpts = {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        task: task,
        force_agent: options.forceAgent || undefined,
        proj_dir: options.projDir || undefined,
        api_key: (typeof apiKey !== 'undefined' ? apiKey : '') || undefined,
        api_provider: (typeof apiProvider !== 'undefined' ? apiProvider : 'deepseek') || undefined,
        profile: (typeof agencyProfile !== 'undefined' ? agencyProfile : 'standard') || 'standard',
        output_dir: localStorage.getItem('agency_output_dir') || undefined
      })
    };
    if (options.signal) fetchOpts.signal = options.signal;

    return fetch('/api/route', fetchOpts)
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.error) throw new Error(d.error);
        return {
          agent: d.agent || 'auto',
          model: d.model || '',
          confidence: (d.confidence || 0) * 100,
          source: d.source || 'keyword',
          category: d.category || '',
          keywordScore: (d.keyword_score || 0) * 100,
          semanticScore: (d.semantic_score || 0) * 100,
          raw: d
        };
      });
  }

  /**
   * 提交路由纠错反馈
   */
  function submitRouteFeedback(task, originalAgent, correctedAgent) {
    return api.post('/api/routing/feedback', {
      task: task,
      original_agent: originalAgent,
      corrected_agent: correctedAgent,
      reason: '用户手动纠正'
    }).catch(function(e) { console.error('路由反馈提交失败:', e); });
  }

  window.RoutingService = {
    computeRoute: computeRoute,
    submitRouteFeedback: submitRouteFeedback
  };
})();
