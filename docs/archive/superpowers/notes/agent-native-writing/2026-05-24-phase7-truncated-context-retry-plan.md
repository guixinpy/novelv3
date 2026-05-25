# Phase 7 Report: Truncated Context Retry Plan

## 目标

将 longform context provenance 的 `truncated` 恢复建议从工具名升级为具体 retry tool params，让 Agent 后续可以直接预览或编排，而不是猜测参数。

## 参考项目取舍

- 采用 `openclaw` 的可解释 fallback：状态异常时输出具体下一步。
- 采用 `openhuman` 的 bounded recall：retry 只在现有 budget 上翻倍，并受 `MAX_MAX_CHARS` 限制。
- 不自动执行 retry，不改变审批策略，不引入模型驱动召回。

## 改动

- `backend/app/services/writing_agent/longform_context_summary.py`
  - `memory_provenance.recovery` 在 blocked 分支输出 `tools=[repair_longform_maintenance]`。
  - `memory_provenance.recovery` 在 truncated 分支输出：
    - `tool_name = summarize_longform_context`
    - `chapter_index = 当前目标章节`
    - `query = 缩小上下文窗口后重新汇总第N章写作上下文。`
    - `max_chars = min(MAX_MAX_CHARS, current_max_chars * 2)`
  - available 分支输出空 tools。

- `backend/tests/test_writing_agent_runs.py`
  - 截断 provenance 用例新增 `recovery.tools` 断言。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections" -q
```

结果：`1 failed, 182 deselected`，失败点为 `KeyError: 'tools'`。

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections" -q
```

结果：`1 passed, 182 deselected`。

相关组合：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "summarize_longform_context or longform_context_provenance or auto_plan_longform_context_blocks_stale_maintenance_before_generation or recovery_chain_after_confirmation" -q
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_knowledge_base_route.py tests/test_writing_agent_tool_executor.py -k "inspect_agent_knowledge_base_route or summarize_longform_context" -q
```

结果：

- `4 passed, 179 deselected`
- `7 passed, 154 deselected`

## 仍未解决

- retry tools 只是 provenance 里的建议，还没有进入 `plan_recovery_tools` 或 `plan_recommended_followups` 的统一预览接口。
- query 仍是确定性中文模板，后续可结合具体 section key 或用户 query 生成更精准的 retry plan。

## 下一阶段建议

Phase 8 可以把 provenance recovery tools 接入推荐后继工具规划，让 `truncated` 不再只是 context 输出内部建议，而是成为 Agent 可预览的 follow-up plan。
