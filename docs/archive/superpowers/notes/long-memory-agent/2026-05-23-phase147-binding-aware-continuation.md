# Phase147 Binding-Aware Continuation Report

## Objective

Expose persisted write-step bindings in continuation and recovery summaries so the Writing Agent can explain blocked writes by exact tool call and target resource.

## Implementation

- Continuation state `_step_marker()` now includes:
  - `tool_call_id`
  - bounded `resource_binding`
- Continuation `failure` now includes the same binding metadata.
- Recovery preview `hash_payload` now includes:
  - `source_tool_call_id`
  - `source_resource_binding`
- Recovery preview `source_step` now includes:
  - `tool_call_id`
  - bounded `resource_binding`

## TDD Evidence

- Continuation RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch -q`
  - Failed because `blocked_tool.tool_call_id` was missing.
- Continuation GREEN:
  - Same command.
  - `1 passed in 0.23s`
- Recovery preview RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_can_plan_recovery_tools_from_blocked_run -q`
  - Failed because `source_step.tool_call_id` was missing.
- Recovery preview GREEN:
  - Same command.
  - `1 passed in 0.20s`

## Verification

- Targeted regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_execute_longform_chapter_batch_blocks_resource_binding_mismatch backend\tests\test_writing_agent_runs.py::test_agent_run_can_plan_recovery_tools_from_blocked_run backend\tests\test_writing_agent_runs.py::test_agent_run_can_execute_approved_longform_chapter_batch_once backend\tests\test_writing_agent_trace_audit.py::test_inspect_agent_trace_audit_includes_dialog_approval_events_without_raw_hash -q`
  - `4 passed in 0.53s`
- Hygiene:
  - `git diff --check` passed.
  - API key scan found no matches in non-archived backend/frontend/docs paths.

## Novel Progress

No new novel chapter was generated in this phase. This phase improves long-running Agent resumability by ensuring blocked runs can name the exact write identity involved in recovery context.

## Known Limits

- Resource binding mismatch still does not have a dedicated recovery policy. Current output explains the binding identity, but next-tool selection remains conservative.
- Frontend views do not yet render binding metadata.

## Next Recommendation

Add a specific recovery policy for `resource_binding_missing` and `resource_binding_target_mismatch` that routes to the correct prepare tool, while keeping execution blocked until a fresh approval contract is generated.
