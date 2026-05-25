# Phase205 Agent Tool Surface Report

## Scope

把 Writing Agent 工具的最小权限/可见性/读写表面暴露到 `describe_agent_tools` / `build_agent_tool_plan`，让 planner 不必只依赖工具名和完整审计工具来判断调用风险。

## Plan

见 `docs/superpowers/plans/long-memory-agent/2026-05-24-phase205-agent-tool-surface.md`。

## Reference Project Translation

- OpenHuman：将 `ToolScope` / `PermissionLevel` 思路转译为 `agent_tool_surface`。
- Hermes：保持完整 contract audit 与当前 agent surface 分离。
- OpenClaw：让上层 allow/deny/approval policy 后续可以基于稳定 surface 字段过滤工具。

## RED

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_tool_plan_exposes_agent_tool_surface or guarded_write_surface" -q`
  - 初始失败：`visible["describe_agent_tools"]` 缺少 `agent_tool_surface`。

## Implementation

- 在 `AgentToolDescriptor.to_public_dict()` 增加 `agent_tool_surface`。
- 新增 descriptor 级 surface helper：
  - `visibility`
  - `tool_scope`
  - `mutability`
  - `permission_level`
  - `requires_confirmation`
  - `parallel_safe`
- `build_agent_tool_plan()` 支持传入 `adapter_metadata_by_name`，避免 planner 只靠命名 fallback 判断真实 adapter 的读写能力。
- `describe_agent_tools`、planner、recovery planner 均接入 adapter metadata 投影。
- `writing_agent_tool_adapter_metadata_by_name()` 纳入 injected `preflight_writing`，避免注入式 read 工具被 surface 标记为 `unclassified`。
- 将 confirm/hash 常量统一放在 `tool_descriptor_types.py`，`tool_contracts` 和 `write_gate_coverage` 复用同一来源。

## Validation

- `pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_tool_plan_exposes_agent_tool_surface or guarded_write_surface or adapter_metadata_for_surface" -q`
  - 3 passed, 57 deselected.
- `pytest backend/tests/test_writing_agent_tool_executor.py -k "tool_executor_handles_describe_agent_tools or inspect_agent_tool_contracts or exposes_adapter_metadata_for_trace" -q`
  - 4 passed, 146 deselected.
- `pytest backend/tests/test_writing_agent_tool_registry.py -q`
  - 60 passed.
- `pytest backend/tests/test_writing_agent_tool_executor.py -q`
  - 150 passed.
- `pytest backend/tests/test_writing_agent_planner.py -q`
  - 7 passed.
- `pytest backend/tests/test_writing_agent_runs.py -k "recovery or auto_plan" -q`
  - 20 passed, 155 deselected.
- `pytest backend/tests/test_writing_agent_write_gate_coverage.py -q`
  - 6 passed.
- `python -m compileall backend/app/services/writing_agent`
  - passed.
- `git diff --check`
  - passed.
- Sensitive DeepSeek key-prefix scan
  - no matches after redacting the report command itself.

## Review

- 子代理审查结论：
  - Critical: 无。
  - Important 1: `preflight_writing` 是 injected read 工具，必须进入 by-name metadata，否则 `describe_agent_tools` surface 会显示 `unclassified`。已修复并补断言。
  - Important 2: 无 metadata fallback 不应把 `verify_` / `inspect_` 类只读 hash 工具误判为 `guarded_write`。已调整 fallback 顺序和 read prefix，并补 registry 断言。
  - Minor: planner/recovery planner 当前未发现实际循环导入；真实 executor 路径已补覆盖。

## Novel Progress

本阶段不推进正文生成。原因：当前阶段继续补 Agent 工具契约基础设施，为后续自主编排 Hermes/Athena/知识库/队列时的安全选择提供元数据。

## Next

- Phase206 建议继续沿 openclaw / hermes-agent / openhuman 的工具编排经验，推进 Agent tool policy 的上层过滤：按 `agent_tool_surface` 给 planner 增加 allow/deny/confirm 路由，而不是继续散落在各模块内部判断。
