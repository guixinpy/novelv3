# Athena World Model Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate Athena/world-model architecture for local long-running use by unifying context assembly, adding incremental retrieval indexing, tightening proposal workflow boundaries, adding Setup import preview, and splitting Athena frontend loading responsibilities.

**Architecture:** Keep FastAPI + SQLAlchemy + SQLite and Vue 3 + Pinia. Add small local modules with explicit interfaces; do not add external services, workers, Redis, or vector DBs. Each stage is independently testable and committed before the next stage.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic-free service changes, pytest, Vue 3, Pinia, Vitest, Playwright.

---

## Stage Gates

- Stage 0: create isolated worktree and run `scripts/verify_local_quality.sh`.
- Stage 1: unified context assembler. Targeted `pytest tests/test_athena_dialog.py tests/test_athena_retrieval.py tests/test_prompting_dialog_migration.py`.
- Stage 2: incremental retrieval sync. Targeted `pytest tests/test_athena_retrieval.py tests/test_world_frontend_api.py tests/test_world_proposals.py`.
- Stage 3: proposal boundary and Setup import preview. Targeted backend API/service tests.
- Stage 4: frontend Athena shell split and lane state. Targeted Vitest plus E2E.
- Stage 5: `RUN_E2E=1 scripts/verify_local_quality.sh`, fast-forward merge to `main`, cleanup.

## Stage 1: Unified World Context Assembler

- [ ] Write failing pytest asserting `build_athena_world_context_blocks()`, `build_athena_world_context()`, and `build_chapter_context_package()` share canonical fact/entity/event ordering and include retrieval evidence.
- [ ] Create `backend/app/core/world_context_assembler.py` with `WorldContextAssembler`, `build_dialog_context_blocks()`, `build_dialog_context_text()`, and `build_chapter_context_package()`.
- [ ] Refactor `backend/app/core/context_injection.py` to delegate to assembler without changing public function signatures.
- [ ] Refactor `backend/app/core/athena_longform.py` chapter context path to delegate to assembler.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_athena_dialog.py tests/test_athena_retrieval.py tests/test_prompting_dialog_migration.py`.
- [ ] Commit `refactor: unify Athena world context assembly`.

## Stage 2: Incremental Retrieval Sync

- [ ] Write failing pytest proving approval of a world proposal creates a searchable `world_fact` retrieval document without full reindex.
- [ ] Write failing pytest proving rollback deletes the corresponding fact retrieval document.
- [ ] Add `sync_fact_retrieval_document()` and `delete_fact_retrieval_document()` in `backend/app/core/athena_retrieval.py`.
- [ ] Limit `search_retrieval()` candidate rows before vector scoring with stable ordering and source filters.
- [ ] Call fact sync after successful approval and fact delete after successful rollback in `backend/app/core/world_proposal_service.py`.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_athena_retrieval.py tests/test_world_frontend_api.py tests/test_world_proposals.py`.
- [ ] Commit `perf: sync world fact retrieval index incrementally`.

## Stage 3: Proposal Boundary And Setup Preview

- [ ] Write failing pytest for Setup import preview: project without world-model returns candidate counts and names without creating DB rows.
- [ ] Create `backend/app/core/world_proposal_state.py` and move status constants/transition checks out of `world_proposal_service.py`.
- [ ] Create `backend/app/core/world_proposal_records.py` and move proposal item/fact payload copy logic out of `world_proposal_service.py`.
- [ ] Add `preview_setup_import_to_world_model()` in `backend/app/core/athena_longform.py`.
- [ ] Add `GET /api/v1/projects/{project_id}/athena/ontology/import-setup/preview`.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_athena_longform.py tests/test_world_proposals.py tests/test_world_frontend_api.py`.
- [ ] Commit `refactor: tighten world proposal workflow boundaries`.

## Stage 4: Athena Frontend Shell And Lanes

- [ ] Write failing Vitest for `AthenaSubnav.vue` rendering all sections and emitting import/analyze/chat actions.
- [ ] Write failing Vitest for lane loading/error: dashboard loading does not mark proposal workbench as loading.
- [ ] Create `frontend/src/components/athena/AthenaSubnav.vue`.
- [ ] Create `frontend/src/composables/useAthenaSectionLoader.ts` and move `loadSectionData()` logic out of `AthenaView.vue`.
- [ ] Add lane loading/error state in `frontend/src/stores/worldModel.ts` while preserving existing `loading`/`error` compatibility.
- [ ] Add import preview API wiring and Overview preview display.
- [ ] Run `cd frontend && npm run test:unit -- src/stores/worldModel.test.ts src/views/AthenaView.test.ts src/components/athena/AthenaSubnav.test.ts src/components/athena/AthenaOverview.test.ts && npm run build`.
- [ ] Commit `refactor: split Athena shell loading boundaries`.

## Stage 5: E2E And Merge

- [ ] Extend `frontend/e2e/athena-world-model.spec.ts` to cover Setup import preview, UI import, proposal review, retrieval search, and projection.
- [ ] Run `RUN_E2E=1 scripts/verify_local_quality.sh`.
- [ ] Commit `test: cover Athena hardening e2e`.
- [ ] Fast-forward merge to `main`, remove worktree and feature branch, verify `git status`.

## Self-Review

- This plan stays local-only and does not introduce infrastructure.
- Each stage is testable and can be committed independently.
- The largest risk is context drift; Stage 1 pins shared ordering and content.
- The frontend work is boundary refactor plus preview display, not a visual redesign.
