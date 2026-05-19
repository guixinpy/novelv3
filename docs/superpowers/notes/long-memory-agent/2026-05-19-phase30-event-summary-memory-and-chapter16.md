# Phase30 Event Summary Memory and Chapter 16

## Goal

Phase30 separated world truth from writing memory more cleanly: reviewed `event_summary` proposal summaries now feed chapter-level longform memory without being merged as confirmed world facts. The phase then continued the real Dogfood loop through Chapter 16.

## Code Change

- Added a reviewed event-summary memory lane in `backend/app/core/longform_memory.py`.
- `rebuild_longform_memory()` and `refresh_longform_memory_for_chapter()` now prefer reviewed `event_summary` proposal summaries for chapter memories.
- Accepted reviewed statuses are `uncertain`, `approved`, and `approved_with_edits`.
- Memory metadata now records `source=reviewed_event_summary`, `event_summary_proposal_item_id`, and `event_summary_item_status` when this lane is used.
- World-model guarded apply behavior was not changed; `event_summary` still does not become world truth automatically.

## TDD Evidence

- RED: `cd backend; .venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_refresh_longform_memory_prefers_reviewed_event_summary_proposal -q`
  - Failed as expected because chapter memory still reported `source=chapter_content`.
- GREEN: `cd backend; .venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_refresh_longform_memory_prefers_reviewed_event_summary_proposal tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_refreshes_longform_memory_and_retrieval -q`
  - `2 passed`.

## Dogfood Memory Evidence

Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`

- Refreshed Chapters 14 and 15 memory, then synced longform memory retrieval documents.
- Chapter 14 memory: `source=reviewed_event_summary`, proposal item `a34fe9c2-279e-458a-8590-fcfe71c549e3`, item status `uncertain`.
- Chapter 15 memory: `source=reviewed_event_summary`, proposal item `ca3f235d-ddb6-46b3-8d3b-cb7418318831`, item status `uncertain`.

After Chapter 16 proposal decisions were reviewed and memory was refreshed:

- Chapter 16 memory: `source=reviewed_event_summary`, proposal item `6897bc07-365f-4ea5-9bd0-b31520ab75e4`, item status `uncertain`.
- Longform maintenance: `status=current`, `ready_for_writing=true`, `issue_count=0`, `latest_synced_chapter_index=16`.

## Dogfood Chapter 16

- Outline expansion run: `cd4453bb-4a00-4956-a542-d7da12c13f1d`
- Preflight run: `e67a5127-e0ee-4416-8cb1-fd89b7f5ba1b`, `status=ready`
- Initial generation/review run: `8600aaf2-c126-4c0f-8454-6bfcf6c8a8c3`
  - Generated Chapter 16 at `2647` words.
  - Quality warning: over target and 5 pending world-model proposals.
  - Continuity review: `ready`.
- Proposal draft run: `c42a0ead-8fd8-4281-a3ec-eec328881e52`
  - Drafted 5 decisions: one `event_summary -> mark_uncertain`, three `presence_count -> reject`, one `mentioned_in_chapter -> reject`.
- Proposal apply run: `db9c7511-6852-4d31-849d-6366e4ffed21`
  - Applied 5 reviews, pending queue reduced from 5 to 0.
- Compression run: `099a8503-8378-4b97-835d-acede96e1bda`
  - Compressed Chapter 16 from `2647` to `2090` words.
  - Quality and continuity review returned `ready`.
- Manual anchor fix:
  - The compressed result still contained a contradiction around N-017: it implied N-017 was not a real military tag.
  - Patched only the affected N-017/军牌 sentences in the local database and created chapter versions.
  - Final Chapter 16 word count: `2105`.
  - Bad phrases removed: `不是我的军牌号`, `研究所里的代号`.
  - Reindexed Chapter 16 and refreshed/synced longform memory.
- Final review run: `57af25e8-2f9a-4343-b376-a91633d8a894`
  - `review_chapter_quality`: `ready`, 0 findings.
  - `review_chapter_continuity`: `ready`, 0 findings.
  - `analyze_chapter_world_model`: created 0, updated 0, skipped duplicates 5.

## Subagent Review

Read-only subagent: `019e3fa4-29bd-73b1-8ef8-ab1c1dde589e`

Conclusion:

- Chapter 16 continues the Chapter 15 `N-07同步完成` hook.
- N-07 and N-017 remain distinct.
- Chapter 16 final word count is `2105`, inside the `2000-2300` target range.
- World-model pending queue is 0.
- Longform memory is current and synced through Chapter 16.
- No blocking issue found.

Non-blocking note:

- The latest outline only reaches Chapter 16, and Chapter 17 content does not exist yet. Next phase should expand Chapter 17 before writing.

## Verification

- `cd backend; .venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_memory or compress_chapter_to_target or review_chapter_quality"` -> `23 passed, 83 deselected`.
- `cd backend; .venv\Scripts\python.exe -m pytest tests\test_longform_scale.py::test_refresh_longform_memory_for_chapter_updates_only_affected_scopes tests\test_longform_scale.py::test_sync_changed_longform_memory_retrieval_documents_preserves_unrelated_docs -q` -> `2 passed`.
- `git diff --check` -> exit 0; only CRLF warning for `backend/tests/test_writing_agent_runs.py`.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"` -> no matches.

## Remaining State

- Dogfood latest generated chapter: 16, title `同步后遗症`, word count `2105`.
- Pending actionable world-model proposals: 0.
- Longform maintenance: current.
- User supplement after Phase30 validation: chapter word count should be an elastic quality target, not a narrow hard cap. `2000+` should mean at least 2000 words with a reasonable upper float, roughly `2000-3000`; hard-compressing every chapter toward 2000 can hurt model writing quality and scene completeness.
- Next recommended phase: update the length policy to use hard lower bounds and soft upper bounds, then expand Chapter 17 outline, preflight, and continue generation.
