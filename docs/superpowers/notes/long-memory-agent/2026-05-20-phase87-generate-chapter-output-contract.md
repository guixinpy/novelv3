# Phase87 Report: Generate Chapter Output Contract

## Summary

Phase87 tightened `generate_chapter` from an adapter-backed tool into a more planner-readable Agent tool contract.

Implemented:

- Added structured `generate_chapter` output schema in the Writing Agent tool registry.
- Added `recommended_next_tools` to successful chapter-generation adapter output.
- Updated contract snapshot expectations so `generate_chapter` no longer has the `output_schema_too_generic` gap.

No prompt changes and no real model generation were performed.

## Files Changed

- `backend/app/services/writing_agent/chapter_generation_tool.py`
- `backend/app/services/writing_agent/tool_registry.py`
- `backend/tests/test_writing_agent_tool_registry.py`
- `backend/tests/test_writing_agent_tool_executor.py`
- `docs/superpowers/plans/long-memory-agent/2026-05-20-phase87-generate-chapter-output-contract.md`

## Output Contract

`generate_chapter` registry output now exposes:

- `status`
- `chapter_index`
- `trace_id`
- `athena_analysis`
- `agent_continuity_feedback`
- `agent_generation_feedback`
- `chapter_length_decision`
- `world_model_proposal_diagnostic`
- `recommended_next_tools`

Successful adapter output now adds:

```text
review_chapter_quality
review_chapter_continuity
analyze_chapter_world_model
```

The adapter uses `setdefault`, so future generation code can override `recommended_next_tools` explicitly.

## Validation

RED tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_generate_chapter_has_structured_output_contract backend/tests/test_writing_agent_tool_executor.py::test_generate_chapter_tool_appends_context_without_run_service backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Result before implementation: `3 failed`

GREEN focused tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_generate_chapter_has_structured_output_contract backend/tests/test_writing_agent_tool_executor.py::test_generate_chapter_tool_appends_context_without_run_service backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Result: `3 passed`

Related T1 slice:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

Result: `68 passed`

Chapter-generation behavior check:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py::test_agent_run_auto_plan_executes_high_level_next_chapter_goal backend/tests/test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift backend/tests/test_writing_agent_runs.py::test_agent_generate_chapter_appends_previous_state_card -q
```

Result: `3 passed`

## Findings

Fixed:

1. `generate_chapter` no longer presents as status-only output in the Agent tool registry.
2. `inspect_agent_tool_contracts` no longer reports `output_schema_too_generic` for `generate_chapter`.
3. The chapter generation adapter now tells the planner which post-generation tools should naturally follow.

Remaining gaps:

- The planner still has its own ordering logic for post-generation tools; Phase87 only made the generation tool output self-descriptive.
- Other core write tools still need structured output contracts.
- `generate_chapter` still lacks explicit confirmation semantics, but this may remain acceptable because direct user-triggered generation is the intended side effect. Batch execution remains guarded separately.

## Next Phase Recommendation

Phase88 should use `inspect_agent_tool_contracts` again and migrate the next high-impact write path. Best candidates:

1. `apply_world_model_proposal_resolution`: guarded world-model write, should become Agent-native adapter with stricter confirmation and output schema.
2. `create_revision_draft`: currently handled in run service, should become a static adapter or structured revision-planning tool.
3. Slash-command control plane: should be reframed as intent-to-tool-plan routing instead of command syntax.

