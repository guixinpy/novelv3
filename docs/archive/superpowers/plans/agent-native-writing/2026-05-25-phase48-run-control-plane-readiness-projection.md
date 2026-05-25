# Phase48: Agent Run 投影控制平面就绪度

## 背景

Phase47 已让 planner trace 携带 `agent_health_projection.control_plane_readiness`。但 Agent run API 目前只投影了 `agent_command_contracts`，上层对话、前端抽屉或后续 Agent 自审仍需要深入解析 run input 的 planner trace。

## 目标

在 `WritingAgentRunDetail` 中直接暴露 `agent_control_plane_readiness`，让运行结果拥有统一的 Agent 控制面摘要。

## 范围

1. 从 run input 的 planner trace 中提取 `agent_health_projection.control_plane_readiness`。
2. 输出有界字段：source、status、version、summary、recommended_next_tools。
3. 更新后端响应 schema 与前端 API 类型。
4. 补充 Agent run detail 测试。

## 非目标

- 不新增 UI 展示。
- 不改变 Agent 执行逻辑。
- 不改变 command contracts 的旧投影，保持兼容。

## 验证

- T0: `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q`
- T0: `git diff --check`
