# Phase52 报告：健康投影推荐统一控制面检查

## 目标

当 Agent 健康投影发现工具契约或命令契约缺口时，优先推荐 `inspect_agent_control_plane_readiness`，让 Agent 有统一的控制面自检入口。

## 变更

- `agent_tool_contract_gaps` 推荐工具从只推荐 `inspect_agent_tool_contracts` 调整为：
  - `inspect_agent_control_plane_readiness`
  - `inspect_agent_tool_contracts`
- `agent_command_contract_gaps` 推荐工具从只推荐 `inspect_agent_command_contracts` 调整为：
  - `inspect_agent_control_plane_readiness`
  - `inspect_agent_command_contracts`
- 命令契约缺口测试新增统一控制面检查断言。

## 验证

- `pytest backend/tests/test_writing_agent_health_projection.py -k "command_contract_gap" -q`
  - 结果：`1 passed, 4 deselected`
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "health_and_route_diagnosis_tools" -q`
  - 结果：`1 passed, 158 deselected`
- `pytest backend/tests/test_writing_agent_health_projection.py backend/tests/test_agent_control_plane_readiness.py -q`
  - 结果：`7 passed`
- `git diff --check`
  - 结果：通过；保留既有 CRLF 提示：`backend/tests/test_writing_agent_runs.py` 下次 Git 触碰时会从 CRLF 转 LF。

## 下一步建议

下一阶段可以将控制平面就绪度纳入 Trace audit 或 job projection，使后台任务和历史运行也能聚合展示控制面健康状态。
