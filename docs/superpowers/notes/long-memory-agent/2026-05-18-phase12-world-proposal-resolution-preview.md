# Phase 12 World Proposal Resolution Preview Report

## Scope

Phase 12 added a non-destructive Writing Agent tool, `preview_world_model_proposal_resolution`, to validate explicit world-model proposal decisions and preview their impact before any real review action is allowed.

This phase intentionally did not apply proposal decisions, split bundles, roll back reviews, build frontend UI, or generate Chapter 4.

## Implementation Summary

- Created `backend/app/core/world_proposal_resolution_preview.py`.
- Wired `preview_world_model_proposal_resolution` into:
  - `ALLOWED_TOOLS`;
  - `INTERNAL_TOOLS`;
  - `NON_BLOCKING_REPORT_TOOLS`;
  - `_execute_tool`;
  - `_target_type_for_tool`;
  - `_should_stop_after_report`;
  - `_successful_report_block_message`;
  - `_allowed_report_followup`.
- Added tests in `backend/tests/test_writing_agent_runs.py`.

The preview core validates:

- missing proposal IDs;
- duplicate proposal IDs;
- missing proposal items;
- profile mismatch;
- non-actionable statuses;
- unsupported actions;
- invalid `approve_with_edits` payloads;
- world-intake approvals that were not atomized.
- non-dict decisions when the project has no current profile;
- string `evidence_refs`, normalized as one reference.

The tool does not call `review_proposal_item`, `split_bundle`, or `rollback_review`.

## Dogfood Evidence

- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- Novel: `雾港回声`
- Generated chapters before and after: 3
- Chapter 4 generation: intentionally skipped

### Direct Preview Run

- Run ID: `0f918c11-1da9-4e0c-8096-2067cb96ae8a`
- Run status: `success`
- Tool output status: `blocked`
- Previewed decisions:
  - `b642eaa2-553a-4dff-a77b-1f6f0e89fca4`: `reject`
  - `9a5a799c-d0df-4616-97cd-798bd3f1425f`: `mark_uncertain`

Before preview:

- actionable proposal items: 24
- proposal reviews: 0
- world fact claims: 0
- selected item statuses: `pending`, `pending`

Preview output:

- `preview_only`: `true`
- `requires_confirmation`: `true`
- `can_auto_apply`: `false`
- `valid_decision_count`: 2
- `invalid_decision_count`: 0
- `would_create_review_count`: 2
- `would_create_fact_count`: 0
- `would_resolve_item_count`: 2
- `remaining_actionable_item_count_after_preview`: 22
- `would_unblock_generation`: `false`
- `should_generate_next_chapter`: `false`

After preview:

- actionable proposal items: 24
- proposal reviews: 0
- world fact claims: 0
- selected item statuses: `pending`, `pending`

### Chain Smoke Run

- Run ID: `1522e21a-5943-4ca3-a24c-ee3b15182f6e`
- Tools:
  - `plan_world_model_proposal_resolution`
  - `preview_world_model_proposal_resolution`
- Run status: `success`
- Both steps completed with output status `blocked`.
- Counts were unchanged after the chained run: 24 actionable items, 0 reviews, 0 facts.

## Verification Evidence

TDD red checks:

- `test_agent_preview_world_model_proposal_resolution_blocks_generation_for_empty_queue_decisions` failed before fixing empty-queue decision handling.
- `test_agent_preview_world_model_proposal_resolution_rejects_non_atomized_world_intake_approve` failed before adding atomization validation.

Targeted green checks:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_validates_decisions_without_writes tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_reports_missing_profile_for_non_dict_decision tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_reports_invalid_decisions tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_reports_non_actionable_items tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_blocks_generation_for_empty_queue_decisions tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_rejects_non_atomized_world_intake_approve tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_allows_preview_followup tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_blocks_followup_generation -q
```

Result: `8 passed in 0.65s`.

Writing Agent suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Result: `46 passed in 3.10s`.

Related T1 suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_outlines.py -q
```

Result: `116 passed in 7.35s`.

Final pre-commit checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Result: whitespace check passed; secret scan returned no matches.

## Issues Found And Fixed

- Preview decisions supplied while the real queue was empty could have implied generation was safe. Fixed so any preview decision keeps `should_generate_next_chapter=false`, and invalid decisions are reported before empty-queue readiness.
- World-intake proposals could be preview-approved without converting them into atomic facts. Fixed by reusing the world-intake atomization validation in preview.
- Missing-profile preview could raise a 500 when a decision was not a dict. Fixed by normalizing invalid decisions in `_empty_result`.
- Non-actionable proposal item validation now has regression coverage.
- String `evidence_refs` no longer splits into individual characters.

## Next Phase Recommendation

Phase 13 should add a guarded apply path for explicit confirmed proposal decisions. Keep the first apply surface narrow:

- accept only explicit item IDs and explicit actions;
- begin with `reject` and `mark_uncertain`, or a very small confirmed batch;
- keep `approve` and `approve_with_edits` under stricter validation because they create durable facts;
- record before/after counts for proposal items, reviews, and fact claims;
- keep chapter generation blocked until the real proposal queue is reduced, deferred, or otherwise resolved.
