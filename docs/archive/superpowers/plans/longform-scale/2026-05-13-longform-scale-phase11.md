# Longform Scale Phase 11 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users repair stale longform maintenance state from Athena instead of only seeing diagnostics.

**Architecture:** Add a read-after-write repair service that refreshes only stale or missing chapter memory, then syncs the affected longform-memory retrieval documents. Expose it through an Athena endpoint and a compact overview action that updates the existing diagnostics state.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Vue 3, Pinia, TypeScript, Vitest, Vite.

---

## File Structure

- Modify `backend/app/core/longform_memory.py`: add repair collection and `repair_longform_maintenance`.
- Modify `backend/app/schemas/longform_memory.py`: add repair response schema.
- Modify `backend/app/api/athena_longform.py`: add `POST /longform/maintenance/repair`.
- Modify `backend/tests/test_longform_scale.py`: cover repair from stale diagnostics to current diagnostics.
- Modify `frontend/src/api/types.ts`: add repair result type.
- Modify `frontend/src/api/client.ts`: add repair client method.
- Modify `frontend/src/stores/athena.ts`: add repair action and result state.
- Modify `frontend/src/stores/athena.maintenance.test.ts`: cover repair action.
- Modify `frontend/src/components/athena/AthenaOverview.vue`: add maintenance repair button.
- Modify `frontend/src/components/athena/AthenaOverview.test.ts`: cover repair button emit.
- Modify `frontend/src/views/AthenaView.vue`: wire repair action.
- Update this plan as tasks are executed.

## Success Criteria

- Repair endpoint refreshes stale/missing chapter memory and syncs affected longform-memory retrieval documents.
- Repair response includes refreshed chapter indexes, synced scope keys, and remaining diagnostics.
- After repair, diagnostics report `status=current` for the tested stale project.
- Athena overview shows a repair button only when diagnostics are stale.
- Clicking the repair button updates store diagnostics from the repair response.
- Backend tests, frontend focused tests, frontend full tests, frontend build, diff hygiene, and exact sensitive-key scan pass before commit.

## Task 1: Backend Repair Endpoint

**Files:**
- Modify: `backend/app/core/longform_memory.py`
- Modify: `backend/app/schemas/longform_memory.py`
- Modify: `backend/app/api/athena_longform.py`
- Test: `backend/tests/test_longform_scale.py`

- [x] **Step 1: Write failing backend repair test**

Add a test that creates three chapters, builds memory and retrieval, edits chapter 2, calls `POST /api/v1/projects/{project_id}/athena/longform/maintenance/repair`, and asserts the response repaired chapter 2 and remaining diagnostics are current.

- [x] **Step 2: Verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_repair_refreshes_memory_and_retrieval -v
```

Expected: FAIL because the repair endpoint does not exist.

- [x] **Step 3: Implement backend repair**

Refactor diagnostics into a collector that can return full stale/missing chapter lists. Repair stale or missing chapter memory with `refresh_longform_memory_for_chapter`, sync affected longform-memory retrieval documents, then return fresh diagnostics.

- [x] **Step 4: Verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_maintenance_repair_refreshes_memory_and_retrieval -v
```

Expected: PASS.

## Task 2: Frontend Repair Action

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/stores/athena.ts`
- Modify: `frontend/src/stores/athena.maintenance.test.ts`
- Modify: `frontend/src/components/athena/AthenaOverview.vue`
- Modify: `frontend/src/components/athena/AthenaOverview.test.ts`
- Modify: `frontend/src/views/AthenaView.vue`

- [x] **Step 1: Write failing frontend repair tests**

Add store coverage for `repairLongformMaintenance` and component coverage that stale diagnostics show a repair button emitting `repairMaintenance`.

- [x] **Step 2: Verify RED**

```powershell
npm --prefix frontend run test:unit -- src/stores/athena.maintenance.test.ts src/components/athena/AthenaOverview.test.ts
```

Expected: FAIL because the repair action and emit do not exist.

- [x] **Step 3: Implement frontend repair wiring**

Add API/store types and action, pass repair state to `AthenaOverview`, emit repair requests, and refresh diagnostics from the repair response.

- [x] **Step 4: Verify GREEN**

```powershell
npm --prefix frontend run test:unit -- src/stores/athena.maintenance.test.ts src/components/athena/AthenaOverview.test.ts
```

Expected: PASS.

## Task 3: Verification and Commit

- [x] **Step 1: Run focused tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -v
npm --prefix frontend run test:unit -- src/stores/athena.maintenance.test.ts src/components/athena/AthenaOverview.test.ts src/views/athenaSectionLoader.test.ts
```

- [x] **Step 2: Run full verification slice**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
npm --prefix frontend run test:unit
npm --prefix frontend run build
```

- [x] **Step 3: Hygiene checks**

```powershell
git diff --check
rg -n "<exact-sensitive-key>" .
git status --short
```

Expected: diff check passes and exact sensitive-key scan returns no matches.

- [x] **Step 4: Commit**

```powershell
git add backend/app/core/longform_memory.py backend/app/schemas/longform_memory.py backend/app/api/athena_longform.py backend/tests/test_longform_scale.py frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/stores/athena.ts frontend/src/stores/athena.maintenance.test.ts frontend/src/components/athena/AthenaOverview.vue frontend/src/components/athena/AthenaOverview.test.ts frontend/src/views/AthenaView.vue docs/superpowers/plans/2026-05-13-longform-scale-phase11.md
git commit -m "feat: repair longform maintenance from athena"
```
