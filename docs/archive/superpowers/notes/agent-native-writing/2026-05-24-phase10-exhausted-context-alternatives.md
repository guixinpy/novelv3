# Phase 10 Report: Exhausted Context Alternatives

## 目标

当 longform context 已达到最大上下文窗口仍然截断时，Agent 不应继续尝试扩大 `summarize_longform_context`，但也不能只得到空恢复建议。本阶段将 exhausted 状态转成可预览的只读替代诊断工具。

## 参考项目取舍

- 采用 `openclaw` 的 fallback next action 思路：达到边界后仍给出可解释下一步。
- 采用 `openhuman` 的 bounded recall 思路：替代工具诊断覆盖率，不再拉取巨大上下文。
- 不新增工具，不自动执行，不改写数据库。

## 改动

- `backend/app/services/writing_agent/longform_context_summary.py`
  - `memory_provenance.recovery.status == "exhausted"` 时：
    - `next_tools = ["inspect_agent_memory_route"]`
    - `tools` 给出 exact params：
      - `chapter_index`
      - `query = 最大上下文窗口仍截断，诊断第N章长篇记忆与检索覆盖。`
      - `include_context_summary = false`

- `backend/tests/test_writing_agent_runs.py`
  - 最大窗口耗尽用例验证 exhausted recovery tools。
  - 验证 `plan_recommended_followups` 能预览 `inspect_agent_memory_route`。
  - 验证不再选择 `summarize_longform_context`。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_exhausts_retry_at_max_window" -q
```

结果：`1 failed, 183 deselected`，失败点为 `next_tools == []`。

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_exhausts_retry_at_max_window" -q
```

结果：`1 passed, 183 deselected`。

相关回归：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections or longform_context_provenance_exhausts_retry_at_max_window or recommended_followup" -q
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_tool_executor.py -k "inspect_agent_memory_route or summarize_longform_context" -q
```

结果：

- `8 passed, 176 deselected`
- `4 passed, 151 deselected`

## 仍未解决

- `inspect_agent_memory_route` 目前主要是覆盖率和维护诊断，还没有给出“按章节分片重建上下文”的具体计划。
- exhausted 后的替代诊断还未展示到前端 Agent run drawer。

## 下一阶段建议

Phase 11 应强化 `inspect_agent_memory_route` 自身的 Agent-native 输出：让它在 longform context exhausted 场景下返回具体的 coverage gaps、retrieval health、recommended read-only next steps，并形成统一 provenance。
