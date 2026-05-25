# Phase38: Agent Command Contracts Tool Report

## 目标

把 Hermes slash 命令控制面变成 Writing Agent 可自主调用的只读自检能力，使 Agent 能审计命令目录、投影类型、依赖工具与缺口，而不只依赖前端或对话 API。

## 变更

- 新增 `agent_command_contracts.py`：
  - `inspect_agent_command_contracts`
  - 版本：`phase38.agent_command_contracts.v1`
  - 输出：`summary`、`commands`、`gaps`、`recommended_next_tools`、`trace`
- 新增 Agent 工具：
  - descriptor: `inspect_agent_command_contracts`
  - adapter: `inspect_agent_command_contracts`
  - target type: `agent_command_contracts`
  - mutability: `read`
  - non-blocking report: enabled
- 命令自检会识别：
  - public 命令缺少 `capability_id`
  - Agent 控制命令缺少 `control_projection_type`
  - Agent 控制命令缺少 required tools
  - 命令因 descriptor/adapter 缺失不可用

## RED 证据

- `pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "agent_command_contracts or core_tool_adapters_live or static_writing_agent_tool_adapter_names or unhandled_internal" -q`
  - 失败点：
    - core adapter 列表缺少 `inspect_agent_command_contracts`
    - adapter metadata 为 `None`
    - executor 返回 `handled=False`
    - registry descriptor 为 `None`

## GREEN 证据

- `pytest backend/tests/test_agent_command_contracts.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "agent_command_contracts or core_tool_adapters_live or static_writing_agent_tool_adapter_names or unhandled_internal" -q`
  - `7 passed, 218 deselected`
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一步可以把 `inspect_agent_command_contracts` 接入 Agent 健康投影或 `/status` 推荐工具中，让用户和 Agent 都能看到命令控制面是否具备完整执行条件。
