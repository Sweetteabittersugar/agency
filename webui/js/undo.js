/* Agency — 撤销系统 (Undo Stack + Toast) */
var _undoStack = (function() {
  var actions = [];

  function push(action) {
    action.timeout = action.timeout || 5000;
    actions.push(action);

    var toast = document.createElement('div');
    toast.className = 'toast undo-toast';

    var duration = (action.timeout / 1000).toFixed(1);
    toast.innerHTML = '<span>' + escHtml(action.label) + '</span>' +
      '<button class="undo-btn">' + t('undo') + '</button>' +
      '<div class="undo-progress"><div class="undo-progress-fill" style="animation-duration:' + duration + 's"></div></div>';

    document.body.appendChild(toast);

    var timer = setTimeout(function() {
      commit(action);
    }, action.timeout);

    toast.querySelector('.undo-btn').addEventListener('click', function(e) {
      e.stopPropagation();
      undoAction(action);
    });

    action._toast = toast;
    action._timer = timer;

    return toast;
  }

  function undoAction(action) {
    if (action._timer) clearTimeout(action._timer);
    if (action._toast) {
      action._toast.style.opacity = '0';
      action._toast.style.transition = 'opacity .3s';
      setTimeout(function() { if (action._toast) action._toast.remove(); }, 300);
    }
    if (action.undo) action.undo();
    var idx = actions.indexOf(action);
    if (idx >= 0) actions.splice(idx, 1);
  }

  function commit(action) {
    if (action._toast) {
      action._toast.style.opacity = '0';
      action._toast.style.transition = 'opacity .3s';
      setTimeout(function() { if (action._toast) action._toast.remove(); }, 300);
    }
    if (action.commit) action.commit();
    var idx = actions.indexOf(action);
    if (idx >= 0) actions.splice(idx, 1);
  }

  return { push: push, undo: undoAction };
})();

function showUndoableToast(label, undoFn, duration, commitFn) {
  return _undoStack.push({
    label: label,
    undo: undoFn,
    timeout: duration || 5000,
    commit: commitFn || function() {}
  });
}
