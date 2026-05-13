# Longform Scale Phase 10 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface longform maintenance diagnostics in Athena so users can see stale or missing chapter memory and retrieval coverage before thousand-chapter projects silently drift.

**Architecture:** Reuse the Phase 9 read-only diagnostics endpoint. Add a typed API client method, Athena store state/action, overview route loading, and a compact health section inside the existing Athena overview component.

**Tech Stack:** Vue 3, Pinia, TypeScript, Vitest, Vite.

---

## File Structure

- Modify `frontend/src/api/types.ts`: add `LongformMaintenanceDiagnostics`.
- Modify `frontend/src/api/client.ts`: add `getAthenaLongformMaintenanceDiagnostics`.
- Modify `frontend/src/stores/athena.ts`: add diagnostics state and loader.
- Modify `frontend/src/views/athenaSectionLoader.ts`: load diagnostics for Athena overview.
- Modify `frontend/src/views/AthenaView.vue`: pass diagnostics into overview.
- Modify `frontend/src/components/athena/AthenaOverview.vue`: render maintenance health.
- Modify tests under `frontend/src/**`: cover API/store loading, route loader, and UI rendering.
- Update this plan as tasks are executed.

## Success Criteria

- Athena overview loads longform maintenance diagnostics with the dashboard.
- Current diagnostics render as `长篇维护：已同步`.
- Stale diagnostics render as `长篇维护：需要维护` and list bounded stale/missing chapter indexes.
- Store caches diagnostics consistently with existing Athena data loading.
- Focused Vitest tests, frontend unit tests, frontend build, diff hygiene, and exact sensitive-key scan pass before commit.

## Task 1: API and Store Diagnostics

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/athena.ts`
- Test: `frontend/src/stores/athena.maintenance.test.ts`

- [ ] **Step 1: Write failing store test**

Add a test that mocks `fetch`, calls `athena.loadLongformMaintenanceDiagnostics('project-1')`, and expects `athena.longformMaintenanceDiagnostics.status === 'stale'`.

- [ ] **Step 2: Verify RED**

```powershell
npm --prefix frontend run test:unit -- frontend/src/stores/athena.maintenance.test.ts
```

Expected: FAIL because the store action and type do not exist.

- [ ] **Step 3: Implement typed API and store state**

Add `LongformMaintenanceDiagnostics`, API client method, `longformMaintenanceDiagnostics` ref, and `loadLongformMaintenanceDiagnostics` action. Reset the diagnostics when project state is cleared.

- [ ] **Step 4: Verify GREEN**

```powershell
npm --prefix frontend run test:unit -- frontend/src/stores/athena.maintenance.test.ts
```

Expected: PASS.

## Task 2: Overview Loading and Rendering

**Files:**
- Modify: `frontend/src/views/athenaSectionLoader.ts`
- Modify: `frontend/src/views/AthenaView.vue`
- Modify: `frontend/src/components/athena/AthenaOverview.vue`
- Test: `frontend/src/views/athenaSectionLoader.test.ts`
- Test: `frontend/src/components/athena/AthenaOverview.test.ts`

- [ ] **Step 1: Write failing loader/UI tests**

Add route-loader coverage that overview calls `loadLongformMaintenanceDiagnostics`. Add overview component coverage for stale diagnostics showing Chinese status and chapter indexes.

- [ ] **Step 2: Verify RED**

```powershell
npm --prefix frontend run test:unit -- frontend/src/views/athenaSectionLoader.test.ts frontend/src/components/athena/AthenaOverview.test.ts
```

Expected: FAIL because loader and overview do not consume diagnostics yet.

- [ ] **Step 3: Implement overview health section**

Pass diagnostics from `AthenaView` into `AthenaOverview`. Render a compact `长篇维护` section with counts and chapter lists. Keep copy Chinese and use existing overview spacing/border patterns.

- [ ] **Step 4: Verify GREEN**

```powershell
npm --prefix frontend run test:unit -- frontend/src/views/athenaSectionLoader.test.ts frontend/src/components/athena/AthenaOverview.test.ts
```

Expected: PASS.

## Task 3: Verification and Commit

- [ ] **Step 1: Run focused tests**

```powershell
npm --prefix frontend run test:unit -- frontend/src/stores/athena.maintenance.test.ts frontend/src/views/athenaSectionLoader.test.ts frontend/src/components/athena/AthenaOverview.test.ts
```

- [ ] **Step 2: Run frontend unit tests and build**

```powershell
npm --prefix frontend run test:unit
npm --prefix frontend run build
```

- [ ] **Step 3: Hygiene checks**

```powershell
git diff --check
rg -n "<exact-sensitive-key>" .
git status --short
```

Expected: diff check passes and exact sensitive-key scan returns no matches.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/stores/athena.ts frontend/src/stores/athena.maintenance.test.ts frontend/src/views/athenaSectionLoader.ts frontend/src/views/athenaSectionLoader.test.ts frontend/src/views/AthenaView.vue frontend/src/components/athena/AthenaOverview.vue frontend/src/components/athena/AthenaOverview.test.ts docs/superpowers/plans/2026-05-13-longform-scale-phase10.md
git commit -m "feat: surface longform maintenance health"
```
