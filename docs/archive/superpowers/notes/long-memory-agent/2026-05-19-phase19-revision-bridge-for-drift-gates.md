# Phase 19 Report: Revision Bridge for Drift Gates

## Summary

Phase19 connected Phase18's deterministic drift gates to the existing non-destructive chapter revision pipeline.

The system can now turn `character_profile_drift`, `ability_boundary_drift`, and `convenient_key_item_acquisition` findings into concrete revision actions. `create_revision_draft` can anchor drift actions to specific evidence excerpts and produce planner-owned annotations without overwriting chapter content.

Chapter 7 was not generated in this phase. The required next action is still to resolve Chapter 6 blockers first.

## Code Changes

- `backend/app/core/chapter_revision_planner.py`
  - Mapped `character_profile_drift` to `fix_character_profile_drift`.
  - Mapped `ability_boundary_drift` to `respect_ability_boundary`.
  - Mapped `convenient_key_item_acquisition` to `add_key_item_cost`.
  - Preserved source finding evidence in each action.
- `backend/app/core/chapter_revision_drafts.py`
  - Extended evidence anchoring to use `excerpt`, `matched_role`, and `matched_terms`.
  - Added specific annotation comments for drift and key-item-cost actions.
- `backend/tests/test_writing_agent_runs.py`
  - Added planner mapping coverage for drift findings.
  - Added draft annotation coverage for drift anchors and comments.

## TDD Evidence

RED command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_maps_drift_findings_to_actions tests\test_writing_agent_runs.py::test_agent_create_revision_draft_anchors_drift_actions -q
```

Initial result: `2 failed`.

Failure reasons:

- planner produced no revision actions for the new drift findings;
- create revision draft skipped because there were no mapped actions.

GREEN command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_maps_drift_findings_to_actions tests\test_writing_agent_runs.py::test_agent_create_revision_draft_anchors_drift_actions -q
```

Result: `2 passed in 0.26s`.

Focused regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_maps_review_findings_to_actions tests\test_writing_agent_runs.py::test_agent_create_revision_draft_from_plan_is_non_destructive tests\test_writing_agent_runs.py::test_agent_create_revision_draft_reuses_existing_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_does_not_modify_manual_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_blocks_followup_generation -q
```

Result: `5 passed in 0.49s`.

T2 verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result: `126 passed in 14.96s`.

## Dogfood: Chapter 6 Revision Plan

Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`

Run id: `d4baaac6-26dd-468f-aa5b-6c9ab4ca40ea`

Tool: `plan_chapter_revision`, Chapter 6.

Result:

- status: `blocked`
- should_generate_next_chapter: `false`
- world model proposal pressure: `0`
- recommended next tools: `revise_chapter`

Revision actions:

- `fix_character_profile_drift`
  - Source finding: `character_profile_drift`
  - Character: `叶知秋`
  - Evidence role: `研究员`
  - Target: restore identity/profession/history to existing setup; do not keep drift as truth.
- `respect_ability_boundary`
  - Source finding: `ability_boundary_drift`
  - Matched term: `制造幻觉`
  - Target: delete or rewrite ability behavior outside existing world rules unless a new unlock and world-model proposal exist.

## Dogfood: Chapter 6 Revision Draft

Run id: `af788393-d17e-4265-925c-b355b43b7e3f`

Tool: `create_revision_draft`, Chapter 6.

Result:

- status: `drafted`
- revision id: `94ee16d6-1559-4dac-b13b-138bb065ae0a`
- revision index: `1`
- annotation count: `2`
- correction count: `0`
- should_generate_next_chapter: `false`

Draft annotations:

- `[PLAN_ACTION:fix_character_profile_drift][SOURCE:character_profile_drift]`
  - selected text contains the `叶知秋` identity drift excerpt.
- `[PLAN_ACTION:respect_ability_boundary][SOURCE:ability_boundary_drift]`
  - selected text: `制造幻觉`

Chapter 6 content was not overwritten:

- chapter id: `e46454fd-8d4b-4379-b4fc-25809ff7d011`
- title: `黑市雾晶`
- word count: `2153`
- status: `generated`

## Chapter 7 Decision

Chapter 7 remains intentionally ungenerated.

Reason: Chapter 6 now has a concrete revision draft, but the content has not yet been revised or re-reviewed to `blocker_count=0`. Continuing generation before applying the revision would propagate known continuity defects.

## Remaining Issues

- The system now creates a repair plan and draft, but it still does not apply the revision automatically.
- The draft contains annotations, not rewritten chapter text.
- The next phase needs either a safe "apply planner-owned deterministic patch" path or a controlled LLM rewrite path that preserves chapter structure and verifies blockers afterward.
- World fact claims remain `0`, so durable truth materialization is still incomplete.

## Next Phase Recommendation

Phase20 should implement the next safe step in the repair loop:

- Option A: deterministic patch for the two known Chapter 6 drift spans, then re-review.
- Option B: controlled revision regeneration using existing revision APIs, with the planner-owned annotations as constraints.

The phase should end only after Chapter 6 review has no blocker findings, or after documenting why automated repair is not safe enough and what manual confirmation is required.
