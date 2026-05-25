# Phase 13 Guarded World Proposal Apply Report

## Scope

Phase 13 added a guarded Writing Agent apply path for explicit world-model proposal decisions.

The phase intentionally supports only non-merge decisions:

- `reject`
- `mark_uncertain`

It does not support `approve`, `approve_with_edits`, bundle split, rollback, frontend UI, or Chapter 4 generation.

## Implementation Summary

- Created `backend/app/core/world_proposal_resolution_apply.py`.
- Wired `apply_world_model_proposal_resolution` into:
  - `ALLOWED_TOOLS`;
  - `INTERNAL_TOOLS`;
  - `NON_BLOCKING_REPORT_TOOLS`;
  - `_execute_tool`;
  - `_target_type_for_tool`;
  - `_should_stop_after_report`;
  - `_successful_report_block_message`;
  - `_allowed_report_followup` from preview to apply.
- Extended `review_proposal_item` with `commit=True` default. Existing callers keep current behavior; guarded apply uses `commit=False` to apply a batch atomically and commits once after all decisions pass review-stage validation.

## Safety Rules

The tool:

- requires `confirm_apply=true`;
- calls Phase12 preview validation before writing;
- refuses the whole batch if any decision is invalid;
- refuses `approve` and `approve_with_edits`;
- creates no `WorldFactClaim`;
- writes `WorldProposalReview` rows only for confirmed `reject` / `mark_uncertain`;
- updates `WorldProposalItem.item_status`;
- keeps chapter generation blocked unless the real actionable queue is clear.

## Review Fixes

Independent review found a valid partial-write risk: `review_proposal_item` committed each item internally, so a later review-stage failure could leave earlier decisions applied.

Fix:

- `review_proposal_item(..., commit=False)` now flushes without committing.
- `apply_world_model_proposal_resolution` loops through decisions and performs one final `db.commit()`.
- If any review-stage `ValueError` occurs, the batch rolls back and returns `apply_failed`.

Regression coverage:

- `test_agent_apply_world_model_proposal_resolution_rolls_back_when_review_stage_fails`
- The test makes preview pass, then causes the second item to fail during review via contract-version drift.
- Expected result: both items remain `pending`, and no review row is created.

## Dogfood Evidence

- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- Novel: `雾港回声`
- Generated chapters before and after: 3
- Chapter 4 generation: intentionally skipped
- Apply run: `03330a03-1c45-4d4d-9bf2-73ee2a9bdea6`

Before apply:

- actionable proposal items: 24
- proposal reviews: 0
- world fact claims: 0
- selected statuses:
  - `b642eaa2-553a-4dff-a77b-1f6f0e89fca4`: `pending`
  - `9a5a799c-d0df-4616-97cd-798bd3f1425f`: `pending`

Applied decisions:

- `b642eaa2-553a-4dff-a77b-1f6f0e89fca4`: `reject`
  - review ID: `f6db0b3d-d38c-40f9-98c7-48acc20413ae`
- `9a5a799c-d0df-4616-97cd-798bd3f1425f`: `mark_uncertain`
  - review ID: `fcf2cf2b-03b3-47f2-9bdb-3db8d624fff6`

After apply:

- actionable proposal items: 22
- proposal reviews: 2
- world fact claims: 0
- selected statuses:
  - `b642eaa2-553a-4dff-a77b-1f6f0e89fca4`: `rejected`
  - `9a5a799c-d0df-4616-97cd-798bd3f1425f`: `uncertain`

Tool output:

- `status`: `blocked`
- `applied_count`: 2
- `invalid_decision_count`: 0
- `requires_confirmation`: `false`
- `should_generate_next_chapter`: `false`
- `recommended_actions`: `continue_world_model_proposal_resolution`

## Verification Evidence

Targeted Phase13 suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_missing_profile_without_decisions tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_applies_confirmed_non_merge_decisions tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rolls_back_when_review_stage_fails tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_invalid_batch_without_partial_writes tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_allows_apply_followup tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_followup_generation_when_queue_remains tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_allows_generation_when_queue_clears -q
```

Result: `9 passed in 0.80s`.

Writing Agent suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Result: `55 passed in 3.70s`.

Independent re-review targeted suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rolls_back_when_review_stage_fails tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_followup_generation_when_queue_remains tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_allows_generation_when_queue_clears -q
```

Result: `4 passed in 0.43s`.

Final checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Result: whitespace check passed; secret scan returned no matches.

## Next Phase Recommendation

Do not generate Chapter 4 yet. The real proposal queue still has 22 actionable items.

Next phase should reduce the queue further by either:

- applying more explicit non-merge decisions in small confirmed batches; or
- adding a report-only decision drafting tool that suggests low-risk non-merge actions while still requiring explicit confirmation before apply.
