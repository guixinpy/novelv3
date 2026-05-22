# Phase116 Dialog Intent Approved Prepare Route Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for code changes. This phase is intentionally narrow and should not change chapter API behavior.

**Goal:** Move chapter continuation plans created from natural-language dialog intent onto the approved prepare route, while keeping the generic Writing Agent planner default compatible with `generate_chapter`.

**Architecture:** Add an optional chapter-generation route mode to `build_writing_agent_run_plan`. The default remains legacy direct `generate_chapter`; `plan_dialog_intent_agent_run` uses the approved prepare mode for `preview_chapter`, producing read/preflight steps followed by `prepare_generate_chapter_execution` and no post-generation steps.

**Tech Stack:** Python, pytest, existing Writing Agent planner/tool executor contracts.

---

## Assumptions

- Phase114 added `prepare_generate_chapter_execution` and `execute_generate_chapter_with_approval`.
- Phase115 added a read-only route preference projection recommending the approved chain.
- `execute_generate_chapter_with_approval` cannot be placed directly in a plan without runtime approval params; the safe first step is to plan `prepare_generate_chapter_execution`.

## Scope

1. Add a `chapter_generation_route` option to `build_writing_agent_run_plan`.
2. Keep the default route as existing `generate_chapter`.
3. For `chapter_generation_route="approved_prepare"`, replace the direct write step with `prepare_generate_chapter_execution`.
4. For approved prepare mode, stop before post-generation tools because no chapter has been written yet.
5. Make `plan_dialog_intent_agent_run` choose approved prepare mode for `preview_chapter`.
6. Add tests proving:
   - generic planner default still emits `generate_chapter`;
   - approved prepare mode emits `prepare_generate_chapter_execution` and omits post-generation tools;
   - dialog intent chapter plan uses approved prepare mode;
   - chapter API generation tests remain green.

## Out Of Scope

- Changing slash command route execution.
- Changing `/projects/{id}/chapters/{chapter}/generate`.
- Automatically executing `execute_generate_chapter_with_approval`.
- Frontend approval UX.
- Longform batch planner migration.
- Generating novel chapters.

## Verification Plan

- T0 RED:
  - Add planner/dialog tests expecting approved prepare route; verify they fail while code still emits `generate_chapter`.
- T0 GREEN:
  - Implement route mode and verify the focused tests pass.
- T1 regression:
  - `backend/tests/test_writing_agent_planner.py`
  - `backend/tests/test_writing_agent_tool_executor.py -k "dialog_intent_agent_plan_for_chapter or route_preference or approved_direct_chapter_generation"`
  - `backend/tests/test_writing_agent_route_preference.py`
  - selected chapter API generation tests.
- Hygiene:
  - `git diff --check`
  - secret scan over `backend` and active `docs`.

## Success Criteria

- `build_writing_agent_run_plan(..., intent="continue_next_chapter")` remains backward compatible by default.
- `build_writing_agent_run_plan(..., chapter_generation_route="approved_prepare")` returns a preview/prepare plan, not a direct write plan.
- `plan_dialog_intent_agent_run` for chapter intent returns `prepare_generate_chapter_execution` as the chapter generation handoff.
- The plan exposes trace evidence of the selected route.
