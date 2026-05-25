# Phase48 报告：Agent Run 投影控制平面就绪度

## 目标

让 Agent run 详情直接返回 `agent_control_plane_readiness`，使对话层、前端抽屉和后续 Agent 自审不必深入解析 `input.planner.trace.agent_health_projection.control_plane_readiness`。

## 变更

- `detail_payload()` 新增 `agent_control_plane_readiness`。
- 新增 `_agent_control_plane_readiness_from_run()`：
  - 从 planner trace 的健康投影读取控制平面就绪度。
  - 输出 `source`、`status`、`version`、`summary`、`recommended_next_tools`。
  - 保持有界摘要，不暴露完整工具或命令列表。
- 抽出 `_planner_health_projection_from_run()`，供旧的 `agent_command_contracts` 和新的控制平面投影共用。
- 后端 `WritingAgentRunDetail` schema 与前端 `WritingAgentRunDetail` 类型已同步新增字段。

## 验证

- `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q`
  - 结果：`1 passed, 184 deselected`
- `pytest backend/tests/test_writing_agent_planner.py -k "ready_next_chapter_tool_chain" -q`
  - 结果：`1 passed, 7 deselected`

## 下一步建议

下一阶段可以把 `agent_control_plane_readiness` 接入对话/Action result 的结果视图，让用户在自然语言触发 Agent 自动规划后能看到统一的控制面状态。
