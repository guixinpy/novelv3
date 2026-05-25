# Phase41: Command Contracts Followup Allowlist

## 背景

Phase38/39/40 已经让 `inspect_agent_command_contracts` 成为 Agent 可调用工具、健康投影子视图和命令目录依赖。但推荐后继规划器的安全白名单还没有允许该工具。如果上游工具建议下一步检查命令控制面，`plan_recommended_followups` 会把它过滤掉。

本阶段把 `inspect_agent_command_contracts` 纳入只读推荐 followup 白名单。

## 成功标准

1. `plan_recommended_followups` 接受 `inspect_agent_command_contracts`。
2. 它仍然拒绝需要确认的写入型 followup。
3. 推荐 followup 结果中能同时保留 health、route preference、command contracts 三类诊断工具。

## TDD 计划

1. 后端 RED：扩展 `test_plan_recommended_followups_allows_health_and_route_diagnosis_tools`，把 `inspect_agent_command_contracts` 放入 canonical followups 并断言被保留。
2. 实现：在 `SAFE_RECOMMENDED_FOLLOWUP_TOOLS` 加入 `inspect_agent_command_contracts`。
3. 验证：
   - `pytest backend/tests/test_writing_agent_tool_executor.py -k "plan_recommended_followups_allows_health_and_route_diagnosis_tools or plan_recommended_followups_rejects_write_followups" -q`
   - `git diff --check`

## 非目标

- 不改变推荐生成逻辑。
- 不自动把该工具插入所有计划。
- 不放宽写入工具保护。
