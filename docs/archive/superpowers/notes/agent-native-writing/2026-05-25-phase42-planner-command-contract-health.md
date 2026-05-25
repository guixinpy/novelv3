# Phase42: Planner Command Contract Health Report

## 目标

让 auto-plan trace 保留 Agent 健康投影中的 `command_contracts` 摘要，使自动规划也能复盘 Hermes 命令控制面健康状态。

## 变更

- `_planner_health_projection` 新增 `command_contracts` 字段。
- 保留的是 health projection 的命令契约摘要，不新增 planner step，不改变工具链顺序。
- `profile_policy` 等大对象仍不展开，保持 planner trace 紧凑。

## RED 证据

- `pytest backend/tests/test_writing_agent_planner.py -k "planner_builds_ready_next_chapter_tool_chain" -q`
  - 失败原因：planner trace 的 `agent_health_projection` 缺少 `command_contracts`。

## GREEN 证据

- `pytest backend/tests/test_writing_agent_planner.py -k "planner_builds_ready_next_chapter_tool_chain" -q`
  - `1 passed, 7 deselected`
- `pytest backend/tests/test_writing_agent_health_projection.py -q`
  - `3 passed`
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一步可以把命令契约摘要投影到 Agent run 详情或前端运行抽屉，让用户不仅在 `/status`，也能在每次 auto-plan 的运行记录里看到命令控制面的健康状态。
