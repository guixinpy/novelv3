# Phase179 Agent Memory Trace Tool Modules Report

## Goal

将 Writing Agent 的 Trace 审计、长篇记忆路由、上下文摘要和长篇维护修复工具拆成独立能力域模块，让长期记忆相关能力更接近 Agent 可编排工具，而不是散落在通用 executor/registry 内。

## Scope

本阶段处理 4 个工具：

- `inspect_agent_trace_audit`
- `inspect_agent_memory_route`
- `summarize_longform_context`
- `repair_longform_maintenance`

其中前三个为只读报告工具，保持 `non_blocking_report=True`；`repair_longform_maintenance` 是维护写入工具，保持 `mutability=write` 且不是 non-blocking report。

## Non-Scope

未纳入本阶段：

- `inspect_agent_job_projection`、`plan_chapter_conflict_recovery`：task queue / job projection 域。
- longform batch 工具：已在 `longform_tool_descriptors.py` / `longform_tool_adapters.py`。
- knowledge base / world model 工具：已有独立能力域模块。
- `backfill_outline_gaps`：outline maintenance，不属于 longform memory maintenance。
- generation 工具：下一阶段可单独处理。

## Changes

- 新增 `backend/app/services/writing_agent/agent_memory_trace_tool_descriptors.py`
  - 承载 4 个 memory/trace descriptor。
- 新增 `backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py`
  - 承载 4 个 adapter handler。
  - 将 `_json_safe_output()` 留在该模块内，确保 `repair_longform_maintenance` 输出仍可序列化。
  - 保留 `query` 从 `params["query"]` 或 `command_args` fallback 的现有行为。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 聚合 `AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS`。
  - 移除 inline memory/trace descriptor。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 聚合 `AGENT_MEMORY_TRACE_TOOL_ADAPTERS`。
  - 移除 inline memory/trace handler 和 adapter entry。
- 更新测试：
  - 新增 memory/trace descriptor module boundary test。
  - 新增 memory/trace adapter module boundary test。
  - 补 `summarize_longform_context` static adapter / dispatch 覆盖。
  - 补 `repair_longform_maintenance` JSON-safe 输出回归测试。

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_memory_trace_tool_descriptors_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_memory_trace_tool_descriptors'`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_memory_trace_tool_adapters_live_in_dedicated_module -q
```

结果：失败，`ModuleNotFoundError: No module named 'app.services.writing_agent.agent_memory_trace_tool_adapters'`。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_memory_trace_tool_descriptors_live_in_dedicated_module -q
```

结果：`1 passed in 0.03s`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_agent_memory_trace_tool_adapters_live_in_dedicated_module -q
```

结果：`1 passed in 0.23s`。

补充回归：

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "summarize_longform_context or repair_longform_maintenance" -q
```

结果：`5 passed, 89 deselected in 0.47s`。

## Verification

T1 registry/executor:

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`136 passed in 4.33s`。

T1 memory/trace subset:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "agent_memory_trace or inspect_agent_memory_route or inspect_agent_trace_audit or summarize_longform_context or repair_longform_maintenance" -q
```

结果：`10 passed, 84 deselected in 0.38s`。

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

## Subagent Findings

只读子代理确认：

- 本阶段最小边界就是 4 个工具，不应把 task queue、knowledge base、world model、outline maintenance 或 generation 工具混入。
- `repair_longform_maintenance` 是真实写入维护工具；本阶段只搬迁，不把它升级为 guarded write。
- `_json_safe_output` 必须随 handler 迁移或抽成共享 helper。
- `summarize_longform_context` 原本缺少直接 dispatch 覆盖，应补参数归一测试。

## Next Phase Suggestion

下一阶段优先拆 generation/outline maintenance 工具域：

- `generate_chapter`
- `prepare_generate_chapter_execution`
- `execute_generate_chapter_with_approval`
- `expand_outline_window`
- `backfill_outline_gaps`

这会继续降低 executor 体积，并为后续让 Agent 自主进行“生成前审批 -> 生成 -> 审稿 -> 修订 -> 世界模型写入”的工具链编排做准备。
