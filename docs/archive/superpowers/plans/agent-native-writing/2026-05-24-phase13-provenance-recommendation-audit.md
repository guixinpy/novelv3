# Phase13: Provenance Recommendation Audit

## 背景

Phase12 已让 `inspect_agent_memory_route` 在检索覆盖退化时返回 `recovery.tools` 和 `recovery.write_tools`。但 `normalize_tool_recommendations` 当前只读取 `recovery.tools`，却把来源字段记录为 `memory_provenance.recovery.next_tools`，审计语义不精确。随着 Agent 自动规划能力增强，这种含混会让读操作和需确认写操作的边界变弱。

## 假设

- `recovery.tools` 表示可进入自动 follow-up 的只读或安全诊断工具。
- `recovery.write_tools` 表示可推荐给用户确认的写入型修复工具，不应进入自动 follow-up。
- `next_tools` 可以继续作为人类可读的建议顺序，但 normalizer 不应把它作为自动执行来源。

## 目标

1. `normalize_tool_recommendations` 的 `source_fields` 使用 `memory_provenance.recovery.tools` 表示自动候选来源。
2. `memory_provenance.recovery.write_tools` 被投影到 `provenance_write_tools`，用于审计和 UI 展示。
3. 写入型 provenance 工具不进入 `runtime_followups` 或 `canonical_followups`。

## 验证

- T0: `pytest tests/test_writing_agent_tool_recommendations.py -k provenance -q`
- T1: `pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections or recommended_followup" -q`
- T1: `pytest tests/test_writing_agent_memory_route.py tests/test_writing_agent_tool_executor.py -k "memory_route or inspect_agent_memory_route" -q`

## 风险控制

- 只调整 recommendation envelope，不改变工具执行器。
- 保持 provenance `tools` 的 exact params 复用逻辑不变。
- 保持旧字段 `next_tools` 在具体工具输出中可见，但不再作为 normalizer 自动候选来源。
