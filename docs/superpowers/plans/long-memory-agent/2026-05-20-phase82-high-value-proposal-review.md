# Phase82 Plan: High Value Proposal Review

## Phase Goal

Give the Writing Agent a safe path to handle the high-risk Chapter 25 world-model proposals surfaced in Phase81 before continuing to Chapter 26.

## Problem

Phase81 correctly promoted high-value plot signals:

- `identifier_meaning_hypothesis`
- `access_permission_anomaly`
- `investigation_lead`

But the existing default draft resolver intentionally leaves these predicates unclassified. That is safer than auto-approving them, but it also means the Agent cannot clear review pressure without a manual decision path.

## Scope

Add a read-only draft tool:

- `draft_high_value_world_proposal_resolution_decisions`

Behavior:

- reads current actionable world proposals;
- filters only high-value Phase81 predicates;
- drafts `mark_uncertain` decisions with evidence and predicate-specific reasons;
- does not write reviews or facts;
- can be followed by existing `apply_world_model_proposal_resolution` when explicitly confirmed.

Rationale:

- `mark_uncertain` preserves the proposal as reviewed but avoids turning a character inference into confirmed world truth;
- the action clears generation pressure safely;
- later phases can add richer fact materialization if needed.

## Files

Create:

- `backend/app/core/high_value_world_proposal_resolution_draft.py`

Modify:

- `backend/app/services/writing_agent/tool_executor.py`
- `backend/app/services/writing_agent/tool_registry.py`
- `backend/app/services/writing_agent/run_service.py`
- `backend/tests/test_writing_agent_runs.py`

## Verification

Targeted:

- new tool drafts high-value proposal decisions without writes;
- new tool leaves unrelated low-risk proposals alone;
- new tool can be followed by confirmed guarded apply;
- default low-risk draft remains unchanged.

Runtime:

- use the live Chapter 25 proposals in `雾港回声`;
- draft, preview, apply with confirmation if valid;
- verify proposal pressure clears or document any blocker.

## Not Doing

- No automatic approval.
- No world fact materialization for these new predicates.
- No frontend UI.
- No Chapter 26 generation until queue pressure is handled.
