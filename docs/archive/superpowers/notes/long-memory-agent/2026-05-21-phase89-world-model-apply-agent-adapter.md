# Phase89 Report: World Model Apply Agent Adapter

## Summary

Phase89 converted `apply_world_model_proposal_resolution` into an Agent-native guarded write adapter.

Implemented:

- Added `backend/app/services/writing_agent/world_model_resolution_apply_tool.py`.
- Registered `apply_world_model_proposal_resolution` as a static Writing Agent adapter.
- Removed the `apply_world_model_proposal_resolution` execution branch from `WritingAgentRunService._execute_tool()`.
- Replaced status-only registry output schema with a structured output contract.
- Aligned `profile_version` schema with the missing-profile path, where the value can be `null`.
- Updated contract snapshot tests so the tool no longer reports `missing_agent_native_adapter` or `output_schema_too_generic`.

No world proposal review semantics were changed.

## Files Changed

- `backend/app/services/writing_agent/world_model_resolution_apply_tool.py`
- `backend/app/services/writing_agent/tool_executor.py`
- `backend/app/services/writing_agent/run_service.py`
- `backend/app/services/writing_agent/tool_registry.py`
- `backend/tests/test_writing_agent_tool_executor.py`
- `backend/tests/test_writing_agent_tool_registry.py`
- `docs/superpowers/plans/long-memory-agent/2026-05-21-phase89-world-model-apply-agent-adapter.md`

## Behavior Preserved

The adapter still delegates to:

```text
app.core.world_proposal_resolution_apply.apply_world_model_proposal_resolution
```

The guarded write behavior remains:

- `confirm_apply=False` returns a blocked/confirmation-required result and does not write reviews.
- invalid decisions block without partial writes.
- confirmed supported decisions apply through the existing core service.
- `should_generate_next_chapter` still governs whether follow-up writing tools may proceed.

## Output Contract

The registry now exposes structured fields for:

- `status`
- `project_id`
- `profile_version`
- `before_actionable_items`
- `after_actionable_items`
- `applied_count`
- `applied_reviews`
- `invalid_decision_count`
- `invalid_decisions`
- `requires_confirmation`
- `can_auto_apply`
- `should_generate_next_chapter`
- `recommended_actions`

The contract snapshot now reports the tool as:

- adapter-backed;
- `guarded_write`;
- confirmation-required;
- no longer status-only.

## Validation

RED tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_lists_unhandled_internal_tools_for_migration_tracking backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_exposes_apply_world_model_proposal_resolution_adapter_metadata backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_apply_world_model_resolution_has_structured_output_contract -q
```

Result before implementation: `5 failed`

GREEN focused tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_lists_unhandled_internal_tools_for_migration_tracking backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_exposes_apply_world_model_proposal_resolution_adapter_metadata backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_apply_world_model_resolution_has_structured_output_contract -q
```

Result: `5 passed`

Reviewer follow-up:

- The first implementation declared `profile_version` as integer-only.
- The missing-profile path returns `profile_version=None`, so the schema now uses `["integer", "null"]`.
- Added a regression assertion that missing-profile apply output keeps `profile_version is None`.

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_apply_world_model_resolution_has_structured_output_contract backend/tests/test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_missing_profile_without_decisions -q
```

Result: `2 passed`

Guarded apply regressions:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "apply_world_model_proposal_resolution" -q
```

Result: `9 passed, 153 deselected`

Related T1 slice:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py -k "apply_world_model_proposal_resolution or inspect_agent_tool_contracts" -q
```

Result: `13 passed, 220 deselected`

## Findings

Fixed:

1. `apply_world_model_proposal_resolution` is no longer an unhandled internal Writing Agent tool.
2. Its guarded write contract is now visible to `inspect_agent_tool_contracts`.
3. The Writing Agent executor now owns the world-model proposal apply step instead of run-service branching.
4. The tool output is structured enough for planner/Trace consumers to read confirmation, invalid decisions, applied reviews, and continuation readiness.

Remaining gaps:

- Other revision write tools such as `create_revision_draft`, `apply_planner_revision_patch`, `expand_chapter_to_target`, and `compress_chapter_to_target` still remain in run-service special-case branches.
- Planner/UI still do not explicitly classify `recommended_actions` into executable-now, confirm-required, or advisory.

## Next Phase Recommendation

Phase90 should target the revision tool cluster. The best first slice is `create_revision_draft`, because it is still unhandled internal and directly blocks/permits follow-up generation in long-form workflows.
