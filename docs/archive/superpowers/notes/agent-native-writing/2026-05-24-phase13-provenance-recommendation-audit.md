# Phase13 Report: Provenance Recommendation Audit

## 本阶段目标

收紧 `normalize_tool_recommendations` 对 `memory_provenance.recovery` 的审计语义，避免把 `next_tools` 误解为自动 follow-up 来源。

## 实现内容

- 自动候选来源字段从 `memory_provenance.recovery.next_tools` 改为 `memory_provenance.recovery.tools`。
- 新增 `provenance_write_tools` 投影，读取 `memory_provenance.recovery.write_tools`。
- `write_tools` 不进入 `raw_recommendations`、`runtime_followups` 或 `canonical_followups`。
- 更新已有 follow-up 预览测试，使其匹配新的来源字段。

## 设计取舍

- `next_tools` 仍可保留在具体工具输出中，用于人类和 UI 理解建议顺序。
- normalizer 只从结构化 `tools` 生成自动 follow-up，保证 Agent 自动链路不会误吞需确认写操作。
- `write_tools` 作为审计/展示数据保留，后续可接入审批 UI 或 action contract。

## 验证

- RED: `pytest tests/test_writing_agent_tool_recommendations.py -k provenance -q`
  - 初始失败：`source_fields` 仍为 `memory_provenance.recovery.next_tools`，且缺少 `provenance_write_tools`。
- GREEN: `pytest tests/test_writing_agent_tool_recommendations.py -k provenance -q`
  - 结果：`1 passed, 3 deselected`
- T1: `pytest tests/test_writing_agent_tool_recommendations.py -q`
  - 结果：`4 passed`
- T1: `pytest tests/test_writing_agent_runs.py -k "longform_context_provenance_reports_limited_sections or recommended_followup" -q`
  - 结果：`7 passed, 177 deselected`
- T1: `pytest tests/test_writing_agent_memory_route.py tests/test_writing_agent_tool_executor.py -k "memory_route or inspect_agent_memory_route" -q`
  - 结果：`5 passed, 153 deselected`

## 后续建议

下一阶段可以把 `provenance_write_tools` 接入 follow-up preview 的审计输出，让前端或审批链路能展示“可自动诊断”和“需确认修复”的区别。
