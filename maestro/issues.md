# Agency 问题追踪 & 验收清单

> 最后更新：2026-06-06

---

## SSE & 流式输出

| # | 问题 | 根因 | 修复 | 状态 |
|---|------|------|------|------|
| 1 | 模型生成完不停止 | 只检查 `[DONE]` 字符串，未检测 `finish_reason` | 加 `finish_reason` 检测 + `resp.close()` | ✅ |
| 2 | SSE reader 泄漏 | abort 时只 abort controller，未 cancel reader | `stopStream` 加 `p._reader.cancel()` + `p._reader=null` | ✅ |
| 3 | 多面板同时流式卡死 | 单线程 `HTTPServer`，SSE 长连接阻塞 | `ThreadingMixIn` + `daemon_threads` | ✅ |

## 会话管理

| # | 问题 | 根因 | 修复 | 状态 |
|---|------|------|------|------|
| 4 | --continue 不生效 | `CLAUDE_CODE_CONFIG_DIR` 设到空目录 | 移除 env var 覆盖 | ✅ |
| 5 | --session-id + --resume 同时使用报错 | 两个参数互斥 | `is_new` → `--session-id`；续接 → `--resume` | ✅ |
| 6 | 对话历史不保存 | `addMsgBubble` 只加 DOM 未 push `messages` 数组 | 每次 `addMsg` 时 push | ✅ |
| 7 | 历史加载错误 | 旧记录无 `sessionId` | 加载时兼容空 `sessionId` | ✅ |

## 子进程 & 稳定性

| # | 问题 | 根因 | 修复 | 状态 |
|---|------|------|------|------|
| 8 | 操作多了页面卡死（一） | `HTTPServer` 单线程 | `ThreadingMixIn` | ✅ |
| 9 | 操作多了页面卡死（二） | 子进程泄漏：`proc.wait(timeout=10)` 超时孤儿 | `finally` 块 `_kill_proc()` | ✅ |
| 10 | 操作多了页面卡死（三） | `_running_procs` set `-=` 赋值 → `UnboundLocalError` | 改 list + `remove`/`append` | ✅ |
| 11 | 和用户主 Claude 会话撞车 | 共用 `~/.claude/` | `CLAUDE_CODE_CONFIG_DIR` → `.claude-isolated/` | ✅ |
| 12 | 隔离后 API 接不上 | `.claude-isolated/` 缺少 agents/settings(含key) | 启动时自动合并全局 settings + 同步 agents/skills | ✅ |
| 13 | Windows GBK 编码崩溃 | subprocess `text=True` 默认 GBK | 全部改 `encoding='utf-8', errors='replace'` | ✅ |

## 前端 UI

| # | 问题 | 根因 | 修复 | 状态 |
|---|------|------|------|------|
| 14 | 发送按钮不响应 | `querySelector('button')` 匹配到关闭按钮 | 改用 `.panel-inp button` 选择器 | ✅ |
| 15 | JS 重复函数语法错误 | 两次编辑导致函数重复 | 删除重复块 | ✅ |
| 16 | `parse_qs` NameError | web.py 简化后缺少 import | 补 `from urllib.parse import urlparse, parse_qs` | ✅ |
| 17 | f-string 反斜杠报错 | Python 3.11 限制 | `chr(10)` 替代 `\n` | ✅ |
| 18 | 侧边栏滚动条丑 | 默认滚动条样式 | `.sidebar *` 全局 `scrollbar-width:none` | ✅ |
| 19 | 侧边栏臃肿 | 8 个标签太多 | 精简到 4 核心标签，Harness 移入仪表盘弹窗 | ✅ |
| 20 | 浏览器显示旧 HTML | `git checkout` 回退了未提交工作 | 从零重写 HTML | ✅ |

## 安全 & 隐私

| # | 问题 | 根因 | 修复 | 状态 |
|---|------|------|------|------|
| 21 | `.claude-isolated/settings.json` 含 API key 进了 git | 自动合并脚本把 key 写入了跟踪文件 | `filter-branch` 清洗历史 + `.gitignore` 排除 | ✅ |
| 22 | gitignore 缺 `*.key`/`*.pem`/`credentials.*` | 未考虑其他凭证文件名 | 补全模式 | ✅ |
| 23 | 新手无法只填 Key 就用 | 依赖全局 `~/.claude/settings.json` | 侧边栏独立 Key 输入 + provider 选择 + env 注入 | ✅ |

## 功能完整性

| # | 问题 | 状态 |
|---|------|------|
| 24 | 多面板分屏（1/2/4窗）| ✅ |
| 25 | @agent名 直接调用 | ✅ |
| 26 | 智能调度（orchestrator）| ✅ |
| 27 | 会话 ID 持久化 & 恢复 | ✅ |
| 28 | 对话历史保存/加载/删除 | ✅ |
| 29 | 开发者模式（成本看板 + Agent工厂）| ✅ |
| 30 | Harness 仪表盘（权限/上下文/SubAgent/Hooks/Skills/MCP/记忆）| ✅ |
| 31 | Skills 管理（浏览/启用/禁用）| ✅ |
| 32 | 记忆文件浏览器 & 编辑器 | ✅ |
| 33 | MCP 服务器状态 | ✅ |
| 34 | 权限 Toast（Allow/Deny/Always）| ✅ |
| 35 | Token 窗口进度条 | ✅ |
| 36 | 独立 API Key 配置 | ✅ |

---

---

## 后续开发

| # | 方向 | 说明 |
|---|------|------|
| 37 | 手机端 | 响应式布局 / PWA / 触屏交互 |
| 38 | 飞书接入 | Webhook → Agent → 回复消息 |
| 39 | 微信接入 | 公众号/企业微信 → 机器人派任务 |
| 40 | 上下文深化 | JSONL 实时解析 token 用量、缓存命中率、压缩日志 |
| 41 | 智能调度 | 多 Agent 编排可视化、SubAgent 树 |
| 42 | 聊天体验 | 代码高亮、Markdown 完善、错误恢复 |
| 43 | 文件/Git | 侧边栏文件浏览器 + Git 状态面板 |

### 基础功能
- [ ] 启动 `start.bat`，浏览器自动打开 `localhost:8800`
- [ ] 侧边栏：Agent / 项目 / 历史 / 工具 4 标签切换正常
- [ ] 发送消息 → 流式返回 → 自动停止
- [ ] Ctrl+N 新建面板，Ctrl+G 切换分屏

### 会话
- [ ] 同一面板连续对话，上下文保持
- [ ] 切换到历史对话，加载完整消息
- [ ] 删除历史对话

### 稳定性
- [ ] 连续发送 10+ 条消息不卡死
- [ ] 快速新建/关闭面板不卡死
- [ ] 多面板同时发送不卡死
- [ ] 刷新页面后重新发送正常

### Harness 仪表盘
- [ ] 点击 📊 仪表盘 → 7 子标签正常切换
- [ ] 权限管线 → 显示权限历史
- [ ] 上下文工程 → Token 进度条
- [ ] Skills 管理 → 列表 + 启用/禁用
- [ ] 记忆 → 浏览文件 + 编辑 + 保存

### 安全
- [ ] `git log -- .claude-isolated/settings.json` 无敏感内容
- [ ] `.env` 被 gitignore 排除
- [ ] 填 API Key → 发送消息正常
- [ ] 不填 API Key → 用全局配置正常
