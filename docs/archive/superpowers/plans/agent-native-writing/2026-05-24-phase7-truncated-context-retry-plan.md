# Phase 7: Truncated Context Retry Plan

## 背景

Phase 5/6 已能把 longform context 的 `truncated` 状态暴露给 Agent runtime，但当前恢复建议只有工具名 `summarize_longform_context`，还不能直接形成可预览的 retry tool params。Agent 下一步仍需要猜测如何重试。

本阶段将 `truncated` fallback 变成可执行但不自动执行的只读 retry plan。

## 参考项目取舍

- 采用 `openclaw` 的状态化 fallback 和可解释 next action：失败/截断时输出具体下一步，而不是让模型猜。
- 采用 `openhuman` 的 bounded recall：retry plan 仍受 `MAX_MAX_CHARS` 限制，不无限扩大上下文。
- 不引入主动自动恢复，不自动执行 retry，不改变审批策略。

## 范围

修改 `backend/app/services/writing_agent/longform_context_summary.py`：

1. `memory_provenance.recovery` 在 `truncated` 时增加 `tools`。
2. retry tool 为 `summarize_longform_context`。
3. retry params 包含：
   - `chapter_index`
   - `query`
   - `max_chars`
4. `max_chars` 使用 `min(MAX_MAX_CHARS, current_max_chars * 2)`，避免 token 预算失控。

测试修改 `backend/tests/test_writing_agent_runs.py`：

1. 现有截断用例断言 `recovery.tools[0]` 是具体 retry tool。
2. 验证 max chars 从 `1200` 提升到 `2400`。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections" -q
```

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections or summarize_longform_context" -q
```

## 成功标准

- truncated provenance 输出具体 retry tool。
- retry 仍是只读工具。
- retry max chars 有上限。
