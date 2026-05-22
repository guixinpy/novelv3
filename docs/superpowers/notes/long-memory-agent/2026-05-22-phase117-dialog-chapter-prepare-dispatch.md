# Phase117 Dialog Chapter Prepare Dispatch Report

## Summary

Confirmed dialog chapter-generation actions now dispatch `prepare_generate_chapter_execution` instead of directly running `generate_chapter`.

The public action type remains `generate_chapter` for UI and pending-action compatibility, but the internal Writing Agent run now stops at the approval contract preparation step. This prevents a single dialog confirmation from writing manuscript content before the Agent approval contract is available.

## Changes

- Updated `SUPPORTED_DIALOG_ACTION_TO_TOOL["generate_chapter"]` to `prepare_generate_chapter_execution`.
- Preserved `action_type == "generate_chapter"` in background task payloads and action results.
- Preserved command args and chapter params in the Writing Agent run input.
- Updated dialog background completion to preserve `approval_required` from prepare output.
- Updated `ActionResultService.record_completion` so `approval_required` is recorded as a meaningful non-success/non-failure terminal message.
- Added dialog tests proving:
  - confirmed chapter pending action dispatches `prepare_generate_chapter_execution`;
  - prepare background work records `approval_required`;
  - no `ChapterContent` is created by the prepare step;
  - existing setup pending-action dispatch remains stable.

## Runtime Boundary

- Chapter API generation remains unchanged and still uses `generate_chapter`.
- Slash command and text intent preview metadata still expose the compatible `generate_chapter` route.
- Dialog pending-action confirmation for chapters now prepares approval only; the second confirmation/execution path is not yet wired.
- No frontend approval UI was changed.

## Verification

- RED evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_resolve_chapter_action_confirm_dispatches_prepare_tool -q`
  - Failed because task payload still used `generate_chapter`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_chapter_prepare_background_work_records_approval_required_without_generating -q`
  - Failed because background work returned `failed` instead of `approval_required`.
- GREEN/T1 evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_resolve_chapter_action_confirm_dispatches_prepare_tool backend/tests/test_dialogs.py::test_chapter_prepare_background_work_records_approval_required_without_generating -q`
  - Result: `2 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py::test_resolve_action_confirm_creates_background_task backend/tests/test_dialogs.py::test_resolve_action_confirm_passes_command_args_to_background -q`
  - Result: `2 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -q`
  - Result: `61 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_chapter_generation_execution.py -q`
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

No new novel chapters were generated. This phase intentionally prevented dialog confirmation from writing a chapter until the approval execution path is wired.

## Next Phase Recommendation

Phase118 should add the second half of the dialog-approved chapter flow:

- expose the prepare result as a follow-up confirmation payload;
- create or reuse a pending action for `execute_generate_chapter_with_approval`;
- pass `confirm_execute`, `approval_contract_hash`, and `approval_contract`;
- preserve run enrichment for generated chapter outputs.

After that, run a browser-level dialog flow check because this will become user-visible.
