# Phase 9 Revision Draft Bridge

## Runtime

- Date: 2026-05-18.
- Verification tier: T1 plus T2 runtime dogfood draft creation.
- Backend base URL: `http://127.0.0.1:8001`.
- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Dogfood novel: `《雾港回声》`.
- Secret handling: no API key was written to source, docs, `.env`, or logs committed to git.

## Implementation

Added Agent tool:

- `create_revision_draft`.

Added draft bridge:

- `backend/app/core/chapter_revision_drafts.py`.

The tool:

- calls `plan_chapter_revision`;
- creates or reuses a planner-owned `ChapterRevision(status="draft")`;
- writes only `RevisionAnnotation` rows;
- writes no `RevisionCorrection` rows;
- does not submit drafts;
- does not call regeneration;
- does not update chapter title or chapter content;
- keeps `should_generate_next_chapter=false` until the draft is handled.

Safety behavior:

- Existing user/manual draft blocks automatic draft creation.
- Existing `submitted` or `failed` active revision blocks automatic draft creation.
- Planner-owned draft can be reused without creating duplicates.
- A drafted but unapplied revision blocks follow-up generation in the same Agent run.

## Dogfood Progress

- Current generated chapters remain: `3`.
- Chapter 4 remains ungenerated.
- Chapter 2 now has an active non-destructive revision draft.

## Chapter 2 Draft Creation

Pre-check:

- Active revision before run: `none`.
- Chapter 2 title: `第2章`.
- Chapter 2 word count: `3511`.
- Chapter 2 content prefix remained:
  - `凌晨两点，雾港市中城的街道上雾气渐散，露出湿漉漉的柏油路面。路灯在雾气折射下投出`

Agent run:

- id: `63cd2a23-c304-401e-9747-f3b09af07b0a`.
- status: `success`.
- tool: `create_revision_draft`, chapter 2.
- step target id: `db93ef9f-6128-4950-b6ea-21b6ccb7a765`.
- output status: `drafted`.
- revision id: `db93ef9f-6128-4950-b6ea-21b6ccb7a765`.
- revision index: `1`.
- annotation count: `3`.
- correction count: `0`.
- `should_generate_next_chapter`: `false`.

Active revision after run:

- id: `db93ef9f-6128-4950-b6ea-21b6ccb7a765`.
- status: `draft`.
- annotations: `3`.
- corrections: `0`.

Annotations:

- `[PLAN_ACTION:retitle_chapter][SOURCE:generic_chapter_title]`
- `[PLAN_ACTION:compress_chapter][SOURCE:chapter_over_target]`
- `[PLAN_ACTION:defer_future_reveals][SOURCE:future_outline_overlap]`

Chapter 2 after run:

- title remained: `第2章`.
- word count remained: `3511`.
- content prefix remained unchanged.

## Follow-Up Gate Run

Agent run:

- id: `5e7d9935-1994-46ed-bfda-61f7c1560ad9`.
- requested tools:
  - `create_revision_draft`, chapter 2.
  - `generate_chapter`, chapter 4.
- run status: `blocked`.
- error: `修订计划未通过，已停止后续写作工具。`
- executed step count: `1`.
- first step status: `success`.
- first output status: `drafted`.
- `should_generate_next_chapter`: `false`.
- Chapter 4 remained missing:
  - `404 Chapter not found`.

## Issues Fixed

- The Agent can now convert revision plans into durable, inspectable draft feedback.
- Draft feedback persists through existing `ChapterRevision` infrastructure without adding a new table.
- The tool does not mutate prose, title, result versions, or world-model proposals.
- Existing manual drafts are protected from planner overwrite.
- Existing submitted/failed revisions are protected from competing draft creation.
- Follow-up generation remains blocked while a revision draft is unapplied.

## Issues Found

- The draft model still lacks structured metadata fields for action type/source; Phase 9 stores stable markers in annotation comments.
- Title-level revision suggestions have to anchor to the first paragraph because the current revision model has no title target.
- Draft annotations are planning instructions, not final replacement text; a later phase must decide whether to submit/regenerate or manually resolve them.
- `review_world_model_proposals` remains a recommended action, not yet an executable Agent tool.

## Verification

- TDD red check:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_create_revision_draft_from_plan_is_non_destructive tests\test_writing_agent_runs.py::test_agent_create_revision_draft_reuses_existing_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_skips_ready_chapter tests\test_writing_agent_runs.py::test_agent_create_revision_draft_blocks_followup_generation -q`.
  - Initial result: `4 failed`.
- Initial targeted green:
  - Same command.
  - Result: `4 passed`.
- Code-review feedback red check:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_create_revision_draft_does_not_modify_manual_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_does_not_compete_with_submitted_revision -q`.
  - Initial result: `2 failed`.
- Code-review feedback green:
  - Same command.
  - Result: `2 passed`.
- Phase 9 targeted suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_create_revision_draft_from_plan_is_non_destructive tests\test_writing_agent_runs.py::test_agent_create_revision_draft_reuses_existing_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_does_not_modify_manual_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_does_not_compete_with_submitted_revision tests\test_writing_agent_runs.py::test_agent_create_revision_draft_skips_ready_chapter tests\test_writing_agent_runs.py::test_agent_create_revision_draft_blocks_followup_generation -q`.
  - Result: `6 passed`.
- T1 Agent suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q`.
  - Result: `27 passed`.
- T1 related suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_chapter_revisions.py tests\test_outlines.py -q`.
  - Result: `60 passed`.
- Diff hygiene:
  - Command: `git diff --check`.
  - Result: exit code `0`.
- Secret scan:
  - Command: `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`.
  - Result: no matches.
- Runtime:
  - Backend health on `8001`: `{"status":"ok"}`.
  - Chapter 2 draft creation succeeded.
  - Follow-up gate run blocked before `generate_chapter`.
  - Chapter 4 remained missing.

## Next Phase Recommendation

Phase 10 should make world-model proposal handling executable but still non-destructive:

- Add report-only Agent tool for proposal review queue triage.
- Return high/medium/low risk clusters and recommended review mode.
- Do not auto-approve proposals yet.
- Use the Chapter 2 draft plus proposal pressure to decide whether revision regeneration is safe in a later phase.
