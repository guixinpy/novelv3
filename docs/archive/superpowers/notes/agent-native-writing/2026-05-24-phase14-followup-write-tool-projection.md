# Phase14 Report: Follow-up Preview Write Tool Projection

## 本阶段目标

把 Phase13 产生的 `provenance_write_tools` 从 recommendation envelope 继续投影到 `plan_recommended_followups` 的 preview 输出中，供 UI/审批/审计层展示。

## 实现内容

- `recommended_followup_planner._followup_state_from_recommendations` 新增 `provenance_write_tools`。
- preview `tools` 仍只包含安全 follow-up 工具，不包含 `repair_longform_maintenance` 等写工具。
- 新增测试覆盖：只读 provenance recovery tool 可进入 preview `tools`，写入 tool 保留在 `recommended_followups.provenance_write_tools`。

## 设计取舍

- 本阶段只做投影，不增加执行写工具的入口。
- 写工具是否执行仍应交给 approval contract 或显式恢复计划。
- 这样能保留 Agent 的自主诊断能力，同时避免自动链路越权修改项目状态。

## 验证

- RED: `pytest tests/test_writing_agent_runs.py -k provenance_write_tools -q`
  - 初始失败：`recommended_followups` 缺少 `provenance_write_tools`。
- GREEN: `pytest tests/test_writing_agent_runs.py -k provenance_write_tools -q`
  - 结果：`1 passed, 184 deselected`
- T1: `pytest tests/test_writing_agent_runs.py -k "recommended_followup or longform_context_provenance_reports_limited_sections" -q`
  - 结果：`8 passed, 177 deselected`
- T1: `pytest tests/test_writing_agent_tool_recommendations.py -q`
  - 结果：`4 passed`

## 后续建议

下一阶段可以把该读写分离信号接到前端 Agent run drawer 或 Hermes 对话消息里，让用户看到“Agent 建议先自动诊断，另有一个需确认的修复动作”。
