# Phase 20 Report: Deterministic Revision Apply and Chapter 7

## Summary

Phase20 added a conservative Writing Agent tool, `apply_planner_revision_patch`, for planner-owned deterministic chapter repairs. The tool is intentionally narrow: it applies only supported `[PLAN_ACTION:*]` annotations, versions the chapter before and after the patch, updates word counts, completes the revision, and forces a quality review before further generation.

The dogfood sequence repaired Chapter 6, cleared its drift blockers, generated Chapter 7, and then resolved Chapter 7 world-model proposal pressure. Chapter 7 still surfaced a non-blocking quality gap: it is 1814 words, below the current 2000-word minimum. That should become the next phase focus via an Agent-owned chapter expansion flow rather than being folded into this drift-specific patch tool.

## Code Changes

- Added `backend/app/core/chapter_revision_apply.py`.
- Registered `apply_planner_revision_patch` in `WritingAgentRunService`.
- Added target type `revision`, report-stop behavior, and explicit allowed follow-ups:
  - `create_revision_draft -> apply_planner_revision_patch`
  - `apply_planner_revision_patch -> review_chapter_quality`
- Added tests for deterministic patch application, chapter versioning, revision completion, and post-patch quality review.

## Test Evidence

- RED: targeted apply-patch tests failed before the tool was registered because the tool had no execution path.
- GREEN:
  - `cd backend`
  - `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_planner_revision_patch_updates_chapter_and_versions tests\test_writing_agent_runs.py::test_agent_apply_planner_revision_patch_then_review_clears_drift_blockers -q`
  - Result: `2 passed in 0.33s`
- Revision-draft regression:
  - `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_create_revision_draft_from_plan_is_non_destructive tests\test_writing_agent_runs.py::test_agent_create_revision_draft_reuses_existing_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_does_not_modify_manual_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_does_not_compete_with_submitted_revision tests\test_writing_agent_runs.py::test_agent_create_revision_draft_blocks_followup_generation -q`
  - Result: `5 passed in 0.50s`
- T2 verification:
  - `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q`
  - Result: `128 passed in 9.70s`

## Dogfood Evidence

### Chapter 6 Repair

- Run id: `f4ca6e09-47f9-473d-a6d6-e93037894f8a`
- Revision id: `94ee16d6-1559-4dac-b13b-138bb065ae0a`
- Applied replacements: 2
- Base version: `1d5aa4d3-4077-4320-9770-a487b5766f4a`
- Result version: `00a40199-de1d-46ed-9b93-d753deb73e13`
- Chapter 6 word count after patch: 2165
- Old drift terms removed:
  - `雾安局研究员`
  - `制造幻觉`
- Replacement terms present:
  - `雾港大学神经科学教授`
  - `扰乱雾中感知`

### Chapter 6 Review

- Status: `ready`
- Finding count: 0
- Blocker count: 0
- Cleared:
  - `character_profile_drift`
  - `ability_boundary_drift`

### Chapter 7 Generation

- Run id: `1ec76939-57d8-4f32-80a6-9495052ccc8c`
- Chapter title: `苏晚晴的梦境`
- Word count: 1814
- Review status: `warning`
- Blocker count: 0
- Findings:
  - `chapter_under_target`: 1814 words, below 2000 minimum.
  - `pending_world_model_proposals`: 3 pending proposals.
- Athena world-model analysis created 3 proposal items during generation, so the explicit analysis step correctly skipped duplicate analysis in the same run.

### World-Model Proposal Cleanup

- Draft decision run id: `ed1c52da-127d-49d0-86ce-fc458edd8ce1`
  - Inspected items: 3
  - Draft decisions: 3
  - Unclassified items: 0
- Apply decision run id: `c7d0ce41-41cf-4911-8668-3cc9f781c408`
  - Before actionable items: 3
  - Applied count: 3
  - After actionable items: 0
- Remaining pending world-model proposals: 0
- Chapter 7 review after proposal cleanup still has the word-count warning only.

## Decisions

- `apply_planner_revision_patch` stays deterministic and narrow. It does not handle `expand_chapter`, `compress_chapter`, arbitrary annotations, or LLM regeneration.
- Chapter 7 under-target length is not fixed by this phase. It needs a separate Agent-owned expansion flow with versioning, review, and tests.
- World-model proposal cleanup used the existing guarded decision workflow rather than direct database edits.

## Next Phase Recommendation

Implement an Agent-owned `expand_chapter_revision` or equivalent flow for `chapter_under_target`:

- plan from `chapter_under_target`;
- create a versioned expansion draft or patch;
- use LLM only with strict context, outline, continuity, and no-new-fact constraints;
- enforce `word_count >= 2000`;
- review after expansion;
- keep world-model proposal queue clear before generating Chapter 8.
