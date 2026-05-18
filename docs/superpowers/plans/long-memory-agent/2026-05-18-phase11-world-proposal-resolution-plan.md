# Phase 11 World Proposal Resolution Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-destructive Writing Agent tool that turns the world-model proposal queue into an ordered resolution plan.

**Architecture:** Reuse the Phase 10 report core and existing proposal queue clustering. The new tool will classify pending proposal clusters into high-priority individual review steps and low-risk batch review steps, but it will not call approval, rejection, split, rollback, or fact materialization services.

**Tech Stack:** FastAPI service layer, SQLAlchemy models, existing Writing Agent run service, existing proposal queue/report core, pytest.

---

## Phase Metadata

- **Phase:** 11
- **Date:** 2026-05-18
- **Verification Tier:** T1 for targeted Agent tests; T2 for runtime dogfood resolution plan on `《雾港回声》`.
- **Primary Output:** Agent tool `plan_world_model_proposal_resolution`.
- **Dogfood Output:** Produce an ordered, non-destructive resolution plan for the current dogfood proposal queue.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Success Criteria

- Agent supports `plan_world_model_proposal_resolution`.
- The tool returns:
  - `status`;
  - `project_id`;
  - `profile_version`;
  - `total_items`;
  - `returned_items`;
  - `resolution_steps`;
  - `high_priority_step_count`;
  - `batch_step_count`;
  - `requires_human_confirmation`;
  - `can_auto_apply`;
  - `recommended_actions`;
  - `should_generate_next_chapter`.
- High-risk and medium-risk clusters become `review_individual` steps.
- Low-risk batch clusters become `review_batch` steps.
- Individual review steps are ordered before batch review steps.
- The tool is report-only:
  - does not change `WorldProposalItem.item_status`;
  - does not create `WorldProposalReview`;
  - does not create `WorldFactClaim`;
  - does not call approval/rejection/split/rollback services.
- If pending proposals exist, `should_generate_next_chapter=false`.
- If no pending proposals exist, `should_generate_next_chapter=true`.
- The tool can be chained before `generate_chapter`; pending proposals stop follow-up generation.

## Explicit Non-Goals

- Do not auto-approve or reject proposal items.
- Do not edit proposal fields.
- Do not split proposal bundles.
- Do not roll back proposal reviews.
- Do not build frontend UI.
- Do not infer semantic truth from prose in this phase.
- Do not generate Chapter 4 while the proposal queue is unresolved.

## Files

- Create: `backend/app/core/world_proposal_resolution_plan.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase11-world-proposal-resolution-plan.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase11-world-proposal-resolution-plan.md`

## Task 1: Add Resolution Plan Core

**Files:**

- Create: `backend/app/core/world_proposal_resolution_plan.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing non-destructive plan test**

Add a test that seeds one high-risk proposal and one low-risk proposal, then calls `plan_world_model_proposal_resolution` through the Agent API. Expected assertions:

```python
assert output["status"] == "blocked"
assert output["total_items"] == 2
assert output["high_priority_step_count"] == 1
assert output["batch_step_count"] == 1
assert output["requires_human_confirmation"] is True
assert output["can_auto_apply"] is False
assert output["should_generate_next_chapter"] is False
assert output["resolution_steps"][0]["action_type"] == "review_individual"
assert output["resolution_steps"][0]["risk_level"] == "high"
assert output["resolution_steps"][1]["action_type"] == "review_batch"
assert output["resolution_steps"][1]["risk_level"] == "low"
assert stored_high_item.item_status == "pending"
assert stored_low_item.item_status == "pending"
assert db_session.query(WorldProposalReview).count() == before_review_count
assert db_session.query(WorldFactClaim).count() == before_fact_count
```

- [ ] **Step 2: Run test to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_orders_review_steps_without_writes -q
```

Expected: fail because `plan_world_model_proposal_resolution` is not yet supported.

- [ ] **Step 3: Implement plan core**

Create:

```python
def build_world_proposal_resolution_plan(db: Session, project_id: str, offset: int = 0, limit: int = 50) -> dict[str, Any]:
    report = build_world_proposal_agent_report(db, project_id, offset=offset, limit=limit)
    clusters = report.get("clusters") if isinstance(report.get("clusters"), list) else []
    steps = _resolution_steps(clusters)
    return {
        "status": report["status"],
        "project_id": project_id,
        "profile_version": report.get("profile_version"),
        "total_items": report.get("total_items", 0),
        "returned_items": report.get("returned_items", 0),
        "resolution_steps": steps,
        "high_priority_step_count": sum(1 for step in steps if step["action_type"] == "review_individual"),
        "batch_step_count": sum(1 for step in steps if step["action_type"] == "review_batch"),
        "requires_human_confirmation": bool(steps),
        "can_auto_apply": False,
        "recommended_actions": _recommended_actions(report, steps),
        "should_generate_next_chapter": report.get("should_generate_next_chapter") is True,
        "report_only": True,
    }
```

Rules:

- Use `build_world_proposal_agent_report`.
- Do not import or call `review_proposal_item`, `split_bundle`, or `rollback_review`.
- Do not create reviews or facts.
- Sort individual steps before batch steps.
- Preserve enough `item_ids`, `bundle_ids`, `predicate`, `subject_refs`, and `chapter_range` for a human or future tool to act.

- [ ] **Step 4: Run targeted test to verify GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_orders_review_steps_without_writes -q
```

Expected: pass.

## Task 2: Wire Agent Tool and Gate

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Add failing Agent wiring tests**

Add tests for:

- empty queue returns `ready`, zero steps, and `should_generate_next_chapter=true`;
- `plan_world_model_proposal_resolution -> generate_chapter` blocks follow-up generation when pending proposals exist;
- step target type is `world_model`.

Expected assertion examples:

```python
assert output["status"] == "ready"
assert output["resolution_steps"] == []
assert output["recommended_actions"] == ["preflight_writing"]
assert output["should_generate_next_chapter"] is True
```

```python
assert payload["status"] == "blocked"
assert payload["steps"][0]["tool_name"] == "plan_world_model_proposal_resolution"
assert payload["steps"][0]["status"] == "success"
assert len(payload["steps"]) == 1
assert calls == []
```

- [ ] **Step 2: Run wiring tests to verify RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_ready_when_queue_empty tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_blocks_followup_generation -q
```

Expected: fail because the Agent tool is not yet wired.

- [ ] **Step 3: Add tool wiring**

Add `plan_world_model_proposal_resolution` to:

- `ALLOWED_TOOLS`;
- `INTERNAL_TOOLS`;
- `NON_BLOCKING_REPORT_TOOLS`;
- `_execute_tool`;
- `_target_type_for_tool`;
- `_should_stop_after_report`;
- `_successful_report_block_message`.

- [ ] **Step 4: Run targeted Agent tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_orders_review_steps_without_writes tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_ready_when_queue_empty tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_blocks_followup_generation -q
```

Expected: pass.

## Task 3: Runtime Dogfood Resolution Plan

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase11-world-proposal-resolution-plan.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase11-world-proposal-resolution-plan.md`

- [ ] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no committed secrets.

- [ ] **Step 2: Run dogfood resolution plan**

Use Agent run against project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`:

```json
{
  "goal": "为《雾港回声》当前世界模型待审提案生成解决计划。",
  "tools": [{"tool_name": "plan_world_model_proposal_resolution", "params": {"limit": 20}}]
}
```

Expected:

- run status `success`;
- output status `blocked` if queue still has pending proposals;
- high-risk steps appear before batch steps;
- no proposal item is approved/rejected;
- no `WorldProposalReview` or `WorldFactClaim` is created by this tool.

- [ ] **Step 3: Record report and next phase recommendation**

The phase report must include:

- dogfood novel progress;
- proposal total and resolution step counts;
- confirmation that proposal statuses were unchanged;
- verification evidence;
- next phase recommendation.

## Phase Report

To be filled after execution.
