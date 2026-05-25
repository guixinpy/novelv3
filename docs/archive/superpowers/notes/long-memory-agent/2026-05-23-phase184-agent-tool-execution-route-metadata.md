# Phase184 Agent Tool Execution Route Metadata Report

## Goal

在 Writing Agent 工具合同快照和 step 结果 envelope 中显式暴露工具执行路径，减少 Agent / 审计链对 `adapter=None` 的隐式猜测。

## Scope

本阶段只增加 metadata，不改变调度：

- `static_adapter`
- `injected_adapter`
- `legacy_action_fallback`
- `unsupported_internal`
- `unsupported`

## Changes

- 更新 `backend/app/services/writing_agent/tool_contracts.py`
  - 每个工具合同新增 `execution_route`。
  - 有 adapter metadata 时输出 `<adapter_type>_adapter`。
  - public descriptor 且无 adapter 时输出 `legacy_action_fallback`。
  - internal descriptor 且无 adapter 时输出 `unsupported_internal`。
- 更新 `backend/app/services/writing_agent/run_service.py`
  - `agent_tool_result` envelope 新增 `execution_route`。
  - `adapter` metadata 只计算一次，并复用来推断 route。
  - 未注册工具输出 `unsupported`。
- 更新 `backend/tests/test_writing_agent_tool_executor.py`
  - 合同快照覆盖 legacy/static/injected 三类 route。
- 更新 `backend/tests/test_writing_agent_runs.py`
  - legacy action envelope 覆盖 `legacy_action_fallback`。
  - static adapter envelope 覆盖 `static_adapter`。
  - unsupported tool envelope 覆盖 `unsupported`。

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

结果：失败，`KeyError: 'execution_route'`。

```powershell
pytest backend/tests/test_writing_agent_runs.py::test_create_agent_run_records_steps_and_returns_detail -q
```

结果：失败，`KeyError: 'execution_route'`。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts backend/tests/test_writing_agent_runs.py::test_create_agent_run_records_steps_and_returns_detail -q
```

结果：`2 passed in 1.04s`。

补充 route 覆盖：

```powershell
pytest backend/tests/test_writing_agent_runs.py::test_agent_run_result_metrics_include_adapter_metadata backend/tests/test_writing_agent_runs.py::test_agent_run_records_normalized_output_for_unsupported_tool -q
```

结果：`2 passed in 1.05s`。

## Verification

T1 combined：

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -q
```

结果：`320 passed in 27.87s`。

Compile：

```powershell
python -m compileall backend/app/services/writing_agent
```

结果：exit 0。

Hygiene：

```powershell
git diff --check
```

结果：exit 0，仅提示 `backend/tests/test_writing_agent_runs.py` 后续 Git touch 时 CRLF 将替换为 LF。

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

结果：exit 1，无输出，未发现提交范围内的 DeepSeek/OpenAI 风格密钥。

## Subagent Findings

只读子代理确认：

- 本阶段应只暴露执行路径 metadata，不改变实际 dispatch。
- `generate_setup` 等 legacy Hermes 工具仍应走 `ActionExecutionService`。
- 不应在本阶段扩散到 planner metadata、approval contract metadata、write gate coverage。
- 推荐枚举与本阶段实现一致。

## Next Phase Suggestion

下一阶段可基于 `execution_route == "legacy_action_fallback"` 明确筛选 legacy action 迁移目标，先设计 `generate_setup` / `generate_storyline` / `generate_outline` 的 Agent-native preview/approval/execute 合同，再考虑实现 adapter。
