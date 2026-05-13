# Athena World Model P1/P2 Optimization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete remaining Athena/world-model P1/P2 improvements for local use without external infrastructure.

**Architecture:** Keep FastAPI + SQLAlchemy + SQLite and Vue 3 + Pinia. Prefer small deterministic service modules, compatibility facades, and targeted tests over broad framework changes.

---

## Stage Gates

- Stage 0: isolated worktree and baseline quality check.
- Stage 1: retrieval recall and context diagnostics.
- Stage 2: local extraction depth for chapters and Setup import.
- Stage 3: proposal approval side-effect boundary.
- Stage 4: Athena backend API module split.
- Stage 5: Athena frontend store split and creator-facing retrieval/projection UI.
- Stage 6: E2E and full local quality gate, then merge cleanup.

## Stage 0: Worktree And Baseline

- [ ] Create worktree `refactor/athena-p1-p2-optimization`.
- [ ] Reuse local backend venv and frontend node_modules through symlinks.
- [ ] Run baseline:

```bash
scripts/verify_local_quality.sh
```

## Stage 1: Retrieval Recall And Context Diagnostics

- [ ] Write failing pytest proving a relevant late chunk beyond the old first-candidate window is returned by `search_retrieval()`.
- [ ] Write failing pytest proving `WorldContextAssembler` exposes a retrieval warning when retrieval context fails without breaking prompt generation.
- [ ] Implement lexical shortlist + fallback candidate selection in `backend/app/core/athena_retrieval.py`.
- [ ] Replace silent retrieval exception swallowing with structured warning context in `backend/app/core/world_context_assembler.py`.
- [ ] Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_athena_retrieval.py tests/test_athena_dialog.py
```

- [ ] Commit `perf: improve Athena retrieval recall`.

## Stage 2: Chapter And Setup Extraction

- [ ] Write failing pytest for unquoted Setup terms appearing in preview and import candidates.
- [ ] Write failing pytest for chapter analysis producing event and character-location proposal candidates.
- [ ] Add shared Setup term extraction helpers in `backend/app/core/athena_longform.py`.
- [ ] Extend deterministic chapter extraction without directly confirming facts.
- [ ] Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_athena_longform.py tests/test_world_proposals.py
```

- [ ] Commit `feat: deepen local Athena extraction`.

## Stage 3: Proposal Approval Index Boundary

- [ ] Write failing pytest where `sync_fact_retrieval_document()` raises but proposal approval still persists the confirmed fact.
- [ ] Move retrieval sync after the core approval commit and make it best-effort with logging.
- [ ] Keep successful sync immediate for local search.
- [ ] Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_world_proposals.py tests/test_athena_retrieval.py
```

- [ ] Commit `fix: isolate proposal approval from retrieval sync`.

## Stage 4: Backend Athena API Split

- [ ] Write route compatibility tests for retrieval, ontology import preview, projection, proposals, dialog, and optimization paths.
- [ ] Split `backend/app/api/athena.py` into small routers while keeping the same external paths.
- [ ] Keep shared dependencies/helpers in private modules, not duplicated across routers.
- [ ] Run:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_world_frontend_api.py tests/test_athena_retrieval.py tests/test_athena_longform.py tests/test_athena_dialog.py tests/test_self_optimization.py
```

- [ ] Commit `refactor: split Athena API routers`.

## Stage 5: Frontend Store Split And Creator UI

- [ ] Write failing Vitest for the compatibility facade `useAthenaStore()` and focused retrieval/proposal actions.
- [ ] Write failing Vitest for RetrievalPanel creator-facing grouping and ProjectionViewer grouped display.
- [ ] Split Athena store internals while keeping existing component imports compatible.
- [ ] Improve RetrievalPanel and ProjectionViewer copy/layout without adding marketing-style UI.
- [ ] Run:

```bash
cd frontend
npm run test:unit -- src/stores/athena.retrieval.test.ts src/stores/athena.proposals.test.ts src/components/athena/RetrievalPanel.test.ts src/components/athena/ProjectionViewer.test.ts
npm run build
```

- [ ] Commit `refactor: focus Athena frontend modules`.

## Stage 6: E2E And Final Quality Gate

- [ ] Extend Athena E2E to cover retrieval search, projection grouping, proposal review, and setup import preview path.
- [ ] Run:

```bash
RUN_E2E=1 scripts/verify_local_quality.sh
```

- [ ] Fast-forward merge back to `main`.
- [ ] Remove worktree and feature branch after merge.
- [ ] Verify `git status --short --branch`.

## Self-Review

- No external infrastructure.
- All behavior changes have targeted tests before implementation.
- Route/store compatibility is preserved for existing callers.
- New extraction remains proposal-based, not auto-confirmed.
