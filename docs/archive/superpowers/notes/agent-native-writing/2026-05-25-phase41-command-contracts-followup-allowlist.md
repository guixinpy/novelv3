# Phase41: Command Contracts Followup Allowlist Report

## 目标

让 Agent 推荐后继规划器接受 `inspect_agent_command_contracts`，使上游工具建议检查命令控制面时不会被安全白名单误过滤。

## 变更

- `SAFE_RECOMMENDED_FOLLOWUP_TOOLS` 新增 `inspect_agent_command_contracts`。
- `plan_recommended_followups` 现在可同时保留：
  - `inspect_agent_health_projection`
  - `inspect_agent_command_contracts`
  - `inspect_agent_route_preference_projection`
- 写入型、需要确认的 followup 仍会被拒绝。

## RED 证据

- `pytest backend/tests/test_writing_agent_tool_executor.py -k "plan_recommended_followups_allows_health_and_route_diagnosis_tools or plan_recommended_followups_rejects_write_followups" -q`
  - 失败原因：`inspect_agent_command_contracts` 被过滤，结果只保留 health 与 route preference。

## GREEN 证据

- `pytest backend/tests/test_writing_agent_tool_executor.py -k "plan_recommended_followups_allows_health_and_route_diagnosis_tools or plan_recommended_followups_rejects_write_followups" -q`
  - `2 passed, 155 deselected`
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一步可以把 `inspect_agent_command_contracts` 纳入 Agent auto-plan 的默认健康工具序列，让自动规划入口也能主动审计命令控制面。
