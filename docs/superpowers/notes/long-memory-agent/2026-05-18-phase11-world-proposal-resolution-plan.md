# Phase 11 World Proposal Resolution Plan

## Runtime

- Date: 2026-05-18.
- Verification tier: T1 plus T2 runtime dogfood proposal resolution planning.
- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Dogfood novel: `《雾港回声》`.
- Runtime path: direct `WritingAgentRunService` execution against the local dogfood DB.
- Secret handling: no API key was written to source, docs, `.env`, or logs committed to git.

## Implementation

Added Agent tool:

- `plan_world_model_proposal_resolution`.

Added planning core:

- `backend/app/core/world_proposal_resolution_plan.py`.

The tool:

- reuses the Phase 10 proposal queue report;
- builds an ordered `resolution_steps` list;
- places individual high/medium review steps before low-risk batch steps;
- exposes allowed review actions as non-executed options;
- returns `can_auto_apply=false`;
- returns `requires_human_confirmation=true` while steps exist;
- returns `should_generate_next_chapter=false` while actionable proposals remain.

Safety behavior:

- Does not approve proposal items.
- Does not reject proposal items.
- Does not split bundles.
- Does not roll back reviews.
- Does not create `WorldProposalReview`.
- Does not create `WorldFactClaim`.
- Does not change `WorldProposalItem.item_status`.

Agent chaining behavior:

- `review_world_model_proposals -> plan_world_model_proposal_resolution` is allowed in the same run.
- `plan_world_model_proposal_resolution -> generate_chapter` is blocked while proposals remain.

## Dogfood Progress

- Current generated chapters remain: `3`.
- Chapter 4 remains ungenerated.
- World-model proposal queue remains unresolved, but now has an Agent-readable resolution order.

## Dogfood Resolution Plan

Primary Agent run:

- id: `21da402c-36e8-48bc-91db-e1801e0f2a5a`.
- status: `success`.
- tool: `plan_world_model_proposal_resolution`.
- output status: `blocked`.
- total proposal items: `24`.
- returned items: `20`.
- resolution steps: `10`.
- high-priority steps: `3`.
- batch steps: `7`.
- `should_generate_next_chapter`: `false`.

Risk counts for returned items:

- high: `3`.
- medium: `0`.
- low: `17`.

Review mode counts for returned items:

- individual: `3`.
- batch: `17`.

Recommended actions:

- `pause_generation_until_proposals_resolved`.
- `resolve_individual_proposals_first`.
- `resolve_batch_proposals_after_individuals`.

First resolution step:

- action: `review_individual`.
- recommended resolution: `manual_individual_review`.
- predicate: `event_summary`.
- subject: `chapter.1`.
- item id: `b642eaa2-553a-4dff-a77b-1f6f0e89fca4`.
- reason: `状态、身份、事件、关系或规则类候选会改变后续叙事，应单独审阅。`

Last returned resolution step:

- action: `review_batch`.
- recommended resolution: `batch_review`.
- predicate: `presence_count`.
- subject: `char.林深`.
- chapter range: `3-3`.

## Chain Smoke

Agent run:

- id: `06f92f9c-9cb5-40fd-9e1f-2fc27b9d89be`.
- status: `success`.
- tools:
  - `review_world_model_proposals`;
  - `plan_world_model_proposal_resolution`.
- step statuses:
  - `success`;
  - `success`.
- first output status: `blocked`.
- second output status: `blocked`.
- second resolution step count: `10`.

## Non-Destructive Evidence

Before primary Agent run:

- proposal items: `24`.
- pending proposal items: `24`.
- proposal reviews: `0`.
- fact claims: `0`.

After primary Agent run:

- proposal items: `24`.
- pending proposal items: `24`.
- proposal reviews: `0`.
- fact claims: `0`.

The before/after counts were identical.

The chain smoke also kept proposal/review/fact counts unchanged.

## Issues Fixed

- `plan_world_model_proposal_resolution` is now an executable Writing Agent tool.
- Agent can convert proposal queue pressure into a concrete review order.
- Phase 10 report can now be followed by Phase 11 planning in the same run.
- Follow-up chapter generation remains blocked while proposal resolution is pending.
- Batch resolution steps keep the full returned item id list instead of inheriting the compact 10-id report limit.
- `high_priority_step_count` now counts only high-risk steps, not all individual medium/high steps.

## Issues Found

- The tool still only plans resolution; it does not yet provide a guarded mechanism for applying approved human decisions.
- Batch planning is grouped by existing queue clusters; future phases may need a user-facing review transaction format.
- Current dogfood queue still blocks Chapter 4 generation until proposal handling is resolved.

## Verification

- TDD red check:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_orders_review_steps_without_writes tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_ready_when_queue_empty tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_allows_resolution_plan_followup tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_blocks_followup_generation -q`.
  - Initial result: `4 failed`.
- Targeted green:
  - Same command.
  - Result: `4 passed`.
- Code review regression red check:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_keeps_full_batch_item_ids tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_counts_medium_separately_from_high -q`.
  - Initial result: `2 failed`.
- Code review regression green:
  - Same command.
  - Result: `2 passed`.
- Phase 11 targeted suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_orders_review_steps_without_writes tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_ready_when_queue_empty tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_keeps_full_batch_item_ids tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_counts_medium_separately_from_high tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_allows_resolution_plan_followup tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_blocks_followup_generation -q`.
  - Result: `6 passed`.
- T1 Agent suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q`.
  - Result: `38 passed`.
- T1 related suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_outlines.py -q`.
  - Result: `108 passed`.
- Diff hygiene:
  - Command: `git diff --check`.
  - Result: exit code `0`.
- Secret scan:
  - Command: `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`.
  - Result: no matches.
- Runtime:
  - Agent run `21da402c-36e8-48bc-91db-e1801e0f2a5a` succeeded.
  - Chain run `06f92f9c-9cb5-40fd-9e1f-2fc27b9d89be` succeeded.
  - Proposal/review/fact business counts were unchanged.

## Next Phase Recommendation

Phase 12 should make proposal resolution actionable but still guarded:

- Define a human-confirmed proposal resolution command format.
- Allow low-risk batch approvals only when explicitly requested.
- Keep high-risk approvals individual and auditable.
- Do not generate Chapter 4 until the proposal queue is reduced or intentionally deferred.
