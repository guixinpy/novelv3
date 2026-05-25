# Phase 12 World Proposal Resolution Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-destructive Writing Agent tool that validates explicit proposal review decisions and previews their impact before any real approval/rejection is allowed.

**Architecture:** Build a preview-only core that reads actionable proposal items, validates user/Agent-supplied decisions, and estimates resulting review/fact changes without calling `review_proposal_item`, `split_bundle`, or `rollback_review`. Wire it as an Agent report tool that can follow the Phase 11 resolution plan but still blocks chapter generation until actual proposal state changes happen in a later guarded phase.

**Tech Stack:** FastAPI service layer, SQLAlchemy models, existing Writing Agent run service, proposal state constants, pytest.

---

## Phase Metadata

- **Phase:** 12
- **Date:** 2026-05-18
- **Verification Tier:** T1 for targeted Agent tests; T2 for runtime dogfood preview on `《雾港回声》`.
- **Primary Output:** Agent tool `preview_world_model_proposal_resolution`.
- **Dogfood Output:** Preview a small explicit decision set for the current dogfood proposal queue without mutating the queue.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Success Criteria

- Agent supports `preview_world_model_proposal_resolution`.
- The tool accepts params:
  - `decisions`: list of explicit proposal decisions;
  - each decision has `proposal_item_id`, `action`, `reason`, optional `evidence_refs`, optional `edited_fields`.
- The tool returns:
  - `status`;
  - `project_id`;
  - `total_actionable_items`;
  - `valid_decision_count`;
  - `invalid_decision_count`;
  - `would_create_review_count`;
  - `would_create_fact_count`;
  - `would_resolve_item_count`;
  - `remaining_actionable_item_count_after_preview`;
  - `would_unblock_generation`;
  - `should_generate_next_chapter`;
  - `valid_decisions`;
  - `invalid_decisions`;
  - `preview_only`;
  - `requires_confirmation`;
  - `can_auto_apply`.
- `approve` and `approve_with_edits` preview as fact-creating decisions.
- `reject` and `mark_uncertain` preview as review-only decisions.
- Invalid item IDs, unsupported actions, duplicate decisions, and non-actionable item statuses are reported without raising a 500.
- The tool is preview-only:
  - does not change `WorldProposalItem.item_status`;
  - does not create `WorldProposalReview`;
  - does not create `WorldFactClaim`;
  - does not call approval/rejection/split/rollback services.
- `plan_world_model_proposal_resolution -> preview_world_model_proposal_resolution` can run in the same Agent run.
- `preview_world_model_proposal_resolution -> generate_chapter` remains blocked while the real queue is still pending.

## Explicit Non-Goals

- Do not apply any proposal review decisions.
- Do not auto-approve low-risk proposals.
- Do not split bundles.
- Do not roll back reviews.
- Do not build frontend UI.
- Do not generate Chapter 4.

## Files

- Create: `backend/app/core/world_proposal_resolution_preview.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase12-world-proposal-resolution-preview.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase12-world-proposal-resolution-preview.md`

## Task 1: Add Preview Core

**Files:**

- Create: `backend/app/core/world_proposal_resolution_preview.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing non-destructive preview test**

Seed one proposal to approve and one proposal to reject, then call `preview_world_model_proposal_resolution` through the Agent API. Expected assertions:

```python
assert output["status"] == "blocked"
assert output["preview_only"] is True
assert output["requires_confirmation"] is True
assert output["can_auto_apply"] is False
assert output["valid_decision_count"] == 2
assert output["invalid_decision_count"] == 0
assert output["would_create_review_count"] == 2
assert output["would_create_fact_count"] == 1
assert output["would_resolve_item_count"] == 2
assert output["remaining_actionable_item_count_after_preview"] == 0
assert output["would_unblock_generation"] is True
assert output["should_generate_next_chapter"] is False
assert stored_approve_item.item_status == "pending"
assert stored_reject_item.item_status == "pending"
assert db_session.query(WorldProposalReview).count() == before_review_count
assert db_session.query(WorldFactClaim).count() == before_fact_count
```

- [x] **Step 2: Run test to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_validates_decisions_without_writes -q
```

Expected: fail because the tool is not yet supported.

- [x] **Step 3: Implement preview core**

Create:

```python
def preview_world_model_proposal_resolution(db: Session, project_id: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    ...
```

Rules:

- Query only `WorldProposalItem` and count actionable items.
- Use proposal state constants for allowed actions and actionable statuses.
- Do not import `review_proposal_item`, `split_bundle`, or `rollback_review`.
- Return normalized valid and invalid decision lists.
- Set `would_unblock_generation=true` only when every current actionable item is covered by valid decisions.
- Set `should_generate_next_chapter=false` whenever preview decisions exist because the DB is not actually changed.

- [x] **Step 4: Run targeted test to verify GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_validates_decisions_without_writes -q
```

Expected: pass.

## Task 2: Wire Agent Tool and Validation Cases

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing wiring and invalid-decision tests**

Add tests for:

- unsupported action and missing item produce `invalid_decisions`;
- duplicate decisions are invalid after the first occurrence;
- `plan_world_model_proposal_resolution -> preview_world_model_proposal_resolution` can run in the same Agent run;
- `preview_world_model_proposal_resolution -> generate_chapter` blocks follow-up generation while real proposals remain pending.

- [x] **Step 2: Run tests to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_reports_invalid_decisions tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_allows_preview_followup tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_blocks_followup_generation -q
```

Expected: fail because the Agent tool is not yet wired.

- [x] **Step 3: Add tool wiring**

Add `preview_world_model_proposal_resolution` to:

- `ALLOWED_TOOLS`;
- `INTERNAL_TOOLS`;
- `NON_BLOCKING_REPORT_TOOLS`;
- `_execute_tool`;
- `_target_type_for_tool`;
- `_should_stop_after_report`;
- `_successful_report_block_message`;
- `_allowed_report_followup` for `plan_world_model_proposal_resolution -> preview_world_model_proposal_resolution`.

- [x] **Step 4: Run targeted Agent tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_validates_decisions_without_writes tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_reports_invalid_decisions tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_allows_preview_followup tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_blocks_followup_generation -q
```

Expected: pass.

## Task 3: Runtime Dogfood Preview

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase12-world-proposal-resolution-preview.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase12-world-proposal-resolution-preview.md`

- [x] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no committed secrets.

- [x] **Step 2: Run dogfood preview**

Use Agent run against project `25fa2b20-5b9f-473b-918b-f4ea491cbb60` with two explicit decisions from the current queue:

```json
{
  "goal": "预览《雾港回声》两个世界模型提案的解决影响，不落库执行。",
  "tools": [{
    "tool_name": "preview_world_model_proposal_resolution",
    "params": {
      "decisions": [
        {"proposal_item_id": "<id>", "action": "reject", "reason": "预览测试，不执行", "evidence_refs": ["phase12:preview"]},
        {"proposal_item_id": "<id>", "action": "mark_uncertain", "reason": "预览测试，不执行", "evidence_refs": ["phase12:preview"]}
      ]
    }
  }]
}
```

Expected:

- run status `success`;
- output status `blocked`;
- valid decisions reported;
- no proposal item is approved/rejected;
- no `WorldProposalReview` or `WorldFactClaim` is created by this tool.

- [x] **Step 3: Record report and next phase recommendation**

The phase report must include:

- dogfood novel progress;
- previewed decision count and impact;
- confirmation that proposal statuses were unchanged;
- verification evidence;
- next phase recommendation.

## Phase Report

### Implementation

- Added `backend/app/core/world_proposal_resolution_preview.py` as a preview-only proposal resolution evaluator.
- Wired `preview_world_model_proposal_resolution` into the Writing Agent internal/report tool path.
- Added Agent tests for non-destructive preview, missing-profile decision validation, invalid decisions, non-actionable items, empty-queue decision blocking, world-intake atomization validation, allowed plan-to-preview chaining, and preview-to-generation blocking.

### Runtime Dogfood

- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60` (`雾港回声`).
- Novel progress remains 3 generated chapters. Chapter 4 was intentionally not generated.
- Proposal queue before preview: 24 actionable items, 0 proposal reviews, 0 world fact claims.
- Preview run `0f918c11-1da9-4e0c-8096-2067cb96ae8a`:
  - run status: `success`;
  - tool output status: `blocked`;
  - valid decisions: 2;
  - invalid decisions: 0;
  - would create reviews: 2;
  - would create facts: 0;
  - would resolve items: 2;
  - remaining actionable items after preview: 22;
  - would unblock generation: `false`;
  - should generate next chapter: `false`.
- Counts after preview were unchanged: 24 actionable items, 0 proposal reviews, 0 world fact claims. Selected proposal item statuses stayed `pending`.
- Chain smoke run `1522e21a-5943-4ca3-a24c-ee3b15182f6e` confirmed `plan_world_model_proposal_resolution -> preview_world_model_proposal_resolution` can execute in one Agent run without mutating proposal state.

### Verification Evidence

- Regression red checks were run for:
  - empty-queue preview decisions incorrectly allowing generation;
  - non-atomized world-intake approval being accepted.
- Targeted Phase12 suite: `8 passed in 0.65s`.
- Full Writing Agent suite: `46 passed in 3.10s`.
- Related T1 suite: `116 passed in 7.35s`.
- Independent review found no Critical issues. Important issues were fixed:
  - missing-profile preview now handles non-dict decisions without 500;
  - non-actionable item validation has regression coverage.
  - string `evidence_refs` is normalized as a single reference instead of being split into characters.
- Final verification is recorded in the phase note.

### Next Phase Recommendation

Add a guarded apply tool for explicit confirmed proposal decisions. Start with narrow, low-risk actions (`reject`, `mark_uncertain`) or a single confirmed batch, keep generation blocked until the real queue is reduced or deferred, and record before/after counts for every applied run.
