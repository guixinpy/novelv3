# Phase116 Dialog Intent Approved Prepare Route Report

## Summary

Moved natural-language dialog chapter planning to the approved prepare route. The generic planner remains backward compatible by default, but `plan_dialog_intent_agent_run` now asks the planner for `approved_prepare` when the dialog action is `preview_chapter`.

This is a planning/preflight migration only. It does not change slash command execution, pending-action execution, or the chapter generation API.

## Changes

- Added planner route constants:
  - `legacy_generate_chapter`
  - `approved_prepare`
- Added optional `chapter_generation_route` to `build_writing_agent_run_plan`.
- Kept default planner behavior on `legacy_generate_chapter`.
- Added approved prepare behavior:
  - keeps context and preflight steps;
  - emits `prepare_generate_chapter_execution`;
  - omits `generate_chapter`;
  - omits post-generation review/world-model tools because no chapter has been written.
- Updated `plan_dialog_intent_agent_run` so `preview_chapter` uses `approved_prepare`.
- Added trace and planner output evidence via `chapter_generation_route`.

## Runtime Boundary

- Existing chapter API generation still runs `generate_chapter`.
- Generic `build_writing_agent_run_plan(..., intent="continue_next_chapter")` still emits `generate_chapter` unless the new route option is explicitly set.
- Dialog pending-action control plane still maps confirmed chapter actions to `generate_chapter`; this phase only changes the read/preflight dialog intent planning tool.
- `execute_generate_chapter_with_approval` is not placed into an auto-executed plan, because it requires a prepared approval contract and explicit confirmation params.

## Subagent Review

The sidecar architecture review warned against globally replacing `generate_chapter` in planner output because `run_service` and chapter API paths still have runtime semantics coupled to that tool name. The implementation follows that constraint by limiting the change to explicit planner route mode and dialog intent planning.

## Verification

- RED evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py::test_planner_can_prepare_next_chapter_through_approved_route -q`
  - Failed with `TypeError: build_writing_agent_run_plan() got an unexpected keyword argument 'chapter_generation_route'`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_dialog_intent_agent_plan_for_chapter -q`
  - Failed with missing `chapter_generation_route` trace.
- GREEN/T1 evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py::test_planner_can_prepare_next_chapter_through_approved_route -q`
  - Result: `1 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_dialog_intent_agent_plan_for_chapter -q`
  - Result: `1 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py -k "planner or dialog_intent_agent_plan_for_chapter or route_preference or approved_direct_chapter_generation" -q`
  - Result: `14 passed, 73 deselected`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "agent_run_auto_plan_executes_high_level_next_chapter_goal or continuation_state_exposes_recommended_followups or agent_generate_chapter_appends_length_feedback" -q`
  - Result: `4 passed, 166 deselected`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_route_preference.py backend/tests/test_writing_agent_chapter_generation_execution.py -q`
  - Result: `95 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -q`
  - Result: `170 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_chapters.py -k "test_generate_chapter or agent_entrypoint" -q`
  - Result: `26 passed, 12 deselected`
  - `git diff --check`
  - Result: no whitespace errors.
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - Result: no matches.

## Novel Progress

No new novel chapters were generated. This phase changed the Agent planning/control surface needed before user-facing approved execution can be safely wired.

## Next Phase Recommendation

Phase117 should add a dialog/control-plane wrapper for the second half of the approved path:

- consume the prepare output and approval contract;
- require explicit confirmation;
- call `execute_generate_chapter_with_approval`;
- preserve chapter run enrichment and continuation semantics currently tied to `generate_chapter`.

Do not migrate slash commands, chapter API, or longform batch generation until this wrapper is proven.
