# Phase86 Report: Generate Chapter Agent Adapter

## Summary

Phase86 migrated `generate_chapter` from a `WritingAgentRunService` legacy special case into an Agent-native static tool adapter.

Implemented:

- Added `backend/app/services/writing_agent/chapter_generation_tool.py`.
- Registered `generate_chapter` in the Writing Agent static executor.
- Changed `execute_writing_agent_tool()` so registered static adapters can handle Agent-visible tools, not only `internal=True` tools.
- Removed the direct `generate_chapter` execution branch from `WritingAgentRunService._execute_tool()`.
- Moved chapter generation feedback helpers out of `run_service.py` so the adapter no longer imports run-service private helpers.
- Updated contract tests so `inspect_agent_tool_contracts` no longer reports `missing_agent_native_adapter` for `generate_chapter`.

No chapter generation was performed against a real model in this phase.

## Behavior Preserved

The new adapter still delegates real generation to:

- `ActionExecutionService(db).execute("generate_chapter", ...)`

The following existing Writing Agent behaviors are preserved:

- `chapter_index` is passed through `action_params`;
- manual `command_args` still reach generation;
- repeated length drift feedback is appended to command args;
- previous chapter state card feedback is appended to command args;
- generation result may still include `agent_continuity_feedback`;
- generation result may still include `agent_generation_feedback`;
- run-step enrichment for chapter length decision and world-model proposal diagnostics remains in `WritingAgentRunService._enrich_step_output()`.

## Files Changed

- `backend/app/services/writing_agent/chapter_generation_tool.py`
- `backend/app/services/writing_agent/tool_executor.py`
- `backend/app/services/writing_agent/run_service.py`
- `backend/tests/test_writing_agent_tool_executor.py`
- `docs/superpowers/plans/long-memory-agent/2026-05-20-phase86-generate-chapter-agent-adapter.md`

## Validation

RED tests before implementation:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_exposes_adapter_metadata_for_trace backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Result before implementation: `3 failed`

Initial GREEN after adapter registration exposed one behavioral regression:

- `generate_chapter` remained non-internal, so executor refused to handle it and run-service fell back to plain `ActionExecutionService` without Agent feedback.

Fix:

- `execute_writing_agent_tool()` now checks static adapters before rejecting non-internal tools.

Focused GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_exposes_adapter_metadata_for_trace backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Result: `3 passed`

Generation behavior regression checks:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py::test_agent_run_auto_plan_executes_high_level_next_chapter_goal backend/tests/test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift backend/tests/test_writing_agent_runs.py::test_agent_generate_chapter_appends_previous_state_card -q
```

Result after executor-order fix: `3 passed`

T1 slices:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "generate_chapter or inspect_agent_tool_contracts" -q
```

Result after review fixes: `9 passed, 199 deselected`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -q
```

Result after review fixes: `46 passed`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "agent_run_auto_plan_executes_high_level_next_chapter_goal or agent_generate_chapter_appends_length_feedback or agent_generate_chapter_appends_previous_state_card" -q
```

Result: `4 passed, 158 deselected`

Reviewer follow-up checks:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_generate_chapter_tool_appends_context_without_run_service backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_does_not_coerce_invalid_generate_chapter_index -q
```

Result: `2 passed`

```powershell
rg "run_service" backend/app/services/writing_agent/chapter_generation_tool.py
```

Result: no matches

## Findings

Fixed:

1. `generate_chapter` is now visible to the Agent executor as an adapter-backed tool.
2. Contract inspection no longer treats `generate_chapter` as missing an Agent-native adapter.
3. The first migration did reveal a real architectural constraint: Agent-visible tools may still need executor adapters, so executor handling cannot be restricted to `internal=True`.
4. The generation-context helper logic is now owned by `chapter_generation_tool.py`, removing the adapter's private dependency on `run_service.py`.
5. Invalid `chapter_index` values are not silently coerced into Chapter 1 before generation.

Remaining known gaps:

- `generate_chapter` still has generic output schema from the registry; future planner autonomy will need a stricter schema with `chapter_index`, `trace_id`, `athena_analysis`, feedback fields, and recovery recommendations.
- Other generation and world-model write tools still need the same adapter migration.

## Next Phase Recommendation

Phase87 should tighten the `generate_chapter` contract after this adapter migration:

1. Replace `generate_chapter`'s generic `_STATUS_OUTPUT` with a structured output schema.
2. Add an explicit post-generation recommended-next-tools contract so planner behavior does not rely on implicit run-service ordering.
3. Use `inspect_agent_tool_contracts` to select the next high-impact legacy tool after `generate_chapter`.
4. Continue migrating world-model write tools into guarded Agent-native adapters.
