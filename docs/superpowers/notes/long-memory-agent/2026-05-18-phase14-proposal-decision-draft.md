# Phase 14 World Proposal Decision Draft Report

## Scope

Phase 14 added a report-only Writing Agent tool, `draft_world_model_proposal_resolution_decisions`, that drafts explicit low-risk non-merge decisions for the world-model proposal queue.

The tool does not apply decisions. It emits decisions for later confirmation through Phase13 `apply_world_model_proposal_resolution`.

## Implementation Summary

- Created `backend/app/core/world_proposal_resolution_draft.py`.
- Wired `draft_world_model_proposal_resolution_decisions` into:
  - `ALLOWED_TOOLS`;
  - `INTERNAL_TOOLS`;
  - `NON_BLOCKING_REPORT_TOOLS`;
  - `_execute_tool`;
  - `_target_type_for_tool`;
  - `_should_stop_after_report`;
  - `_successful_report_block_message`;
  - `_allowed_report_followup` from draft to apply.

## Built-In Policies

- `presence_count` -> `reject`
  - Rationale: diagnostic extraction metadata, not durable world truth.
- `mentioned_in_chapter` -> `reject`
  - Rationale: textual mention metadata, not world truth.
- `present_at_location` -> `mark_uncertain`
  - Rationale: derived location inference requiring confirmation.
- `event_summary` -> `mark_uncertain`
  - Rationale: narrative compression requiring curation before truth-layer merge.

Custom predicate policies are accepted only for `reject` and `mark_uncertain`. Attempts to draft `approve` or `approve_with_edits` are ignored.

## Safety Rules

The draft tool:

- reads only current actionable proposal items;
- creates no `WorldProposalReview`;
- creates no `WorldFactClaim`;
- does not update `WorldProposalItem.item_status`;
- never drafts `approve` or `approve_with_edits`;
- blocks direct follow-up generation;
- allows only `draft_world_model_proposal_resolution_decisions -> apply_world_model_proposal_resolution` as a report follow-up.

## Dogfood Evidence

- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- Novel: `雾港回声`
- Generated chapters before and after: 3
- Chapter 4 generation: intentionally skipped in this phase

### Draft Run

- Run ID: `b56de21e-123b-415b-b079-0fda6c2ec251`
- Run status: `success`
- Tool status: `blocked`

Before draft:

- actionable proposal items: 22
- proposal reviews: 2
- world fact claims: 0

After draft:

- actionable proposal items: 22
- proposal reviews: 2
- world fact claims: 0

Draft summary:

- inspected items: 22
- drafted decisions: 22
- unclassified items: 0
- action distribution:
  - `reject`: 18
  - `mark_uncertain`: 4
- predicate distribution:
  - `mentioned_in_chapter`: 9
  - `presence_count`: 9
  - `present_at_location`: 3
  - `event_summary`: 1

### Confirmed Apply Run

- Run ID: `ffa1058e-4d96-4182-b975-6785ce300b9e`
- Run status: `success`
- Tool status: `ready`

Before apply:

- actionable proposal items: 22
- proposal reviews: 2
- world fact claims: 0

After apply:

- actionable proposal items: 0
- proposal reviews: 24
- world fact claims: 0

Apply summary:

- applied decisions: 22
- invalid decisions: 0
- `should_generate_next_chapter`: `true`
- `recommended_actions`: `preflight_writing`

## Verification Evidence

Phase14 targeted suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_tracks_unclassified_items tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_ignores_approval_policy_overrides tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_allows_apply_followup tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_blocks_followup_generation -q
```

Result: `5 passed in 0.53s`.

Writing Agent suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Result: `59 passed in 4.24s`.

Independent review:

- No Critical issues.
- No Important issues.
- Minor test gap fixed by adding approval-policy override coverage.

Final checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Result: whitespace check passed; secret scan returned no matches.

## Next Phase Recommendation

Phase 15 should run preflight and generate Chapter 4 now that the actionable world proposal queue is clear.

Recommended next loop:

1. Run Writing Agent `preflight_writing`.
2. Generate Chapter 4.
3. Review Chapter 4 quality.
4. Analyze Chapter 4 into world-model proposals.
5. Use the draft/apply path to prevent low-value extraction metadata from blocking future generation.
