# Phase46: Agent Control Plane Readiness Report

## 目标

新增 Agent-callable 的 control-plane readiness 工具，把工具契约和命令契约合并成一个可审计摘要，供 Agent 编排前判断控制面是否适合继续运行。

## 变更

- 新增 `agent_control_plane_readiness.py`：
  - 聚合 `tool_contracts` 与 `agent_command_contracts` 的 bounded summary。
  - 输出 `status`、`summary`、`diagnostics`、`recommended_next_tools`、`control_surfaces`、`trace`。
  - 有工具契约或命令契约 gap 时标记 `degraded`，无 gap 时为 `ready`。
- 新增 Agent 工具 `inspect_agent_control_plane_readiness`：
  - descriptor：`target_type=agent_control_plane_readiness`
  - adapter：static/read/preflight
  - non-blocking report tool
- 更新 core descriptor/adapter 精确清单测试，纳入新增工具。

## RED 证据

- `pytest backend/tests/test_agent_control_plane_readiness.py -q`
  - 失败原因：`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_control_plane_readiness'`。
- `pytest backend/tests/test_writing_agent_tool_registry.py -k "control_plane_readiness" -q`
  - 失败原因：descriptor 为 `None`。
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "control_plane_readiness" -q`
  - 失败原因：adapter metadata 为 `None`，executor `handled=False`。

## GREEN 证据

- `pytest backend/tests/test_agent_control_plane_readiness.py -q`
  - `2 passed`
- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_core_tool_descriptors_live_in_dedicated_module or control_plane_readiness" -q`
  - `2 passed, 65 deselected`
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "agent_core_tool_adapters_live_in_dedicated_module or control_plane_readiness or static_adapter_names_are_report_or_agent_native_tools" -q`
  - `4 passed, 155 deselected`
- `pytest backend/tests/test_agent_control_plane_readiness.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -k "control_plane_readiness" -q`
  - `5 passed, 223 deselected`
- `git diff --check`
  - 通过；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一阶段可以把 `inspect_agent_control_plane_readiness` 接入 `inspect_agent_health_projection` 或 planner trace，使 Agent 在自动规划时先引用这个更小的 readiness 摘要，而不是重复展开工具契约与命令契约的内部细节。
