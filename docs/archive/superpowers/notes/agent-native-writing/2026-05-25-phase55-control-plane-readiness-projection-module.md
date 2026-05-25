# Phase55 报告：控制平面就绪度投影模块

## 目标

把 run detail、Trace audit、Job projection 中重复的控制面就绪度解析逻辑抽为共享模块，使 Agent 控制面字段后续演进只需要维护一处。

## 变更

- 新增 `backend/app/services/writing_agent/control_plane_readiness_projection.py`：
  - `CONTROL_PLANE_READINESS_SOURCE`
  - `control_plane_readiness_from_run_input(run_input)`
  - `control_plane_readiness_needs_attention(value)`
- 新增 `backend/tests/test_control_plane_readiness_projection.py`，覆盖有界摘要输出与降级判定。
- 替换三处调用：
  - `run_service.detail_payload()` 的 `agent_control_plane_readiness`
  - `inspect_agent_trace_audit()` 的控制面摘要与推荐动作判定
  - `inspect_agent_job_projection()` 的 selected task / agent run 控制面摘要与推荐工具判定
- 移除三处重复的私有控制面解析函数。

## 验证

- `pytest backend/tests/test_control_plane_readiness_projection.py -q`
  - 结果：`2 passed`
- `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q`
  - 结果：`1 passed, 184 deselected`
- `pytest backend/tests/test_writing_agent_trace_audit.py -k "control_plane_readiness" -q`
  - 结果：`1 passed, 6 deselected`
- `pytest backend/tests/test_writing_agent_job_projection.py -k "active_control_plane" -q`
  - 结果：`1 passed, 3 deselected`
- `pytest backend/tests/test_control_plane_readiness_projection.py backend/tests/test_writing_agent_trace_audit.py backend/tests/test_writing_agent_job_projection.py -q`
  - 结果：`13 passed`
- `pytest backend/tests/test_writing_agent_runs.py -k "agent_run_detail_exposes_agent_profile_projection_for_auto_plan or recommended_followup" -q`
  - 结果：`8 passed, 177 deselected`
- `git diff --check`
  - 结果：通过；保留既有 CRLF 提示：`backend/tests/test_writing_agent_runs.py` 下次 Git 触碰时会从 CRLF 转 LF。
- `rg "_agent_control_plane_readiness_from_run|_control_plane_readiness_from_run|_control_plane_needs_attention\\(" backend/app/services/writing_agent`
  - 结果：无匹配，重复私有实现已移除。

## 下一步建议

下一阶段可以用同样方式抽取 `agent_command_contracts` 的 run 投影逻辑，继续减少控制面相关重复代码，并让命令契约摘要成为 Trace / Job / Run 可共享能力。
