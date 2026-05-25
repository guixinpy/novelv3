# Phase14: Follow-up Preview Write Tool Projection

## 背景

Phase13 已让 recommendation normalizer 输出 `provenance_write_tools`，但 follow-up preview 还只保留 `provenance_recovery_tools`。这会导致 UI/审计层只能看到自动诊断工具，看不到同一条 recovery 下建议但需要确认的写入修复工具。

## 假设

- 自动 follow-up preview 的 `tools` 仍只能包含安全工具。
- `provenance_write_tools` 应保留在 `recommended_followups` 中，供审批 UI、审计视图或后续 plan approval contract 使用。
- 本阶段不新增写工具执行能力。

## 目标

1. `plan_recommended_followups` 输出的 `recommended_followups` 包含 `provenance_write_tools`。
2. `provenance_write_tools` 不进入 preview `tools`。
3. 现有安全 follow-up 执行行为不变。

## 验证

- T0: `pytest tests/test_writing_agent_runs.py -k provenance_write_tools -q`
- T1: `pytest tests/test_writing_agent_runs.py -k "recommended_followup or longform_context_provenance_reports_limited_sections" -q`

## 风险控制

- 只投影数据，不执行写工具。
- 不改变 `SAFE_RECOMMENDED_FOLLOWUP_TOOLS`。
- 不改变 plan hash 的工具执行清单，避免影响已确认计划的执行语义。
