# Phase42: Planner Command Contract Health

## 背景

Phase39 已经让 `inspect_agent_health_projection` 输出 `command_contracts`，但 planner 的 `_planner_health_projection` 只保留版本、状态、诊断和推荐工具，会丢掉命令控制面摘要。这样 auto-plan trace 无法复盘“命令控制面是否健康”。

本阶段让 auto-plan trace 的 `agent_health_projection` 保留 `command_contracts` 摘要。

## 成功标准

1. `build_writing_agent_run_plan(...).trace.agent_health_projection.command_contracts` 存在。
2. 该摘要包含 `summary.gap_count` 和 `summary.agent_control_commands`。
3. 不把完整 health projection 的大对象塞入 planner trace；继续保持 profile policy 等大对象不展开。

## TDD 计划

1. 后端 RED：扩展 `test_planner_builds_ready_next_chapter_tool_chain`，断言 planner health projection 中存在 `command_contracts`。
2. 实现：在 `_planner_health_projection` 中保留 `output["command_contracts"]` 的摘要。
3. 验证：
   - `pytest backend/tests/test_writing_agent_planner.py -k "planner_builds_ready_next_chapter_tool_chain" -q`
   - `pytest backend/tests/test_writing_agent_health_projection.py -q`
   - `git diff --check`

## 非目标

- 不新增 planner step。
- 不自动执行 `inspect_agent_command_contracts` 作为单独步骤。
- 不改变章节生成工具链顺序。
