# Phase53 报告：Trace Audit 投影控制平面就绪度

## 目标

让 `inspect_agent_trace_audit` 能直接读取并投影 planner trace 中的 `control_plane_readiness`，使历史运行审计也能看到 Agent 控制面状态。

## 变更

- `inspect_agent_trace_audit` 顶层新增 `control_plane_readiness`。
- `audit` 中新增：
  - `control_plane_status`
  - `control_plane_gap_count`
- 新增 `_control_plane_readiness_from_run()`，从 `run.input.planner.trace.agent_health_projection.control_plane_readiness` 提取有界摘要。
- 当 run 未失败/阻塞但控制面降级或存在 gap 时，`recommended_actions` 推荐：
  - `inspect_agent_control_plane_readiness`
- 失败/阻塞 run 的恢复建议优先级保持不变。

## 验证

- `pytest backend/tests/test_writing_agent_trace_audit.py -k "control_plane_readiness" -q`
  - 结果：`1 passed, 6 deselected`
- `pytest backend/tests/test_writing_agent_health_projection.py -q`
  - 结果：`5 passed`
- `pytest backend/tests/test_writing_agent_trace_audit.py -q`
  - 结果：`7 passed`
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_trace_audit or control_plane_readiness" -q`
  - 结果：`4 passed, 155 deselected`
- `git diff --check`
  - 结果：通过；保留既有 CRLF 提示：`backend/tests/test_writing_agent_runs.py` 下次 Git 触碰时会从 CRLF 转 LF。

## 下一步建议

下一阶段可以把同一控制面摘要接入 `inspect_agent_job_projection`，让后台任务投影也能显示 Agent 控制面健康状态，便于长篇批处理和异步任务排障。
