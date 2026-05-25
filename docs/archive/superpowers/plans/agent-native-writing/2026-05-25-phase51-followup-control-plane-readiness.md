# Phase51: 后继建议允许控制平面就绪度检查

## 背景

`inspect_agent_control_plane_readiness` 已成为 Agent 控制面统一自检工具，但 `plan_recommended_followups` 的安全只读工具白名单尚未包含它。这样会导致上游推荐该工具时被错误拒绝。

## 目标

允许推荐后继计划自动安排 `inspect_agent_control_plane_readiness`，使 Agent 能在发现控制面风险后继续执行只读自检。

## 范围

1. 更新推荐后继安全工具白名单。
2. 补充工具执行测试，覆盖健康、命令契约、控制平面、路由偏好四类只读诊断工具。

## 非目标

- 不改变写入工具的确认门禁。
- 不改变 followup hash 或执行策略。

## 验证

- T0: `pytest backend/tests/test_writing_agent_tool_executor.py -k "health_and_route_diagnosis_tools" -q`
- T0: `git diff --check`
