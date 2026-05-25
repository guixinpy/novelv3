# Phase 10: Exhausted Context Alternatives

## 背景

Phase 9 在 longform context 达到 `MAX_MAX_CHARS` 仍截断时，停止继续推荐 `summarize_longform_context` retry。这避免了循环，但 Agent 仍缺少下一步可执行的替代诊断。

本阶段把 exhausted 状态转成可预览的只读替代工具链，优先复用现有 `inspect_agent_memory_route`，让 Agent 检查长篇记忆、检索索引和维护状态，而不是继续扩大上下文。

## 参考项目取舍

- 采用 `openclaw` 的 fallback next action 思路：达到边界后给出替代动作，而不是空状态。
- 采用 `openhuman` 的 bounded recall 思路：替代动作应诊断来源和覆盖率，不再次拉取巨大上下文。
- 不新增工具，不自动执行，不改写数据库。

## 范围

修改 `backend/app/services/writing_agent/longform_context_summary.py`：

1. 当 `memory_provenance.recovery.status == "exhausted"`：
   - `next_tools = ["inspect_agent_memory_route"]`
   - `tools` 给出 exact params：
     - `chapter_index`
     - `query`
     - `include_context_summary = false`
2. 保留 `reason = "longform_context_window_limit_exhausted"`。

测试修改 `backend/tests/test_writing_agent_runs.py`：

1. 最大窗口耗尽用例断言 recovery tools 指向 `inspect_agent_memory_route`。
2. 断言 `plan_recommended_followups` 能预览该只读替代工具。
3. 断言不再选择 `summarize_longform_context`。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_exhausts_retry_at_max_window" -q
```

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_exhausts_retry_at_max_window or longform_context_provenance_reports_limited_sections" -q
```

## 成功标准

- exhausted 不再产生 summarize retry。
- exhausted 产生 inspect memory route 替代诊断。
- follow-up planner 能消费 exact params。
