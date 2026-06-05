#!/usr/bin/env node
// install-apply.js — Post-install hook
// Runs after npm install to link configuration files

const fs = require('fs');
const path = require('path');
const os = require('os');

const PKG_ROOT = path.resolve(__dirname, '..');
const CLAUDE_HOME = process.env.CLAUDE_CONFIG_DIR
  || path.join(os.homedir(), '.claude');

const DIRS = ['agents', 'skills', 'commands', 'hooks', 'rules'];

function copyDir(src, dest) {
  if (!fs.existsSync(src)) return;
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

console.log('[agency-kit] Installing config files...');

for (const dir of DIRS) {
  const src = path.join(PKG_ROOT, dir);
  const dest = path.join(CLAUDE_HOME, dir);
  if (fs.existsSync(src)) {
    copyDir(src, dest);
    console.log(`  ✓ ${dir}`);
  }
}

// Copy maestro
const maestroSrc = path.join(PKG_ROOT, 'maestro');
const maestroDest = path.join(CLAUDE_HOME, '..', 'maestro');
if (fs.existsSync(maestroSrc)) {
  copyDir(maestroSrc, maestroDest);
  console.log('  ✓ maestro');
}

console.log('[agency-kit] Done!');
console.log('');

// ── 安装后验证 ──────────────────────────────────────────
console.log('[agency-kit] Validating installation...');

let passed = 0;
let failed = 0;

function check(condition, label) {
  if (condition) {
    console.log(`  ✓ ${label}`);
    passed++;
  } else {
    console.log(`  ✗ ${label}`);
    failed++;
  }
}

// 检查 agents/ 目录
const agentsDir = path.join(PKG_ROOT, 'agents');
const agentMdFiles = fs.existsSync(agentsDir)
  ? fs.readdirSync(agentsDir).filter(f => f.endsWith('.md'))
  : [];
check(agentMdFiles.length >= 9, `agents/ 至少 9 个 .md 文件 (实际: ${agentMdFiles.length})`);

// 检查 rules/common/ 子目录
const rulesCommonDir = path.join(PKG_ROOT, 'rules', 'common');
check(fs.existsSync(rulesCommonDir) && fs.statSync(rulesCommonDir).isDirectory(),
  'rules/common/ 目录存在');

// 检查 hooks/ 目录有 .sh 文件
const hooksDir = path.join(PKG_ROOT, 'hooks');
const hookShFiles = fs.existsSync(hooksDir)
  ? fs.readdirSync(hooksDir).filter(f => f.endsWith('.sh'))
  : [];
check(hookShFiles.length > 0, `hooks/ 有 .sh 文件 (实际: ${hookShFiles.length})`);

console.log(`[agency-kit] Validation: ${passed} passed, ${failed} failed`);
if (failed > 0) {
  console.warn('[agency-kit] WARNING: Some checks failed. Review the installation.');
}

console.log('');
console.log('Try in Claude Code:');
console.log('  @status    # Check agent status');
console.log('  /design    # Enter design mode');
console.log('  @cost      # View API costs');
