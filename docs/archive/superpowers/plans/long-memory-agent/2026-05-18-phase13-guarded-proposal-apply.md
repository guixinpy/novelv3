# Phase 13 Guarded World Proposal Apply Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a guarded Writing Agent tool that applies explicit confirmed non-merge world-model proposal decisions so the dogfood novel can safely reduce the pending proposal queue.

**Architecture:** Build a narrow apply core on top of Phase 12 preview validation. The first apply surface supports only `reject` and `mark_uncertain`, requires an explicit confirmation flag, refuses approvals, and returns before/after queue counts so generation stays blocked until the real queue is actually clear.

**Tech Stack:** FastAPI service layer, SQLAlchemy models, existing world proposal review service, existing Writing Agent run service, pytest.

---

## Phase Metadata

- **Phase:** 13
- **Date:** 2026-05-18
- **Verification Tier:** T1 for targeted Agent/world proposal tests; T2 for runtime dogfood apply on `《雾港回声》`.
- **Primary Output:** Agent tool `apply_world_model_proposal_resolution`.
- **Dogfood Output:** Apply a very small explicit non-merge decision set to the current dogfood proposal queue.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Success Criteria

- Agent supports `apply_world_model_proposal_resolution`.
- The tool accepts params:
  - `confirm_apply`: boolean, must be `true` to mutate data;
  - `decisions`: list of explicit decisions;
  - each decision has `proposal_item_id`, `action`, `reason`, optional `evidence_refs`.
- The tool only applies `reject` and `mark_uncertain` in this phase.
- `approve` and `approve_with_edits` are rejected as invalid for guarded apply.
- Missing confirmation returns a blocked result and writes nothing.
- Any invalid decision blocks the whole batch and writes nothing.
- Successful non-merge apply:
  - creates one `WorldProposalReview` per applied decision;
  - changes each target `WorldProposalItem.item_status` to `rejected` or `uncertain`;
  - creates no `WorldFactClaim`;
  - returns applied review IDs and before/after queue counts.
- `preview_world_model_proposal_resolution -> apply_world_model_proposal_resolution` can run in one Agent run.
- `apply_world_model_proposal_resolution -> generate_chapter` remains blocked when real pending proposals remain.
- `apply_world_model_proposal_resolution -> generate_chapter` is allowed only when the real proposal queue is clear.

## Explicit Non-Goals

- Do not approve facts.
- Do not support `approve_with_edits`.
- Do not split bundles.
- Do not roll back reviews.
- Do not build frontend UI.
- Do not generate Chapter 4 unless the real proposal queue is clear after apply.

## Files

- Create: `backend/app/core/world_proposal_resolution_apply.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase13-guarded-proposal-apply.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase13-guarded-proposal-apply.md`

## Task 1: Add Guarded Apply Core

**Files:**

- Create: `backend/app/core/world_proposal_resolution_apply.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing missing-confirmation test**

Add `test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes`:

```python
def test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase13.agent.needs-confirm",
        predicate="role",
        subject_ref="char.林深",
    )
    before_review_count = db_session.query(WorldProposalReview).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "尝试未确认地应用世界模型提案决策",
            "tools": [
                {
                    "tool_name": "apply_world_model_proposal_resolution",
                    "params": {
                        "decisions": [
                            {
                                "proposal_item_id": item.id,
                                "action": "reject",
                                "reason": "未确认，不应落库",
                            }
                        ]
                    },
                }
            ],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_item = db_session.query(WorldProposalItem).filter_by(id=item.id).one()
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["requires_confirmation"] is True
    assert output["applied_count"] == 0
    assert output["invalid_decision_count"] == 0
    assert output["should_generate_next_chapter"] is False
    assert stored_item.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
```

- [x] **Step 2: Run test to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes -q
```

Expected: fail because the tool is not supported.

- [x] **Step 3: Implement minimal apply core**

Create:

```python
def apply_world_model_proposal_resolution(
    db: Session,
    project_id: str,
    decisions: list[dict[str, Any]],
    *,
    confirm_apply: bool,
) -> dict[str, Any]:
    ...
```

Implementation rules:

- Call `preview_world_model_proposal_resolution` first.
- If preview has invalid decisions, return blocked with `applied_count=0`.
- Convert any valid `approve` or `approve_with_edits` decision into invalid code `approval_not_supported_in_guarded_apply`.
- If `confirm_apply` is not true, return blocked with `applied_count=0`.
- Only after the above gates call `review_proposal_item` for `reject` and `mark_uncertain`.
- Use reviewer ref `writing_agent.phase13`.
- Count actionable proposal items before and after apply.
- Return `should_generate_next_chapter=true` only when the after count is zero.

- [x] **Step 4: Run missing-confirmation test to verify GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes -q
```

Expected: pass.

## Task 2: Add Validation and Apply Behavior

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`
- Modify: `backend/app/core/world_proposal_resolution_apply.py`

- [x] **Step 1: Write failing apply behavior tests**

Add tests:

- `test_agent_apply_world_model_proposal_resolution_applies_confirmed_non_merge_decisions`
- `test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes`
- `test_agent_apply_world_model_proposal_resolution_blocks_invalid_batch_without_partial_writes`

Expected confirmed non-merge assertions:

```python
assert output["status"] == "ready"
assert output["applied_count"] == 2
assert output["after_actionable_items"] == 0
assert output["should_generate_next_chapter"] is True
assert db_session.query(WorldFactClaim).count() == before_fact_count
assert stored_reject_item.item_status == "rejected"
assert stored_uncertain_item.item_status == "uncertain"
assert {review.review_action for review in reviews} == {"reject", "mark_uncertain"}
```

Expected invalid batch assertions:

```python
assert output["status"] == "blocked"
assert output["applied_count"] == 0
assert output["invalid_decision_count"] >= 1
assert stored_valid_item.item_status == "pending"
assert db_session.query(WorldProposalReview).count() == before_review_count
```

- [x] **Step 2: Run tests to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_applies_confirmed_non_merge_decisions tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_invalid_batch_without_partial_writes -q
```

Expected: fail until validation and apply behavior are complete.

- [x] **Step 3: Complete apply behavior**

Update the core so it returns:

- `status`;
- `project_id`;
- `profile_version`;
- `before_actionable_items`;
- `after_actionable_items`;
- `applied_count`;
- `applied_reviews`;
- `invalid_decision_count`;
- `invalid_decisions`;
- `requires_confirmation`;
- `can_auto_apply`;
- `should_generate_next_chapter`;
- `recommended_actions`.

- [x] **Step 4: Run apply behavior tests to verify GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_applies_confirmed_non_merge_decisions tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_invalid_batch_without_partial_writes -q
```

Expected: pass.

## Task 3: Wire Writing Agent Tool and Follow-Up Blocking

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing Agent chaining tests**

Add tests:

- `test_agent_preview_world_model_proposal_resolution_allows_apply_followup`
- `test_agent_apply_world_model_proposal_resolution_blocks_followup_generation_when_queue_remains`
- `test_agent_apply_world_model_proposal_resolution_allows_generation_when_queue_clears`

Expected chain:

```python
assert [step["tool_name"] for step in payload["steps"]] == [
    "preview_world_model_proposal_resolution",
    "apply_world_model_proposal_resolution",
]
```

Expected blocked generation:

```python
assert payload["status"] == "blocked"
assert len(payload["steps"]) == 1
assert calls == []
```

Expected allowed generation:

```python
assert payload["status"] == "success"
assert [step["tool_name"] for step in payload["steps"]] == [
    "apply_world_model_proposal_resolution",
    "generate_chapter",
]
assert calls == ["generate_chapter"]
```

- [x] **Step 2: Run chaining tests to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_allows_apply_followup tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_followup_generation_when_queue_remains tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_allows_generation_when_queue_clears -q
```

Expected: fail until the Agent tool is wired.

- [x] **Step 3: Wire the tool**

Add `apply_world_model_proposal_resolution` to:

- `ALLOWED_TOOLS`;
- `INTERNAL_TOOLS`;
- `NON_BLOCKING_REPORT_TOOLS`;
- `_execute_tool`;
- `_target_type_for_tool`;
- `_should_stop_after_report`;
- `_successful_report_block_message`;
- `_allowed_report_followup` for `preview_world_model_proposal_resolution -> apply_world_model_proposal_resolution`.

- [x] **Step 4: Run full Phase13 targeted suite**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_requires_confirmation_without_writes tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_applies_confirmed_non_merge_decisions tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_rejects_approval_actions_without_writes tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_invalid_batch_without_partial_writes tests\test_writing_agent_runs.py::test_agent_preview_world_model_proposal_resolution_allows_apply_followup tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_blocks_followup_generation_when_queue_remains tests\test_writing_agent_runs.py::test_agent_apply_world_model_proposal_resolution_allows_generation_when_queue_clears -q
```

Expected: pass.

## Task 4: Runtime Dogfood Apply and Report

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase13-guarded-proposal-apply.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase13-guarded-proposal-apply.md`

- [x] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no committed secrets.

- [x] **Step 2: Run dogfood guarded apply**

Use dogfood project `25fa2b20-5b9f-473b-918b-f4ea491cbb60` and apply two explicit non-merge decisions only if their current statuses are still `pending`:

```json
{
  "goal": "应用《雾港回声》两个已预览的世界模型非合并提案决策。",
  "tools": [{
    "tool_name": "apply_world_model_proposal_resolution",
    "params": {
      "confirm_apply": true,
      "decisions": [
        {"proposal_item_id": "b642eaa2-553a-4dff-a77b-1f6f0e89fca4", "action": "reject", "reason": "Phase13 guarded apply：事件摘要暂不进入世界真相。", "evidence_refs": ["phase13:guarded-apply"]},
        {"proposal_item_id": "9a5a799c-d0df-4616-97cd-798bd3f1425f", "action": "mark_uncertain", "reason": "Phase13 guarded apply：第2章事件摘要保留为待确认。", "evidence_refs": ["phase13:guarded-apply"]}
      ]
    }
  }]
}
```

Expected:

- run status `success`;
- tool output status `blocked` if other proposals remain;
- applied count is 2;
- pending queue decreases from 24 to 22 if no intervening changes occurred;
- two `WorldProposalReview` rows are created;
- no `WorldFactClaim` is created;
- Chapter 4 is not generated.

- [x] **Step 3: Record phase report and next recommendation**

The report must include:

- dogfood novel progress;
- applied decision IDs and review IDs;
- before/after proposal/review/fact counts;
- whether generation remains blocked;
- verification evidence;
- next phase recommendation.

## Phase Report

### Implementation

- Added `backend/app/core/world_proposal_resolution_apply.py`.
- Wired `apply_world_model_proposal_resolution` into the Writing Agent internal/report tool path.
- Extended `review_proposal_item` with `commit=True` default so existing callers keep behavior, while Phase13 apply can use `commit=False` and commit the batch atomically.
- Added Agent tests for confirmation gating, missing profile, confirmed non-merge apply, approval refusal, batch rollback, invalid batch blocking, preview-to-apply chaining, and apply-to-generation gating.

### Review Feedback Resolved

- Independent review found that calling `review_proposal_item` one decision at a time would commit each item and could partially apply a batch if a later item failed during review.
- Fixed by using `review_proposal_item(..., commit=False)` inside `apply_world_model_proposal_resolution`, then one final `db.commit()`.
- Added regression coverage where preview decisions are valid, but the second item fails during review due to contract drift. The first item remains `pending`, the second remains `pending`, and no review row is created.
- Added direct `approve_with_edits` rejection coverage.

### Runtime Dogfood

- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60` (`雾港回声`).
- Novel progress remains 3 generated chapters. Chapter 4 was intentionally not generated.
- Apply run: `03330a03-1c45-4d4d-9bf2-73ee2a9bdea6`.
- Before apply:
  - actionable proposal items: 24;
  - proposal reviews: 0;
  - world fact claims: 0;
  - selected statuses: `pending`, `pending`.
- Applied decisions:
  - `b642eaa2-553a-4dff-a77b-1f6f0e89fca4`: `reject`, review `f6db0b3d-d38c-40f9-98c7-48acc20413ae`;
  - `9a5a799c-d0df-4616-97cd-798bd3f1425f`: `mark_uncertain`, review `fcf2cf2b-03b3-47f2-9bdb-3db8d624fff6`.
- After apply:
  - actionable proposal items: 22;
  - proposal reviews: 2;
  - world fact claims: 0;
  - selected statuses: `rejected`, `uncertain`.
- Tool output status remained `blocked`, with `should_generate_next_chapter=false`, because 22 actionable proposal items remain.

### Verification Evidence

- Missing confirmation RED: tool unsupported before implementation.
- Missing profile empty decision RED: apply initially returned `ready`; fixed to `missing_profile` with `should_generate_next_chapter=false`.
- Phase13 targeted suite: `9 passed in 0.80s`.
- Writing Agent suite: `55 passed in 3.70s`.
- Independent re-review targeted suite: `4 passed in 0.43s`.
- Final verification is recorded in the phase note.

### Next Phase Recommendation

Continue resolving the dogfood proposal queue before generating Chapter 4. Next phase should either:

- apply additional explicit `reject` / `mark_uncertain` decisions in small batches; or
- add an Agent-assisted decision drafting tool that proposes safe non-merge decisions for low-risk/noisy proposal types while still requiring confirmation.
