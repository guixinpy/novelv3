# Phase 8 Revision Decision Loop

## Runtime

- Date: 2026-05-18.
- Verification tier: T1 plus T2 runtime dogfood planning.
- Backend base URL: `http://127.0.0.1:8001`.
- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Dogfood novel: `《雾港回声》`.
- Secret handling: no API key was written to source, docs, `.env`, or logs committed to git.

## Implementation

Added Agent revision-decision tool:

- `plan_chapter_revision`.

Added core planner:

- `backend/app/core/chapter_revision_planner.py`.

The planner is intentionally read-only. It:

- calls deterministic `review_chapter_quality`;
- maps review findings into revision actions;
- summarizes world-model proposal pressure through the proposal review queue;
- returns `should_generate_next_chapter`;
- does not regenerate or overwrite `ChapterContent`;
- does not approve, reject, or edit world-model proposal items.

Revision action mapping:

- `generic_chapter_title` -> `retitle_chapter`.
- `chapter_over_target` -> `compress_chapter`.
- `chapter_under_target` -> `expand_chapter`.
- `future_outline_overlap` -> `defer_future_reveals`.
- `missing_outline_chapter` -> `repair_outline_gap`.

Safety gate:

- A standalone blocked `plan_chapter_revision` run succeeds as a report.
- If a blocked revision plan is followed by another tool in the same Agent run, the run stops as `blocked`.
- This prevents a caller from chaining `plan_chapter_revision -> generate_chapter` and bypassing revision decisions.

## Dogfood Progress

- Current generated chapters remain: `3`.
- Chapter 4 remains ungenerated.
- Chapter 4 check after gate validation:
  - `GET /api/v1/projects/25fa2b20-5b9f-473b-918b-f4ea491cbb60/chapters/4`
  - Result: `404 Chapter not found`.

## Chapter 2 Revision Plan

Agent run:

- id: `fa9dbb34-a3bf-4870-843e-dbee78658145`.
- status: `success`.
- tool: `plan_chapter_revision`, chapter 2.
- plan status: `blocked`.
- `should_generate_next_chapter`: `false`.
- finding count: `4`.
- blocker count: `3`.
- pending proposal total: `24`.

Actions:

- `retitle_chapter`.
- `compress_chapter`.
- `defer_future_reveals`.

Recommended next tools/actions:

- `revise_chapter`.
- `review_world_model_proposals`.

## Chapter 3 Revision Plan

Agent run:

- id: `b985a789-4698-4c8c-af69-a8f787f80b37`.
- status: `success`.
- tool: `plan_chapter_revision`, chapter 3.
- plan status: `blocked`.
- `should_generate_next_chapter`: `false`.
- finding count: `3`.
- blocker count: `2`.
- pending proposal total: `24`.

Actions:

- `compress_chapter`.
- `defer_future_reveals`.

Recommended next tools/actions:

- `revise_chapter`.
- `review_world_model_proposals`.

## Follow-Up Gate Run

Agent run:

- id: `ef5f2558-f51e-4595-8c7d-aea4f201e8e1`.
- requested tools:
  - `plan_chapter_revision`, chapter 3.
  - `generate_chapter`, chapter 4.
- run status: `blocked`.
- error: `修订计划未通过，已停止后续写作工具。`
- executed step count: `1`.
- first step status: `success`.
- Chapter 4 was not generated.

## Issues Fixed

- Added a safe middle layer between quality review and destructive chapter regeneration.
- Review findings now produce structured revision actions that can guide manual or later automated revision.
- Pending world-model proposal pressure is visible in revision planning, not only in review output.
- A blocked revision plan now gates follow-up writing tools inside the same Agent run.
- Planner output is stored in Agent step output, preserving traceability without adding a new schema.

## Issues Found

- `review_world_model_proposals` is still a recommended action, not yet a Writing Agent executable tool.
- The planner is deterministic and only maps known quality findings; semantic continuity issues still require a later model-assisted or subagent-assisted review loop.
- Revision actions do not yet create `ChapterRevision` drafts. This is deliberate for Phase 8, but Phase 9 should decide whether to create draft feedback records.
- World-model proposal pressure reports only the first queue window risk counts; the full queue still needs dedicated triage tooling.

## Verification

- TDD red check:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_maps_review_findings_to_actions tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_records_revision_plan_target_type -q`.
  - Initial result: `2 failed`.
- Initial targeted green:
  - Same command.
  - Result: `2 passed`.
- Code-review feedback red check:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_blocks_followup_generation_when_plan_is_blocked tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_reports_world_model_pressure_without_reviewing_items -q`.
  - Initial result: `1 failed, 1 passed`.
- Code-review feedback green:
  - Same command.
  - Result: `2 passed`.
- T1 Agent suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q`.
  - Result: `21 passed` before feedback fixes, `25 passed` after feedback fixes.
- T1 related suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q`.
  - Result: `38 passed`.
- Diff hygiene:
  - Command: `git diff --check`.
  - Result: exit code `0`.
- Secret scan:
  - Command: `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`.
  - Result: no matches.
- Runtime:
  - Backend health on `8001`: `{"status":"ok"}`.
  - Chapter 2 and Chapter 3 revision planning runs succeeded as reports.
  - Follow-up gate run blocked before `generate_chapter`.
  - Chapter 4 remained missing.

## Next Phase Recommendation

Phase 9 should turn revision decisions into non-destructive revision drafts:

- Create or reuse `ChapterRevision(status="draft")` from planner actions.
- Convert `retitle_chapter`, `compress_chapter`, and `defer_future_reveals` into structured annotations/corrections.
- Add a report-only Agent tool for world-model proposal queue triage, so `review_world_model_proposals` becomes an executable Agent capability without auto-approval.
- Keep destructive `regenerate_revision` behind explicit user/operator action until quality gates and rollback paths are stronger.
