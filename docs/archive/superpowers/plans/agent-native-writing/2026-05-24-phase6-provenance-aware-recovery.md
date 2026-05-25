# Phase 6: Provenance-Aware Recovery

## 背景

Phase 4/5 已让知识库和长篇上下文输出 `memory_provenance`。但当前 run loop 的恢复链主要仍看旧字段，例如 `recommended_actions` 和 `should_generate_next_chapter`。本阶段把 provenance 纳入 Agent runtime 的状态判断，让后续 planner 可以直接消费 provenance，而不是重新解析散落字段。

## 参考项目取舍

- 采用 `openclaw` 的状态化 active memory fallback：召回状态和恢复动作进入运行状态，而不是只写在提示词里。
- 采用 `openhuman` 的 citation/provenance 旁路字段：保留结构化来源和边界，不塞进正文 prompt。
- 不引入新子 Agent，不改变 tool allowlist，不改自动执行审批策略。

## 范围

1. `recovery_policy.py`
   - `summarize_longform_context` 的恢复策略优先读取 `memory_provenance.recovery.next_tools`。
   - 保留旧 `recommended_actions` 兼容。
   - 恢复对象带上 `memory_provenance_status`、`memory_provenance_recovery_status`、`memory_source_count`。

2. `run_service.py`
   - `continuation_state` 增加最新 `memory_provenance` 摘要。
   - `_latest_recommended_recovery_from_steps` 透传 provenance 状态，方便 `agent_loop.next_action` 后续演进。

3. 测试
   - 在长篇维护阻塞 auto-plan 用例中断言 continuation state 暴露 provenance。
   - 断言 recovery 对象带 provenance 状态。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "auto_plan_longform_context_blocks_stale_maintenance_before_generation" -q
```

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "auto_plan_longform_context_blocks_stale_maintenance_before_generation or summarize_longform_context or longform_context_provenance" -q
```

## 成功标准

- blocked longform context run 的 `continuation_state.memory_provenance.status == "blocked"`。
- `continuation_state.recovery.memory_provenance_status == "blocked"`。
- 恢复链仍然推荐 `repair_longform_maintenance`。
- 旧 recovery 行为不回归。
