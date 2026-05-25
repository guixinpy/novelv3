# Phase54: Job Projection 投影控制平面就绪度

## 背景

Trace audit 已能显示 planner trace 中的控制面状态，但 `inspect_agent_job_projection` 仍只展示后台任务的传统 `control_plane` 和关联 run 列表。对于长篇批处理和异步写作任务，用户仍无法从任务投影直接判断 Agent 控制面是否健康。

## 目标

让选中后台任务的投影包含最新关联 WritingAgentRun 的 `control_plane_readiness` 摘要，并在控制面降级时推荐统一自检工具。

## 范围

1. 在 selected task 中新增 `control_plane_readiness`。
2. 在 `agent_runs` 列表中给每个 run 附带有界 `control_plane_readiness` 摘要。
3. 当 selected task 的控制面降级或存在 gap 时，`recommended_tools` 推荐 `inspect_agent_control_plane_readiness`。

## 非目标

- 不改变后台任务执行逻辑。
- 不改变队列筛选。
- 不暴露完整 planner trace。

## 验证

- T0: `pytest backend/tests/test_writing_agent_job_projection.py -k "active_control_plane" -q`
- T0: `pytest backend/tests/test_writing_agent_trace_audit.py -k "control_plane_readiness" -q`
- T0: `git diff --check`
