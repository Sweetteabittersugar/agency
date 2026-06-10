# Agency 完整功能设计方案

> 汇编自：计划文件 + 工作日志 + 代码现状 + cc-connect + CC-Switch + ECC 研究
> 汇编时间：2026-06-09 | 状态：等待确认

---

## 1. 当前代码基准线

**Agent：** 31 个 .md 文件在 agents/ 子目录中，但 agent.yaml 只注册了 21 个
**路由：** shared.py ROUTING_KEYWORDS 20 个 Agent，简单关键词无权重
**前端：** 使用 `$()` 别名，引导仅 2 步
**Provider：** 仅 3 个（deepseek/anthropic/openai）
**安全：** 有 safety.py 但 web 端未调用，subprocess 全部 shell=True

---

## 2. 安全加固

1. CSP 头：static.py handle_index 加 Content-Security-Policy
2. CSRF：web.py do_POST，/api/setup 等无状态端点跳过
3. 命令注入：chat/webhook/agent_factory/sandbox 全部 shell=True→列表传参
4. XSS：app.js renderAgents 中 a.name 用 escHtml 转义
5. Web 安全检查：do_POST 调 check_input + check_rate_limit
6. cleanup-agents.py：task_id 白名单校验

---

## 3. Agent 阵列

**删 2：** refactor-cleaner（→coder）、qa（→test-runner）
**升级 2：** cost-analyst→Cost Guard、orchestrator 吸收 Coordinator
**新建 8：** architect、debugger、verifier、designer、test-generator、critic、memory-keeper、router
**总数：** 25-2+8=31（含 3 个协调层）

**关键词改为 3 级权重（1/2/3），5 处配置同步（agent.yaml/shared.py/main.py/agents.json/AGENTS.md）**

---

## 4. 前端修复

- $→el 全局重命名（消除变量遮蔽 bug）
- Markdown：CRLF 换行、代码块不挤一行、renderMD O(n²) 节流
- 停止按钮：立即重置 UI + 空内容显示 ⏹已停止
- 焦点不抢：删除 setStreaming 中的 input.focus()
- 无全局快捷键
- getFocusedPanel 兜底
- Toast z-index 9999
- 滚动条全局隐藏
- 768px 响应式
- hljs 在 app.js 之前加载
- fetch catch 全覆盖
- 三态（加载/空/错误）全覆盖
- deprecated execCommand → navigator.clipboard
- escHtml null 防护
- SSE \r\n 兼容
- saveAllConvos debounce 500ms
- ORCH 常量化
- apiFetch 不可变浅拷贝
- 401 认证修复
- 历史不自动清理（删除 4MB pop 逻辑）

---

## 5. 引导 4 步

Step 1: API Key + 11 Provider 下拉框
Step 2: 项目文件夹（可选）
Step 3: 远端开关
Step 4: 远端配置（地址+密码+指引）

---

## 6. 聊天交互

- Agent 粘性选择（panel._lastAgent）
- 消息排队（移动端排队，桌面端替换）
- 输出目录配置
- 思考过程折叠渲染
- 文件路径高亮
- 历史删除同步清后端 JSONL+cost.db

---

## 7. 仪表盘

- 上下文每会话独立（非全量求和）
- 会话名显示首句
- 权限/SubAgent/Hooks/MCP 四标签补数据
- 标签焦点保持
- 面板可缩放
- 测试面板（URL 输入→自动测试）

---

## 8. 侧边栏

- Agent 删除按钮（后端 /api/agent-delete + 确认弹窗）
- Skills 标签（搜索+详情+启用/禁用+源码）
- 项目栏删除
- Agent 卡片 tools 小标签

---

## 9. 帮助界面

- 四标签（快速入门/功能介绍/常见问题/快捷键）
- 历史记录不丢失说明

---

## 10. 远端访问

- 远端登录页（非 localhost 弹出密码认证）
- token 持久化（localStorage）

---

## 11. 模型与计价

- PROVIDER_MAP 3→11（deepseek/anthropic/openai/google/xai/siliconflow/qwen/kimi/glm/minimax/custom）
- MODEL_PRICES 完整表（覆盖全部主流模型）
- 前端下拉框 11 项

---

## 12. Skill 体系

- 侧边栏 Skill 详情（描述/分类/标签/触发词/路径/状态）
- 启用/禁用 toggle
- 查看源码（/api/skills/content/:name）
- skill-index.py（扫描+冲突检测）

---

## 13. 后端增强

- /api/health 端点
- /api/session/delete
- /api/test/run + /api/test/status
- 看门狗（zombie 清理+超时杀）
- 审计日志
- 编码降级修复
- MCP 权限注入（sandbox.py 追加 mcp__*）
- CategoryRouter 两级路由
- 即时回复 ack
- thinking/tool 过滤
- 安全白名单（ALLOW_FROM/ADMIN_FROM）

---

## 14. 文件整理

**删：** quicksort.py、login-system/、三工具脚本、TOC.md、.npmignore
**移：** 文档→docs/、.prettierrc→.claude/
**更新：** .env.example 与实际一致、CSS 死代码 5 个

---

## 15. 实施顺序

1. 安全加固（致命优先）
2. Agent 阵列 + 关键词权重
3. 前端 Bug 修复（$→el 优先）
4. 引导+聊天+仪表盘+侧边栏
5. Skill 体系+后端增强
6. 模型计价（放最后）
7. 全量验证

---

> 研究来源：cc-connect 架构分析、CC-Switch 代理网关设计、ECC 五阶段管线、Agent Team 三位一体模式
