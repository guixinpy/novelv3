# Athena World Model Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Athena a usable local world-model workbench by fixing projection rendering, converging frontend state ownership, improving proposal review UX, reducing backend projection duplication, and adding one deterministic chapter-analysis improvement.

**Architecture:** Keep the current FastAPI + SQLite + Vue/Pinia stack. Use `worldModel` as the frontend owner for projection and proposal review state, while `athena` remains responsible for Athena chat, ontology facade, timeline, retrieval, and optimization. Extract backend world projection assembly into a small service without introducing queues, caches, remote services, or distributed infrastructure.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Vue 3, Pinia, Vitest, Playwright E2E, SQLite.

---

## Stage Gates

- Stage 0 baseline: `scripts/verify_local_quality.sh`
- Stage 1 frontend regression tests: targeted Vitest for projection and proposal workbench, expected red before implementation.
- Stage 2 frontend convergence: targeted Vitest, `npm run build`, focused Playwright Athena navigation/section E2E.
- Stage 3 backend projection service: targeted pytest for world-model endpoints, then full backend pytest.
- Stage 4 deterministic analysis enhancement: targeted pytest for Athena longform, then proposal-store Vitest if frontend contract changes.
- Stage 5 final verification: `RUN_E2E=1 scripts/verify_local_quality.sh`

## File Structure

- `frontend/src/views/AthenaView.vue`
  - Route-level coordinator only. It chooses section, triggers section-specific loading, and delegates rendering.
- `frontend/src/stores/worldModel.ts`
  - Frontend owner for world profile, projection, subject knowledge, chapter snapshot, proposal bundles, selected detail, filters, and proposal review actions.
- `frontend/src/stores/athena.ts`
  - Keep chat, ontology facade, timeline, retrieval, consistency list, and optimization state. Remove proposal-review ownership from new Athena UI paths.
- `frontend/src/components/athena/ProjectionViewer.vue`
  - Render `WorldProjection` object maps correctly: entities, facts, presence, events.
- `frontend/src/components/athena/SubjectKnowledgePanel.vue`
  - New compact panel for selecting a subject and viewing subject-scoped projection.
- `frontend/src/components/athena/ProposalWorkbench.vue`
  - New Athena proposal workbench using `worldModel` store and existing `components/world/*` review cards.
- `frontend/e2e/athena-world-model.spec.ts`
  - New Playwright coverage for Athena section navigation, no broken core panels, and no API/console errors.
- `backend/app/core/world_projection_service.py`
  - New small service that loads current profile, anchors, events, facts, and builds current/subject/snapshot projections.
- `backend/app/api/world_model.py`
  - Delegate projection endpoints to the service.
- `backend/app/core/athena_longform.py`
  - Add deterministic mention-based candidate facts for known non-character world entities found in chapter text.
- Tests:
  - `frontend/src/components/athena/ProjectionViewer.test.ts`
  - `frontend/src/components/athena/ProposalWorkbench.test.ts`
  - `frontend/src/stores/worldModel.test.ts`
  - `backend/tests/test_world_frontend_api.py`
  - `backend/tests/test_athena_longform.py`

## Task 0: Baseline And Plan

**Files:**
- Create: `docs/superpowers/plans/2026-04-29-athena-world-model-workbench.md`
- Modify: `docs/superpowers/README.md`

- [ ] **Step 1: Verify isolated worktree baseline**

Run:

```bash
cd /home/guixin/project_workspace/novelv3/.worktrees/athena-world-model-workbench
scripts/verify_local_quality.sh
```

Expected: backend pytest passes, frontend unit tests pass, frontend build passes, E2E is skipped unless `RUN_E2E=1`.

- [ ] **Step 2: Commit plan docs**

Run:

```bash
cd /home/guixin/project_workspace/novelv3/docs
git add superpowers/plans/2026-04-29-athena-world-model-workbench.md superpowers/README.md
git commit -m "docs: plan Athena world model workbench"
```

Expected: docs nested repo has a new plan commit and clean status.

## Task 1: Frontend Regression Tests

**Files:**
- Create: `frontend/src/components/athena/ProjectionViewer.test.ts`
- Create: `frontend/src/components/athena/ProposalWorkbench.test.ts`
- Modify: `frontend/src/stores/worldModel.test.ts`

- [ ] **Step 1: Add projection renderer regression test**

Test behavior:

```ts
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProjectionViewer from './ProjectionViewer.vue'

describe('ProjectionViewer', () => {
  it('renders WorldProjection facts stored as subject maps', () => {
    const wrapper = mount(ProjectionViewer, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {
            'char.lin': { entity_type: 'character', attributes: { name: '林舟', status: 'alive' } },
          },
          relations: {},
          presence: {
            'char.lin': { location_ref: 'loc.tower', presence_status: 'active' },
          },
          occurred_events: {},
          event_links: {},
          facts: {
            'char.lin': {
              rank: '守夜人',
              secret: '知道旧灯塔真相',
            },
          },
        },
      },
    })

    expect(wrapper.text()).toContain('char.lin')
    expect(wrapper.text()).toContain('rank')
    expect(wrapper.text()).toContain('守夜人')
    expect(wrapper.text()).toContain('loc.tower')
  })
})
```

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/ProjectionViewer.test.ts
```

Expected before implementation: FAIL because the current renderer treats `facts` as an array.

- [ ] **Step 2: Add proposal workbench contract test**

Test behavior:

```ts
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProposalWorkbench from './ProposalWorkbench.vue'
import { useWorldModelStore } from '../../stores/worldModel'

vi.mock('../../api/client', () => ({
  api: {
    listWorldProposalBundles: vi.fn(),
    getWorldProposalBundle: vi.fn(),
    reviewWorldProposalItem: vi.fn(),
    splitWorldProposalBundle: vi.fn(),
    rollbackWorldProposalReview: vi.fn(),
    getWorldModelOverview: vi.fn(),
  },
}))

describe('ProposalWorkbench', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders selected proposal detail from worldModel store', () => {
    const store = useWorldModelStore()
    store.proposalBundles = [{
      id: 'bundle-1',
      project_id: 'project-1',
      project_profile_version_id: 'profile-1',
      profile_version: 1,
      parent_bundle_id: null,
      bundle_status: 'pending',
      title: '第1章世界事实候选',
      summary: 'summary',
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = {
      bundle: store.proposalBundles[0],
      items: [{
        id: 'item-1',
        bundle_id: 'bundle-1',
        parent_item_id: null,
        item_status: 'pending',
        claim_id: 'claim.1',
        subject_ref: 'loc.tower',
        predicate: 'mentioned_in_chapter',
        object_ref_or_value: { chapter_index: 1, mention_count: 2 },
        claim_layer: 'truth',
        evidence_refs: ['chapter:1'],
        authority_type: 'derived',
        confidence: 0.8,
        contract_version: 'world.contract.v1',
        approved_claim_id: null,
        created_by: 'athena.chapter_analyzer',
        created_at: '2026-04-29T00:00:00Z',
      }],
      reviews: [],
      impact_snapshots: [],
      conflicts: [],
    }

    const wrapper = mount(ProposalWorkbench, { props: { projectId: 'project-1' } })

    expect(wrapper.text()).toContain('第1章世界事实候选')
    expect(wrapper.text()).toContain('loc.tower.mentioned_in_chapter')
  })
})
```

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/ProposalWorkbench.test.ts
```

Expected before implementation: FAIL because `ProposalWorkbench.vue` does not exist.

## Task 2: Frontend Athena Workbench Convergence

**Files:**
- Modify: `frontend/src/stores/worldModel.ts`
- Modify: `frontend/src/views/AthenaView.vue`
- Modify: `frontend/src/components/athena/ProjectionViewer.vue`
- Create: `frontend/src/components/athena/SubjectKnowledgePanel.vue`
- Create: `frontend/src/components/athena/ProposalWorkbench.vue`
- Create: `frontend/e2e/athena-world-model.spec.ts`

- [ ] **Step 1: Expose lightweight overview loading in `worldModel` store**

Add `loadOverview(projectId)` that only calls `api.getWorldModelOverview(projectId)` and uses the existing request-lane guard for `overview`.

Run:

```bash
cd frontend
npm run test:unit -- src/stores/worldModel.test.ts
```

Expected: all `worldModel` tests pass.

- [ ] **Step 2: Fix `ProjectionViewer.vue` for object-map projections**

Render:
- entities from `projection.entities`
- facts from `projection.facts`
- presence from `projection.presence`
- event count from `projection.occurred_events`

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/ProjectionViewer.test.ts
```

Expected: projection regression test passes.

- [ ] **Step 3: Add `SubjectKnowledgePanel.vue`**

Behavior:
- Accept `projectId`, `projection`, `subjectKnowledge`, `selectedSubjectRef`
- Build subject options from `projection.entities`
- On selection, emit `selectSubject(subjectRef)`
- Render selected subject facts from `subjectKnowledge.facts`

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/ProjectionViewer.test.ts
```

Expected: unchanged projection tests pass. Add component tests only if behavior grows beyond this contract.

- [ ] **Step 4: Add `ProposalWorkbench.vue`**

Use:
- `WorldProposalBundleList`
- `WorldProposalImpactList`
- `WorldProposalItemCard`
- `worldModel.selectBundle`
- `worldModel.loadMoreBundles`
- `worldModel.applyBundleFilters`
- `worldModel.reviewProposalItem`
- `worldModel.splitProposalBundle`
- `worldModel.rollbackProposalReview`

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/ProposalWorkbench.test.ts src/stores/worldModel.test.ts
```

Expected: proposal workbench and store tests pass.

- [ ] **Step 5: Wire `AthenaView.vue` to `worldModel` for state/proposals**

Section behavior:
- `projection`: call `worldModel.loadOverview(projectId)` only when projection is missing.
- `knowledge`: call `worldModel.loadOverview(projectId)` and render `SubjectKnowledgePanel`.
- `proposals`: call `worldModel.loadSetupPanelData(projectId)` only when proposal data is not loaded.
- Keep ontology/timeline/retrieval/optimization/chat in `athena` store.
- Display `athena.error || worldModel.error` in the main content instead of silently swallowing failures.

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/ProjectionViewer.test.ts src/components/athena/ProposalWorkbench.test.ts src/stores/worldModel.test.ts src/stores/athena.scope.test.ts
npm run build
```

Expected: targeted tests and build pass.

- [ ] **Step 6: Add focused Athena E2E**

Create `frontend/e2e/athena-world-model.spec.ts`:
- create local project
- navigate Athena default view
- open `projection`, `knowledge`, `retrieval`, `proposals`
- assert workspace remains visible
- assert no console errors and no failed API responses

Run:

```bash
scripts/verify_frontend_e2e.sh
```

Expected: Playwright E2E passes.

Commit:

```bash
git add frontend/src frontend/e2e
git commit -m "refactor: converge Athena world model frontend"
```

## Task 3: Backend Projection Service

**Files:**
- Create: `backend/app/core/world_projection_service.py`
- Modify: `backend/app/api/world_model.py`
- Modify: `backend/tests/test_world_frontend_api.py`

- [ ] **Step 1: Add service-level regression coverage**

Add tests proving current truth, subject knowledge, and chapter snapshot endpoints still return the same `view_type` and facts.

Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_world_frontend_api.py -q
```

Expected before implementation: existing tests pass; new tests initially guide refactor behavior.

- [ ] **Step 2: Extract projection assembly**

Move duplicated profile/anchor/event/fact loading from `world_model.py` into `world_projection_service.py`:
- `build_current_truth_overview(db, project_id)`
- `build_subject_knowledge_overview(db, project_id, subject_ref)`
- `build_chapter_snapshot_overview(db, project_id, chapter_index)`

Keep API response schemas unchanged.

Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_world_frontend_api.py -q
```

Expected: world-model API tests pass.

Commit:

```bash
git add backend/app/core/world_projection_service.py backend/app/api/world_model.py backend/tests/test_world_frontend_api.py
git commit -m "refactor: extract world projection service"
```

## Task 4: Deterministic Athena Analysis Enhancement

**Files:**
- Modify: `backend/app/core/athena_longform.py`
- Modify: `backend/tests/test_athena_longform.py`

- [ ] **Step 1: Add failing test for non-character entity mentions**

Seed a world profile with a `WorldLocation`, `WorldFaction`, or `WorldArtifact`, create a chapter mentioning its name, run `analyze_chapter_to_world_proposals`, and assert a pending proposal item with:
- `predicate == "mentioned_in_chapter"`
- `subject_ref` equals the entity canonical id
- `object_ref_or_value.chapter_index` equals the analyzed chapter
- duplicate analysis skips the same claim id

Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_athena_longform.py -q
```

Expected before implementation: FAIL because non-character mentions are not extracted.

- [ ] **Step 2: Implement deterministic mention candidates**

In `athena_longform.py`:
- Query known non-character entities for current profile.
- Count exact name occurrences in chapter content.
- Create `ProposalCandidateFactCreate` with predicate `mentioned_in_chapter`.
- Use deterministic claim id: `claim.chapter.{chapter_index}.{slug(entity_ref)}.mentioned_in_chapter`.
- Keep all candidates in proposal workflow; do not directly write truth claims.

Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_athena_longform.py tests/test_athena_retrieval.py -q
```

Expected: targeted backend tests pass.

Commit:

```bash
git add backend/app/core/athena_longform.py backend/tests/test_athena_longform.py
git commit -m "feat: extract Athena non-character mentions"
```

## Task 5: Final Verification And Merge

**Files:**
- No planned source changes.

- [ ] **Step 1: Run full quality gate with E2E**

Run:

```bash
cd /home/guixin/project_workspace/novelv3/.worktrees/athena-world-model-workbench
RUN_E2E=1 scripts/verify_local_quality.sh
```

Expected:
- backend pytest passes
- frontend unit tests pass
- frontend build passes
- Playwright E2E passes

- [ ] **Step 2: Inspect diff and status**

Run:

```bash
git status --short
git log --oneline -5
git diff --stat main...HEAD
```

Expected: no generated DBs, no secrets, only planned source/test files.

- [ ] **Step 3: Fast-forward main and clean worktree**

Run:

```bash
cd /home/guixin/project_workspace/novelv3
git merge --ff-only refactor/athena-world-model-workbench
git worktree remove .worktrees/athena-world-model-workbench
git branch -d refactor/athena-world-model-workbench
```

Expected: `main` contains the work, worktree is removed, branch deleted, root status clean.
