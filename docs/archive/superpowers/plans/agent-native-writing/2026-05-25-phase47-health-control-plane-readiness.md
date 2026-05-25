# Phase47: Agent Health 投影接入控制平面就绪度

## 背景

Phase46 已新增 `inspect_agent_control_plane_readiness`，可以把 Agent 工具契约与对话命令控制面汇总成一个可读的就绪度快照。但该能力目前仍是独立工具，planner 与健康投影不会自然消费它，Agent 在规划前仍需要分别理解 `tool_contracts` 与 `command_contracts`。

## 目标

让 `inspect_agent_health_projection` 暴露一个有界的 `control_plane_readiness` 摘要，并让 planner trace 携带该摘要，使 Agent 的上层计划链路可以直接判断“控制平面是否适合继续自主编排”。

## 范围

1. 在健康投影中复用已有工具契约和命令契约快照，避免重复构建同一类诊断。
2. 输出有界的 `control_plane_readiness` 摘要：状态、gap 计数、Agent 控制命令覆盖与推荐下一步工具。
3. 在 planner trace 的 `agent_health_projection` 中透出该摘要。
4. 同步工具描述符的输出 schema。

## 非目标

- 不改变写入执行门禁。
- 不改 UI 展示。
- 不新增完整端到端流程。

## 验证

- T0: `pytest backend/tests/test_writing_agent_health_projection.py -k "control_plane_readiness" -q`
- T0: `pytest backend/tests/test_writing_agent_planner.py -k "ready_next_chapter_tool_chain" -q`
- T0: `git diff --check`
