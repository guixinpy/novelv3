# Phase51 报告：后继建议允许控制平面就绪度检查

## 目标

让 `plan_recommended_followups` 能安排 `inspect_agent_control_plane_readiness`，避免 Agent 收到控制面自检建议后被白名单错误拒绝。

## 变更

- `SAFE_RECOMMENDED_FOLLOWUP_TOOLS` 新增 `inspect_agent_control_plane_readiness`。
- 工具执行测试覆盖健康投影、控制平面就绪度、命令契约、路由偏好四类只读诊断工具可被推荐后继安排。

## 验证

- `pytest backend/tests/test_writing_agent_tool_executor.py -k "health_and_route_diagnosis_tools" -q`
  - 结果：`1 passed, 158 deselected`
- `pytest backend/tests/test_writing_agent_runs.py -k "recommended_followup" -q`
  - 结果：`7 passed, 178 deselected`

## 下一步建议

下一阶段可以让健康投影在控制面降级时直接把 `inspect_agent_control_plane_readiness` 纳入 `recommended_tools`，使自检工具本身成为统一入口，而不是只推荐更底层的契约检查工具。
