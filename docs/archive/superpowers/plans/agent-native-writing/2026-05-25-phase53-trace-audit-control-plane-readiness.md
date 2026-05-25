# Phase53: Trace Audit 投影控制平面就绪度

## 背景

Phase47-52 已让控制平面就绪度进入健康投影、planner trace、Agent run API、对话视图、抽屉和后继建议。但 Trace audit 仍不能直接看到 run 规划时的控制面状态，导致历史排障仍要手动读取 `run.input.planner.trace`。

## 目标

让 `inspect_agent_trace_audit` 暴露有界的 `control_plane_readiness` 摘要，并在控制面降级但 run 未失败时推荐 `inspect_agent_control_plane_readiness`。

## 范围

1. 从 `WritingAgentRun.input.planner.trace.agent_health_projection.control_plane_readiness` 提取摘要。
2. `audit` 中记录 `control_plane_status` 与 `control_plane_gap_count`。
3. 顶层输出 `control_plane_readiness`。
4. 对成功但控制面降级的 run，推荐统一自检工具。

## 非目标

- 不改变失败/阻塞 run 的恢复推荐优先级。
- 不暴露完整工具或命令列表。
- 不改前端 UI。

## 验证

- T0: `pytest backend/tests/test_writing_agent_trace_audit.py -k "control_plane_readiness" -q`
- T0: `pytest backend/tests/test_writing_agent_health_projection.py -q`
- T0: `git diff --check`
