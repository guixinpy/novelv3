# Phase27 Stable Truth Anchors and Chapter 14 Report

## Scope

Phase27 moved the highest-risk dogfood continuity anchors into the world-model truth layer and made `review_chapter_continuity` compare generated chapter text against confirmed `WorldFactClaim` rows.

This phase did not add a parallel anchor table. It reused the existing proposal/review/fact governance path so approved anchors remain visible through world-model facts and rollback-capable review records.

## Implementation

Added deterministic continuity-anchor proposal seeding:

- New module: `backend/app/core/continuity_anchor_proposals.py`.
- New Writing Agent tool: `seed_continuity_anchor_proposals`.
- The tool creates missing proposal items for whitelisted anchor predicates and blocks follow-up generation until they are approved.

Allowed guarded approval for only Phase27 continuity-anchor proposals:

- Modified `backend/app/core/world_proposal_resolution_apply.py`.
- Ordinary `approve` / `approve_with_edits` decisions still remain blocked in guarded Writing Agent apply.
- Seeded continuity-anchor items can be approved with `confirm_apply=True`, using the existing `review_proposal_item()` path.

Extended continuity review:

- Modified `backend/app/core/chapter_continuity_review.py`.
- It now reads current-profile confirmed truth facts for stable anchors.
- It emits `stable_truth_anchor_conflict` when chapter text contradicts stable truth.

Initial stable anchor contract:

- `林深.father_name = 林建国`
- `顾衍.military_tag_number = N-017`
- `identifier.N-07.identifier_meaning = 实验代号/实验体编号，不是顾衍军牌编号`
- `event.fog_disaster.event_date = 2045年8月12日`
- `event.fog_disaster.minus_3_days.relative_event_date = 2045年8月9日`

## TDD Evidence

RED/GREEN checks were run for the behavior changes:

- `test_agent_review_chapter_continuity_blocks_against_confirmed_father_truth` failed before continuity review queried `WorldFactClaim`, then passed.
- Equivalent military-tag and relative-event-date truth conflict tests passed after the same implementation.
- `test_agent_seed_continuity_anchor_proposals_creates_missing_anchor_items` failed before the tool existed, then passed.
- `test_agent_apply_world_model_proposal_resolution_allows_confirmed_continuity_anchor_approval` failed while guarded apply still rejected all approvals, then passed after whitelisting Phase27 anchor items.
- `test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes` stayed green, proving ordinary approvals are still blocked.

Targeted command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_blocks_against_confirmed_father_truth tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_blocks_against_confirmed_military_tag_truth tests\test_writing_agent_runs.py::test_agent_review_chapter_continuity_blocks_against_confirmed_relative_event_date_truth tests\test_writing_agent_runs.py::test_agent_seed_continuity_anchor_proposals_creates_missing_anchor_items tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_allows_confirmed_continuity_anchor_approval tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes -q
```

Result:

```text
6 passed in 0.69s
```

## Dogfood Evidence

Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

Phase27 runs:

- Seed anchors: `20771f9a-c82d-42b1-ad89-61aec5386196`, created 5 proposal items.
- Approve anchors: `c6f04067-4557-43b5-98e7-678d23c310e7`, applied 5 approvals.
- Review Chapter 13 anchors: `f9afa01d-3d54-44b8-9c1a-9795e842f2bb`, ready, 0 findings.
- First Chapter 14 preflight: `c689065e-219d-42aa-9031-c73998264496`, blocked only because Chapter 14 outline was missing.
- Expand and preflight Chapter 14: `772016bd-306f-4d86-b0e3-4d02e4359f6a`, outline added and preflight ready.

Dogfood state after Phase27:

```text
world_fact_claims: 5
pending_items: 0
generated_chapters: 13
outline_has_14: true
maintenance_status: current
maintenance_issue_count: 0
```

Confirmed anchor facts:

```text
event.fog_disaster.event_date = 2045年8月12日
event.fog_disaster.minus_3_days.relative_event_date = 2045年8月9日
顾衍.military_tag_number = N-017
identifier.N-07.identifier_meaning = {"value": "实验代号/实验体编号", "not_values": ["顾衍军牌编号"], "status": "confirmed_limited"}
林深.father_name = 林建国
```

Chapter 14 is not generated yet. It is ready for the next phase after stable anchors and preflight.

## Verification

T2 backend verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result:

```text
156 passed in 11.13s
```

Hygiene:

- `git diff --check`: no whitespace errors; only the existing CRLF-to-LF warning for `backend/tests/test_writing_agent_runs.py`.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"`: no matches.

## Decisions and Limits

The stable anchor contract is intentionally narrow. It only covers facts that are already repeated and high-risk in the dogfood novel.

The seed tool is deterministic and currently dogfood-specific. This is acceptable for the current goal loop because the real novel is the active testbed, but a later phase should generalize anchor extraction from approved chapter evidence rather than hardcoding this exact truth set.

Guarded approval remains constrained. It only allows proposals created by `seed_continuity_anchor_proposals`; ordinary model-extracted proposals still cannot be merged automatically through Writing Agent apply.

## Phase28 Recommendation

Generate Chapter 14 using the new stable truth anchors as part of the world context, then run:

- quality review;
- continuity review;
- world-model analysis;
- proposal resolution;
- subagent reader/continuity review.

If Chapter 14 generation still confuses `N-017 / N-07 / N-00` or the fog-disaster dates, the next fix should be prompt/context injection of the confirmed truth anchors, not another post-hoc repair only.
