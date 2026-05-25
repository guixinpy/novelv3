# Phase146 Step Binding Persistence Report

## Objective

Persist Writing Agent step-level `tool_call_id` and bounded `resource_binding` so run details and trace audit can inspect approved write bindings without relying only on nested tool output.

## Implementation

- Added nullable `tool_call_id` and `resource_binding` fields to `WritingAgentStep`.
- Added matching nullable fields to `WritingAgentStepOut`.
- Added Alembic migration:
  - `backend/alembic/versions/20260523_add_writing_agent_step_bindings.py`
  - Adds both columns and `ix_writing_agent_steps_project_tool_call`.
- Updated `WritingAgentRunService` to persist step binding fields on success and blocked steps.
- Binding extraction prefers:
  - `execution_resource_binding.resource_binding`
  - direct `resource_binding`
  - first `approval_verification_event.resource_bindings` item
- Updated trace audit step summaries and `tool_step` event-chain entries to include bounded binding data.

## TDD Evidence

- Model/schema RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_writing_agent_step_binding_fields_are_modelled -q`
  - Failed because `WritingAgentStep.tool_call_id` was missing.
- Model/schema GREEN:
  - Same command.
  - `1 passed in 0.02s`
- Run-service persistence RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once -q`
  - Failed because persisted `WritingAgentStep.tool_call_id` was `None`.
- Run-service persistence GREEN:
  - Same command.
  - `1 passed in 0.26s`
- Trace audit RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - Failed because `tool_step` events did not expose `tool_call_id`.
- Trace audit GREEN:
  - Same command.
  - `1 passed in 0.14s`
- Migration smoke:
  - `backend\.venv\Scripts\python.exe -m py_compile backend\alembic\versions\20260523_add_writing_agent_step_bindings.py`
  - Passed.
- Migration chain smoke:
  - Temporary SQLite database with `MOZHOU_DATABASE_URL`.
  - `.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head`
  - Applied through `20260523_add_writing_agent_step_bindings`.

## Verification

- Targeted regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_trace_audit.py::test_writing_agent_step_binding_fields_are_modelled backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash backend\tests\test_writing_agent_chapter_generation_execution.py backend\tests\test_writing_agent_step_binding.py -q`
  - `15 passed in 0.73s`
- Hygiene:
  - `git diff --check` passed.
  - API key scan found no matches in non-archived backend/frontend/docs paths.

## Novel Progress

No new novel chapter was generated in this phase. This phase improves the Agent execution substrate for long-running autonomous writing by making write-step identity queryable and auditable.

## Known Limits

- Historical rows are not backfilled.
- The persisted `resource_binding` is intentionally bounded; full internal binding payloads remain in approval contract/output where needed.
- Multi-write plans still need exact step or `tool_call_id` execution selection beyond target matching.

## Next Recommendation

Use persisted step bindings to improve recovery and continuation planning: when a run blocks or fails, recommended follow-up tools should name the exact `tool_call_id`, target resource, and whether the next step should re-prepare approval or retry execution.
