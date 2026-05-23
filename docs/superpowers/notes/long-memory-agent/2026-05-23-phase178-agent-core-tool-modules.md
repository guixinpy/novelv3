# Phase178 Agent Core Tool Modules Report

## Goal

将 Writing Agent 的 preflight/planning/approval/route-inspection 核心工具拆成独立能力域模块，让 `tool_registry.py` 和 `tool_executor.py` 继续向纯聚合入口收敛。

## Scope

本阶段处理 15 个 core descriptor：

- `describe_agent_tools`
- `plan_writing_agent_run`
- `plan_dialog_intent_agent_run`
- `preview_agent_plan_approval_contract`
- `verify_agent_plan_approval_contract`
- `plan_recovery_tools`
- `plan_recommended_followups`
- `inspect_agent_slash_command_route`
- `inspect_agent_dialog_route_projection`
- `inspect_agent_route_preference_projection`
- `inspect_agent_intent_projection`
- `inspect_agent_tool_contracts`
- `inspect_agent_write_gate_coverage`
- `inspect_agent_mutation_fingerprints`
- `preflight_writing`

其中 `preflight_writing` 只迁 descriptor，仍保持 executor 注入式 special-case，不进入 static adapter。

## Non-Scope

未纳入本阶段：

- generation 域：`generate_chapter`、`prepare_generate_chapter_execution`、`execute_generate_chapter_with_approval`、`expand_outline_window`
- task queue 域：`inspect_agent_job_projection`、`plan_chapter_conflict_recovery`
- trace / longform-memory 域：`inspect_agent_trace_audit`、`inspect_agent_memory_route`、`summarize_longform_context`

## Changes

- 新增 `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - 承载 15 个 core descriptor。
  - 本地拥有 approval/write-gate 输出 schema。
- 新增 `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - 提供 `build_agent_core_tool_adapters(...)`。
  - 通过 callable provider 在 handler 执行时读取完整 static adapter metadata 和 tool name 集合，避免拍摄早期空快照。
  - 将 `preflight_writing` injected metadata 集中到 core adapter 模块内部 helper，`tool_executor.py` 仍保留对外 metadata special-case。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 聚合 `AGENT_CORE_TOOL_DESCRIPTORS`。
  - 移除 inline core descriptor 和相关 schema 常量。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 聚合 `build_agent_core_tool_adapters(...)`。
  - 移除 inline core handler 和 adapter entry。
- 更新测试：
  - `backend/tests/test_writing_agent_tool_registry.py`
  - `backend/tests/test_writing_agent_tool_executor.py`

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_core_tool_descriptors_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_core_tool_descriptors'`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_core_tool_adapters_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_core_tool_adapters'`。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_core_tool_descriptors_live_in_dedicated_module -q
```

结果：`1 passed in 0.03s`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_core_tool_adapters_live_in_dedicated_module -q
```

结果：`1 passed in 0.04s`。

## Verification

T1 registry/executor:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`131 passed in 4.26s`。

T1 core executor subset:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "agent_core or adapter_metadata_for_trace or inspect_agent_route_preference_projection or inspect_agent_tool_contracts or inspect_agent_write_gate_coverage or slash_command_route or dialog_route_projection or intent_projection or mutation_fingerprints" -q
```

结果：`12 passed, 78 deselected in 0.47s`。

T1 registry subset:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py -k "agent_core or tool_registry_has_unique_names_and_contracts or non_blocking" -q
```

结果：`2 passed, 39 deselected in 0.03s`。

T1 run-service related:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "plan_recovery_tools or plan_recommended_followups" -q
```

结果：`1 passed, 174 deselected in 0.23s`。

Compile:

```powershell
python -m compileall backend/app/services/writing_agent
```

结果：exit 0。

Hygiene:

```powershell
git diff --check
```

结果：exit 0，无输出。

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

结果：exit 1，无输出，未发现提交范围内的 DeepSeek/OpenAI 风格密钥。

无效验证记录：

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "plan_writing_agent_run or plan_dialog_intent_agent_run or preview_agent_plan_approval_contract or verify_agent_plan_approval_contract or inspect_agent_slash_command_route or inspect_agent_intent_projection" -q
```

结果：`175 deselected`，没有实际命中测试，因此不作为通过证据。

## Subagent Findings

只读子代理确认：

- 本阶段边界应限于 category=`preflight` 的 Agent plan / intent plan / approval / route inspection / contract inspection。
- `preflight_writing` 应保留 injected special-case。
- provider 必须在 handler 执行时读取完整 static adapter 集合，不能在构建 adapter dict 时拍快照。
- `_approval_tool_metadata_by_name` 不应从新模块反向 import executor 全局字典，避免循环依赖。

## Next Phase Suggestion

继续拆分剩余高价值工具域：

1. `trace` + `longform_memory`：将 `inspect_agent_trace_audit`、`inspect_agent_memory_route`、`summarize_longform_context` 独立为可编排的记忆/审计能力域。
2. `generation`：将章节生成、生成审批、outline window 扩展迁出 executor，为后续“Agent 自主生成长篇并自检”准备更清晰的生成工具边界。
