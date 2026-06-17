/* Agency — 工作流模板 (Round 3: 从 utils.js 剥离) */
(function() {
  'use strict';

  let WORKFLOW_TEMPLATES = [
    {icon:'🆕',label:{zh:'写新功能',en:'New Feature'},content:'@coder 请帮我实现以下功能：\n功能描述：\n技术栈：\n具体要求：'},
    {icon:'🐛',label:{zh:'修 Bug',en:'Fix Bug'},content:'@coder 请修复以下 Bug：\nBug 描述：\n复现步骤：\n期望行为：'},
    {icon:'🔍',label:{zh:'代码审查',en:'Code Review'},content:'@reviewer 请审查以下代码，重点关注：\n1. 安全问题\n2. 性能问题\n3. 代码规范'},
    {icon:'🧪',label:{zh:'写测试',en:'Write Tests'},content:'@test 请为以下代码编写测试：\n测试框架：\n覆盖要求：'},
    {icon:'📚',label:{zh:'搜索资料',en:'Search'},content:'@explorer 请搜索以下内容：\n关键词：\n范围：\n格式要求：'},
    {icon:'⚡',label:{zh:'性能分析',en:'Performance'},content:'@coder 请分析以下代码的性能瓶颈：\n场景：\n数据量：'}
  ];

  function getCustomTemplates() {
    try { return JSON.parse(localStorage.getItem('agency_custom_templates') || '[]'); } catch(e) { console.warn('加载自定义模板失败:',e); return []; }
  }

  function saveCustomTemplates(list) {
    localStorage.setItem('agency_custom_templates', JSON.stringify(list));
  }

  function getAllTemplates() {
    return WORKFLOW_TEMPLATES.concat(getCustomTemplates());
  }

  window.WORKFLOW_TEMPLATES = WORKFLOW_TEMPLATES;
  window.getCustomTemplates = getCustomTemplates;
  window.saveCustomTemplates = saveCustomTemplates;
  window.getAllTemplates = getAllTemplates;
})();
