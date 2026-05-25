# Phase 7 Chapter Quality Review

## Runtime

- Date: 2026-05-18.
- Verification tier: T1 plus T2 runtime dogfood review.
- Backend base URL: `http://127.0.0.1:8001`.
- Secret handling: the model API key was used only as a runtime environment variable and was not written to source, docs, or `.env`.

## Implementation

- Added deterministic chapter quality review core:
  - `backend/app/core/chapter_quality_review.py`.
- Added Agent tool:
  - `review_chapter_quality`.
- Review tool output contract:
  - `status`.
  - `chapter_index`.
  - `finding_count`.
  - `blocker_count`.
  - `findings`.
  - `recommended_actions`.
- The tool reports blocked review findings while keeping the Agent run itself `success`, because the review report completed successfully.

Implemented deterministic findings:

- `missing_chapter`.
- `missing_outline_chapter`.
- `generic_chapter_title`.
- `chapter_over_target`.
- `chapter_under_target`.
- `future_outline_overlap`.
- `pending_world_model_proposals`.

## Chapter 2 Review

Agent run:

- id: `67082153-ecad-4bbe-8bfd-8db46d667603`.
- status: `success`.
- tool: `review_chapter_quality`, chapter 2.
- review status: `blocked`.
- finding count: `4`.
- blocker count: `3`.

Findings:

- `generic_chapter_title`: Chapter 2 title is still `第2章`.
- `chapter_over_target`: Chapter 2 has `3511` words, target max is `2300`.
- `future_outline_overlap`: Chapter 2 appears to overlap later outline material.
- `pending_world_model_proposals`: world-model queue has `24` pending proposal items.

Recommended actions:

- `revise_chapter`.
- `review_world_model_proposals`.

## Chapter 3 Review

Agent run:

- id: `28aeed43-b356-4a3f-ac55-f135b9978e00`.
- status: `success`.
- tool: `review_chapter_quality`, chapter 3.
- review status: `blocked`.
- finding count: `3`.
- blocker count: `2`.

Findings:

- `chapter_over_target`: Chapter 3 has `3080` words, target max is `2300`.
- `future_outline_overlap`: Chapter 3 overlaps future outline material:
  - Chapter 4 `顾衍的警告`.
  - Chapter 5 `空白信的秘密`.
  - Chapter 7 `苏晚晴的梦境`.
- `pending_world_model_proposals`: world-model queue has `24` pending proposal items.

Recommended actions:

- `revise_chapter`.
- `review_world_model_proposals`.

## Issues Found

- Deterministic overlap detection is intentionally conservative but can produce false positives on common character names such as `苏晚晴`.
- Chapter 2's deterministic backfilled outline preserved the generic title because the existing generated chapter title was generic.
- Review findings are not persisted in a dedicated review table yet; they live in Agent step output.
- Semantic issues from human-quality review remain outside deterministic tooling:
  - Chapter 1-2 relationship continuity conflict.
  - Chapter 3 fog-crystal ownership gap.
  - Gu Yan identity inconsistency.
  - Su Wanqing age inconsistency.
- The project still needs a revision workflow before Chapter 4 should be generated.

## Issues Fixed

- The system now has an Agent-visible chapter review tool.
- Obvious manuscript quality risks can be surfaced without relying on context-window memory.
- Generic fallback titles and over-target chapters are now machine-detectable review findings.
- Future outline overlap is now visible before it silently damages later chapter pacing.
- Pending world-model proposal pressure is visible in chapter quality review output.

## Verification

- TDD red check:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_generic_title_and_length tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_future_outline_overlap -q`.
  - Initial result: `2 failed`.
- T1 targeted after implementation:
  - Same command.
  - Result: `2 passed`.
- T1 Agent suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q`.
  - Result: `19 passed`.
- T1 related suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q`.
  - Result: `34 passed`.
- Diff hygiene:
  - Command: `git diff --check`.
  - Result: exit code `0`.
- Secret scan:
  - Command: `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`.
  - Result: no matches.
- Runtime:
  - Backend health on `8001`: `{"status":"ok"}`.
  - Chapter 2 review run succeeded and reported blocked findings.
  - Chapter 3 review run succeeded and reported blocked findings.

## Next Phase Recommendation

Phase 8 should turn review findings into a revision decision loop:

- Create a revision-plan Agent tool that converts review findings into specific chapter-edit tasks.
- Decide whether Chapter 2 and Chapter 3 should be revised before Chapter 4.
- Add an explicit operator decision or policy for repeated over-target chapters:
  - compress existing chapters.
  - adjust project word target.
  - split chapters.
- Triage the 24 pending world-model proposals, especially facts affecting character identity, age, relationships, and plot reveals.
- Add a semantic review pass later, likely model-assisted, after deterministic checks are stable.
