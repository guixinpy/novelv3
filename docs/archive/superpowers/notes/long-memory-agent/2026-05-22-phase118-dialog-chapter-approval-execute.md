# Phase118 Dialog Chapter Approval Execute Report

## Summary

Completed the backend dialog approval loop for single-chapter generation.

After the first dialog confirmation prepares a chapter approval contract, the system now creates a second pending action. Confirming that follow-up action dispatches `execute_generate_chapter_with_approval` with the prepared contract hash and snapshot.

## Changes

- Added param-sensitive dispatch in `dialog_control_plane`:
  - `generate_chapter` without approval params -> `prepare_generate_chapter_execution`;
  - `generate_chapter` with approval params -> `execute_generate_chapter_with_approval`.
- On `approval_required`, `ActionResultService` now:
  - creates a follow-up `PendingAction`;
  - stores `confirm_execute=True`, `approval_contract_hash`, and `approval_contract`;
  - marks the dialog as `pending_action`;
  - records an assistant-visible message so message listing can attach the pending action.
- Added tests for:
  - prepare output creating a follow-up pending action;
  - follow-up dispatch selecting `execute_generate_chapter_with_approval`;
  - first confirmation still dispatching prepare;
  - no chapter row being created before second confirmation.

## Runtime Boundary

- Public pending action type remains `generate_chapter`.
- Slash/text route metadata remains compatible.
- Direct chapter API generation remains unchanged.
- This phase only completes backend dispatch and pending-action state; frontend UX polish is still pending.

## Verification

- RED evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_chapter_prepare_background_work_records_approval_required_without_generating -q`
  - Failed because the approval-required message was still a system message and no follow-up pending action existed.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_chapter_approval_followup_dispatches_execute_tool -q`
  - Failed because no follow-up pending action existed.
- GREEN/T1 evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_chapter_prepare_background_work_records_approval_required_without_generating -q`
  - Result: `1 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_chapter_approval_followup_dispatches_execute_tool -q`
  - Result: `1 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_resolve_chapter_action_confirm_dispatches_prepare_tool -q`
  - Result: `1 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -q`
  - Result: `62 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_chapter_generation_execution.py backend/tests/test_writing_agent_tool_executor.py -q`
  - Result: `85 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_chapters.py -k "test_generate_chapter or agent_entrypoint" -q`
  - Result: `26 passed, 12 deselected`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "agent_run_auto_plan_executes_high_level_next_chapter_goal or agent_generate_chapter_appends_length_feedback or continuation_state_exposes_recommended_followups" -q`
  - Result: `4 passed, 166 deselected`
  - `git diff --check`
  - Result: no whitespace errors.
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - Result: no matches.

## Novel Progress

No new novel chapters were generated. This phase completed the backend safety gate needed before dialog-driven generation can resume with explicit approval.

## Next Phase Recommendation

Phase119 should run a browser-level dialog flow check:

1. create or use a small project with setup/storyline/outline;
2. request chapter generation through dialog;
3. confirm once and verify approval-required state appears;
4. confirm again and verify execution starts or returns a meaningful blocked result;
5. record any frontend UX gaps around the second confirmation.

If backend API gaps appear during browser testing, fix those before styling.
