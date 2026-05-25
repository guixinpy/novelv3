# Phase 6 Report: Provenance-Aware Recovery

## 目标

把 Phase 4/5 新增的 `memory_provenance` 接入 Agent runtime，而不是只停留在工具输出字段。重点是让恢复链和 `continuation_state` 能直接暴露上下文召回状态、来源数量和恢复建议。

## 参考项目取舍

- 采用 `openclaw` 的 active memory 状态化 fallback：召回状态进入 runtime/recovery，而不是只靠文本提示。
- 采用 `openhuman` 的结构化 provenance 旁路字段：不把 citation 写进 prompt，也不引入新 memory tree。
- 不照搬参考项目的子 Agent、XML prompt、session allowlist 或治理 UI。

## 改动

- `backend/app/services/writing_agent/recovery_policy.py`
  - `summarize_longform_context` 恢复策略现在可读取 `memory_provenance.recovery.next_tools`。
  - 保留旧 `recommended_actions` 兼容路径。
  - recovery 对象新增：
    - `memory_provenance_status`
    - `memory_provenance_recovery_status`
    - `memory_source_count`

- `backend/app/services/writing_agent/run_service.py`
  - `_latest_recommended_recovery_from_steps` 透传 provenance 状态。
  - 新增 `_latest_memory_provenance_from_steps`。
  - `continuation_state` 新增 `memory_provenance` 摘要，包含 source tool、status、source count、prompt context 和 recovery next tools。

- `backend/tests/test_writing_agent_runs.py`
  - 维护阻塞 auto-plan 用例新增断言：
    - `state.recovery.memory_provenance_status == "blocked"`
    - `state.memory_provenance.status == "blocked"`
    - `state.memory_provenance.recovery.next_tools == ["repair_longform_maintenance"]`

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "auto_plan_longform_context_blocks_stale_maintenance_before_generation" -q
```

结果：`1 failed, 182 deselected`，失败点为 `KeyError: 'memory_provenance_status'`。

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "auto_plan_longform_context_blocks_stale_maintenance_before_generation" -q
```

结果：`1 passed, 182 deselected`。

相关组合：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "summarize_longform_context or longform_context_provenance or auto_plan_longform_context_blocks_stale_maintenance_before_generation or recovery_chain_after_confirmation" -q
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_tool_executor.py -k "summarize_longform_context" -q
```

结果：

- `4 passed, 179 deselected`
- `2 passed, 153 deselected`

## 仍未解决

- `truncated` provenance 目前只进入 continuation 摘要，不会自动生成更窄 query 的 retry plan。
- 知识库 provenance 还没有接入 continuation state；当前只接入 longform context，因为它已经有恢复链。
- planner 的初始计划仍然是静态工具链，尚未根据历史 provenance 自动改变后续计划。

## 下一阶段建议

Phase 7 可以做 `truncated` 的 deterministic retry plan：当 longform context provenance 显示 section 或 prompt 被截断时，生成一个只读 preview，建议缩窄 query、提高 `max_chars` 或先跑检索/维护。该阶段应保持 preview-only，避免自动扩大上下文导致 token 预算失控。
