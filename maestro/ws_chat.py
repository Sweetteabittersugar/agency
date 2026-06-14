"""WebSocket 聊天任务处理 — 从 routes/chat.py 提取核心逻辑
供 SocketIO /ws/chat 和 HTTP /api/chat 共用
Phase 2: 聊天 SSE → WebSocket 升级"""
# 不可移除——此模块是 /ws/chat namespace 的核心处理逻辑

import json, time, os, logging

log = logging.getLogger(__name__)


def process_chat_task(data, emit_callback):
    """
    处理聊天任务，通过 emit_callback 推送流式事件。
    数据格式 {task, api_key, api_provider, model?, force_agent?, session_id?, is_first?}

    emit_callback(event_type, payload) — 向单个 socket 连接推送事件
    返回: {ok, model, agent, total_in, total_out, total_cost, in_tokens, out_tokens,
            cost, elapsed, compaction, session_id, content_preview}
    """
    task = data.get('task', '').strip()
    api_key = data.get('api_key', '')
    api_provider = data.get('api_provider', 'deepseek')

    # 后台配置优先：无前端 Key 时从环境变量读取
    if not api_key:
        import os
        from maestro.models import get_provider_config
        _, env_key, _ = get_provider_config()
        api_key = env_key
    if not api_provider:
        import os
        api_provider = os.environ.get("PROVIDER", "deepseek")

    # Phase 2: 输入校验——空任务和缺 Key 在推送 error 事件后立即返回
    if not task:
        emit_callback('error', {'error': '请求为空'})
        return {'ok': False, 'error': '请求为空'}

    if not api_key:
        emit_callback('error', {'error': '未配置 API Key', 'action': 'open_settings'})
        return {'ok': False, 'error': '未配置 API Key'}

    from maestro.main import simple_route
    from maestro.shared import PROJECT_ROOT, build_isolated_env
    from maestro.claude_session import get_or_create
    from maestro.models import resolve_model

    # Phase 2: 路由决定——前端可强制指定 agent，否则走路由引擎
    force_agent = data.get('force_agent', '')
    route_info = simple_route(task) if not force_agent else None
    agent_name = force_agent or (route_info['agent'] if route_info else '')
    model = data.get('model', '') or resolve_model('balanced')

    # Phase 2: 推送路由结果事件——前端据此更新 UI
    emit_callback('routing', {'agent': agent_name, 'model': model})

    # 构建隔离环境（API Key + Provider）
    session_id = data.get('session_id') or data.get('sid') or str(__import__('uuid').uuid4())
    iso_env = build_isolated_env(api_key, api_provider)

    # Phase 2: 获取或创建 Claude 会话——每个面板独立 session
    cs = get_or_create(session_id, str(PROJECT_ROOT), iso_env)
    if cs is None:
        emit_callback('error', {'error': '无法启动 Claude 进程'})
        return {'ok': False, 'error': '无法启动 Claude 进程'}

    emit_callback('executing', {'agent': agent_name})

    # Phase 2: 如前端 @agent 前缀指定了 Agent，剥离后发送实际任务
    actual_task = task
    if force_agent:
        m = task.strip().split(' ', 1)
        if len(m) > 1 and m[0].startswith('@'):
            actual_task = m[1]

    # Phase 2: 新会话注入记忆——首次对话时扫描 memory/ 目录
    if data.get('is_first'):
        try:
            from maestro.memory_engine import build_injection_prefix
            actual_task = build_injection_prefix(actual_task, str(PROJECT_ROOT))
        except Exception:
            pass

    start_time = time.time()
    # 不可移除——send_and_read 是整个对话管道的核心：发送任务 → 接收 Claude 流式响应
    events = cs.send_and_read(actual_task)

    chat_output = ''
    done_data = {}
    for evt in events:
        if 'content' in evt:
            chat_output += evt['content']
            emit_callback('content', {'content': evt['content']})
        elif 'done' in evt:
            done_data = evt['done']
        elif 'error' in evt:
            emit_callback('error', {'error': evt['error']})

    # Phase 2: 统计——耗时 / Token / 费用 / 压缩状态
    elapsed = round(time.time() - start_time, 1)
    in_tokens = done_data.get('in_tokens', len(task) // 4)
    out_tokens = done_data.get('out_tokens', 0)
    model_used = done_data.get('model', model)
    from maestro.models import estimate_cost, check_compaction
    cost = estimate_cost(model_used, in_tokens, out_tokens)
    comp = check_compaction(model_used, cs._total_in_tokens)

    # Phase 2: 费用记录——写入 Web 费用日志
    try:
        from maestro.web_cost import record_cost
        record_cost(model_used, in_tokens, out_tokens, cost, agent_name, 'ws_chat')
    except Exception:
        pass

    return {
        'ok': True,
        'model': model_used,
        'agent': agent_name,
        'total_in': cs._total_in_tokens,
        'total_out': cs._total_out_tokens,
        'total_cost': cs._total_cost,
        'in_tokens': in_tokens,
        'out_tokens': out_tokens,
        'cost': round(cost, 6),
        'elapsed': elapsed,
        'compaction': comp,
        'session_id': session_id,
        'content_preview': chat_output[:200],
    }
