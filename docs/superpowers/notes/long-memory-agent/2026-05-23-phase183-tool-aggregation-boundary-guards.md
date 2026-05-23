# Phase183 Tool Aggregation Boundary Guards Report

## Goal

为 Writing Agent 工具聚合层增加静态边界守护，防止 `tool_registry.py` / `tool_executor.py` 后续重新内联 descriptor 或 adapter 构造，并移除历史 re-export 依赖。

## Scope

本阶段处理聚合层边界：

- `tool_registry.py` 不再运行时导入 `AgentToolDescriptor`。
- `tool_executor.py` 不再运行时导入 `WritingAgentToolAdapter`、`WritingAgentToolContext`、`PreflightWriting`。
- 消费方从源模块导入类型：
  - `AgentToolDescriptor` 来自 `tool_descriptor_types`。
  - `WritingAgentToolContext` 来自 `tool_adapter_types`。

## Changes

- 新增 `backend/tests/test_writing_agent_tool_aggregation_boundaries.py`
  - 检查 `tool_registry.py` 不包含 `AgentToolDescriptor(...)`、`object_schema`、descriptor runtime import。
  - 检查 `tool_executor.py` 不包含 `WritingAgentToolAdapter`。
  - 使用 AST 检查 app 内部不再从聚合模块导入 `AgentToolDescriptor` / `WritingAgentToolContext`。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 移除 `AgentToolDescriptor` 运行时 import。
  - 聚合层本地 annotation 改为 `Any`。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 只从 `tool_adapter_types` 运行时导入 `WritingAgentToolExecutionResult`。
  - `context`、`preflight_writing` 与 `_STATIC_TOOL_ADAPTERS` annotation 改为 `Any`。
- 更新 `backend/app/services/writing_agent/tool_contracts.py`
  - `AgentToolDescriptor` 改从 `tool_descriptor_types` 导入。
- 更新 `backend/app/services/writing_agent/write_gate_coverage.py`
  - `AgentToolDescriptor` 改从 `tool_descriptor_types` 导入。
- 更新 `backend/app/services/writing_agent/run_service.py`
  - `WritingAgentToolContext` 改从 `tool_adapter_types` 导入。
- 更新 `backend/tests/test_writing_agent_tool_executor.py`
  - `WritingAgentToolContext` 改从 `tool_adapter_types` 导入。

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py -q
```

结果：失败 2 项：

- `tool_registry.py` 仍从 `tool_descriptor_types` 运行时导入 `AgentToolDescriptor`。
- `tool_executor.py` 仍导入/标注 `WritingAgentToolAdapter`。

调试中发现两个历史 re-export 耦合：

- `tool_contracts.py` / `write_gate_coverage.py` 从 `tool_registry.py` 导入 `AgentToolDescriptor`。
- `run_service.py` 从 `tool_executor.py` 导入 `WritingAgentToolContext`。

这些耦合点已纳入边界测试。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py -q
```

结果：`4 passed in 0.67s`。

## Verification

T1 registry/executor：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`141 passed in 3.90s`。

Compile：

```powershell
python -m compileall backend/app/services/writing_agent
```

结果：exit 0。

Final combined T1：

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`145 passed in 5.02s`。

Hygiene：

```powershell
git diff --check
```

结果：exit 0，无输出。

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

结果：exit 1，无输出，未发现提交范围内的 DeepSeek/OpenAI 风格密钥。

## Next Phase Suggestion

当前工具描述和执行聚合层已经有边界守护。下一阶段可以开始评估 legacy Hermes action 的 Agent-native 迁移设计：

- 先设计 `generate_setup` / `generate_storyline` / `generate_outline` 的审批与写入契约。
- 再决定是否补 static adapter，而不是直接让 executor 调旧 action service。
