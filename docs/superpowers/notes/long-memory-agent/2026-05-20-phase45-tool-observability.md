# Phase45 Report: Tool Observability

## Phase Goal

Make the Writing Agent tool layer observable enough to support later recovery, task queue, and self-optimization work.

Phase45 does not migrate additional mutation-heavy tools. It adds metadata and metrics around the adapter system created in Phase43-44.

## Implemented

- Added `WritingAgentToolAdapter` metadata in `tool_executor.py`.
- Added `writing_agent_tool_adapter_metadata(tool_name)`.
- Added `unhandled_internal_writing_agent_tool_names()`.
- Marked static adapters with:
  - `adapter_type`;
  - `category`;
  - `mutability`;
  - `handler_name`.
- Added injected adapter metadata for `preflight_writing`.
- Added `agent_tool_result` metrics:
  - `adapter`;
  - `elapsed_ms`;
  - `output_size_bytes`.
- Kept output size non-recursive by measuring the step output before adding `agent_tool_result`.
- Added tests for:
  - adapter metadata;
  - unhandled internal migration list;
  - adapter metadata and metrics in API run output.

## Subagent Review

A read-only subagent reviewed the current scope and confirmed:

- mutation-heavy and run-coupled tools should remain in `run_service.py` for now;
- `preflight_writing`, `analyze_chapter_world_model`, and `expand_outline_window` have strong reasons to stay coupled to run context or private checks;
- envelope metrics are best added inside `_agent_tool_result_envelope()` without database schema changes.

Current unhandled internal tools are therefore migration candidates, not defects.

## Why This Helps Agentization

The Agent tool layer can now answer operational questions:

- which tools are adapter-backed;
- which tools still require legacy run-service handling;
- whether a step was handled by a static or injected adapter;
- how large each tool result is;
- how long each step took.

This supports the later plan/retry/recovery loop without forcing those systems to parse tool-specific payloads.

## Validation

Validation level: T1.

Focused RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "adapter_metadata or unhandled_internal or result_metrics"
```

RED result:

```text
ImportError: cannot import name 'unhandled_internal_writing_agent_tool_names'
```

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "adapter_metadata or unhandled_internal or result_metrics"
```

Result:

```text
3 passed, 122 deselected
```

T1 module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result:

```text
132 passed
```

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

```text
git diff --check: exit 0; warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF the next time Git touches it
secret scan: exit 1; no matches
```

## Current Limits

- Metrics are JSON envelope fields, not database columns.
- `adapter` is `None` for legacy action-service and run-service branches.
- The unhandled list is a migration diagnostic, not a runtime error.
- No UI exposes these metrics yet.

## Next Phase Recommendation

Phase46 should use these diagnostics to migrate one mutation-light maintenance tool with pinned behavior, likely `backfill_outline_gaps`, or add recovery policy decisions that read `agent_tool_result` instead of tool-specific output.
