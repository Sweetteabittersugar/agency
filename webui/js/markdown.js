/* Markdown 渲染 — 基于 marked.js */
var renderMD = (function() {
  'use strict';

  if (typeof marked !== 'undefined') {
    marked.setOptions({
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false
    });
  }

  function renderMarkdown(text) {
    if (!text) return '';

    try {
      if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
        return marked.parse(text);
      }
    } catch(e) {
      console.warn('marked 渲染失败，回退到纯文本', e);
    }

    return escHtml(text).replace(/\n/g, '<br>');
  }

  window.renderMD = renderMarkdown;
  return renderMarkdown;
})();

window.renderMD = renderMD;
export { renderMD };
