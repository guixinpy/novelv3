# Longform Scale Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce world-model proposal review noise by exposing a risk-aware, cluster-based review queue without changing approval semantics.

**Architecture:** Keep `WorldProposalItem` and existing review APIs unchanged. Add a read-only queue builder that groups actionable proposal items by risk, predicate, subject/chapter scope, and recommended review mode.

**Tech Stack:** FastAPI, SQLAlchemy, existing world proposal models/services, pytest.

---

## File Structure

- Create `backend/app/core/world_proposal_review_queue.py`: classify pending proposal risk and build review clusters.
- Modify `backend/app/schemas/world_proposals.py`: add review queue response schemas.
- Modify `backend/app/schemas/__init__.py`: export new schemas.
- Modify `backend/app/api/world_model.py`: add `/proposal-review-queue`.
- Modify `backend/app/api/athena_evolution.py`: add Athena facade `/evolution/proposal-review-queue`.
- Modify `backend/tests/test_world_frontend_api.py`: add queue clustering test.

## Success Criteria

- Low-risk chapter-scoped presence candidates can be grouped into one batch-review cluster.
- High-risk state/identity/event candidates are surfaced before low-risk clusters and recommend individual review.
- Queue only includes current profile and actionable statuses.
- Queue is read-only and does not alter bundle/item status.
- Verification commands pass:
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py::test_world_model_proposal_review_queue_clusters_low_risk_and_prioritizes_high_risk -v`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py backend\tests\test_world_proposals.py -v`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v`

## Tasks

### Task 1: Review Queue Clustering

**Files:**
- Create: `backend/app/core/world_proposal_review_queue.py`
- Modify: `backend/app/api/world_model.py`
- Modify: `backend/app/api/athena_evolution.py`
- Modify: `backend/app/schemas/world_proposals.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_world_frontend_api.py`

- [ ] **Step 1: Write failing test**

Add `test_world_model_proposal_review_queue_clusters_low_risk_and_prioritizes_high_risk`:

- create current profile;
- create one bundle;
- add two `presence_count` pending items in chapter 1;
- add one `status` pending item in chapter 1;
- call `/world-model/proposal-review-queue`;
- assert first cluster is high risk, `review_mode == "individual"`;
- assert low-risk `presence_count` cluster has `candidate_count == 2`, `review_mode == "batch"`;
- assert item statuses remain `pending`.

- [ ] **Step 2: Run failing test**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py::test_world_model_proposal_review_queue_clusters_low_risk_and_prioritizes_high_risk -v
```

Expected: FAIL because the endpoint does not exist.

- [ ] **Step 3: Implement queue builder**

`build_proposal_review_queue(db, project_id, profile)` should:

- query `WorldProposalItem` for current profile and statuses `pending` / `needs_edit`;
- classify `presence_count`, `mentioned_in_chapter`, and `present_at_location` as low risk;
- classify `status`, `identity`, `role`, `event_summary`, and predicates containing `death` as high risk;
- classify everything else as medium risk;
- use `review_mode="batch"` for low risk and `review_mode="individual"` for medium/high risk;
- cluster low-risk items by `predicate` and `chapter_index`;
- keep high/medium items as individual clusters;
- sort high before medium before low, then by chapter.

- [ ] **Step 4: Add schemas and endpoints**

Add response shape:

```python
{
    "project_id": "...",
    "profile_version": 1,
    "total_items": 3,
    "clusters": [
        {
            "cluster_id": "high:status:item-id",
            "risk_level": "high",
            "review_mode": "individual",
            "candidate_count": 1,
            "item_ids": ["..."],
            "subject_refs": ["char.hero"],
            "predicate": "status",
            "chapter_range": {"start": 1, "end": 1},
            "reason": "状态、身份、事件或规则类候选会改变后续叙事，应单独审阅。"
        }
    ]
}
```

Expose:

- `GET /api/v1/projects/{project_id}/world-model/proposal-review-queue`
- `GET /api/v1/projects/{project_id}/athena/evolution/proposal-review-queue`

- [ ] **Step 5: Run focused test**

Run the focused test again. Expected: PASS.

### Task 2: Verification and Commit

- [ ] **Step 1: Run related suites**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py backend\tests\test_world_proposals.py -v
```

- [ ] **Step 2: Run backend suite**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
```

- [ ] **Step 3: Check hygiene**

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9_-]{20,}|api_key|API_KEY" backend docs frontend .agents
git status --short
```

- [ ] **Step 4: Commit**

```powershell
git add backend docs\superpowers\plans\2026-05-13-longform-scale-phase3.md
git commit -m "feat: add proposal review queue clustering"
```
