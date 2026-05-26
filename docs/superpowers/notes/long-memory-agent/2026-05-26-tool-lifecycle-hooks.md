# 2026-05-26 Tool Lifecycle Hooks Slice

## Goal Link

Active goal: complete the full Agent-native long-memory writing Agent upgrade from `docs/agent-native-guide/01-reference-patterns-report.md`.

This note covers Task 4 from `docs/superpowers/plans/2026-05-26-agent-native-long-memory-writing-agent.md`: add deterministic tool lifecycle hooks.

## Implemented

- Added `tool_lifecycle_hooks.py` with built-in `before_tool_call`, `after_tool_call`, and `on_tool_error` hooks.
- The before hook denies child-agent guarded writes, currently using existing agent profile definitions and tool mutability metadata.
- `execute_writing_agent_tool` now returns lifecycle metadata alongside unchanged business output.
- `run_service` stores hook metadata inside `agent_tool_result.tool_lifecycle_hooks` and strips the transient transport key from persisted step output.
- Adapter `ValueError` behavior remains unchanged for invalid input coercion tests.

## Evidence

Focused tests and executor regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_lifecycle_hooks.py backend\tests\test_writing_agent_tool_executor.py -q
# 163 passed
```

Run-service metadata regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py -k "agent_tool_result or lifecycle or result_metrics or unsupported or stop_hooks" -q
# 3 passed, 183 deselected
```

## Remaining

- Plugin loading is intentionally out of scope for this slice; hooks are deterministic built-ins only.
- Future worker-definition work should replace profile inference with repo-local AgentDefinition policy.
- Later queue/event slices should decide whether lifecycle events are persisted as first-class queue or trace events rather than only step metadata.
