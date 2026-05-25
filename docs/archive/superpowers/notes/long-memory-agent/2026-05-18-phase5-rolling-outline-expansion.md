# Phase 5 Rolling Outline Expansion

## Runtime

- Date: 2026-05-18.
- Verification tier: T1 plus T2 runtime dogfood expansion and Chapter 3 generation.
- Backend base URL: `http://127.0.0.1:8001`.
- Secret handling: the model API key was used only as a runtime environment variable and was not written to source, docs, or `.env`.

## Implementation

- Added a rolling outline expansion endpoint:
  - `POST /api/v1/projects/{project_id}/outline/expand-window`.
- Added merge behavior for outline windows:
  - preserve existing chapters.
  - append only chapters inside the requested window.
  - skip chapters that already exist.
  - skip out-of-window model output.
  - sort merged chapters by `chapter_index`.
- Added an Agent tool:
  - `expand_outline_window`.
- Added tests for:
  - preserving existing outline chapters.
  - normalizing structured scene and character values.
  - ignoring out-of-window generated chapters.
  - Agent expansion followed by ready preflight.

## Dogfood Outline Expansion

Dogfood project:

- Name: `雾港回声`.
- Project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Target: 600 chapters, 1,200,000 words.

Agent run:

- id: `e73d03b2-d003-4902-8ddf-e0d6fc709316`.
- status: `success`.
- tool: `expand_outline_window`.
- requested window: Chapter 3 to Chapter 8.
- outline id: `49229388-f2d6-4bdb-bfa0-f4e8b9aa0beb`.
- expansion trace id: `8d0ca318-5bff-4993-a176-e71fee9f5c84`.
- added chapter count: `6`.

Outline coverage after expansion:

- Chapter 1: `雾中回声`.
- Chapter 3: `雾中童谣`.
- Chapter 4: `顾衍的警告`.
- Chapter 5: `空白信的秘密`.
- Chapter 6: `黑市雾晶`.
- Chapter 7: `苏晚晴的梦境`.
- Chapter 8: `废弃实验室`.

Important caveat:

- Chapter 2 content exists, but its outline entry is still missing because this phase intentionally expanded only Chapter 3-8.
- Phase 6 should add gap detection and outline backfill so generated chapters and outline coverage cannot drift apart.

## Chapter 3 Generation

Agent run:

- id: `292a8b5b-cd1e-424b-98cd-fb9ac20aaf57`.
- status: `success`.
- tools:
  - `preflight_writing`, chapter 3.
  - `generate_chapter`, chapter 3.
  - `analyze_chapter_world_model`, chapter 3.

Preflight:

- status: `ready`.
- missing Chapter 3 outline blocker from Phase 4 was cleared by the expansion run.

Generated chapter:

- id: `ca020da6-5ab3-4a61-8b6d-ad425e68cd5f`.
- chapter index: `3`.
- title: `雾中童谣`.
- word count: `3080`.
- status: `generated`.
- trace id: `26d0bdb4-43cc-49bd-a7ac-6192f036ac79`.

Model trace:

- status: `success`.
- prompt tokens: `3901`.
- completion tokens: `2321`.
- latency: `39614 ms`.
- context blocks included: `9`.
- context blocks omitted: `0`.
- used context chars: `5896`.

Prose quality trace:

- status: `prose`.
- line count: `72`.
- outline marker count: `0`.
- sentence ending count: `153`.
- warnings: none.

Length decision:

```json
{
  "status": "over",
  "decision": "accept_with_warning",
  "actual_word_count": 3080,
  "target_max_word_count": 2300
}
```

World-model analysis:

- Chapter generation auto-analysis created `9` proposal items.
- Explicit `analyze_chapter_world_model` immediately after generation created `0` new items and skipped `9` duplicates.
- Proposal queue after Chapter 3:

```json
{
  "profile_version": 1,
  "total_items": 24,
  "returned_items": 24,
  "has_more": false
}
```

Maintenance after Chapter 3:

```json
{
  "ready_for_writing": true,
  "chapter_count": 3,
  "word_target": {
    "status": "drift",
    "over_target_count": 3,
    "over_target_chapter_indexes": [1, 2, 3]
  },
  "stale_memory_count": 0,
  "missing_memory_count": 0,
  "stale_retrieval_count": 0,
  "missing_retrieval_count": 0
}
```

## Issues Found

- Chapter 2 outline entry is still missing even though Chapter 2 content exists. The next phase needs outline gap detection and backfill.
- All three generated chapters are over the configured target. The system records this but still accepts with warning.
- The proposal review queue now has `24` pending items. Long batch writing needs triage or batching before continuing too far.
- Running explicit `analyze_chapter_world_model` after `generate_chapter` is redundant when generation already returns completed Athena analysis.

## Issues Fixed

- Chapter 3 is no longer generated beyond outline coverage.
- Rolling outline expansion can safely append missing future chapter plans without overwriting existing outline entries.
- The Agent can call outline expansion as a first-class tool.
- Chapter 3 received a semantic title from the expanded outline instead of falling back to a generic title.

## Verification

- T1 targeted:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_expand_outline_window_adds_missing_outline_then_preflight_ready tests\test_outlines.py::test_expand_outline_window_appends_missing_chapters_without_overwriting_existing tests\test_outlines.py::test_expand_outline_window_ignores_out_of_window_chapters -q`.
  - Result: `3 passed`.
- T1 related suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q`.
  - Result: `27 passed`.
- Diff hygiene:
  - Command: `git diff --check`.
  - Result: exit code `0`.
- Secret scan:
  - Command: `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`.
  - Result: no matches.
- Runtime:
  - Backend health on `8001`: `{"status":"ok"}`.
  - Outline expansion run succeeded.
  - Chapter 3 preflight returned `ready`.
  - Chapter 3 was generated through the Agent path.
  - Chapter 3 world-model proposals were recorded.

## Next Phase Recommendation

Phase 6 should focus on turning the Agent from a tool executor into a safer writing loop:

- Add outline gap detection and backfill for missing historical chapter entries, starting with Chapter 2.
- Add a repeated-over-target policy: after multiple overlong chapters, require revision, compression, or target adjustment instead of warning-only acceptance.
- Avoid redundant world-model analysis when `generate_chapter` already produced Athena proposal items.
- Add proposal queue triage before generating more chapters.
- Continue dogfood by generating Chapter 4 only after the above checks pass.
