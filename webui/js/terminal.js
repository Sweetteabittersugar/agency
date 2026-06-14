/* 终端管理器 — 基于 xterm.js + Socket.IO，每个面板独立终端实例
   为何用 xterm.js：成熟的终端模拟库，支持256色、Unicode */

var termSockets = {};  // {pid: socket}
var termInstances = {}; // {pid: Terminal}

function toggleTerminal(pid) {
  var panel = panels.find(function(p){ return p.id===parseInt(pid,10); }); // pid 从 onclick 来是字符串，转为数字匹配
  if (!panel) return;
  var container = document.getElementById('term-'+pid);
  if (!container) {
    // 首次打开：创建终端 DOM
    var msgArea = panel.dom.messages;
    container = document.createElement('div');
    container.id = 'term-'+pid;
    container.className = 'panel-terminal';
    msgArea.parentNode.insertBefore(container, msgArea.nextSibling);
    initTerminal(pid, container);
  }
  container.classList.toggle('on');
  if (container.classList.contains('on')) {
    startTerminal(pid);
  }
}

function initTerminal(pid, container) {
  /* 初始化 xterm.js。不可移除——终端渲染依赖此初始化 */
  if (typeof Terminal === 'undefined') {
    container.textContent = 'xterm.js 未加载，请检查网络';
    return;
  }
  var term = new Terminal({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: '"JetBrains Mono", Consolas, monospace',
    theme: { background: '#0d1117', foreground: '#c9d1d9', cursor: '#58a6ff' },
    rows: 12,
    cols: 80
  });
  term.open(container);
  termInstances[pid] = term;

  // 用户输入 → SocketIO → 后端 PTY
  term.onData(function(data) {
    var sock = termSockets[pid];
    if (sock && sock.connected) {
      sock.emit('terminal_input', { sid: pid, data: data });
    }
  });
}

function startTerminal(pid) {
  /* 建立 SocketIO 连接并启动 PTY */
  if (termSockets[pid] && termSockets[pid].connected) return;
  if (typeof io === 'undefined') { console.error('Socket.IO not loaded'); return; }
  var sock = io('/ws/terminal');
  termSockets[pid] = sock;

  sock.on('connect', function() {
    sock.emit('terminal_start', { sid: pid, cwd: window.projDir || '.' });
  });

  sock.on('terminal_ready', function(d) {
    if (d.sid === pid && termInstances[pid]) termInstances[pid].focus();
  });

  // PTY 输出 → xterm.js 渲染
  sock.on('terminal_output', function(d) {
    if (d.sid === pid && termInstances[pid]) termInstances[pid].write(d.data);
  });

  sock.on('terminal_died', function(d) {
    if (d.sid === pid && termInstances[pid]) {
      termInstances[pid].write('\r\n[终端已关闭]\r\n');
    }
  });
}

window.stopTerminal = function(pid) {
  /* 面板关闭时清理终端 */
  if (termSockets[pid]) {
    termSockets[pid].emit('terminal_kill', { sid: pid });
    termSockets[pid].disconnect();
    delete termSockets[pid];
  }
  if (termInstances[pid]) {
    termInstances[pid].dispose();
    delete termInstances[pid];
  }
};
window.toggleTerminal = toggleTerminal;
