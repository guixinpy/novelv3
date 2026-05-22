# Phase115 Route Preference Projection Report

## Summary

Added a read-only Agent route preference projection for chapter-generation routes. The projection keeps the current slash/dialog runtime route at `generate_chapter`, but explicitly recommends the approved Agent chain:

1. `prepare_generate_chapter_execution`
2. `execute_generate_chapter_with_approval`

This gives the next phase a concrete migration target without silently changing runtime behavior.

## Changes

- Added `inspect_agent_route_preference_projection` in `slash_command_route.py`.
- Registered the projection as an internal preflight Agent tool.
- Added a static executor adapter so the Agent can call the projection directly.
- Added tests for:
  - chapter routes preferring the approved chain,
  - non-chapter routes staying unchanged,
  - source filtering,
  - degraded status when preferred approval tools are missing,
  - registry and executor metadata.

## Runtime Behavior

- Existing slash command and dialog route behavior is unchanged.
- `preview_chapter` still reports current runtime tool `generate_chapter`.
- The new projection marks the approved prepare/execute chain as `recommended_not_applied`.
- No chapter generation, API behavior, planner output, or frontend behavior changed in this phase.

## Verification

- RED evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_route_preference.py -q`
  - Failed before implementation with missing `inspect_agent_route_preference_projection` import.
- GREEN/T1 evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_route_preference.py -q`
  - Result: `4 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py -q`
  - Result: `33 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference or slash_command_route or dialog_route_projection or dialog_intent_agent_plan_for_chapter" -q`
  - Result: `5 passed, 76 deselected`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_route_preference.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q`
  - Result: `118 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_chapters.py -k "test_generate_chapter or agent_entrypoint" -q`
  - Result: `26 passed, 12 deselected`
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_chapter_generation_execution.py -q`
  - Result: `4 passed`
  - `git diff --check`
  - Result: no whitespace errors.
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - Result: no matches.

## Novel Progress

No new novel chapters were generated. This phase was an Agent orchestration phase: it exposed the preferred approved route before changing planner/runtime behavior.

## Subagent Notes

The architecture review recommended keeping Phase115 read-only and locating the projection beside the existing slash/dialog route projection. The implementation follows that recommendation and avoids planner/runtime migration in this phase.

## Next Phase Recommendation

Phase116 should migrate one narrow entry point to use the approved route preference:

- option A: update `plan_dialog_intent_agent_run` so chapter intent plans prefer `prepare_generate_chapter_execution` followed by `execute_generate_chapter_with_approval`;
- option B: keep planner output stable and add an approval-aware execution wrapper that consumes the Phase115 projection.

Use a targeted T1 gate first, then run chapter API regression before committing.
