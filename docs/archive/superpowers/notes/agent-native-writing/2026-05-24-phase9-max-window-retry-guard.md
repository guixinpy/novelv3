# Phase 9 Report: Max Window Retry Guard

## 目标

给 Phase 7/8 的 longform context retry 链增加最大窗口保护：当 `max_chars` 已达到上限仍然截断时，不再推荐同类 retry，避免 Agent 反复扩大一个已经不能扩大的上下文窗口。

## 参考项目取舍

- 采用 `openclaw` 的 loop/fallback budget 思路：到达确定边界时输出 exhausted。
- 采用 `openhuman` 的 bounded recall 思路：召回窗口有硬上限，不无限扩张。
- 不新增复杂 retry counter；先处理 `MAX_MAX_CHARS` 这个确定边界。

## 改动

- `backend/app/services/writing_agent/longform_context_summary.py`
  - `_provenance_recovery` 在截断且 `char_limit >= MAX_MAX_CHARS` 时返回：
    - `status = "exhausted"`
    - `reason = "longform_context_window_limit_exhausted"`
    - `next_tools = []`
    - `tools = []`

- `backend/tests/test_writing_agent_runs.py`
  - 新增 `test_agent_run_longform_context_provenance_exhausts_retry_at_max_window`。
  - 验证最大窗口截断不产生 `summarize_longform_context` retry follow-up。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_exhausts_retry_at_max_window" -q
```

结果：`1 failed, 183 deselected`，失败点为 recovery status 仍是 `optional`。

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_exhausts_retry_at_max_window" -q
```

结果：`1 passed, 183 deselected`。

相关回归：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections or longform_context_provenance_exhausts_retry_at_max_window or recommended_followup" -q
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "summarize_longform_context or auto_plan_longform_context_blocks_stale_maintenance_before_generation or recovery_chain_after_confirmation" -q
```

结果：

- `8 passed, 176 deselected`
- `3 passed, 181 deselected`

## 仍未解决

- exhausted 后还没有给出替代策略，例如缩小 query 范围、分段章节窗口或先跑检索诊断。
- retry budget 只覆盖 max window，没有覆盖同一 run 多次相似 retry 的总次数。

## 下一阶段建议

Phase 10 应把 exhausted 状态转成更具体的替代只读建议，例如“改用查询感知检索”“按章节范围拆分上下文摘要”或“先检查 longform memory/retrieval 覆盖率”，并保持 preview-only。
