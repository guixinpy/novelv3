# World Model Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 7 follow-up features for the world model: subject knowledge view, chapter snapshot view, full diff editor, pagination, filtering, conflict indicators, and configurable reviewer identity.

**Architecture:** Tab-based WorldProjectionViewer (Current Truth / Subject Knowledge / Chapter Snapshot) with new backend endpoints leveraging existing `project_subject_knowledge()` and `project_snapshot()` functions. Proposal list gets pagination + filtering at the API level. Diff editor replaces the notes-only approve_with_edits flow. Reviewer identity stored in localStorage.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Vue 3 (Composition API), Pinia, TypeScript, Tailwind-adjacent custom CSS

---

### Task 1: Backend — Subject Knowledge API Endpoint

**Files:**
- Modify: `backend/app/api/world_model.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_world_model_api.py — append to existing file or create
import pytest
from fastapi.testclient import TestClient

def test_subject_knowledge_returns_filtered_projection(client, seeded_world_project):
    """GET /world-model/subject-knowledge?subject_ref=X returns projection scoped to that subject."""
    project_id = seeded_world_project["project_id"]
    subject = seeded_world_project["subject_ref"]  # e.g. "张三"
    resp = client.get(f"/api/v1/projects/{project_id}/world-model/subject-knowledge?subject_ref={subject}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["projection"]["view_type"] == "subject_knowledge"
    assert data["project_profile"] is not None

def test_subject_knowledge_missing_param(client, seeded_world_project):
    project_id = seeded_world_project["project_id"]
    resp = client.get(f"/api/v1/projects/{project_id}/world-model/subject-knowledge")
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_world_model_api.py::test_subject_knowledge_returns_filtered_projection -v`
Expected: FAIL — 404 (endpoint doesn't exist)

- [ ] **Step 3: Implement the endpoint**

Add to `backend/app/api/world_model.py` after the `get_world_model_overview` function:

```python
@router.get("/subject-knowledge", response_model=ProjectWorldOverviewOut)
def get_subject_knowledge(
    project_id: str,
    subject_ref: str,
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    if profile is None:
        return ProjectWorldOverviewOut(project_profile=None, projection=None)

    anchors = (
        db.query(WorldTimelineAnchor)
        .filter(
            WorldTimelineAnchor.project_id == project_id,
            WorldTimelineAnchor.profile_version == profile.version,
        )
        .order_by(WorldTimelineAnchor.chapter_index.asc(), WorldTimelineAnchor.intra_chapter_seq.asc())
        .all()
    )
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(WorldEvent.chapter_index.asc(), WorldEvent.intra_chapter_seq.asc())
        .all()
    )
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
        )
        .order_by(WorldFactClaim.chapter_index.asc(), WorldFactClaim.intra_chapter_seq.asc())
        .all()
    )
    anchor_index = build_anchor_time_index(anchors)
    try:
        projection = project_subject_knowledge(
            subject_ref=subject_ref,
            events=[ledger_event_from_world_event(event, anchor_index=anchor_index) for event in events],
            facts=[_fact_record_from_model(fact) for fact in facts],
            anchors=anchors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectWorldOverviewOut(
        project_profile=profile,
        projection=WorldProjectionOut(view_type="subject_knowledge", **projection),
    )
```

Update the import at the top of the file — add `project_subject_knowledge` to the import from `app.core.world_projection`:

```python
from app.core.world_projection import FactRecord, project_world_truth, project_subject_knowledge
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_world_model_api.py::test_subject_knowledge_returns_filtered_projection -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/world_model.py backend/tests/test_world_model_api.py
git commit -m "feat: add subject-knowledge API endpoint"
```

---

### Task 2: Backend — Chapter Snapshot API Endpoint

**Files:**
- Modify: `backend/app/api/world_model.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_world_model_api.py — append
def test_snapshot_returns_scoped_projection(client, seeded_world_project):
    project_id = seeded_world_project["project_id"]
    resp = client.get(f"/api/v1/projects/{project_id}/world-model/snapshot?chapter_index=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["projection"]["view_type"] == "chapter_snapshot"

def test_snapshot_missing_chapter(client, seeded_world_project):
    project_id = seeded_world_project["project_id"]
    resp = client.get(f"/api/v1/projects/{project_id}/world-model/snapshot")
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_world_model_api.py::test_snapshot_returns_scoped_projection -v`
Expected: FAIL — 404

- [ ] **Step 3: Implement the endpoint**

Add to `backend/app/api/world_model.py` after the subject-knowledge endpoint:

```python
@router.get("/snapshot", response_model=ProjectWorldOverviewOut)
def get_chapter_snapshot(
    project_id: str,
    chapter_index: int,
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    if profile is None:
        return ProjectWorldOverviewOut(project_profile=None, projection=None)

    anchors = (
        db.query(WorldTimelineAnchor)
        .filter(
            WorldTimelineAnchor.project_id == project_id,
            WorldTimelineAnchor.profile_version == profile.version,
        )
        .order_by(WorldTimelineAnchor.chapter_index.asc(), WorldTimelineAnchor.intra_chapter_seq.asc())
        .all()
    )
    events = (
        db.query(WorldEvent)
        .filter(
            WorldEvent.project_id == project_id,
            WorldEvent.project_profile_version_id == profile.id,
            WorldEvent.profile_version == profile.version,
        )
        .order_by(WorldEvent.chapter_index.asc(), WorldEvent.intra_chapter_seq.asc())
        .all()
    )
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
        )
        .order_by(WorldFactClaim.chapter_index.asc(), WorldFactClaim.intra_chapter_seq.asc())
        .all()
    )
    anchor_index = build_anchor_time_index(anchors)
    try:
        projection = project_snapshot(
            events=[ledger_event_from_world_event(event, anchor_index=anchor_index) for event in events],
            facts=[_fact_record_from_model(fact) for fact in facts],
            chapter_index=chapter_index,
            anchors=anchors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProjectWorldOverviewOut(
        project_profile=profile,
        projection=WorldProjectionOut(view_type="chapter_snapshot", **projection),
    )
```

Update the import — add `project_snapshot`:

```python
from app.core.world_projection import FactRecord, project_world_truth, project_subject_knowledge, project_snapshot
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_world_model_api.py::test_snapshot_returns_scoped_projection -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/world_model.py backend/tests/test_world_model_api.py
git commit -m "feat: add chapter-snapshot API endpoint"
```

---

### Task 3: Backend — Proposal Bundles Pagination & Filtering

**Files:**
- Modify: `backend/app/api/world_model.py`
- Modify: `backend/app/schemas/world_proposals.py`

- [ ] **Step 1: Add paginated response schema**

Add to `backend/app/schemas/world_proposals.py` before `ProposalBundleDetailOut`:

```python
class PaginatedProposalBundlesOut(BaseModel):
    items: list[ProposalBundleOut] = Field(default_factory=list)
    total: int = 0
    offset: int = 0
    limit: int = 20

    model_config = ConfigDict(extra="forbid")
```

Export it in `backend/app/schemas/__init__.py`:

```python
from .world_proposals import (
    ...
    PaginatedProposalBundlesOut,
)
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_world_model_api.py — append
def test_list_bundles_paginated(client, seeded_world_project):
    project_id = seeded_world_project["project_id"]
    resp = client.get(f"/api/v1/projects/{project_id}/world-model/proposal-bundles?offset=0&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["offset"] == 0
    assert data["limit"] == 5

def test_list_bundles_filtered_by_status(client, seeded_world_project):
    project_id = seeded_world_project["project_id"]
    resp = client.get(f"/api/v1/projects/{project_id}/world-model/proposal-bundles?bundle_status=pending")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["bundle_status"] == "pending"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_world_model_api.py::test_list_bundles_paginated -v`
Expected: FAIL — response is a list, not paginated object

- [ ] **Step 4: Implement pagination and filtering**

Replace the `list_world_proposal_bundles` function in `backend/app/api/world_model.py`:

```python
@router.get("/proposal-bundles", response_model=PaginatedProposalBundlesOut)
def list_world_proposal_bundles(
    project_id: str,
    offset: int = 0,
    limit: int = 20,
    bundle_status: str | None = None,
    item_status: str | None = None,
    profile_version: int | None = None,
    db: Session = Depends(get_db),
):
    _require_project(db=db, project_id=project_id)
    profile = _get_current_profile(db=db, project_id=project_id)
    if profile is None:
        return PaginatedProposalBundlesOut(items=[], total=0, offset=offset, limit=limit)

    query = db.query(WorldProposalBundle).filter(
        WorldProposalBundle.project_id == project_id,
        WorldProposalBundle.project_profile_version_id == profile.id,
        WorldProposalBundle.profile_version == profile.version,
    )
    if bundle_status is not None:
        query = query.filter(WorldProposalBundle.bundle_status == bundle_status)
    if profile_version is not None:
        query = query.filter(WorldProposalBundle.profile_version == profile_version)
    if item_status is not None:
        matching_bundle_ids = (
            db.query(WorldProposalItem.bundle_id)
            .filter(
                WorldProposalItem.project_id == project_id,
                WorldProposalItem.item_status == item_status,
            )
            .distinct()
            .subquery()
        )
        query = query.filter(WorldProposalBundle.id.in_(matching_bundle_ids))

    total = query.count()
    items = (
        query
        .order_by(WorldProposalBundle.updated_at.desc(), WorldProposalBundle.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return PaginatedProposalBundlesOut(items=items, total=total, offset=offset, limit=limit)
```

Add `PaginatedProposalBundlesOut` to the imports from `app.schemas` at the top of the file.

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_world_model_api.py -v -k "paginated or filtered"`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/world_model.py backend/app/schemas/world_proposals.py backend/app/schemas/__init__.py backend/tests/test_world_model_api.py
git commit -m "feat: add pagination and filtering to proposal bundles API"
```

---

### Task 4: Backend — Conflict Detection in Bundle Detail

**Files:**
- Modify: `backend/app/api/world_model.py`
- Modify: `backend/app/schemas/world_proposals.py`

- [ ] **Step 1: Add conflict schema**

Add to `backend/app/schemas/world_proposals.py` before `PaginatedProposalBundlesOut`:

```python
class ProposalItemConflictOut(BaseModel):
    item_id: str
    conflict_type: str  # "truth_conflict" | "high_impact"
    detail: str
    existing_claim_id: str | None = None

    model_config = ConfigDict(extra="forbid")
```

Update `ProposalBundleDetailOut` to include conflicts:

```python
class ProposalBundleDetailOut(BaseModel):
    bundle: ProposalBundleOut
    items: list[ProposalItemOut] = Field(default_factory=list)
    reviews: list[ProposalReviewOut] = Field(default_factory=list)
    impact_snapshots: list[ProposalImpactScopeSnapshotOut] = Field(default_factory=list)
    conflicts: list[ProposalItemConflictOut] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
```

Export `ProposalItemConflictOut` in `backend/app/schemas/__init__.py`.

- [ ] **Step 2: Implement conflict detection**

Add to `backend/app/api/world_model.py` — a helper function before `_build_bundle_detail`:

```python
def _detect_item_conflicts(
    *,
    db: Session,
    project_id: str,
    items: list[WorldProposalItem],
    impact_snapshots: list[WorldProposalImpactScopeSnapshot],
) -> list[dict]:
    conflicts = []
    for item in items:
        if item.item_status in ("approved", "approved_with_edits", "rejected", "rolled_back"):
            continue
        existing = (
            db.query(WorldFactClaim)
            .filter(
                WorldFactClaim.project_id == project_id,
                WorldFactClaim.subject_ref == item.subject_ref,
                WorldFactClaim.predicate == item.predicate,
                WorldFactClaim.claim_status == "confirmed",
                WorldFactClaim.claim_layer == "truth",
            )
            .first()
        )
        if existing is not None:
            existing_val = existing.object_ref_or_value
            proposed_val = item.object_ref_or_value
            if existing_val != proposed_val:
                conflicts.append({
                    "item_id": item.id,
                    "conflict_type": "truth_conflict",
                    "detail": f"与现有真相冲突：{item.subject_ref}.{item.predicate} = {existing_val}",
                    "existing_claim_id": existing.id,
                })
    for snapshot in impact_snapshots:
        if len(snapshot.affected_truth_claim_ids) >= 3:
            for candidate_id in snapshot.candidate_item_ids:
                if not any(c["item_id"] == candidate_id and c["conflict_type"] == "high_impact" for c in conflicts):
                    conflicts.append({
                        "item_id": candidate_id,
                        "conflict_type": "high_impact",
                        "detail": f"高影响：涉及 {len(snapshot.affected_truth_claim_ids)} 条关联事实",
                        "existing_claim_id": None,
                    })
    return conflicts
```

Update `_build_bundle_detail` to call it:

```python
def _build_bundle_detail(*, db: Session, project_id: str, bundle_id: str) -> ProposalBundleDetailOut:
    bundle = _get_project_bundle_or_404(db=db, project_id=project_id, bundle_id=bundle_id)
    items = (
        db.query(WorldProposalItem)
        .filter(
            WorldProposalItem.project_id == project_id,
            WorldProposalItem.project_profile_version_id == bundle.project_profile_version_id,
            WorldProposalItem.profile_version == bundle.profile_version,
            WorldProposalItem.bundle_id == bundle_id,
        )
        .order_by(WorldProposalItem.created_at.asc(), WorldProposalItem.id.asc())
        .all()
    )
    reviews = (
        db.query(WorldProposalReview)
        .filter(
            WorldProposalReview.project_id == project_id,
            WorldProposalReview.project_profile_version_id == bundle.project_profile_version_id,
            WorldProposalReview.profile_version == bundle.profile_version,
            WorldProposalReview.bundle_id == bundle_id,
        )
        .order_by(WorldProposalReview.created_at.asc(), WorldProposalReview.id.asc())
        .all()
    )
    impact_snapshots = (
        db.query(WorldProposalImpactScopeSnapshot)
        .filter(
            WorldProposalImpactScopeSnapshot.project_id == project_id,
            WorldProposalImpactScopeSnapshot.project_profile_version_id == bundle.project_profile_version_id,
            WorldProposalImpactScopeSnapshot.profile_version == bundle.profile_version,
            WorldProposalImpactScopeSnapshot.bundle_id == bundle_id,
        )
        .order_by(
            WorldProposalImpactScopeSnapshot.created_at.desc(),
            WorldProposalImpactScopeSnapshot.id.desc(),
        )
        .all()
    )
    if not impact_snapshots and items:
        impact_snapshots = [calculate_bundle_impact_scope(db=db, bundle_id=bundle_id)]
    conflicts = _detect_item_conflicts(
        db=db, project_id=project_id, items=items, impact_snapshots=impact_snapshots,
    )
    return ProposalBundleDetailOut(
        bundle=bundle,
        items=items,
        reviews=reviews,
        impact_snapshots=impact_snapshots,
        conflicts=conflicts,
    )
```

- [ ] **Step 3: Run all backend tests**

Run: `cd backend && python -m pytest -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/world_model.py backend/app/schemas/world_proposals.py backend/app/schemas/__init__.py
git commit -m "feat: add conflict detection to proposal bundle detail"
```


---

### Task 5: Frontend — API Client & Types for New Endpoints

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add new types to `frontend/src/api/types.ts`**

Append after `ProposalRollbackRequest`:

```typescript
export interface PaginatedProposalBundles {
  items: ProposalBundle[]
  total: number
  offset: number
  limit: number
}

export interface ProposalItemConflict {
  item_id: string
  conflict_type: 'truth_conflict' | 'high_impact'
  detail: string
  existing_claim_id: string | null
}
```

Update `ProposalBundleDetail` to include conflicts:

```typescript
export interface ProposalBundleDetail {
  bundle: ProposalBundle
  items: ProposalItem[]
  reviews: ProposalReview[]
  impact_snapshots: ProposalImpactSnapshot[]
  conflicts: ProposalItemConflict[]
}
```

- [ ] **Step 2: Add new API methods to `frontend/src/api/client.ts`**

Update the import to include `PaginatedProposalBundles`. Change `listWorldProposalBundles` and add two new methods:

```typescript
listWorldProposalBundles: (id: string, params?: { offset?: number; limit?: number; bundle_status?: string; item_status?: string; profile_version?: number }) => {
  const query = new URLSearchParams()
  if (params?.offset !== undefined) query.set('offset', String(params.offset))
  if (params?.limit !== undefined) query.set('limit', String(params.limit))
  if (params?.bundle_status) query.set('bundle_status', params.bundle_status)
  if (params?.item_status) query.set('item_status', params.item_status)
  if (params?.profile_version !== undefined) query.set('profile_version', String(params.profile_version))
  const qs = query.toString()
  return request<PaginatedProposalBundles>(`/projects/${id}/world-model/proposal-bundles${qs ? `?${qs}` : ''}`)
},
getSubjectKnowledge: (id: string, subjectRef: string) =>
  request<WorldModelOverview>(`/projects/${id}/world-model/subject-knowledge?subject_ref=${encodeURIComponent(subjectRef)}`),
getChapterSnapshot: (id: string, chapterIndex: number) =>
  request<WorldModelOverview>(`/projects/${id}/world-model/snapshot?chapter_index=${chapterIndex}`),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat: add frontend API client for new world model endpoints"
```

---

### Task 6: Frontend — Store Updates for New Views & Pagination

**Files:**
- Modify: `frontend/src/stores/worldModel.ts`

- [ ] **Step 1: Add new state and methods**

Add new state refs after `selectedBundleDetail`:

```typescript
const subjectKnowledge = ref<WorldProjection | null>(null)
const selectedSubjectRef = ref<string | null>(null)
const chapterSnapshot = ref<WorldProjection | null>(null)
const selectedChapterIndex = ref<number | null>(null)
const reviewerName = ref(localStorage.getItem(`mozhou_reviewer_${currentProjectScope.value}`) || 'editor')
const bundlesTotal = ref(0)
const bundlesOffset = ref(0)
const bundlesLimit = ref(20)
const bundleFilters = ref<{ bundle_status?: string; item_status?: string; profile_version?: number }>({})
```

Add `WorldProjection` to the import from `../api/types`.

- [ ] **Step 2: Add loadSubjectKnowledge method**

```typescript
async function loadSubjectKnowledge(projectId: string, subjectRef: string) {
  ensureProjectScope(projectId)
  selectedSubjectRef.value = subjectRef
  try {
    const overview = await api.getSubjectKnowledge(projectId, subjectRef)
    subjectKnowledge.value = overview.projection
  } catch (err) {
    error.value = toErrorMessage(err)
  }
}
```

- [ ] **Step 3: Add loadChapterSnapshot method**

```typescript
async function loadChapterSnapshot(projectId: string, chapterIndex: number) {
  ensureProjectScope(projectId)
  selectedChapterIndex.value = chapterIndex
  try {
    const overview = await api.getChapterSnapshot(projectId, chapterIndex)
    chapterSnapshot.value = overview.projection
  } catch (err) {
    error.value = toErrorMessage(err)
  }
}
```

- [ ] **Step 4: Add setReviewerName method**

```typescript
function setReviewerName(projectId: string, name: string) {
  reviewerName.value = name
  localStorage.setItem(`mozhou_reviewer_${projectId}`, name)
}
```

- [ ] **Step 5: Update loadSetupPanelData to use pagination**

In `loadSetupPanelData`, change the `api.listWorldProposalBundles` call:

```typescript
const [overview, bundlesPage] = await Promise.all([
  api.getWorldModelOverview(projectId),
  api.listWorldProposalBundles(projectId, {
    offset: bundlesOffset.value,
    limit: bundlesLimit.value,
    ...bundleFilters.value,
  }),
])
if (!isLatestRequest(snapshot, 'overview') || !isLatestRequest(snapshot, 'bundles')) return

projectProfile.value = overview.project_profile
projection.value = overview.projection
proposalBundles.value = bundlesPage.items
bundlesTotal.value = bundlesPage.total
```

- [ ] **Step 6: Add loadMoreBundles method**

```typescript
async function loadMoreBundles(projectId: string) {
  ensureProjectScope(projectId)
  const nextOffset = bundlesOffset.value + bundlesLimit.value
  try {
    const page = await api.listWorldProposalBundles(projectId, {
      offset: nextOffset,
      limit: bundlesLimit.value,
      ...bundleFilters.value,
    })
    proposalBundles.value = [...proposalBundles.value, ...page.items]
    bundlesOffset.value = nextOffset
    bundlesTotal.value = page.total
  } catch (err) {
    error.value = toErrorMessage(err)
  }
}
```

- [ ] **Step 7: Add applyBundleFilters method**

```typescript
async function applyBundleFilters(projectId: string, filters: typeof bundleFilters.value) {
  bundleFilters.value = filters
  bundlesOffset.value = 0
  await loadSetupPanelData(projectId)
}
```

- [ ] **Step 8: Update refreshBundles to use pagination**

```typescript
async function refreshBundles(projectId: string, requestSnapshot?: RequestSnapshot) {
  const snapshot = requestSnapshot ?? captureRequest(projectId, ['bundles'])
  const page = await api.listWorldProposalBundles(projectId, {
    offset: 0,
    limit: bundlesOffset.value + bundlesLimit.value,
    ...bundleFilters.value,
  })
  if (!isLatestRequest(snapshot, 'bundles')) return
  proposalBundles.value = page.items
  bundlesTotal.value = page.total
  bundlesOffset.value = Math.max(0, page.items.length - bundlesLimit.value)
  if (selectedBundleId.value && !page.items.some((bundle) => bundle.id === selectedBundleId.value)) {
    selectedBundleId.value = page.items[0]?.id ?? null
  }
}
```

- [ ] **Step 9: Update resetProjectScopedState**

Add resets for new state:

```typescript
subjectKnowledge.value = null
selectedSubjectRef.value = null
chapterSnapshot.value = null
selectedChapterIndex.value = null
bundlesTotal.value = 0
bundlesOffset.value = 0
bundleFilters.value = {}
```

- [ ] **Step 10: Export new state and methods in the return block**

Add to the return object:

```typescript
subjectKnowledge,
selectedSubjectRef,
chapterSnapshot,
selectedChapterIndex,
reviewerName,
bundlesTotal,
bundlesOffset,
bundlesLimit,
bundleFilters,
loadSubjectKnowledge,
loadChapterSnapshot,
loadMoreBundles,
applyBundleFilters,
setReviewerName,
```

- [ ] **Step 11: Commit**

```bash
git add frontend/src/stores/worldModel.ts
git commit -m "feat: add store support for subject knowledge, snapshot, pagination, reviewer"
```


---

### Task 7: Frontend — WorldProjectionViewer Tab Refactor + SubjectKnowledge & Snapshot Components

**Files:**
- Modify: `frontend/src/components/world/WorldProjectionViewer.vue`
- Create: `frontend/src/components/world/WorldSubjectKnowledge.vue`
- Create: `frontend/src/components/world/WorldChapterSnapshot.vue`

- [ ] **Step 1: Create WorldSubjectKnowledge.vue**

```vue
<template>
  <div class="subject-knowledge" data-testid="world-subject-knowledge">
    <div class="subject-knowledge__selector">
      <span class="subject-knowledge__label">选择主体：</span>
      <select
        v-model="selected"
        class="subject-knowledge__select"
        @change="onSelect"
      >
        <option value="" disabled>请选择</option>
        <option v-for="ref in subjectRefs" :key="ref" :value="ref">{{ ref }}</option>
      </select>
    </div>
    <div v-if="projection" class="subject-knowledge__grid">
      <article class="subject-knowledge__block">
        <h4>作为主体的事实</h4>
        <ul v-if="asSubjectEntries.length" class="subject-knowledge__list">
          <li v-for="[pred, val] in asSubjectEntries" :key="pred">
            <strong>{{ selected }}.{{ pred }}</strong>
            <span>{{ String(val) }}</span>
          </li>
        </ul>
        <p v-else class="subject-knowledge__empty">无</p>
      </article>
      <article class="subject-knowledge__block">
        <h4>作为客体的事实</h4>
        <ul v-if="asObjectEntries.length" class="subject-knowledge__list">
          <li v-for="[subj, facts] in asObjectEntries" :key="subj">
            <strong>{{ subj }}</strong>
            <span>{{ formatFacts(facts) }}</span>
          </li>
        </ul>
        <p v-else class="subject-knowledge__empty">无</p>
      </article>
    </div>
    <p v-else-if="selected" class="subject-knowledge__empty">加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { WorldProjection } from '../../api/types'

const props = defineProps<{
  subjectRefs: string[]
  projection: WorldProjection | null
}>()

const emit = defineEmits<{
  select: [subjectRef: string]
}>()

const selected = ref('')

const asSubjectEntries = computed(() => {
  if (!props.projection || !selected.value) return []
  const facts = props.projection.facts[selected.value]
  return facts ? Object.entries(facts) : []
})

const asObjectEntries = computed(() => {
  if (!props.projection || !selected.value) return []
  return Object.entries(props.projection.facts).filter(([key]) => key !== selected.value)
})

function formatFacts(facts: Record<string, unknown>) {
  return Object.entries(facts).map(([k, v]) => `${k}: ${String(v)}`).join(' / ')
}

function onSelect() {
  if (selected.value) emit('select', selected.value)
}
</script>

<style scoped>
.subject-knowledge__selector {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.8rem;
}
.subject-knowledge__label { color: var(--ink-muted); font-size: 0.8rem; }
.subject-knowledge__select {
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 0.6rem;
  padding: 0.4rem 0.6rem;
  background: rgba(255, 252, 246, 0.92);
  color: var(--ink-strong);
  font-size: 0.8rem;
}
.subject-knowledge__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; }
.subject-knowledge__block { display: grid; gap: 0.4rem; }
.subject-knowledge__block h4 { margin: 0; color: var(--ink-strong); font-size: 0.84rem; }
.subject-knowledge__list { display: grid; gap: 0.35rem; margin: 0; padding: 0; list-style: none; }
.subject-knowledge__list li { display: grid; gap: 0.1rem; }
.subject-knowledge__list strong { color: var(--ink-strong); font-size: 0.78rem; }
.subject-knowledge__list span,
.subject-knowledge__empty { color: var(--ink-muted); font-size: 0.78rem; }
</style>
```

- [ ] **Step 2: Create WorldChapterSnapshot.vue**

```vue
<template>
  <div class="chapter-snapshot" data-testid="world-chapter-snapshot">
    <div class="chapter-snapshot__selector">
      <span class="chapter-snapshot__label">截至章节：</span>
      <button class="chapter-snapshot__nav" :disabled="!canPrev" @click="prev">◀</button>
      <span class="chapter-snapshot__current">第 {{ selectedChapter }} 章</span>
      <button class="chapter-snapshot__nav" :disabled="!canNext" @click="next">▶</button>
      <span class="chapter-snapshot__total">/ 共 {{ maxChapter }} 章</span>
      <span class="chapter-snapshot__badge">只读快照</span>
    </div>
    <div v-if="projection" class="chapter-snapshot__grid">
      <article class="chapter-snapshot__block">
        <h4>实体状态</h4>
        <ul v-if="entityEntries.length" class="chapter-snapshot__list">
          <li v-for="[ref, entity] in entityEntries" :key="ref">
            <strong>{{ ref }}</strong>
            <span>{{ formatAttrs(entity.attributes) }}</span>
          </li>
        </ul>
        <p v-else class="chapter-snapshot__empty">无</p>
      </article>
      <article class="chapter-snapshot__block">
        <h4>关键事实</h4>
        <ul v-if="factEntries.length" class="chapter-snapshot__list">
          <li v-for="[subj, facts] in factEntries" :key="subj">
            <strong>{{ subj }}</strong>
            <span>{{ formatAttrs(facts) }}</span>
          </li>
        </ul>
        <p v-else class="chapter-snapshot__empty">无</p>
      </article>
      <article class="chapter-snapshot__block">
        <h4>在场信息</h4>
        <ul v-if="presenceEntries.length" class="chapter-snapshot__list">
          <li v-for="[ref, p] in presenceEntries" :key="ref">
            <strong>{{ ref }}</strong>
            <span>{{ p.location_ref || '未知' }} / {{ p.presence_status || '未标注' }}</span>
          </li>
        </ul>
        <p v-else class="chapter-snapshot__empty">无</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WorldProjection } from '../../api/types'

const props = defineProps<{
  projection: WorldProjection | null
  selectedChapter: number
  maxChapter: number
}>()

const emit = defineEmits<{
  'update:selectedChapter': [chapter: number]
}>()

const canPrev = computed(() => props.selectedChapter > 1)
const canNext = computed(() => props.selectedChapter < props.maxChapter)

const entityEntries = computed(() => props.projection ? Object.entries(props.projection.entities).slice(0, 6) : [])
const factEntries = computed(() => props.projection ? Object.entries(props.projection.facts).slice(0, 6) : [])
const presenceEntries = computed(() => props.projection ? Object.entries(props.projection.presence).slice(0, 6) : [])

function formatAttrs(val: Record<string, unknown>) {
  return Object.entries(val).map(([k, v]) => `${k}: ${String(v)}`).join(' / ')
}
function prev() { if (canPrev.value) emit('update:selectedChapter', props.selectedChapter - 1) }
function next() { if (canNext.value) emit('update:selectedChapter', props.selectedChapter + 1) }
</script>

<style scoped>
.chapter-snapshot__selector {
  display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.8rem;
}
.chapter-snapshot__label { color: var(--ink-muted); font-size: 0.8rem; }
.chapter-snapshot__nav {
  border: 1px solid rgba(111, 69, 31, 0.14); border-radius: 0.4rem;
  padding: 0.2rem 0.5rem; background: rgba(255, 252, 246, 0.92);
  color: var(--ink-muted); font-size: 0.78rem; cursor: pointer;
}
.chapter-snapshot__nav:disabled { opacity: 0.4; cursor: default; }
.chapter-snapshot__current {
  font-weight: 700; color: var(--accent-strong); font-size: 0.88rem;
  min-width: 4rem; text-align: center;
}
.chapter-snapshot__total { color: var(--ink-muted); font-size: 0.76rem; }
.chapter-snapshot__badge {
  margin-left: auto; border-radius: 999px; padding: 0.2rem 0.6rem;
  background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 0.7rem; font-weight: 700;
}
.chapter-snapshot__grid { display: grid; gap: 0.8rem; }
.chapter-snapshot__block { display: grid; gap: 0.4rem; border: 1px dashed rgba(111, 69, 31, 0.14); border-radius: 0.8rem; padding: 0.8rem; }
.chapter-snapshot__block h4 { margin: 0; color: var(--ink-strong); font-size: 0.84rem; }
.chapter-snapshot__list { display: grid; gap: 0.35rem; margin: 0; padding: 0; list-style: none; }
.chapter-snapshot__list li { display: grid; gap: 0.1rem; }
.chapter-snapshot__list strong { color: var(--ink-strong); font-size: 0.78rem; }
.chapter-snapshot__list span,
.chapter-snapshot__empty { color: var(--ink-muted); font-size: 0.78rem; }
</style>
```

- [ ] **Step 3: Refactor WorldProjectionViewer.vue to 3-tab structure**

Replace the entire content of `WorldProjectionViewer.vue`:

```vue
<template>
  <section class="world-panel" data-testid="world-projection-viewer">
    <header class="world-panel__header">
      <div class="world-panel__tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="world-panel__tab"
          :class="{ 'is-active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
      <span class="world-panel__pill">{{ entityEntries.length }} 个实体</span>
    </header>

    <div v-if="activeTab === 'current'" class="world-panel__grid">
      <article class="world-panel__block">
        <h4>实体状态</h4>
        <ul v-if="entityEntries.length" class="world-panel__list">
          <li v-for="[entityRef, entity] in entityEntries" :key="entityRef">
            <strong>{{ entityRef }}</strong>
            <span>{{ formatAttributes(entity.attributes) }}</span>
          </li>
        </ul>
        <p v-else class="world-panel__empty">当前没有结构化实体。</p>
      </article>
      <article class="world-panel__block">
        <h4>关键事实</h4>
        <ul v-if="factEntries.length" class="world-panel__list">
          <li v-for="[subjectRef, facts] in factEntries" :key="subjectRef">
            <strong>{{ subjectRef }}</strong>
            <span>{{ formatAttributes(facts) }}</span>
          </li>
        </ul>
        <p v-else class="world-panel__empty">当前没有确认事实。</p>
      </article>
      <article class="world-panel__block">
        <h4>在场信息</h4>
        <ul v-if="presenceEntries.length" class="world-panel__list">
          <li v-for="[entityRef, presence] in presenceEntries" :key="entityRef">
            <strong>{{ entityRef }}</strong>
            <span>{{ presence.location_ref || '未知位置' }} / {{ presence.presence_status || '未标注' }}</span>
          </li>
        </ul>
        <p v-else class="world-panel__empty">当前没有在场投影。</p>
      </article>
    </div>

    <WorldSubjectKnowledge
      v-else-if="activeTab === 'subject'"
      :subject-refs="subjectRefs"
      :projection="subjectKnowledge"
      @select="$emit('loadSubjectKnowledge', $event)"
    />

    <WorldChapterSnapshot
      v-else-if="activeTab === 'snapshot'"
      :projection="chapterSnapshot"
      :selected-chapter="selectedChapter"
      :max-chapter="maxChapter"
      @update:selected-chapter="$emit('loadChapterSnapshot', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { WorldProjection } from '../../api/types'
import WorldSubjectKnowledge from './WorldSubjectKnowledge.vue'
import WorldChapterSnapshot from './WorldChapterSnapshot.vue'

const props = defineProps<{
  projection: WorldProjection
  subjectKnowledge: WorldProjection | null
  chapterSnapshot: WorldProjection | null
  selectedChapter: number
  maxChapter: number
}>()

defineEmits<{
  loadSubjectKnowledge: [subjectRef: string]
  loadChapterSnapshot: [chapterIndex: number]
}>()

const tabs = [
  { key: 'current', label: '当前真相' },
  { key: 'subject', label: '主体认知' },
  { key: 'snapshot', label: '章节快照' },
] as const

const activeTab = ref<'current' | 'subject' | 'snapshot'>('current')

const entityEntries = computed(() => Object.entries(props.projection.entities).slice(0, 6))
const factEntries = computed(() => Object.entries(props.projection.facts).slice(0, 6))
const presenceEntries = computed(() => Object.entries(props.projection.presence).slice(0, 6))
const subjectRefs = computed(() => Object.keys(props.projection.entities))

function formatAttributes(value: Record<string, unknown>) {
  return Object.entries(value).map(([key, entry]) => `${key}: ${String(entry)}`).join(' / ')
}
</script>
```

Keep the existing `<style scoped>` block and add tab styles:

```css
.world-panel__tabs {
  display: flex;
  gap: 0;
}

.world-panel__tab {
  padding: 0.45rem 0.85rem;
  border: none;
  background: none;
  color: var(--ink-muted);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.world-panel__tab.is-active {
  color: var(--accent-strong);
  border-bottom-color: var(--accent-strong);
}
```

- [ ] **Step 4: Run type check**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/world/WorldProjectionViewer.vue frontend/src/components/world/WorldSubjectKnowledge.vue frontend/src/components/world/WorldChapterSnapshot.vue
git commit -m "feat: add tab-based projection viewer with subject knowledge and chapter snapshot"
```


---

### Task 8: Frontend — ProposalClaimDiffEditor Component

**Files:**
- Create: `frontend/src/components/world/ProposalClaimDiffEditor.vue`

- [ ] **Step 1: Create the diff editor component**

```vue
<template>
  <div class="diff-editor" data-testid="proposal-claim-diff-editor">
    <header class="diff-editor__header">
      <span class="diff-editor__title">编辑 Proposal Item</span>
      <span class="diff-editor__claim">{{ item.subject_ref }}.{{ item.predicate }}</span>
      <span v-if="changedCount > 0" class="diff-editor__badge">{{ changedCount }} 处变更</span>
    </header>

    <div class="diff-editor__fields">
      <div
        v-for="field in fields"
        :key="field.key"
        class="diff-editor__row"
        :class="{ 'is-changed': isChanged(field.key) }"
      >
        <span class="diff-editor__field-name">{{ field.key }}</span>
        <div class="diff-editor__field-value">
          <template v-if="field.type === 'number'">
            <span v-if="isChanged(field.key)" class="diff-editor__original">{{ field.original }}</span>
            <span v-if="isChanged(field.key)" class="diff-editor__arrow">→</span>
            <input
              type="number"
              :value="editedValues[field.key] ?? field.original"
              class="diff-editor__input"
              @input="onInput(field.key, ($event.target as HTMLInputElement).value, 'number')"
            >
          </template>
          <template v-else-if="field.type === 'select'">
            <span v-if="isChanged(field.key)" class="diff-editor__original">{{ field.original || '—' }}</span>
            <span v-if="isChanged(field.key)" class="diff-editor__arrow">→</span>
            <select
              :value="editedValues[field.key] ?? field.original ?? ''"
              class="diff-editor__input"
              @change="onInput(field.key, ($event.target as HTMLSelectElement).value, 'string')"
            >
              <option value="">—</option>
              <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
            </select>
          </template>
          <template v-else-if="field.type === 'textarea'">
            <div v-if="isChanged(field.key)" class="diff-editor__original">{{ field.original }}</div>
            <textarea
              :value="editedValues[field.key] ?? field.original ?? ''"
              class="diff-editor__textarea"
              rows="2"
              @input="onInput(field.key, ($event.target as HTMLTextAreaElement).value, 'string')"
            />
          </template>
          <template v-else>
            <span v-if="isChanged(field.key)" class="diff-editor__original">{{ field.original || '—' }}</span>
            <span v-if="isChanged(field.key)" class="diff-editor__arrow">→</span>
            <input
              type="text"
              :value="editedValues[field.key] ?? field.original ?? ''"
              class="diff-editor__input"
              @input="onInput(field.key, ($event.target as HTMLInputElement).value, 'string')"
            >
          </template>
        </div>
        <button
          v-if="isChanged(field.key)"
          type="button"
          class="diff-editor__reset"
          @click="resetField(field.key)"
        >
          重置
        </button>
      </div>
    </div>

    <footer class="diff-editor__footer">
      <span class="diff-editor__hint">只有修改过的字段会提交</span>
      <div class="diff-editor__actions">
        <button type="button" class="diff-editor__btn" @click="$emit('cancel')">取消</button>
        <button type="button" class="diff-editor__btn diff-editor__btn--primary" @click="submit">确认编辑并通过</button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { ProposalItem } from '../../api/types'

const props = defineProps<{
  item: ProposalItem
  anchorOptions: string[]
}>()

const emit = defineEmits<{
  submit: [editedFields: Record<string, unknown>]
  cancel: []
}>()

interface FieldDef {
  key: string
  type: 'number' | 'text' | 'select' | 'textarea' | 'tags'
  original: unknown
  options?: string[]
}

const fields = computed<FieldDef[]>(() => [
  { key: 'chapter_index', type: 'number', original: (props.item as any).chapter_index ?? null },
  { key: 'intra_chapter_seq', type: 'number', original: (props.item as any).intra_chapter_seq ?? 0 },
  { key: 'valid_from_anchor_id', type: 'select', original: (props.item as any).valid_from_anchor_id ?? null, options: props.anchorOptions },
  { key: 'valid_to_anchor_id', type: 'select', original: (props.item as any).valid_to_anchor_id ?? null, options: props.anchorOptions },
  { key: 'source_event_ref', type: 'text', original: (props.item as any).source_event_ref ?? null },
  { key: 'evidence_refs', type: 'text', original: (props.item.evidence_refs ?? []).join(', ') },
  { key: 'notes', type: 'textarea', original: (props.item as any).notes ?? '' },
])

const editedValues = reactive<Record<string, unknown>>({})

const changedCount = computed(() =>
  fields.value.filter((f) => isChanged(f.key)).length,
)

function isChanged(key: string): boolean {
  if (!(key in editedValues)) return false
  const field = fields.value.find((f) => f.key === key)
  return field ? editedValues[key] !== field.original : false
}

function onInput(key: string, value: string, type: 'number' | 'string') {
  editedValues[key] = type === 'number' ? (value === '' ? null : Number(value)) : value
}

function resetField(key: string) {
  delete editedValues[key]
}

function submit() {
  const result: Record<string, unknown> = {}
  for (const field of fields.value) {
    if (isChanged(field.key)) {
      let val = editedValues[field.key]
      if (field.key === 'evidence_refs' && typeof val === 'string') {
        val = val.split(',').map((s: string) => s.trim()).filter(Boolean)
      }
      result[field.key] = val
    }
  }
  emit('submit', result)
}
</script>

<style scoped>
.diff-editor { display: grid; gap: 0; border: 1px solid rgba(111, 69, 31, 0.14); border-radius: 0.8rem; overflow: hidden; }
.diff-editor__header { display: flex; align-items: center; gap: 0.6rem; padding: 0.7rem 0.85rem; border-bottom: 1px solid rgba(111, 69, 31, 0.1); }
.diff-editor__title { color: var(--ink-strong); font-size: 0.84rem; font-weight: 700; }
.diff-editor__claim { color: var(--ink-muted); font-size: 0.76rem; }
.diff-editor__badge { margin-left: auto; border-radius: 0.4rem; padding: 0.15rem 0.5rem; background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 0.7rem; font-weight: 700; }
.diff-editor__fields { display: grid; }
.diff-editor__row { display: flex; align-items: center; gap: 0.6rem; padding: 0.55rem 0.85rem; border-bottom: 1px solid rgba(111, 69, 31, 0.06); }
.diff-editor__row.is-changed { background: rgba(245, 158, 11, 0.06); }
.diff-editor__field-name { width: 10rem; color: var(--ink-muted); font-size: 0.76rem; flex-shrink: 0; }
.diff-editor__row.is-changed .diff-editor__field-name { color: #d97706; font-weight: 700; }
.diff-editor__field-value { flex: 1; display: flex; align-items: center; gap: 0.5rem; }
.diff-editor__original { color: var(--ink-muted); font-size: 0.76rem; text-decoration: line-through; opacity: 0.7; }
.diff-editor__arrow { color: var(--ink-muted); font-size: 0.76rem; }
.diff-editor__input, .diff-editor__textarea {
  border: 1px solid rgba(111, 69, 31, 0.14); border-radius: 0.4rem;
  padding: 0.3rem 0.5rem; background: rgba(255, 252, 246, 0.92);
  color: var(--ink-strong); font-size: 0.78rem; flex: 1;
}
.diff-editor__textarea { resize: vertical; width: 100%; }
.diff-editor__reset { background: none; border: none; color: var(--ink-muted); font-size: 0.7rem; cursor: pointer; }
.diff-editor__footer { display: flex; align-items: center; justify-content: space-between; padding: 0.65rem 0.85rem; border-top: 1px solid rgba(111, 69, 31, 0.1); }
.diff-editor__hint { color: var(--ink-muted); font-size: 0.72rem; }
.diff-editor__actions { display: flex; gap: 0.45rem; }
.diff-editor__btn { border: 1px solid rgba(111, 69, 31, 0.18); border-radius: 999px; padding: 0.35rem 0.7rem; background: rgba(255, 252, 246, 0.92); color: var(--ink-muted); font-size: 0.76rem; cursor: pointer; }
.diff-editor__btn--primary { background: var(--accent-strong); color: #fff; border-color: var(--accent-strong); font-weight: 700; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/world/ProposalClaimDiffEditor.vue
git commit -m "feat: add ProposalClaimDiffEditor component"
```

---

### Task 9: Frontend — Wire Diff Editor into ActionPanel + Reviewer Identity

**Files:**
- Modify: `frontend/src/components/world/WorldProposalActionPanel.vue`
- Modify: `frontend/src/components/world/WorldProposalItemCard.vue`

- [ ] **Step 1: Update WorldProposalActionPanel.vue**

Replace the entire `<script setup>` and template to integrate the diff editor and reviewer identity:

In the template, replace the `editNotes` textarea with a conditional diff editor. When `showDiffEditor` is true, show `ProposalClaimDiffEditor` instead of the textarea. Update `emitReview` to use `reviewerRef` prop instead of hardcoded `'frontend.reviewer'`.

Key changes to the script:

```typescript
import ProposalClaimDiffEditor from './ProposalClaimDiffEditor.vue'
import type { ProposalItem, ProposalReviewRequest } from '../../api/types'

const props = defineProps<{
  busy: boolean
  approvalReviewId: string | null
  canRollback: boolean
  item: ProposalItem
  reviewerRef: string
  anchorOptions: string[]
}>()

const showDiffEditor = ref(false)
const pendingEditedFields = ref<Record<string, unknown>>({})

function emitReview(action: ProposalReviewRequest['action'], fallbackReason: string) {
  if (action === 'approve_with_edits' && !showDiffEditor.value) {
    showDiffEditor.value = true
    return
  }
  emit('review', {
    reviewer_ref: props.reviewerRef,
    action,
    reason: buildReason(fallbackReason),
    evidence_refs: [],
    edited_fields: action === 'approve_with_edits' ? pendingEditedFields.value : {},
  })
  showDiffEditor.value = false
}

function onDiffSubmit(editedFields: Record<string, unknown>) {
  pendingEditedFields.value = editedFields
  emitReview('approve_with_edits', '编辑后通过')
}
```

Remove the `editNotes` textarea. Add the diff editor in the template:

```html
<ProposalClaimDiffEditor
  v-if="showDiffEditor"
  :item="item"
  :anchor-options="anchorOptions"
  @submit="onDiffSubmit"
  @cancel="showDiffEditor = false"
/>
```

- [ ] **Step 2: Update WorldProposalItemCard.vue props**

Add `reviewerRef` and `anchorOptions` props, pass them through to ActionPanel:

```typescript
const props = defineProps<{
  item: ProposalItem
  busy: boolean
  approvalReviewId: string | null
  reviewerRef: string
  anchorOptions: string[]
}>()
```

Pass to ActionPanel in template:

```html
<WorldProposalActionPanel
  :busy="busy"
  :approval-review-id="approvalReviewId"
  :can-rollback="item.item_status !== 'rolled_back'"
  :item="item"
  :reviewer-ref="reviewerRef"
  :anchor-options="anchorOptions"
  @review="forwardReview"
  @split="forwardSplit"
  @rollback="forwardRollback"
/>
```

- [ ] **Step 3: Run type check**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/world/WorldProposalActionPanel.vue frontend/src/components/world/WorldProposalItemCard.vue
git commit -m "feat: integrate diff editor into action panel, use configurable reviewer"
```

---

### Task 10: Frontend — Bundle List Pagination, Filtering & Conflict Badges

**Files:**
- Modify: `frontend/src/components/world/WorldProposalBundleList.vue`
- Modify: `frontend/src/components/world/WorldProposalItemCard.vue`

- [ ] **Step 1: Add pagination and filter UI to WorldProposalBundleList.vue**

Add filter bar at the top and "load more" button at the bottom. Update props:

```typescript
const props = defineProps<{
  bundles: ProposalBundle[]
  selectedBundleId: string | null
  total: number
  filters: { bundle_status?: string; item_status?: string; profile_version?: number }
}>()

const emit = defineEmits<{
  select: [bundleId: string]
  loadMore: []
  updateFilters: [filters: { bundle_status?: string; item_status?: string; profile_version?: number }]
}>()
```

Add filter bar in template before the list:

```html
<div class="bundle-list__filters">
  <select :value="filters.bundle_status || ''" @change="onFilterChange('bundle_status', $event)">
    <option value="">Bundle 状态: 全部</option>
    <option value="pending">pending</option>
    <option value="approved">approved</option>
    <option value="rejected">rejected</option>
  </select>
  <select :value="filters.item_status || ''" @change="onFilterChange('item_status', $event)">
    <option value="">Item 状态: 全部</option>
    <option value="pending">pending</option>
    <option value="needs_edit">needs_edit</option>
    <option value="approved">approved</option>
    <option value="rejected">rejected</option>
  </select>
  <button v-if="hasActiveFilters" type="button" class="bundle-list__clear" @click="clearFilters">清除筛选</button>
</div>
```

Add load more button after the list:

```html
<button
  v-if="bundles.length < total"
  type="button"
  class="bundle-list__load-more"
  @click="$emit('loadMore')"
>
  加载更多 ({{ bundles.length }}/{{ total }})
</button>
```

- [ ] **Step 2: Add conflict badges to WorldProposalItemCard.vue**

Add `conflicts` prop:

```typescript
import type { ProposalItem, ProposalItemConflict } from '../../api/types'

const props = defineProps<{
  item: ProposalItem
  busy: boolean
  approvalReviewId: string | null
  reviewerRef: string
  anchorOptions: string[]
  conflicts: ProposalItemConflict[]
}>()
```

Add conflict display in the template header:

```html
<div v-if="itemConflicts.length" class="proposal-item-card__conflicts">
  <div
    v-for="conflict in itemConflicts"
    :key="conflict.conflict_type"
    class="proposal-item-card__conflict"
    :class="`is-${conflict.conflict_type}`"
  >
    <span v-if="conflict.conflict_type === 'truth_conflict'" class="proposal-item-card__conflict-icon">⚠</span>
    <span v-else class="proposal-item-card__conflict-icon">⚡</span>
    {{ conflict.detail }}
  </div>
</div>
```

Add computed:

```typescript
const itemConflicts = computed(() =>
  props.conflicts.filter((c) => c.item_id === props.item.id),
)
```

Add conflict styles:

```css
.proposal-item-card__conflicts { display: grid; gap: 0.3rem; }
.proposal-item-card__conflict { font-size: 0.72rem; line-height: 1.4; }
.proposal-item-card__conflict.is-truth_conflict { color: #dc2626; }
.proposal-item-card__conflict.is-high_impact { color: #d97706; }
.proposal-item-card__conflict-icon { margin-right: 0.2rem; }
```

Add left border styling based on conflict type — add a computed class to the root article:

```typescript
const conflictClass = computed(() => {
  if (itemConflicts.value.some((c) => c.conflict_type === 'truth_conflict')) return 'has-conflict'
  if (itemConflicts.value.some((c) => c.conflict_type === 'high_impact')) return 'has-risk'
  return ''
})
```

```css
.proposal-item-card.has-conflict { border-left: 3px solid #dc2626; }
.proposal-item-card.has-risk { border-left: 3px solid #d97706; }
```

- [ ] **Step 3: Run type check and build**

Run: `cd frontend && npx vue-tsc --noEmit && npm run build`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/world/WorldProposalBundleList.vue frontend/src/components/world/WorldProposalItemCard.vue
git commit -m "feat: add pagination, filtering, and conflict badges to proposal list"
```

---

### Task 11: Frontend — Wire Everything in SetupWorldPanel Parent

**Files:**
- Modify: the parent component that renders `WorldProjectionViewer`, `WorldProposalBundleList`, and `WorldProposalItemCard` (likely the setup inspector or workspace panel that uses the worldModel store)

- [ ] **Step 1: Identify and update the parent component**

Find the component that imports and renders `WorldProjectionViewer` and `WorldProposalBundleList`. Pass the new props from the store:

For `WorldProjectionViewer`:
```html
<WorldProjectionViewer
  :projection="worldModel.projection"
  :subject-knowledge="worldModel.subjectKnowledge"
  :chapter-snapshot="worldModel.chapterSnapshot"
  :selected-chapter="worldModel.selectedChapterIndex ?? 1"
  :max-chapter="maxChapterIndex"
  @load-subject-knowledge="worldModel.loadSubjectKnowledge(projectId, $event)"
  @load-chapter-snapshot="worldModel.loadChapterSnapshot(projectId, $event)"
/>
```

For `WorldProposalBundleList`:
```html
<WorldProposalBundleList
  :bundles="worldModel.proposalBundles"
  :selected-bundle-id="worldModel.selectedBundleId"
  :total="worldModel.bundlesTotal"
  :filters="worldModel.bundleFilters"
  @select="worldModel.selectBundle(projectId, $event)"
  @load-more="worldModel.loadMoreBundles(projectId)"
  @update-filters="worldModel.applyBundleFilters(projectId, $event)"
/>
```

For `WorldProposalItemCard` (in the bundle detail loop):
```html
<WorldProposalItemCard
  :item="item"
  :busy="worldModel.isActionPending(item.id)"
  :approval-review-id="getApprovalReviewId(item.id)"
  :reviewer-ref="worldModel.reviewerName"
  :anchor-options="anchorOptions"
  :conflicts="worldModel.selectedBundleDetail?.conflicts ?? []"
  @review="worldModel.reviewProposalItem(projectId, $event[0], $event[1])"
  @split="worldModel.splitProposalBundle(projectId, $event[0], { reviewer_ref: worldModel.reviewerName, reason: $event[2], evidence_refs: [], item_ids: [$event[1]] })"
  @rollback="worldModel.rollbackProposalReview(projectId, $event[0], { reviewer_ref: worldModel.reviewerName, reason: $event[1], evidence_refs: [] }, $event[2])"
/>
```

- [ ] **Step 2: Add reviewer name settings UI**

Add a small settings gear icon near the world model panel header that opens an inline input:

```html
<div class="reviewer-setting">
  <button type="button" class="reviewer-setting__toggle" @click="showReviewerInput = !showReviewerInput">⚙</button>
  <div v-if="showReviewerInput" class="reviewer-setting__input">
    <label>审阅者名称：</label>
    <input
      :value="worldModel.reviewerName"
      @change="worldModel.setReviewerName(projectId, ($event.target as HTMLInputElement).value)"
    >
  </div>
</div>
```

- [ ] **Step 3: Run full verification**

Run: `cd frontend && npx vue-tsc --noEmit && npm run build`
Run: `cd backend && python -m pytest -v`
Run: `cd frontend && npm run test:unit`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: wire world model follow-up features into parent components"
```

---

### Task 12: Final Verification & Cleanup

- [ ] **Step 1: Run full test suite**

```bash
cd backend && python -m pytest -v
cd ../frontend && npm run test:unit
```

- [ ] **Step 2: Type check and build**

```bash
cd frontend && npx vue-tsc --noEmit && npm run build
```

- [ ] **Step 3: Manual browser verification**

Start dev server and verify:
1. WorldProjectionViewer shows 3 tabs
2. "主体认知" tab: select a subject, see filtered facts
3. "章节快照" tab: navigate chapters, see read-only snapshot
4. "编辑后通过" opens diff editor with 7 fields
5. Bundle list shows pagination and filters
6. Conflict/risk badges appear on relevant items
7. Reviewer name is configurable and persists

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: cleanup after world model follow-ups implementation"
```
