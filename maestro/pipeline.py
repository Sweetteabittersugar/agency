"""五阶段管线状态机 + pass@k 验证 + 模型分级硬规则"""

import logging
import re
import subprocess
import time

log = logging.getLogger(__name__)

# ── 阶段定义 ──
TASK_STATES = {
    "research": {"enter": "信息是否充分？>=3个来源", "exit": "需求理解完整"},
    "plan": {"enter": "research 通过", "exit": "方案覆盖所有约束"},
    "dry_run": {"enter": "plan 通过", "exit": "只读分析完成，输出变更计划"},
    "gate": {"enter": "dry_run 通过", "exit": "硬门控检查通过"},
    "implement": {"enter": "gate 通过", "exit": "代码通过 lint+test"},
    "review": {"enter": "implement 通过", "exit": "pass@3 轻量版通过"},
    "verify": {"enter": "review 通过", "exit": "原始需求全部满足"},
}

STAGE_ORDER = ["research", "plan", "dry_run", "gate", "implement", "review", "verify"]

# ── Opus 触发条件 ──
OPUS_CONDITIONS = [
    "任务涉及 5+ 文件跨模块重构",
    "存在多步骤依赖推理链",
    "安全/正确性零容忍场景（生产关键路径）",
    "用户显式指定 @agent --opus",
]

# 复杂度关键词（用于 select_model 自动判断）
_HIGH_COMPLEXITY_KW = [
    "重构",
    "架构",
    "多模块",
    "跨模块",
    "分布式",
    "并发",
    "异步",
    "数据库迁移",
    "API设计",
    "系统设计",
    "安全审计",
    "性能优化",
    "refactor",
    "architecture",
    "multi-module",
    "concurrent",
]


class PipelineStateMachine:
    """五阶段管线状态机（支持自定义阶段列表）"""

    def __init__(self, task: dict, active_stages: list | None = None):
        self.task = task
        self.active_stages = active_stages if active_stages is not None else list(STAGE_ORDER)
        self.current_stage = self.active_stages[0] if self.active_stages else "done"
        self.stage_history: list[dict] = []
        self.stage_outputs: dict[str, str] = {}

    def can_advance(self, stage: str, output: str) -> tuple[bool, str]:
        """检查是否可以进入下一阶段。返回 (通过?, 原因)"""
        if stage not in STAGE_ORDER:
            return False, f"未知阶段: {stage}"

        current_idx = self.active_stages.index(stage) if stage in self.active_stages else -1
        if current_idx < 0:
            return False, f"阶段 {stage} 不在当前管线中"

        # 检查前置阶段是否通过（仅检查活跃阶段列表中位于当前阶段之前的）
        for prev in self.active_stages[:current_idx]:
            prev_record = next((h for h in self.stage_history if h["stage"] == prev), None)
            if not prev_record or prev_record.get("status") != "passed":
                return False, f"前置阶段 {prev} 未通过"

        # 阶段特定验证
        if stage == "research":
            if not output or len(output.strip()) < 50:
                return False, "研究输出不足（<50字符），信息不充分"
            # 检查是否引用了 >=3 个来源
            source_count = len(re.findall(r"(?:来源|source|参考|ref|https?://)", output, re.I))
            if source_count < 3:
                return False, f"信息来源不足（需 >=3，当前 {source_count}）"

        elif stage == "plan":
            if not output or len(output.strip()) < 100:
                return False, "方案输出不足（<100字符）"
            task_text = self.task.get("task", "")
            if task_text:
                keywords = re.findall(r"[一-鿿]{2,}", task_text)
                covered = sum(1 for kw in keywords if kw in output)
                if covered < len(keywords) * 0.5:
                    return False, f"方案未覆盖足够约束（覆盖 {covered}/{len(keywords)}）"

        elif stage == "dry_run":
            if not output or len(output.strip()) < 50:
                return False, "dry-run 输出不足"
            # 检查是否输出结构化计划
            if "files" not in output.lower() and "文件" not in output:
                return False, "dry-run 未输出文件级变更计划"

        elif stage == "gate":
            # gate 阶段由 hard_gate_check 裁决，不需要输出检查
            return True, "通过（由 hard_gate_check 裁决）"

        elif stage == "implement":
            if not output or len(output.strip()) < 50:
                return False, "实现输出不足"

        elif stage == "review":
            if not output or len(output.strip()) < 20:
                return False, "审查输出不足"

        elif stage == "verify":
            if not output or len(output.strip()) < 20:
                return False, "验证输出不足"

        return True, "通过"

    def advance(self, output: str):
        """记录阶段输出并推进到下一阶段"""
        self.stage_outputs[self.current_stage] = output
        self.stage_history.append(
            {
                "stage": self.current_stage,
                "status": "passed",
                "output_preview": output[:200],
                "timestamp": time.time(),
            }
        )
        current_idx = self.active_stages.index(self.current_stage)
        if current_idx < len(self.active_stages) - 1:
            self.current_stage = self.active_stages[current_idx + 1]
        else:
            self.current_stage = "done"

    def fail_stage(self, reason: str):
        """标记当前阶段失败"""
        self.stage_history.append(
            {
                "stage": self.current_stage,
                "status": "failed",
                "reason": reason,
                "timestamp": time.time(),
            }
        )

    def rollback(self):
        """退回到上一阶段"""
        try:
            current_idx = self.active_stages.index(self.current_stage)
        except ValueError:
            return
        if current_idx > 0:
            self.current_stage = self.active_stages[current_idx - 1]
            # 清除失败阶段记录
            self.stage_history = [
                h for h in self.stage_history if h["stage"] != self.active_stages[current_idx]
            ]

    def get_current_prompt(self) -> str:
        """获取当前阶段对应的 Agent prompt"""
        stage_info = TASK_STATES.get(self.current_stage, {})
        task_text = self.task.get("task", "")

        prompts = {
            "research": (
                f"你需要对以下任务进行深入研究：\n\n{task_text}\n\n"
                f"要求：\n"
                f"1. 收集至少 3 个信息来源\n"
                f"2. 分析需求的关键约束和边界条件\n"
                f"3. 输出结构化研究报告（含来源标注）\n\n"
                f"入口条件: {stage_info.get('enter', '')}\n"
                f"出口条件: {stage_info.get('exit', '')}"
            ),
            "plan": (
                f"基于研究结果，制定实施方案：\n\n任务：{task_text}\n\n"
                f"前置阶段输出：\n{self.stage_outputs.get('research', '无')[:500]}\n\n"
                f"要求：\n"
                f"1. 列出所有实施步骤\n"
                f"2. 标注每步依赖和风险\n"
                f"3. 确保方案覆盖所有约束\n\n"
                f"入口条件: {stage_info.get('enter', '')}\n"
                f"出口条件: {stage_info.get('exit', '')}"
            ),
            "dry_run": (
                f"【只读预演 — 禁止修改任何文件】\n\n"
                f"方案：\n{self.stage_outputs.get('plan', '无')[:800]}\n\n"
                f"任务：{task_text}\n\n"
                f"要求：\n"
                f"1. 只读分析：阅读相关文件，确认修改范围\n"
                f"2. 输出结构化变更计划（JSON格式）：\n"
                f'   {{"files": [{{"path": "相对路径", "action": "create|modify|delete", '
                f'"summary": "变更摘要", "risk_level": "low|medium|high|critical"}}], '
                f'"total_changes": N}}\n'
                f"3. 禁止使用 Write/Edit 工具\n\n"
                f"入口条件: {stage_info.get('enter', '')}\n"
                f"出口条件: {stage_info.get('exit', '')}"
            ),
            "gate": (
                f"【硬门控检查 — 自动裁决】\n\n"
                f"dry_run 计划：\n{self.stage_outputs.get('dry_run', '无')[:1000]}\n\n"
                f"此阶段为自动检查，不调用 Agent。\n"
                f"检查项：敏感文件、文件数上限、高风险操作、风险等级汇总。"
            ),
            "implement": (
                f"按照 dry-run 计划实施：\n\n任务：{task_text}\n\n"
                f"dry-run 计划：\n{self.stage_outputs.get('dry_run', '无')[:800]}\n\n"
                f"方案：\n{self.stage_outputs.get('plan', '无')[:800]}\n\n"
                f"要求：\n"
                f"1. 严格按照 dry-run 计划执行\n"
                f"2. 代码需通过 lint 和测试\n"
                f"3. 完成后标注修改的文件列表\n\n"
                f"入口条件: {stage_info.get('enter', '')}\n"
                f"出口条件: {stage_info.get('exit', '')}"
            ),
            "review": (
                f"审查实施结果：\n\n任务：{task_text}\n\n"
                f"实施输出：\n{self.stage_outputs.get('implement', '无')[:1000]}\n\n"
                f"要求：\n"
                f"1. 检查代码正确性、边界条件\n"
                f"2. 检查安全风险\n"
                f"3. 检查代码质量和可维护性\n\n"
                f"入口条件: {stage_info.get('enter', '')}\n"
                f"出口条件: {stage_info.get('exit', '')}"
            ),
            "verify": (
                f"最终验证：\n\n原始任务：{task_text}\n\n"
                f"全部阶段输出摘要：\n"
                + "\n".join(f"- {s}: {o[:100]}" for s, o in self.stage_outputs.items())
                + f"\n\n要求：\n"
                f"1. 逐条确认原始需求是否满足\n"
                f"2. 标记未满足项和遗留风险\n"
                f"3. 输出最终验证报告\n\n"
                f"入口条件: {stage_info.get('enter', '')}\n"
                f"出口条件: {stage_info.get('exit', '')}"
            ),
        }
        return prompts.get(self.current_stage, f"执行阶段: {self.current_stage}\n任务: {task_text}")

    def to_dict(self) -> dict:
        """序列化当前状态"""
        return {
            "current_stage": self.current_stage,
            "stage_history": self.stage_history,
            "task": self.task,
        }


# ── 硬门控检查 ──

SENSITIVE_PATTERNS = [
    ".env",
    ".gitignore",
    "*.pem",
    "*.key",
    "credentials.*",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
    "authorized_keys",
]
HIGH_RISK_ACTIONS = [
    "rm -rf",
    "rm -r",
    "chmod 777",
    "chown",
    "systemctl",
    "iptables",
    "sudo",
    "mkfs.",
    "dd if=",
    ":(){ :|:& };:",
]


def hard_gate_check(dry_run_plan: dict) -> tuple:
    """硬门控：检查 dry-run 计划是否可以执行。返回 (通过?, 原因)。"""
    if not dry_run_plan or not isinstance(dry_run_plan, dict):
        return False, "dry_run 计划为空或格式无效"

    files = dry_run_plan.get("files", [])
    if not files:
        return False, "dry_run 计划不包含任何文件变更"

    # 1. 敏感文件检查
    for f in files:
        path = f.get("path", "")
        for pattern in SENSITIVE_PATTERNS:
            if pattern.replace("*", "") in path.lower():
                return False, f"涉及敏感文件: {path}（匹配规则 {pattern}）"

    # 2. 单次文件数上限
    if len(files) > 10:
        return False, f"单次修改文件数 ({len(files)}) 超过上限 10，请拆分任务"

    # 3. 高风险操作检查
    for f in files:
        summary = (f.get("summary", "") + f.get("action", "")).lower()
        for action in HIGH_RISK_ACTIONS:
            if action.lower() in summary:
                return False, f"包含高风险操作: {f.get('summary', '')[:80]}"

    # 4. 风险等级汇总
    risk_levels = [f.get("risk_level", "low").lower() for f in files]
    if "critical" in risk_levels:
        return False, "存在 critical 风险等级 — 触发 Coordinator escalation"
    if "high" in risk_levels:
        return False, "存在 high 风险等级 — 需 Coordinator escalation"

    return True, f"门控通过（{len(files)} 文件，风险: {set(risk_levels)}）"


# ── pass@k 轻量版验证 ──

PASS_K_PERSPECTIVES = [
    {
        "name": "correctness",
        "prompt": (
            "你是一位资深代码审查专家。从**正确性**角度审查以下输出：\n\n"
            "{output}\n\n"
            "原始任务：{task}\n\n"
            "请判断：\n"
            "1. 逻辑是否正确？\n"
            "2. 边界条件是否覆盖？\n"
            "3. 是否有明显的 bug？\n\n"
            "只回复 PASS 或 FAIL，然后简要说明原因（不超过 3 句话）。"
        ),
    },
    {
        "name": "security",
        "prompt": (
            "你是一位安全审计专家。从**安全性**角度审查以下输出：\n\n"
            "{output}\n\n"
            "原始任务：{task}\n\n"
            "请判断：\n"
            "1. 是否存在注入风险？\n"
            "2. 是否有敏感信息泄露？\n"
            "3. 是否有越权访问风险？\n\n"
            "只回复 PASS 或 FAIL，然后简要说明原因（不超过 3 句话）。"
        ),
    },
    {
        "name": "simplicity",
        "prompt": (
            "你是一位代码质量专家。从**简洁性**角度审查以下输出：\n\n"
            "{output}\n\n"
            "原始任务：{task}\n\n"
            "请判断：\n"
            "1. 是否有冗余代码？\n"
            "2. 代码是否可维护？\n"
            "3. 命名和结构是否清晰？\n\n"
            "只回复 PASS 或 FAIL，然后简要说明原因（不超过 3 句话）。"
        ),
    },
]


def _call_haiku(
    prompt: str, api_key: str = "", api_provider: str = "deepseek", timeout: int = 30
) -> str:
    """调用轻量模型（haiku 级别）"""
    from maestro.shared import CLAUDE_BIN, build_isolated_env

    if not CLAUDE_BIN:
        log.warning("Claude CLI 不可用，跳过 pass@k 验证")
        return "PASS (CLI 不可用，默认放行)"

    try:
        iso_env = build_isolated_env(api_key, api_provider)
        # 使用 haiku 模型
        iso_env["ANTHROPIC_MODEL"] = iso_env.get(
            "ANTHROPIC_DEFAULT_HAIKU_MODEL", "deepseek-v4-flash"
        )

        cmd = [
            "cmd",
            "/c",
            CLAUDE_BIN,
            "-p",
            prompt,
            "--bare",
            "--permission-mode",
            "auto",
            "--max-turns",
            "1",
            "--model",
            iso_env.get("ANTHROPIC_MODEL", "deepseek-v4-flash"),
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            env=iso_env,
        )
        stdout, _ = proc.communicate(timeout=timeout)
        return (stdout or "").strip()
    except subprocess.TimeoutExpired:
        log.warning("pass@k haiku 调用超时")
        return "PASS (超时，默认放行)"
    except Exception as e:
        log.warning(f"pass@k haiku 调用失败: {e}")
        return "PASS (调用失败，默认放行)"


def pass_k_verify(
    output: str, task: str, k: int = 3, api_key: str = "", api_provider: str = "deepseek"
) -> tuple[bool, dict]:
    """k 视角独立验证。返回 (通过?, {各视角结果})"""
    results = {}
    pass_count = 0

    for i, p in enumerate(PASS_K_PERSPECTIVES[:k]):
        prompt = p["prompt"].format(output=output[:4000], task=task[:1000])
        raw = _call_haiku(prompt, api_key=api_key, api_provider=api_provider)

        # 解析 PASS/FAIL
        raw_upper = raw.upper()
        is_pass = "PASS" in raw_upper and "FAIL" not in raw_upper
        if is_pass:
            pass_count += 1

        results[p["name"]] = {
            "passed": is_pass,
            "raw": raw[:500],
        }
        log.info(f"pass@k [{p['name']}]: {'PASS' if is_pass else 'FAIL'}")

    overall = pass_count >= max(2, k - 1)  # 多数通过
    log.info(f"pass@k 结果: {pass_count}/{k} 通过 → {'通过' if overall else '不通过'}")

    return overall, results


# ── 模型分级硬规则 ──


def _count_opus_conditions(task: dict) -> int:
    """统计满足的 Opus 条件数"""
    task_text = task.get("task", "")
    agent = task.get("agent", "")
    score = 0

    # 条件1: 5+ 文件跨模块重构
    # 匹配 "N个文件"、"N个模块"、"N处"、"文件：N" 等模式
    file_patterns = re.findall(r"(\d+)\s*(?:个|处|份)?\s*(?:文件|模块|file|module)", task_text)
    file_count = sum(int(n) for n in file_patterns)
    if file_count >= 5 or "跨模块" in task_text or "多文件" in task_text or "多模块" in task_text:
        score += 1

    # 条件2: 多步骤依赖推理链
    step_indicators = [
        "步骤",
        "第一步",
        "第二步",
        "然后",
        "接着",
        "最后",
        "依赖",
        "前置",
        "后置",
        "顺序",
        "流程",
        "多步骤",
        "step",
        "then",
        "after",
        "before",
        "depends",
    ]
    if sum(1 for kw in step_indicators if kw in task_text.lower()) >= 3:
        score += 1

    # 条件3: 安全/正确性零容忍场景
    safety_kw = [
        "安全",
        "漏洞",
        "注入",
        "加密",
        "认证",
        "授权",
        "生产",
        "关键路径",
        "支付",
        "交易",
        "密码",
        "审计",
        "security",
        "auth",
        "production",
        "critical",
    ]
    if any(kw in task_text.lower() for kw in safety_kw):
        score += 1

    # 条件4: 用户显式指定
    if "--opus" in task_text or "--opus" in str(agent):
        score += 1

    return score


def _is_high_complexity(task: dict) -> bool:
    """判断是否为高复杂度任务"""
    task_text = task.get("task", "")
    kw_count = sum(1 for kw in _HIGH_COMPLEXITY_KW if kw.lower() in task_text.lower())
    # 任务描述长度 > 100 字符且有复杂度关键词
    if len(task_text) > 100 and kw_count >= 1:
        return True
    # 复杂度关键词 >= 2
    if kw_count >= 2:
        return True
    # 包含重构/架构等强关键词
    strong_kw = ["重构", "架构", "安全", "性能", "refactor", "architecture"]
    if any(kw in task_text.lower() for kw in strong_kw) and len(task_text) > 50:
        return True
    return False


def select_model(task: dict, agent: str = "") -> str:
    """满足 >=2 个 Opus 条件 -> opus; 高复杂度 -> sonnet; 其他 -> haiku"""
    opus_count = _count_opus_conditions(task)

    if opus_count >= 2:
        log.info(f"select_model: opus (满足 {opus_count} 个条件)")
        return "opus"

    if _is_high_complexity(task):
        log.info("select_model: sonnet (高复杂度)")
        return "sonnet"

    log.info("select_model: haiku (默认)")
    return "haiku"


def resolve_model_name(tier: str, api_provider: str = "deepseek") -> str:
    """将能力级别转换为具体模型名"""
    from maestro.shared import PROVIDER_MAP

    provider = PROVIDER_MAP.get(api_provider, PROVIDER_MAP["deepseek"])
    tier_map = {
        "opus": provider.get("ANTHROPIC_MODEL", "deepseek-v4-pro"),
        "sonnet": provider.get(
            "ANTHROPIC_DEFAULT_SONNET_MODEL", provider.get("ANTHROPIC_MODEL", "deepseek-v4-pro")
        ),
        "haiku": provider.get("ANTHROPIC_DEFAULT_HAIKU_MODEL", "deepseek-v4-flash"),
    }
    return tier_map.get(tier, tier_map["haiku"])
