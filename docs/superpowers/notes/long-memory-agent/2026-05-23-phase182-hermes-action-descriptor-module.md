# Phase182 Hermes Action Descriptor Module Report

## Goal

将 Writing Agent registry 中剩余 legacy Hermes action descriptors 拆成独立模块，让 `tool_registry.py` 不再内联任何 `AgentToolDescriptor(...)`。

## Scope

本阶段处理 3 个 legacy public descriptors：

- `generate_setup`
- `generate_storyline`
- `generate_outline`

## Non-Scope

本阶段未新增 static adapter，也未改变 Hermes action runtime：

- `generate_setup`
- `generate_storyline`
- `generate_outline`

它们仍由旧 action 路径承接；在 Writing Agent tool executor 中继续保持 unhandled。

## Changes

- 新增 `backend/app/services/writing_agent/hermes_action_tool_descriptors.py`
  - 承载 `HERMES_ACTION_AGENT_TOOL_DESCRIPTORS`。
  - 保留三个 legacy Hermes descriptor 的 module、category、target type、sort key、availability checks 与 output schema。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 聚合 `HERMES_ACTION_AGENT_TOOL_DESCRIPTORS`。
  - 移除最后 3 个 inline `AgentToolDescriptor(...)`。
  - 移除不再使用的 `_STATUS_OUTPUT` 和 `_object_schema`。
- 更新 `backend/tests/test_writing_agent_tool_registry.py`
  - 新增 Hermes action descriptor module boundary test。

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_hermes_action_tool_descriptors_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.hermes_action_tool_descriptors'`。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_hermes_action_tool_descriptors_live_in_dedicated_module -q
```

结果：`1 passed in 0.03s`。

## Verification

Legacy behavior subset：

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_generation_tools_unhandled or slash_command_route or static_writing_agent_tool_adapter_names" -q
```

结果：`2 passed, 94 deselected in 0.19s`。

T1 registry/executor：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`141 passed in 3.97s`。

Compile：

```powershell
python -m compileall backend/app/services/writing_agent
```

结果：exit 0。

Hygiene：

```powershell
git diff --check
```

结果：exit 0，无输出。

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

结果：exit 1，无输出，未发现提交范围内的 DeepSeek/OpenAI 风格密钥。

## Subagent Findings

只读子代理确认：

- registry 剩余 inline descriptors 只有 `generate_setup`、`generate_storyline`、`generate_outline`。
- 这三个工具都属于 legacy Hermes action descriptors。
- Phase182 不应新增 static adapter，不应让 `tool_executor.py` 调 `ActionExecutionService`。
- slash/dialog route projection 中的旧命令映射应保持现状。

## Next Phase Suggestion

当前 `tool_registry.py` 和 `tool_executor.py` 已经基本成为聚合层。下一阶段建议从“工具化质量”转向“Agent 工具契约巡检”：

- 增加一个面向维护者的静态边界测试，确保 registry/executor 不再重新出现 inline descriptor/adapter。
- 或开始梳理 legacy Hermes action 到 Agent-native 工具的迁移路线，但应先设计审批与写入契约，不能直接补 unguarded adapter。
