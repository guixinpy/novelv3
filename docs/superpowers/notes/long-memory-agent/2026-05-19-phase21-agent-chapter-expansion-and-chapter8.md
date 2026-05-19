# Phase 21 Report: Agent Chapter Expansion and Chapter 8

## Summary

Phase21 added an Agent-owned `expand_chapter_to_target` tool so under-target generated chapters can be repaired without manual editing or full chapter regeneration. The tool uses existing chapter word targets, chapter revision/version models, model-call trace storage, quality review gates, and Writing Agent report-stop behavior.

Dogfood progress continued from Chapter 7 to Chapter 8. Chapter 7 was expanded from 1814 to 2670 words and no longer triggers `chapter_under_target`. Chapter 8 was then generated at 2647 words. Both chapters have `blocker_count=0`, and the world-model proposal queue is clear. The remaining system issue is now different: length control is overshooting the 2300-word upper target, which should be addressed in the next phase.

## Code Changes

- Added `backend/app/core/chapter_expansion.py`.
- Registered `expand_chapter_to_target` in `WritingAgentRunService`.
- Added report-stop behavior so expansion cannot be followed directly by `generate_chapter`.
- Allowed `expand_chapter_to_target -> review_chapter_quality`.
- Added tests for:
  - successful expansion with completed revision and base/result versions;
  - review-after-expansion clearing `chapter_under_target`;
  - blocking direct follow-up generation;
  - skipping already-at-target chapters without model calls;
  - blocking expansion when world-model proposals are pending.

## Test Evidence

- RED:
  - `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_updates_chapter_versions_and_requires_review -q`
  - Result: failed with `ModuleNotFoundError: No module named 'app.core.chapter_expansion'`.
- GREEN focused:
  - `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_updates_chapter_versions_and_requires_review tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_then_review_clears_under_target_warning tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_blocks_direct_followup_generation tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_skips_when_chapter_already_at_target tests\test_writing_agent_runs.py::test_agent_expand_chapter_to_target_blocks_pending_world_model_proposals -q`
  - Result: `5 passed in 0.60s`
- T2 verification:
  - `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q`
  - Result: `133 passed in 9.94s`

## Dogfood Evidence

### Chapter 7 Expansion

- Run id: `8f1dbbf6-7908-4a00-a659-ac6b5dadfd83`
- Revision id: `d4e593ef-7117-4390-8251-3d47ec21035f`
- Trace id: `b93eb4ab-bae6-48a7-8d07-3f97e6b36b10`
- Previous word count: 1814
- New word count: 2670
- Target range: 2000-2300
- Status: `completed`
- Remaining pending world-model proposals before expansion: 0

### Chapter 7 Review and Analysis

- Run id: `450fea79-f230-4103-80fa-2fa50ac2dcfc`
- Review status: `warning`
- Finding count: 1
- Blocker count: 0
- Cleared:
  - `chapter_under_target`
- Remaining warning:
  - `chapter_over_target`: 2670 words, above 2300 target max.
- Athena analysis:
  - created proposals: 0
  - duplicate skips: 3
- Remaining pending world-model proposals: 0

### Chapter 8 Generation

- Run id: `2efb467b-08e5-4378-82a1-edfa99839927`
- Chapter title: `废弃实验室`
- Word count: 2647
- Review status: `warning`
- Finding count: 2 before proposal cleanup
- Blocker count: 0
- Athena analysis during generation created 7 world-model proposal items.

### Chapter 8 World-Model Cleanup

- Draft decision run id: `cd4606a1-ee15-4e92-9f36-be41e5e66bed`
  - inspected items: 7
  - draft decisions: 7
  - unclassified items: 0
- Apply decision run id: `2def5806-d5a2-4fe8-96eb-1832a16306a1`
  - before actionable items: 7
  - applied count: 7
  - after actionable items: 0
- Final Chapter 8 review:
  - finding count: 1
  - blocker count: 0
  - remaining warning: `chapter_over_target`
- Remaining pending world-model proposals: 0

## Current Novel Progress

- Generated chapters: 8
- Current chapters and word counts:
  - Chapter 1 `雾中回声`: 3735
  - Chapter 2 `第2章`: 3511
  - Chapter 3 `雾中童谣`: 3080
  - Chapter 4 `顾衍的警告`: 1861
  - Chapter 5 `空白信的秘密`: 2482
  - Chapter 6 `黑市雾晶`: 2165
  - Chapter 7 `苏晚晴的梦境`: 2670
  - Chapter 8 `废弃实验室`: 2647
- Pending world-model proposals: 0

## Decisions

- Expansion is versioned and Agent-owned, not a manual text patch.
- The tool blocks on pending world-model proposals and does not approve or merge facts itself.
- The tool currently enforces the lower bound but does not reject mild upper-bound overshoot. This allowed dogfood to proceed because review had no blocker, but it exposed a real length-control weakness.

## Next Phase Recommendation

Phase22 should focus on length discipline:

- strengthen generation feedback so chapters target 2000-2300 instead of drifting high;
- consider a guarded `compress_chapter_to_target` tool for `chapter_over_target`;
- make repeated upper-bound warnings affect `preflight_writing` before Chapter 9;
- review earlier chapters with extreme over-target counts, especially Chapters 1-3, as accumulated scale risk.
