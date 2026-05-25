# Phase 9: Max Window Retry Guard

## 背景

Phase 7/8 已能把 longform context 截断转成可预览 retry。当前 retry 策略是 `max_chars * 2`，并受 `MAX_MAX_CHARS` 限制。但当请求已经达到最大窗口仍被截断时，继续推荐同类 retry 没有意义，可能导致 Agent 反复预览同类工具。

## 参考项目取舍

- 采用 `openclaw` 的 loop/fallback budget 思路：达到边界时要明确 exhausted，而不是继续重试。
- 采用 `openhuman` 的 bounded recall 思路：不无限扩大召回窗口。
- 不新增复杂 retry counter；本阶段只处理最大窗口这一确定边界。

## 范围

修改 `backend/app/services/writing_agent/longform_context_summary.py`：

1. 当 `has_section_truncation or prompt_truncated` 且 `char_limit >= MAX_MAX_CHARS`：
   - `memory_provenance.recovery.status = "exhausted"`
   - `next_tools = []`
   - `tools = []`
   - reason 标记为 `longform_context_window_limit_exhausted`
2. 非最大窗口截断仍按 Phase 7 输出 retry tool。

测试修改 `backend/tests/test_writing_agent_runs.py`：

1. 增加 max window 截断用例。
2. 验证 `plan_recommended_followups` 不产生 retry tool。

## 验证

RED：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_exhausts_retry_at_max_window" -q
```

GREEN：

```powershell
$env:PYTHONPATH='.'; .\.venv\Scripts\python -m pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections or longform_context_provenance_exhausts_retry_at_max_window" -q
```

## 成功标准

- 最大窗口截断不再推荐同类 retry。
- 普通截断 retry 行为不回归。
