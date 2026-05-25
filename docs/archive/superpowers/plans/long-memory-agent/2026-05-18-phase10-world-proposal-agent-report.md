# Phase 10 World Proposal Agent Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a report-only Writing Agent tool for world-model proposal queue triage.

**Architecture:** Reuse the existing Athena/world-model proposal review queue builder. The Agent tool summarizes queue pressure, risk levels, review modes, and recommended next actions without approving, rejecting, splitting, rolling back, or materializing facts.

**Tech Stack:** FastAPI service layer, SQLAlchemy models, existing Writing Agent run service, existing world proposal review queue, pytest.

---

## Phase Metadata

- **Phase:** 10
- **Date:** 2026-05-18
- **Verification Tier:** T1 for targeted Agent tests; T2 for runtime dogfood queue report on `《雾港回声》`.
- **Primary Output:** Agent tool `review_world_model_proposals`.
- **Dogfood Output:** Produce a non-destructive world-model proposal queue report for the current dogfood project.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Success Criteria

- Agent supports `review_world_model_proposals`.
- The tool returns:
  - `status`;
  - `project_id`;
  - `profile_version`;
  - `total_items`;
  - `returned_items`;
  - `risk_counts`;
  - `review_mode_counts`;
  - `clusters`;
  - `recommended_actions`;
  - `should_generate_next_chapter`.
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
- Do not solve proposal semantics yet; this phase only exposes queue pressure to the Agent.

## Files

- Create: `backend/app/core/world_proposal_agent_report.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase10-world-proposal-agent-report.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase10-world-proposal-agent-report.md`

## Task 1: Add Report Core

**Files:**

- Create: `backend/app/core/world_proposal_agent_report.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing report-only test**

Seed a current profile and pending proposal item, then call `review_world_model_proposals`. Expected:

```python
assert output["status"] == "blocked"
assert output["total_items"] == 1
assert output["risk_counts"]["high"] == 1
assert output["review_mode_counts"]["individual"] == 1
assert output["should_generate_next_chapter"] is False
assert stored_item.item_status == "pending"
assert db_session.query(WorldProposalReview).count() == 0
assert db_session.query(WorldFactClaim).count() == 0
```

- [x] **Step 2: Implement report core**

Create:

```python
def build_world_proposal_agent_report(db: Session, project_id: str, offset: int = 0, limit: int = 50) -> dict[str, Any]:
    ...
```

Rules:

- Use current `ProjectProfileVersion`.
- Use `build_proposal_review_queue`.
- Summarize risk counts and review mode counts from returned clusters.
- Return top clusters with bounded `item_ids`.
- Do not mutate proposal tables.

- [x] **Step 3: Run targeted test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_reports_queue_without_reviewing_items -q
```

Expected after implementation: pass.

## Task 2: Wire Agent Tool and Gate

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing Agent wiring tests**

Add tests for:

- empty queue returns `ready` and `should_generate_next_chapter=true`;
- pending queue sets target type `world_model`;
- `review_world_model_proposals -> generate_chapter` blocks follow-up generation when pending proposals exist.

- [x] **Step 2: Add tool wiring**

Add `review_world_model_proposals` to:

- `ALLOWED_TOOLS`;
- `INTERNAL_TOOLS`;
- `_execute_tool`;
- `_target_type_for_tool`;
- follow-up generation gate.

- [x] **Step 3: Run targeted Agent tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_reports_queue_without_reviewing_items tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_ready_when_queue_empty tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_blocks_followup_generation -q
```

Expected: pass.

## Task 3: Runtime Dogfood Queue Report

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase10-world-proposal-agent-report.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase10-world-proposal-agent-report.md`

- [x] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no committed secrets.

- [x] **Step 2: Run dogfood queue report**

Use Agent run against project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`:

```json
{
  "goal": "汇总《雾港回声》当前世界模型待审提案队列。",
  "tools": [{"tool_name": "review_world_model_proposals", "params": {"limit": 20}}]
}
```

Expected:

- run status `success`;
- output status `blocked` if queue still has pending proposals;
- no proposal item is approved/rejected;
- no `WorldProposalReview` or `WorldFactClaim` is created by this tool.

- [x] **Step 3: Record report and next phase recommendation**

The phase report must include:

- dogfood novel progress;
- proposal total and risk counts;
- confirmation that proposal statuses were unchanged;
- verification evidence;
- next phase recommendation.

## Phase Report

Completed on 2026-05-18.

Implemented:

- Added `backend/app/core/world_proposal_agent_report.py`.
- Added Writing Agent tool `review_world_model_proposals`.
- Added chained generation gate so pending proposals stop later writing tools in the same run.
- Added targeted tests for report-only behavior, empty-queue readiness, target type, and follow-up generation blocking.
- Added runtime note: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase10-world-proposal-agent-report.md`.

TDD evidence:

- Initial targeted run:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_reports_queue_without_reviewing_items tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_ready_when_queue_empty tests\test_writing_agent_runs.py::test_agent_review_world_model_proposals_blocks_followup_generation -q`.
  - Result: `3 failed`.
- Targeted green:
  - Same command.
  - Result: `3 passed`.

Verification evidence:

- `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q` -> `32 passed`.
- `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_outlines.py -q` -> `102 passed`.
- `git diff --check` -> exit code `0`.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references` -> no matches.

Dogfood evidence:

- Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Novel: `《雾港回声》`.
- Agent run: `f1477c3f-191f-4044-985f-159f39417025`.
- Run status: `success`.
- Output status: `blocked`.
- Proposal total: `24`.
- Returned items: `20`.
- Risk counts: high `3`, medium `0`, low `17`.
- Review modes: individual `3`, batch `17`.
- `should_generate_next_chapter`: `false`.
- Business counts unchanged before/after:
  - proposal items: `24 -> 24`;
  - pending proposal items: `24 -> 24`;
  - proposal reviews: `0 -> 0`;
  - fact claims: `0 -> 0`.

Next phase:

- Add Agent-assisted proposal resolution planning.
- Keep approval/rejection explicit and guarded.
- Use this report as the preflight gate before any future proposal mutation.
