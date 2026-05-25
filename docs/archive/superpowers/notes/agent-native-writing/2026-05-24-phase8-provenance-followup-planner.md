# Phase 8 Report: Provenance Follow-up Planner

## 目标

把 `memory_provenance.recovery.tools` 接入现有 `plan_recommended_followups` 预览链路，使截断上下文的 retry 建议能成为 Agent 可预览的后继工具。

## 参考项目取舍

- 采用 `openclaw` 的 fallback next-action 结构化思想：异常状态必须能转成下一步工具。
- 采用 `openhuman` 的 provenance 旁路字段：follow-up planner 读取 JSON，不解析文本。
- 不新增自动执行，不绕过 follow-up hash/confirmation。

## 改动

- `backend/app/services/writing_agent/tool_recommendations.py`
  - 读取 `memory_provenance.recovery.tools`。
  - 将 `memory_provenance.recovery.next_tools` 纳入 source fields 和 canonical followups。
  - 将 exact provenance tool requests 透传到 recommendations。

- `backend/app/services/writing_agent/recommended_followup_planner.py`
  - follow-up state 暴露 `provenance_recovery_tools`。
  - exact provenance params 优先于通用 `_params_for_followup`。
  - 同工具 retry 只有 params 与源 step 不同时允许，避免同参循环。
  - 选中工具的 `planner.step_index` 改为实际 selected index，避免前面候选被拒绝后跳号。

- `backend/tests/test_writing_agent_runs.py`
  - 截断 longform context 用例新增 `plan_recommended_followups` 预览断言。
  - 验证 retry params 保留 `chapter_index/query/max_chars`。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections" -q
```

结果：`1 failed, 182 deselected`，最初失败为 follow-up preview `status == "ready"`，说明旧 planner 看不到 provenance recovery tools。

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections" -q
```

结果：`1 passed, 182 deselected`。

相关回归：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "recommended_followup or longform_context_provenance_reports_limited_sections" -q
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "summarize_longform_context or longform_context_provenance or auto_plan_longform_context_blocks_stale_maintenance_before_generation or recovery_chain_after_confirmation" -q
```

结果：

- `7 passed, 176 deselected`
- `4 passed, 179 deselected`

## 仍未解决

- provenance follow-up 目前只支持 output 内部已经给出的 exact tools；还没有自动为知识库 sparse、retrieval sparse 等状态生成 follow-up。
- 同工具不同参数 retry 已允许，但还没有统一的 retry count/loop budget。
- 还未将 provenance follow-up 状态展示到前端。

## 下一阶段建议

Phase 9 应加入 provenance retry loop budget，避免 Agent 在截断上下文上反复 preview/retry；可以复用 Phase 3 的 loop risk 思路，但范围限定在 provenance follow-up retry。
