# Agency Design System

> **单一参考源**——改 CSS/HTML 之前先读这个文件。所有设计令牌定义在 `css/tokens.css`。

## 设计令牌速查

### 调色板（三主题）

| Token | 暗色 | 亮色 | 高对比 | 用途 |
|-------|------|------|--------|------|
| `--bg` | `#070b12` | `#ffffff` | `#000000` | 页面背景 |
| `--surface` | `#0e1420` | `#f8f9fa` | `#000000` | 卡片/面板 |
| `--surface2` | `#161e2e` | `#e9ecef` | `#111111` | 抬高表面 |
| `--surface3` | `#1c2538` | `#dee2e6` | `#222222` | 悬停/激活 |
| `--text` | `#eef0f4` | `#212529` | `#ffffff` | 主文字 |
| `--text2` | `#a0a8bb` | `#495057` | `#cccccc` | 次要文字 |
| `--muted` | `#8899aa` | `#868e96` | `#aaaaaa` | 禁用/提示 |
| `--accent` | `#10b981` | `#059669` | `#4fc3f7` | 主操作色 |
| `--accent2` | `#059669` | `#047857` | `#29b6f6` | 悬停加深 |
| `--danger` | `#d32f2f` | `#dc2626` | `#ff5252` | 错误/删除 |
| `--warn` | `#e65100` | `#d97706` | `#ffd600` | 警告 |
| `--success` | `#2e7d32` | `#2e7d32` | `#69f0ae` | 成功状态 |
| `--border` | `#1e2a3e` | `#dee2e6` | `#444444` | 边框 |
| `--border2` | `#263348` | `#ced4da` | `#555555` | 加粗边框 |

**规则**：永远用 `var(--xxx)`，不写硬编码颜色。不确定用哪个 → `--surface2` 作背景，`--text` 作文字，`--accent` 作强调。

### 圆角

| Token | 值 | 场景 |
|-------|----|------|
| `--radius-xs` | `6px` | 历史条目、标签、徽章 |
| `--radius-sm` | `4px` | 按钮、小输入框 |
| `--radius` | `8px` | 卡片、面板、输入框（默认） |
| `--radius-lg` | `12px` | 弹窗、模态框 |

### 间距（4px 基准）

```
4px  → 紧凑图标间距
8px  → 默认 gap、标题间距
12px → 卡片内边距
16px → 面板内边距
24px → 段落间距
```

### 阴影

| Token | 值 | 场景 |
|-------|----|------|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,.12)` | 轻微抬起 |
| `--shadow` | `0 2px 8px rgba(0,0,0,.3)` | 默认卡片 |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,.15)` | 抬高面板 |
| `--shadow-lg` | `0 8px 32px rgba(0,0,0,.5)` | 模态框 |

### 过渡

| Token | 值 | 场景 |
|-------|----|------|
| `--transition-fast` | `0.12s ease` | 按钮悬停、小交互 |
| `--transition-normal` | `0.25s ease` | 面板切换、卡片悬停 |
| `--transition-slide` | `0.3s ease` | 侧边栏、滑入 |
| `--transition-progress` | `0.5s ease` | 进度条、仪表动画 |

**规则**：所有 transition/animation 用变量，不硬编码秒数（进度条/倒计时除外）。

---

## 组件规范

### 按钮 `.btn`

```css
.btn {
  background: var(--surface2);
  border: 1px solid var(--border2);
  color: var(--text2);
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
/* 变体 */
.btn.primary  → bg: var(--accent), color: #fff
.btn.danger   → color: var(--danger)
.btn.on       → bg: var(--accent), color: #fff  (激活态)
/* 交互 */
.btn:hover    → border-color: var(--accent), color: var(--text)
.btn:active   → transform: scale(.96)
```

### 卡片

```css
/* 通用可点击卡片 */
.agent-card, .skill-card, .theme-option {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
  cursor: pointer;
  transition: all var(--transition-normal);
}
.agent-card:hover → border-color: var(--accent), translateX(2px)
/* 选中态 */
.selected, [aria-selected] → border-color: var(--accent), bg tint
```

### 输入框

```css
input, textarea, select {
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  color: var(--text);
  padding: 8px 10px;
  font-size: 14px;
  transition: border-color var(--transition-fast);
}
:focus → border-color: var(--accent), outline: 2px solid var(--focus-ring)
```

### 面板 `.panel`

```css
.panel {
  display: flex; flex-direction: column;
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  /* .on → display: flex (默认 none) */
}
.panel-bar { background: var(--surface); padding: 3px 10px; }
.panel-msgs { flex: 1; overflow-y: auto; }
.panel-inp { padding: 8px 10px; display: flex; gap: 6px; }
.panel-route { font-size: 9px; padding: 3px 10px; color: var(--muted); }
```

### 消息气泡 `.msg`

```css
.msg .bubble {
  max-width: 85%; padding: 8px 12px; border-radius: var(--radius-lg);
  font-size: 12px; line-height: 1.5;
  animation: fadeIn var(--transition-normal);
}
.msg.user .bubble → bg: rgba(16,185,129,.12), 右上角直角
.msg.assistant .bubble → bg: var(--surface2), 左上角直角
```

### 弹窗/模态框

```css
.overlay → fixed inset 0, rgba(0,0,0,.55), backdrop-filter blur(2px), z-index 200+
.modal → bg: var(--surface), radius: var(--radius-lg), shadow: var(--shadow-lg)
.modal-header → 13px bold, border-bottom
.modal-body → 12px, scrollable
.modal-footer → border-top, 右对齐按钮
```
宽度参考：搜索 560px | 设置/帮助 620px | 确认 380px

### Toast

```css
.toast → fixed bottom:24px left:16px, bg: var(--surface2), radius: var(--radius),
         shadow: var(--shadow), z-index: 9999, animation: fadeIn
.error → border-left: 3px solid var(--danger)
.warn → border-left: 3px solid var(--warn)
```

---

## 布局规范

```
┌─ sidebar (280px) ──┬── main (flex:1) ──────────────┐
│  conversations      │  header (48px)                 │
│  agents             │  grid.g1/.g2/.g4              │
│  skills             │    ├─ panel[on]               │
│  worktree           │    ├─ panel                   │
│  memory             │                                │
└─────────────────────┴────────────────────────────────┘
```

- 侧边栏固定 280px，`<=1024px` 缩到 60px 图标模式，`<=768px` 变成 off-canvas
- 网格：`.g1`=1列 `.g2`=2列 `.g4`=4列（面板数>4 时自动）
- 所有页面级容器用 `class="page"` 控制显示/隐藏

---

## 动画库

| 动画 | 时长 | 效果 |
|------|------|------|
| `fadeIn` | `.25s` | opacity 0→1, translateY(3px→0) |
| `pulse` | `1s` | opacity 0.5↔1 循环（加载指示） |
| `blink` | `0.5s` | 光标闪烁 |
| `shimmer` | `1.5s` | 骨架屏光泽扫描 |
| `paletteIn` | `.15s` | 命令面板弹出 (scale+.fade) |
| `batchBarIn` | `.2s` | 批量操作栏滑入 |
| `undoShrink` | `5s` | 撤销进度条收缩（固定时长） |

---

## 交互模式

### 悬停反馈
- 按钮：`var(--transition-fast)` 边框变色
- 卡片：`var(--transition-normal)` 边框高亮 + 微位移

### 聚焦
- 所有可交互元素用 `:focus-visible { outline: 2px solid var(--focus-ring) }`
- 弹窗打开时锁定背景滚动（`overflow: hidden` on body）

### 危险操作
- 删除类按钮加 `transition-delay: 0.3s` 防误触
- 不可逆操作用 `showDeleteConfirm()` 弹窗确认

### 响应式
- `1024px`：侧边栏图标模式、g4→g2
- `768px`：侧边栏 off-canvas、g2→g1、底部导航栏 (56px)

---

## AI 开发指南

### 改 UI 之前
1. 读这个文件（已经在了）
2. 所有颜色用 `var(--xxx)`，不要硬编码
3. 不确定间距就选 8px
4. 不确定圆角就选 `--radius` (8px)

### 写完 CSS 之后
1. 搜索硬编码颜色：`grep -n '#[0-9a-fA-F]\{3,6\}'` 确保都是 `var(--xxx)` 或 rgba
2. 运行 `node --check` 确保 JS 语法
3. Playwright 截图验证
