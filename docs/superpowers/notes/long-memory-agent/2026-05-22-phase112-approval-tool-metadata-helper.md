# Phase112 Approval Tool Metadata Helper Report

## Phase Summary

Phase112 extracted the Agent approval tool metadata projection from `tool_executor.py` into a neutral helper. This keeps Phase111's execution approval gate behavior intact while making the metadata projection reusable for future write execution paths.

## Goal Alignment

- Moves approval verification support out of executor-local logic and toward reusable Agent control-plane utilities.
- Preserves the current dependency direction: execution paths consume metadata providers; approval verification remains pure and read-only.
- Supports future Agent toolization work by making approval drift metadata easier to reuse outside the current longform batch executor adapter.

## Implemented

- Added `approval_tool_metadata.py` with `build_approval_tool_metadata_by_name`.
- The helper accepts:
  - an Agent plan dict,
  - optional adapter metadata keyed by tool name.
- The helper projects only approval-relevant steps:
  - `requires_confirmation is True`,
  - or `mutability` is `write` / `guarded_write`.
- The projected metadata includes:
  - `tool_exists`
  - `adapter_exists`
  - `adapter_type`
  - `handler_name`
  - `mutability`
  - `requires_confirmation`
  - `required_fields`
- Refactored `tool_executor.py` so `_approval_tool_metadata_by_name` delegates to the helper.
- Added `_static_adapter_metadata_by_name()` to avoid duplicating static adapter metadata projection inside `tool_executor.py`.

## Boundary Decision

This phase intentionally did not move `_STATIC_TOOL_ADAPTERS` out of `tool_executor.py`. Adapter registration is still executor-owned; the extracted helper only consumes adapter metadata when provided.

This keeps Phase112 as a low-risk extraction and avoids a broader adapter registry migration.

## Subagent Review

A read-only architecture subagent was started to review the extraction boundary, but it did not return within the bounded wait window and was closed. The implementation proceeded because the change was narrow and covered by focused RED/GREEN plus T1 regression tests.

## Novel Progress

No new novel chapter was generated in this phase. This phase improves the Agent execution control layer that future autonomous long-running generation will use.

## Verification

RED helper test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_tool_metadata.py -q
```

Initial result:

```text
ModuleNotFoundError: No module named 'app.services.writing_agent.approval_tool_metadata'
```

GREEN helper test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_tool_metadata.py -q
```

Result:

```text
4 passed
```

T1 related coverage:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_registry.py -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "longform_chapter_batch_execution or execute_longform_chapter_batch" -q
```

Result:

```text
116 passed
8 passed, 162 deselected
```

## Next Phase Recommendation

Phase113 should continue widening the Agent approval gate beyond the current batch execution path. A practical next step is to identify the next high-value write adapter whose execute path still lacks a persisted Agent plan approval contract, then apply the same prepare/verify/execute shape.
