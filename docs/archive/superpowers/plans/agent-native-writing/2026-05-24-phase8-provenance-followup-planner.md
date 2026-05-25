# Phase 8: Provenance Follow-up Planner

## 背景

Phase 7 已让 `memory_provenance.recovery.tools` 输出具体 retry tool params，但这些建议仍停留在工具输出内部。novelv3 已有 `plan_recommended_followups` 预览链路，本阶段将 provenance recovery tools 接入该链路。

## 参考项目取舍

- 采用 `openclaw` 的 fallback 可执行化：状态异常应转成可预览的 next action。
- 采用 `openhuman` 的结构化 citation/provenance 旁路：follow-up planner 读取 JSON 字段，而不是解析自然语言。
- 不新增工具，不自动执行，不绕过现有 follow-up confirmation。

## 范围

1. `tool_recommendations.py`
   - 从 `memory_provenance.recovery.next_tools` 读取 runtime followups。
   - 透传 `memory_provenance.recovery.tools` 作为 exact tool requests。

2. `recommended_followup_planner.py`
   - follow-up state 暴露 provenance tool requests。
   - 当 provenance 给出 exact params 时优先使用。
   - 同工具 retry 只有在 params 与源 step 不同时允许，避免 planner loop。

3. 测试
   - 截断 longform context run 后，调用 `plan_recommended_followups`。
   - 预览应返回 `summarize_longform_context`，并保留 provenance 里的 `chapter_index/query/max_chars`。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections" -q
```

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections or auto_plan_previews_recommended_followups_by_default" -q
```

## 成功标准

- provenance retry tools 能进入 `plan_recommended_followups`。
- retry params 不丢失。
- 相同工具相同参数仍被视为 planner loop。
