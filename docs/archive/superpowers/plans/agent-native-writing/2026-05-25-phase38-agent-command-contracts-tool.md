# Phase38: Agent Command Contracts Tool

## 背景

Phase34-37 已经把 `/continue`、`/status` 的控制投影契约贯通到目录、前端候选、运行时 meta、pending action params 和 Trace。但这些契约仍主要服务 UI 与对话 API，Writing Agent 自身还缺少一个可调用的只读自检工具来检查命令控制面是否完整。

本阶段新增 `inspect_agent_command_contracts`，让 Agent 能主动审计 slash 命令目录、可用性、投影类型、依赖工具与缺口，作为后续自主编排和恢复策略的输入。

## 成功标准

1. 新增服务 `agent_command_contracts.py`，输出命令控制面契约快照：
   - `status`
   - `version`
   - `summary`
   - `commands`
   - `gaps`
   - `recommended_next_tools`
   - `trace`
2. `/continue` 在快照中包含：
   - `category: agent_control`
   - `capability_id: agent.continue`
   - `control_projection_type: continue_agent_control`
   - 4 个 `required_agent_tools`
   - `contract_status: ready`
3. 会话命令允许无投影类型，并保持 `contract_status: ready`。
4. 当 public Agent 命令缺少适配器时，快照产生 gap，并推荐 `inspect_agent_tool_contracts`。
5. 工具注册：
   - descriptor: `inspect_agent_command_contracts`
   - adapter: `inspect_agent_command_contracts`
   - executor 可直接执行。

## TDD 计划

1. 后端 RED：
   - 新增 `test_agent_command_contracts.py`，直接测试快照服务。
   - 扩展 `test_writing_agent_tool_executor.py`，断言 core adapters 列表、静态 adapter 列表和 executor 可执行该工具。
   - 扩展 `test_writing_agent_tool_registry.py`，断言 descriptor 注册、target type 和 non-blocking report。
2. 实现：
   - 新建 `backend/app/services/writing_agent/agent_command_contracts.py`
   - 在 `agent_core_tool_descriptors.py` 增加 descriptor。
   - 在 `agent_core_tool_adapters.py` 增加 adapter。
3. 验证：
   - `pytest backend/tests/test_agent_command_contracts.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "agent_command_contracts or core_tool_adapters_live or static_writing_agent_tool_adapter_names or unhandled_internal" -q`
   - `git diff --check`

## 非目标

- 不改变 slash 命令运行行为。
- 不新增前端视图。
- 不把命令自检结果自动写入 Trace；本阶段只提供 Agent 可调用工具。
