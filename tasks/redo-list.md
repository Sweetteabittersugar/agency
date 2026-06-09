# Agency 两天改动清单 — 明天重做

> 2026-06-07 ~ 2026-06-08 | 因 git checkout -- . 全部回滚

---

## 一、安全加固（致命级）

- [ ] **XSS 防护** — Agent 名 HTML 转义、Markdown 链接协议白名单、代码块双重转义修复
- [ ] **命令注入修复** — chat/webhook/agent_factory 从 shell=True 改为列表传参
- [ ] **CSRF 防护** — web.py do_POST 加 CSRF token 校验（/api/setup 等无状态端点跳过）
- [ ] **CSP 头** — static.py handle_index 加 Content-Security-Policy
- [ ] **Web 安全检查启用** — do_POST 调用 safety.py 的 check_input + check_rate_limit
- [ ] **cleanup-agents.py 注入防护** — task_id 加白名单校验

## 二、前端修复

- [ ] **$→el 全局重命名** — 消除 `var el = el(...)` 21 处变量遮蔽 bug
- [ ] **Markdown 渲染修复** — CRLF换行、代码块不挤一行、renderMD O(n²)节流
- [ ] **停止按钮不卡死** — stopStream 加标志位防止竞态、空内容时显示 ⏹已停止
- [ ] **焦点不抢** — setStreaming 删除 input.focus()
- [ ] **无全局快捷键** — 删除 keydown 监听
- [ ] **getFocusedPanel 兜底** — panels 为空时自动 addPanel()
- [ ] **401 认证修复** — apiFetch 取消 prompt 后抛错而非静默失败
- [ ] **Toast z-index** — 从 99 升到 9999
- [ ] **滚动条** — 全局隐藏（非局部）
- [ ] **响应式** — 768px 媒体查询
- [ ] **hljs 加载顺序** — 移到 app.js 之前
- [ ] **fetch catch 全覆盖** — 7 处补齐
- [ ] **三态补全** — 加载/空/错误全覆盖
- [ ] **deprecated execCommand** — 3 处改用 navigator.clipboard
- [ ] **escHtml null 防护** — s??''
- [ ] **SSE \r\n 兼容** — buf.split 前替换
- [ ] **saveAllConvos debounce** — 500ms 延迟防 UI 阻塞
- [ ] **ORCH 常量化** — 15s/20s 提取为全局常量
- [ ] **apiFetch 不可变** — opts 浅拷贝

## 三、引导流程

- [ ] **4 步向导** — API Key→项目文件夹→远端开关→远端配置
- [ ] **setup 下拉框 11 provider** — DeepSeek/Anthropic/OpenAI/Google/xAI/SiliconFlow/Qwen/Kimi/GLM/MiniMax/自定义
- [ ] **setupFinish 保存 proj_dir** — 项目文件夹路径同步到 localStorage

## 四、聊天交互

- [ ] **Agent 粘性选择** — panel._lastAgent 记住上次选中的 agent，不自动切回 orchestrator
- [ ] **消息排队（移动端）** — 桌面端不排队直接替换
- [ ] **输出目录配置** — 设置面板可指定生成文件输出目录
- [ ] **思考过程渲染** — [Thinking] 折叠块，灰底左边框
- [ ] **文件路径高亮** — renderMD 中路径自动 code 标签
- [ ] **历史不自动清理** — 删除 4MB 自动 pop 逻辑

## 五、仪表盘

- [ ] **上下文每会话独立** — 非全量求和，每会话一条 token 进度条
- [ ] **会话名显示首句** — 非只显示 session ID
- [ ] **四标签有数据** — 权限/SubAgent/Hooks/MCP 补数据渲染
- [ ] **标签焦点保持** — 开关仪表盘回到上次选中标签
- [ ] **面板可缩放** — overflow:auto + resize:both
- [ ] **测试面板** — URL 输入→开始测试→状态轮询

## 六、侧边栏

- [ ] **Agent 删除按钮** — 后端 /api/agent-delete + 前端确认弹窗
- [ ] **Skills 标签** — 搜索+查看详情+启用禁用+源码
- [ ] **项目栏删除** — 无用的项目栏整块移除
- [ ] **Agent 卡片 tools 标签** — 小标签显示

## 七、帮助界面

- [ ] **四标签可切换** — 快速入门/功能介绍/常见问题/快捷键
- [ ] **历史记录说明** — 告知不丢失 + JSONL 路径

## 八、远端访问

- [ ] **远端登录页** — 非 localhost 弹出密码认证页
- [ ] **token 持久化** — localStorage 保存，刷新不需重登
- [ ] **CSRF 不对 setup/health/route 等生效**

## 九、Agent 阵列（22→27）

- [ ] **删 2** — refactor-cleaner（→coder）、qa（→test-runner）
- [ ] **关键词合并** — refactor-cleaner关键词→coder，qa+e2e关键词→test-runner
- [ ] **升级 2** — cost-analyst→Cost Guard、orchestrator吸收Coordinator
- [ ] **新建 5** — architect、debugger、verifier、designer、test-generator
- [ ] **新建 3（协调层）** — critic、memory-keeper、router
- [ ] **关键词加权** — ROUTING_KEYWORDS 全部 3 级权重
- [ ] **配置同步** — agent.yaml/shared.py/main.py/agents.json/AGENTS.md 5 处一致

## 十、模型与计价

- [ ] **PROVIDER_MAP 11 个** — shared.py + setup.py 同步扩充
- [ ] **MODEL_PRICES 完整表** — models.py 覆盖所有主流模型
- [ ] **前端下拉 11 项** — 引导+设置同步

## 十一、Skill 体系

- [ ] **侧边栏 Skill 详情** — 点击查看描述/分类/标签/路径/状态
- [ ] **启用/禁用** — toggleSkill 调 POST /api/skills/toggle
- [ ] **查看源码** — /api/skills/content/:name
- [ ] **skill-index.py** — 扫描生成 index.json + 冲突检测

## 十二、后端增强

- [ ] **/api/health 端点** — status/uptime/version/active_procs
- [ ] **/api/session/delete** — 删除会话文件+cost.db
- [ ] **/api/test/run + /api/test/status** — 测试 API
- [ ] **看门狗** — proc_manager 僵尸进程清理+超时杀
- [ ] **审计日志** — do_POST 记录 log_audit
- [ ] **编码降级修复** — 解码与 JSON 解析解耦
- [ ] **双路由表注释** — 标记 TODO 统一数据源
- [ ] **settings_sync 不清旧 agent** — 只同步不删除
- [ ] **webhook 耗时修复** — start_time 替代 time.time()-time.time()
- [ ] **MCP 权限注入** — sandbox.py 追加 mcp__* 到 allowedTools
- [ ] **CategoryRouter** — 8 领域分类器
- [ ] **两级路由** — classify→simple_route domain 兜底
- [ ] **即时回复 ack** — SSE stream 前发 event: ack
- [ ] **thinking/tool 过滤** — SHOW_THINKING/SHOW_TOOLS 环境变量
- [ ] **安全白名单** — ALLOW_FROM/ADMIN_FROM

## 十三、文件整理

- [ ] **删除无用** — quicksort.py、login-system/、code-stats.py、json-reader.py、toc-gen.py、TOC.md、.npmignore
- [ ] **移动位置** — GETTING-STARTED/USAGE/RULES→docs/、.prettierrc→.claude/
- [ ] **.env.example 更新** — 与实际 .env 键名一致
- [ ] **CSS 死代码清理** — 5 个未使用 class

## 十四、调研成果（不用重做，直接用）

- [ ] **cc-connect** — 忙标志+排队、平台适配器、安全白名单、即时回复
- [ ] **CC-Switch** — 代理网关、SSOT 配置存储、熔断故障转移
- [ ] **ECC** — 五阶段管线、选择性加载、模型分级、pass@3 验证
- [ ] **Agent Team** — Supervisor-Worker+Critic+MemoryKeeper 三位一体
- [ ] **前端自动测试** — Playwright MCP，Agent 自动 70%

---

## 执行顺序建议

1. 安全加固（致命漏洞必须最先）
2. Agent 阵列调整 + 配置同步（改一处验一处）
3. 前端 bug 修复（$→el 优先，其他按影响面）
4. 模型计价（最后做，避免再次回滚）
5. 全量验证（curl 路由 + 语法 + 服务健康）
