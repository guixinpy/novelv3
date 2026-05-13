# Athena World Model Next Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the next local-only Athena/world-model upgrade by making subject knowledge persistable, adding safe in-process projection caching, and introducing an Athena Overview workbench.

**Architecture:** Keep the current FastAPI + SQLAlchemy + SQLite + Vue/Pinia stack. Add only local service-layer cache and schema fields; no Redis, queues, background workers, or distributed invalidation. Each stage has a focused red-green test gate and one commit.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, Vue 3, Pinia, Vitest, Playwright E2E, SQLite.

---

## Stage Gates

- Stage 0: isolated worktree baseline with `scripts/verify_local_quality.sh`.
- Stage 1: subject cognition persistence. Targeted pytest for proposal review and subject projection.
- Stage 2: projection cache. Targeted service tests proving cache hit and invalidation after review/import/analyze.
- Stage 3: Athena Overview. Targeted Vitest for store/component plus build.
- Stage 4: E2E and full quality gate with `RUN_E2E=1 scripts/verify_local_quality.sh`.

## File Structure

- `backend/app/models/world_fact_claim.py`
  - Add `perspective_ref` and `disclosed_to_refs` fields.
- `backend/app/models/world_proposal_bundle.py`
  - Add the same fields to `WorldProposalItem` so belief/disclosure proposals survive review.
- `backend/alembic/versions/20260429_add_subject_knowledge_fields.py`
  - Add nullable `perspective_ref` and JSON `disclosed_to_refs` columns to fact claims and proposal items.
- `backend/app/schemas/world_events.py`
  - Expose subject knowledge fields on fact claim create/out schemas.
- `backend/app/schemas/world_proposals.py`
  - Expose subject knowledge fields on proposal candidate/item/edit schemas.
- `backend/app/core/world_proposal_service.py`
  - Copy subject knowledge fields through candidate write, split, approve, and edit paths.
- `backend/app/core/world_projection_service.py`
  - Add a small in-process cache keyed by project/profile/view params and invalidation helpers.
- `backend/app/core/athena_longform.py`
  - Invalidate projection cache after import/setup analysis writes.
- `backend/app/api/world_model.py`
  - Invalidate projection cache after review/split/rollback and surface overview metrics endpoint.
- `backend/app/schemas/world_profiles.py`
  - Add `WorldModelDashboardOut` for Overview metrics.
- `frontend/src/api/types.ts`
  - Add subject fields and dashboard types.
- `frontend/src/api/client.ts`
  - Add `getWorldModelDashboard`.
- `frontend/src/stores/worldModel.ts`
  - Add dashboard loading and refresh after review.
- `frontend/src/components/athena/AthenaOverview.vue`
  - New overview panel for profile status, projection count, proposal count, and next action.
- `frontend/src/views/AthenaView.vue`
  - Add overview as the default Athena section.
- Tests:
  - `backend/tests/test_world_proposals.py`
  - `backend/tests/test_world_projection_service.py`
  - `backend/tests/test_world_frontend_api.py`
  - `frontend/src/stores/worldModel.test.ts`
  - `frontend/src/components/athena/AthenaOverview.test.ts`
  - `frontend/e2e/athena-world-model.spec.ts`

## Stage 1: Subject Cognition Persistence

- [ ] Write a failing backend test that approves a proposal with `claim_layer="belief"`, `perspective_ref="char.detective"`, and `disclosed_to_refs=[]`, then asserts `/world-model/subject-knowledge?subject_ref=char.detective` returns the belief value while `/world-model` truth does not.
- [ ] Run targeted pytest and confirm the failure is caused by missing schema/model fields.
- [ ] Add Alembic migration and ORM/schema fields for fact claims and proposal items.
- [ ] Copy fields through `write_candidate_fact`, `_get_item_snapshot`, approve, split, and `fact_record_from_model`.
- [ ] Run targeted pytest:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_world_proposals.py tests/test_world_projection_service.py tests/test_world_frontend_api.py
```

- [ ] Commit: `feat: persist world subject knowledge fields`.

## Stage 2: Local Projection Cache

- [ ] Write failing service tests that call the same projection twice and assert the second call reuses cached source/projection, then invalidates after review/import/analyze hooks.
- [ ] Implement a module-local cache in `world_projection_service.py` keyed by `project_id`, `profile.id`, `profile.version`, `view_type`, `subject_ref`, and `chapter_index`.
- [ ] Add `invalidate_world_projection_cache(project_id: str)` and call it only after writes that can change projection results.
- [ ] Keep cache process-local and conservative. Any uncertainty should invalidate, not try to diff.
- [ ] Run targeted pytest:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_world_projection_service.py tests/test_world_frontend_api.py tests/test_athena_longform.py
```

- [ ] Commit: `perf: cache local world projections`.

## Stage 3: Athena Overview Workbench

- [ ] Write failing frontend tests for `worldModel.loadDashboard()` and `AthenaOverview.vue`.
- [ ] Add backend dashboard endpoint returning profile status, entity/fact/presence/event counts, pending proposal counts, and next action.
- [ ] Add frontend API/store types and a compact overview component.
- [ ] Make Athena default section `overview`; keep direct `/athena/projection` etc. unchanged.
- [ ] Run targeted tests and build:

```bash
cd frontend
npm run test:unit -- src/stores/worldModel.test.ts src/components/athena/AthenaOverview.test.ts
npm run build
```

- [ ] Commit: `feat: add Athena world overview`.

## Stage 4: E2E And Final Gate

- [ ] Extend Athena E2E to land on Overview, verify next action, open projection, review a proposal, and confirm Overview counts refresh.
- [ ] Run:

```bash
RUN_E2E=1 scripts/verify_local_quality.sh
```

- [ ] Commit: `test: extend Athena overview e2e`.
- [ ] Fast-forward merge back to `main`, remove worktree and feature branch.

## Self-Review

- No external services or distributed cache are introduced.
- Each stage has a concrete test gate and commit.
- Subject knowledge persistence is schema-backed instead of UI-only.
- Cache invalidation is conservative and tied to existing write paths.
- Overview is a small operational panel, not a landing page or marketing surface.
