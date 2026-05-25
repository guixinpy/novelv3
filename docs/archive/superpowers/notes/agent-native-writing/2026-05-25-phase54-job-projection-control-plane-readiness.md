# Phase54 报告：Job Projection 投影控制平面就绪度

## 目标

让 `inspect_agent_job_projection` 在选中后台任务时展示关联 WritingAgentRun 的控制面就绪度，覆盖长篇批处理和异步写作任务的排障入口。

## 变更

- `selected_task.control_plane_readiness` 新增最新关联 run 的控制面摘要。
- `selected_task.agent_runs[*].control_plane_readiness` 新增每个关联 run 的有界控制面摘要。
- 当 selected task 的控制面降级或存在 gap 时，`recommended_tools` 返回：
  - `inspect_agent_control_plane_readiness`
  - `inspect_agent_trace_audit`
- 失败/取消任务的恢复建议仍优先返回 `inspect_agent_trace_audit` 与 `plan_recovery_tools`。

## 验证

- `pytest backend/tests/test_writing_agent_job_projection.py -k "active_control_plane" -q`
  - 结果：`1 passed, 3 deselected`
- `pytest backend/tests/test_writing_agent_trace_audit.py -k "control_plane_readiness" -q`
  - 结果：`1 passed, 6 deselected`
- `pytest backend/tests/test_writing_agent_job_projection.py -q`
  - 结果：`4 passed`
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_job_projection" -q`
  - 结果：`3 passed, 156 deselected`
- `git diff --check`
  - 结果：通过；保留既有 CRLF 提示：`backend/tests/test_writing_agent_runs.py` 下次 Git 触碰时会从 CRLF 转 LF。

## 下一步建议

下一阶段可以减少 `run_service`、`agent_trace_audit`、`agent_job_projection` 中重复的控制面摘要提取逻辑，抽成单一投影模块，降低后续 Agent 控制面字段演进成本。
