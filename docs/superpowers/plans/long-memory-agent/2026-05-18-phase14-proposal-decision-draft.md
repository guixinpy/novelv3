# Phase 14 World Proposal Decision Draft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a report-only Writing Agent tool that drafts explicit low-risk non-merge world proposal decisions so the Agent can reduce queue friction without silently applying changes.

**Architecture:** Build a deterministic drafting core that reads the current actionable proposal queue, classifies items by predicate policy, and emits explicit `reject` or `mark_uncertain` decisions with reasons and evidence refs. The tool is report-only and feeds Phase13 `apply_world_model_proposal_resolution` for explicit confirmed application.

**Tech Stack:** FastAPI service layer, SQLAlchemy models, existing world proposal state constants, existing Writing Agent run service, pytest.

---

## Phase Metadata

- **Phase:** 14
- **Date:** 2026-05-18
- **Verification Tier:** T1 for targeted Agent/world proposal tests; T2 for runtime dogfood draft/apply on `《雾港回声》`.
- **Primary Output:** Agent tool `draft_world_model_proposal_resolution_decisions`.
- **Dogfood Output:** Draft non-merge decisions for the remaining current dogfood proposal queue, then use Phase13 apply to confirm a low-risk batch.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Success Criteria

- Agent supports `draft_world_model_proposal_resolution_decisions`.
- The tool accepts params:
  - `limit`: max actionable items to inspect, default 50;
  - `predicate_policies`: optional dict overriding built-in predicate policies;
  - `include_unclassified`: boolean, default false.
- Built-in policy drafts:
  - `presence_count` -> `reject`;
  - `mentioned_in_chapter` -> `reject`;
  - `present_at_location` -> `mark_uncertain`;
  - `event_summary` -> `mark_uncertain`.
- The tool returns:
  - `status`;
  - `project_id`;
  - `profile_version`;
  - `inspected_item_count`;
  - `draft_decision_count`;
  - `unclassified_item_count`;
  - `draft_decisions`;
  - `unclassified_items`;
  - `requires_confirmation`;
  - `can_auto_apply`;
  - `should_generate_next_chapter`;
  - `recommended_next_tools`.
- The tool is report-only:
  - does not create `WorldProposalReview`;
  - does not change `WorldProposalItem.item_status`;
  - does not create `WorldFactClaim`.
- `draft_world_model_proposal_resolution_decisions -> apply_world_model_proposal_resolution` can run in one Agent run.
- `draft_world_model_proposal_resolution_decisions -> generate_chapter` remains blocked.

## Predicate Policy Rationale

- `presence_count`: diagnostic extraction metadata, not durable world truth. Draft `reject`.
- `mentioned_in_chapter`: textual mention metadata, not world truth. Draft `reject`.
- `present_at_location`: location inference may be useful but should not become truth without review. Draft `mark_uncertain`.
- `event_summary`: useful narrative compression but must be curated before truth-layer merge. Draft `mark_uncertain`.

## Explicit Non-Goals

- Do not apply decisions in the drafting tool.
- Do not draft `approve` or `approve_with_edits`.
- Do not call LLMs.
- Do not build frontend UI.
- Do not generate Chapter 4 unless the real proposal queue is clear after a separate confirmed apply.

## Files

- Create: `backend/app/core/world_proposal_resolution_draft.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase14-proposal-decision-draft.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase14-proposal-decision-draft.md`

## Task 1: Add Draft Core

**Files:**

- Create: `backend/app/core/world_proposal_resolution_draft.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing report-only draft test**

Add `test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes`:

```python
def test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes(client, db_session):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1])
    import_setup_to_world_model(db_session, project.id)
    presence_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.presence",
        predicate="presence_count",
        subject_ref="char.林深",
    )
    location_item = _seed_pending_world_proposal(
        db_session,
        project_id=project.id,
        claim_id="claim.phase14.agent.location",
        predicate="present_at_location",
        subject_ref="char.苏晚晴",
    )
    before_review_count = db_session.query(WorldProposalReview).count()
    before_fact_count = db_session.query(WorldFactClaim).count()

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "草拟低风险世界模型提案决策",
            "tools": [{"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 20}}],
        },
    )

    output = response.json()["steps"][0]["output"]
    stored_presence = db_session.query(WorldProposalItem).filter_by(id=presence_item.id).one()
    stored_location = db_session.query(WorldProposalItem).filter_by(id=location_item.id).one()
    actions = {decision["proposal_item_id"]: decision["action"] for decision in output["draft_decisions"]}
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert output["status"] == "blocked"
    assert output["report_only"] is True
    assert output["draft_decision_count"] == 2
    assert actions[presence_item.id] == "reject"
    assert actions[location_item.id] == "mark_uncertain"
    assert output["requires_confirmation"] is True
    assert output["can_auto_apply"] is False
    assert output["should_generate_next_chapter"] is False
    assert stored_presence.item_status == "pending"
    assert stored_location.item_status == "pending"
    assert db_session.query(WorldProposalReview).count() == before_review_count
    assert db_session.query(WorldFactClaim).count() == before_fact_count
```

- [ ] **Step 2: Run test to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes -q
```

Expected: fail because the tool is not supported.

- [ ] **Step 3: Implement draft core**

Create:

```python
def draft_world_model_proposal_resolution_decisions(
    db: Session,
    project_id: str,
    *,
    limit: int = 50,
    predicate_policies: dict[str, Any] | None = None,
    include_unclassified: bool = False,
) -> dict[str, Any]:
    ...
```

Implementation rules:

- Query current profile and actionable proposal items only.
- Clamp `limit` between 1 and 200.
- Built-in policy maps predicate to `action`, `reason`, and `confidence`.
- A custom policy may override only to `reject` or `mark_uncertain`.
- Draft decisions include `proposal_item_id`, `action`, `reason`, `evidence_refs`, `policy_id`, and `predicate`.
- Do not write to the database.

- [ ] **Step 4: Run report-only test to verify GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes -q
```

Expected: pass.

## Task 2: Validation and Chaining

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing validation/chaining tests**

Add tests:

- `test_agent_draft_world_model_proposal_resolution_decisions_tracks_unclassified_items`
- `test_agent_draft_world_model_proposal_resolution_decisions_allows_apply_followup`
- `test_agent_draft_world_model_proposal_resolution_decisions_blocks_followup_generation`

Expected unclassified assertions:

```python
assert output["draft_decision_count"] == 0
assert output["unclassified_item_count"] == 1
assert output["unclassified_items"][0]["predicate"] == "custom_truth"
assert output["recommended_next_tools"] == ["plan_world_model_proposal_resolution"]
```

Expected chain assertions:

```python
assert [step["tool_name"] for step in payload["steps"]] == [
    "draft_world_model_proposal_resolution_decisions",
    "apply_world_model_proposal_resolution",
]
assert payload["steps"][1]["output"]["applied_count"] == 1
```

Expected generation block:

```python
assert payload["status"] == "blocked"
assert len(payload["steps"]) == 1
assert calls == []
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_tracks_unclassified_items tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_allows_apply_followup tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_blocks_followup_generation -q
```

Expected: fail until tool is wired and follow-up rules are updated.

- [ ] **Step 3: Wire Writing Agent tool**

Add `draft_world_model_proposal_resolution_decisions` to:

- `ALLOWED_TOOLS`;
- `INTERNAL_TOOLS`;
- `NON_BLOCKING_REPORT_TOOLS`;
- `_execute_tool`;
- `_target_type_for_tool`;
- `_should_stop_after_report`;
- `_successful_report_block_message`;
- `_allowed_report_followup` for `draft_world_model_proposal_resolution_decisions -> apply_world_model_proposal_resolution`.

- [ ] **Step 4: Run Phase14 targeted suite**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_reports_without_writes tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_tracks_unclassified_items tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_allows_apply_followup tests\test_writing_agent_runs.py::test_agent_draft_world_model_proposal_resolution_decisions_blocks_followup_generation -q
```

Expected: pass.

## Task 3: Runtime Dogfood Draft/Apply

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase14-proposal-decision-draft.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase14-proposal-decision-draft.md`

- [ ] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no committed secrets.

- [ ] **Step 2: Dogfood draft current queue**

Use Agent run against project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`:

```json
{
  "goal": "草拟《雾港回声》剩余世界模型提案的低风险非合并决策。",
  "tools": [{
    "tool_name": "draft_world_model_proposal_resolution_decisions",
    "params": {"limit": 50, "include_unclassified": true}
  }]
}
```

Expected:

- run status `success`;
- draft decision count matches classifiable items;
- no proposal status changes;
- no review/fact rows are created.

- [ ] **Step 3: Dogfood confirm/apply drafted decisions**

If the draft contains only `reject` and `mark_uncertain`, use `apply_world_model_proposal_resolution` with `confirm_apply=true` and the drafted decisions.

Expected:

- actionable queue decreases by applied count;
- no `WorldFactClaim` is created;
- if queue clears, `should_generate_next_chapter=true`, but do not generate Chapter 4 in this phase unless explicitly planned after report review.

- [ ] **Step 4: Record phase report and next recommendation**

The report must include:

- dogfood novel progress;
- queue counts before draft, after draft, and after apply;
- drafted action distribution;
- applied review IDs;
- whether Chapter 4 remains blocked;
- verification evidence;
- next phase recommendation.

## Phase Report

To be filled after execution.
