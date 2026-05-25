# Phase55: 控制平面就绪度投影模块

## 背景

`run_service`、`agent_trace_audit`、`agent_job_projection` 已经都需要从 `run.input.planner.trace.agent_health_projection.control_plane_readiness` 提取有界摘要。当前三处重复实现，后续字段调整容易出现不一致。

## 目标

新增共享纯函数模块，统一控制面就绪度提取与降级判定。

## 范围

1. 新增 `control_plane_readiness_projection.py`。
2. 提供：
   - `CONTROL_PLANE_READINESS_SOURCE`
   - `control_plane_readiness_from_run_input(run_input)`
   - `control_plane_readiness_needs_attention(value)`
3. 替换三个调用点中的重复逻辑：
   - `run_service`
   - `agent_trace_audit`
   - `agent_job_projection`

## 非目标

- 不改变 API 输出结构。
- 不改变推荐工具策略。
- 不移动 command contracts 投影逻辑。

## 验证

- T0: `pytest backend/tests/test_control_plane_readiness_projection.py -q`
- T1: `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q`
- T1: `pytest backend/tests/test_writing_agent_trace_audit.py -k "control_plane_readiness" -q`
- T1: `pytest backend/tests/test_writing_agent_job_projection.py -k "active_control_plane" -q`
- T0: `git diff --check`
