# Longform Scale Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Athena narrative and proposal review screens usable by default on thousand-chapter projects without rendering every chapter, graph node, or proposal item at once.

**Architecture:** Keep the existing Vue/Pinia/FastAPI shape. Add frontend-only locality controls for narrative chapters and atlas graphs, and wire the existing read-only proposal review queue into the proposal workbench. Do not change proposal approval semantics in this phase.

**Tech Stack:** Vue 3, Pinia, TypeScript, Vitest, existing FastAPI review queue endpoint.

---

## File Structure

- Modify `frontend/src/api/types.ts`: add proposal review queue response types.
- Modify `frontend/src/api/client.ts`: add `getWorldProposalReviewQueue()`.
- Modify `frontend/src/stores/worldModel.ts`: store/load proposal review queue alongside proposal bundles.
- Modify `frontend/src/components/athena/ProposalWorkbench.vue`: render risk queue summary above bundle detail.
- Modify `frontend/src/components/athena/ProposalWorkbench.test.ts`: verify localized queue summary and no raw backend labels.
- Modify `frontend/src/components/athena/NarrativeWorkbench.vue`: render chapters by 100-chapter volume and 50-chapter page window; jump moves to the target window.
- Modify `frontend/src/components/athena/NarrativeWorkbench.test.ts`: verify large chapter plans do not render all chapters and jump reveals target chapter.
- Modify `frontend/src/components/athena/NarrativeAtlasView.vue`: default atlas to a chapter window when the graph is large; expose window controls.
- Modify `frontend/src/components/athena/NarrativeAtlasView.test.ts`: verify large graph defaults to local scope and does not render all chapter nodes.

## Success Criteria

- A 250+ chapter chapter-plan view renders a bounded subset by default and can jump to a later chapter without search.
- A 250+ chapter atlas view renders a bounded chapter window by default and exposes the visible range.
- Proposal workbench surfaces high/medium/low risk cluster counts from `/world-model/proposal-review-queue`.
- Raw backend status values such as `high`, `medium`, `low`, `individual`, and `batch` do not leak into the UI.
- Verification commands pass:
  - `npm run test:unit -- src/components/athena/NarrativeWorkbench.test.ts src/components/athena/NarrativeAtlasView.test.ts src/components/athena/ProposalWorkbench.test.ts src/stores/worldModel.test.ts`
  - `npm run build`
  - `git diff --check`

## Task 1: Proposal Review Queue Frontend Contract

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/worldModel.ts`
- Test: `frontend/src/stores/worldModel.test.ts`

- [x] **Step 1: Write failing store test**

Add a test that mocks `api.getWorldProposalReviewQueue`, calls `store.loadSetupPanelData('project-1')`, and asserts `store.proposalReviewQueue?.total_items === 3`.

- [x] **Step 2: Run focused test**

```powershell
cd frontend; npm run test:unit -- src/stores/worldModel.test.ts
```

Expected: FAIL because the store has no proposal review queue state yet.

- [x] **Step 3: Add types, API client, and store lane**

Add `ProposalReviewQueueCluster` / `ProposalReviewQueue` types, `api.getWorldProposalReviewQueue()`, a store `proposalReviewQueue` ref, and load/refresh it with dashboard/overview/bundles.

- [x] **Step 4: Run focused test**

```powershell
cd frontend; npm run test:unit -- src/stores/worldModel.test.ts
```

Expected: PASS.

## Task 2: Proposal Workbench Queue Summary

**Files:**
- Modify: `frontend/src/components/athena/ProposalWorkbench.vue`
- Test: `frontend/src/components/athena/ProposalWorkbench.test.ts`

- [x] **Step 1: Write failing component test**

Seed `store.proposalReviewQueue` with one high-risk individual cluster and one low-risk batch cluster. Mount `ProposalWorkbench` and assert the UI contains `高风险`, `单独审阅`, `批量审阅`, and does not contain raw values `high`, `individual`, or `batch`.

- [x] **Step 2: Run focused test**

```powershell
cd frontend; npm run test:unit -- src/components/athena/ProposalWorkbench.test.ts
```

Expected: FAIL because the workbench does not render the queue yet.

- [x] **Step 3: Render localized queue summary**

Render a compact section above the proposal detail with total actionable items and cluster rows. Keep it read-only.

- [x] **Step 4: Run focused test**

```powershell
cd frontend; npm run test:unit -- src/components/athena/ProposalWorkbench.test.ts
```

Expected: PASS.

## Task 3: Chapter Planning Windowed Rendering

**Files:**
- Modify: `frontend/src/components/athena/NarrativeWorkbench.vue`
- Test: `frontend/src/components/athena/NarrativeWorkbench.test.ts`

- [x] **Step 1: Write failing large-plan test**

Create a 250-chapter outline, mount chapter view, and assert:

- `chapter-1` exists;
- `chapter-51` does not render by default;
- after selecting jump value `240`, `chapter-240` exists and `chapter-1` no longer renders.

- [x] **Step 2: Run focused test**

```powershell
cd frontend; npm run test:unit -- src/components/athena/NarrativeWorkbench.test.ts
```

Expected: FAIL because all chapters render.

- [x] **Step 3: Add volume and page window controls**

Use 100 chapters per volume and 50 visible chapters per window. Search mode may still render matching results, but default browsing must stay bounded.

- [x] **Step 4: Run focused test**

```powershell
cd frontend; npm run test:unit -- src/components/athena/NarrativeWorkbench.test.ts
```

Expected: PASS.

## Task 4: Narrative Atlas Local Scope

**Files:**
- Modify: `frontend/src/components/athena/NarrativeAtlasView.vue`
- Test: `frontend/src/components/athena/NarrativeAtlasView.test.ts`

- [x] **Step 1: Write failing large-graph test**

Create a 250-chapter plan, mount atlas view, and assert:

- `chapter:1` exists;
- `chapter:120` does not render by default;
- range text shows the local window.

- [x] **Step 2: Run focused test**

```powershell
cd frontend; npm run test:unit -- src/components/athena/NarrativeAtlasView.test.ts
```

Expected: FAIL because atlas renders all chapter nodes.

- [x] **Step 3: Add scoped graph projection**

Keep the full graph for metrics and detail safety, but pass a scoped graph to `NarrativeAtlasCanvas` when chapter count exceeds 120. Default window size: 80 chapters.

- [x] **Step 4: Run focused test**

```powershell
cd frontend; npm run test:unit -- src/components/athena/NarrativeAtlasView.test.ts
```

Expected: PASS.

## Task 5: Verification and Commit

- [x] **Step 1: Run focused frontend tests**

```powershell
cd frontend; npm run test:unit -- src/components/athena/NarrativeWorkbench.test.ts src/components/athena/NarrativeAtlasView.test.ts src/components/athena/ProposalWorkbench.test.ts src/stores/worldModel.test.ts
```

- [x] **Step 2: Run build**

```powershell
cd frontend; npm run build
```

- [x] **Step 3: Check hygiene**

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9_-]{20,}" backend docs frontend .agents
git status --short
```

- [x] **Step 4: Commit**

```powershell
git add frontend docs/superpowers/plans/2026-05-13-longform-scale-phase4.md
git commit -m "feat: localize longform athena views"
```
