# Phase47 报告：Agent Health 接入控制平面就绪度

## 目标

把 Phase46 的 `inspect_agent_control_plane_readiness` 接入 Agent 健康投影与 planner trace，使 Agent 在规划链路中直接获得控制平面是否可继续自主编排的摘要。

## 变更

- `inspect_agent_health_projection` 现在输出 `control_plane_readiness`：
  - `status`
  - `version`
  - `summary.total_gap_count`
  - `summary.tool_gap_count`
  - `summary.command_gap_count`
  - `summary.agent_control_commands`
  - `recommended_next_tools`
- 健康投影复用同一次 `tool_contracts` 和 `command_contracts` 原始快照，再交给 `inspect_agent_control_plane_readiness` 汇总，避免重复诊断。
- planner trace 的 `agent_health_projection` 现在包含 `control_plane_readiness`，但仍保持有界摘要，不暴露完整 profile policy 或完整工具列表。
- `inspect_agent_health_projection` 的工具输出 schema 已同步新增 `control_plane_readiness`。

## 验证

- `pytest backend/tests/test_writing_agent_health_projection.py -k "control_plane_readiness" -q`
  - 结果：`2 passed, 3 deselected`
- `pytest backend/tests/test_writing_agent_planner.py -k "ready_next_chapter_tool_chain" -q`
  - 结果：`1 passed, 7 deselected`
- `pytest backend/tests/test_writing_agent_health_projection.py backend/tests/test_agent_control_plane_readiness.py -q`
  - 结果：`7 passed`
- `pytest backend/tests/test_writing_agent_planner.py -q`
  - 结果：`8 passed`
- `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan or agent_run_can_plan_writing_tool_chain" -q`
  - 结果：`2 passed, 183 deselected`
- `pytest backend/tests/test_writing_agent_tool_registry.py -k "health_projection or control_plane_readiness" -q`
  - 结果：`2 passed, 65 deselected`
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_health_projection or control_plane_readiness" -q`
  - 结果：`4 passed, 155 deselected`
- `git diff --check`
  - 结果：通过；保留既有 CRLF 提示：`backend/tests/test_writing_agent_runs.py` 下次 Git 触碰时会从 CRLF 转 LF。

## 下一步建议

下一阶段可以把 `control_plane_readiness` 从 planner trace 继续投影到 Agent run / 对话结果视图，让用户和前端能看到“当前 Agent 控制平面是否适合继续自主执行”的统一状态，而不需要分别阅读工具契约和命令契约。
