# Local Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the local single-user architecture into stable service boundaries, a unified SQLite-backed task lifecycle, and predictable workspace state without adding external infrastructure.

**Architecture:** Keep external FastAPI routes and Vue workflows compatible while moving orchestration out of oversized API modules into focused services. Use the existing SQLite database and `background_tasks` table as the local task source of truth, with an in-process runner and explicit test gates after every stage.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, pytest, Vue 3, Pinia, Vite, Vitest, agent-browser, shell scripts.

---

## Delivery Rules

- Each phase must leave the app runnable.
- Each phase must have a focused test command and a full gate command.
- Do not introduce PostgreSQL, Redis, Celery, MQ, microservices, or remote observability.
- Keep API paths stable unless a phase explicitly adds a backwards-compatible field.
- Prefer service extraction before behavior change.
- Stop if focused tests, full tests, build, browser smoke, or workspace perf smoke regresses.
- Commit each completed phase separately.

## Phase 0: Baseline And Local Verification Gate

**Purpose:** Make the refactor measurable before touching behavior.

**Files:**

- Create: `scripts/verify_local_quality.sh`
- Modify: none outside scripts unless existing commands fail for environmental reasons.

### Task 0.1: Add local quality gate script

- [ ] Create `scripts/verify_local_quality.sh`.
- [ ] Script behavior:
  - run backend pytest;
  - run frontend vitest;
  - run frontend production build;
  - optionally run workspace perf smoke when `PERF_SMOKE_BASE_URL`, `PERF_SMOKE_PROJECT_ID`, and `PERF_SMOKE_SESSION` are set.
- [ ] Make it executable.
- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Expected: backend tests pass, frontend tests pass, frontend build passes, perf smoke is skipped if env vars are absent.
- [ ] Commit: `test: add local quality gate`.

### Task 0.2: Record baseline

- [ ] Run `git status --short`.
- [ ] Run `cd backend && source .venv/bin/activate && pytest`.
- [ ] Run `cd frontend && npm run test:unit`.
- [ ] Run `cd frontend && npm run build`.
- [ ] If local servers are available, run `node scripts/workspace_perf_smoke.mjs --base-url "$PERF_SMOKE_BASE_URL" --project-id "$PERF_SMOKE_PROJECT_ID" --session "$PERF_SMOKE_SESSION"`.
- [ ] Expected: no failures before service extraction begins.

## Phase 1: Service Layer Skeleton And Workspace Read Path

**Purpose:** Establish service boundaries using low-risk read paths before moving write/action behavior.

**Files:**

- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/workspace/__init__.py`
- Create: `backend/app/services/workspace/bootstrap.py`
- Create: `backend/app/services/dialog/__init__.py`
- Create: `backend/app/services/dialog/messages.py`
- Modify: `backend/app/api/projects.py`
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/api/athena.py`
- Test: `backend/tests/test_workspace_bootstrap.py`
- Test: `backend/tests/test_dialog_messages_pagination.py`
- Test: `backend/tests/test_athena_dialog.py`

### Task 1.1: Extract workspace bootstrap read model

- [ ] Move bootstrap assembly from API code into `WorkspaceBootstrapService`.
- [ ] Keep `GET /api/v1/projects/{project_id}/workspace-bootstrap` response shape unchanged.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_workspace_bootstrap.py -q`.
- [ ] Expected: all workspace bootstrap tests pass.

### Task 1.2: Extract dialog message pagination

- [ ] Move message query and `limit/after_id/before_id` handling into `DialogMessageService`.
- [ ] Keep Hermes and Athena message endpoints compatible.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_dialog_messages_pagination.py tests/test_athena_dialog.py -q`.
- [ ] Expected: all dialog pagination and Athena dialog tests pass.

### Task 1.3: Full phase gate

- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Run workspace perf smoke when env vars are available.
- [ ] Expected: no regression in request count compared with the previous committed baseline.
- [ ] Commit: `refactor: extract workspace read services`.

## Phase 2: Unified Local Task Lifecycle

**Purpose:** Make background tasks reliable and queryable before migrating more actions.

**Files:**

- Create: `backend/app/services/tasks/__init__.py`
- Create: `backend/app/services/tasks/background_task_service.py`
- Create: `backend/app/services/tasks/local_task_runner.py`
- Modify: `backend/app/api/background_tasks_api.py`
- Modify: `backend/app/api/consistency.py`
- Test: `backend/tests/test_background.py`
- Test: `backend/tests/test_consistency.py`

### Task 2.1: Implement BackgroundTaskService

- [ ] Add constants for valid statuses: `pending`, `running`, `completed`, `failed`, `cancelled`.
- [ ] Add methods: `create`, `mark_running`, `mark_completed`, `mark_failed`, `mark_cancelled`, `get`, `list_for_project`, `fail_interrupted_running_tasks`.
- [ ] Ensure every state write commits or flushes through the caller-owned session.
- [ ] Add tests for success, failure, cancellation, and interrupted running task recovery.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_background.py -q`.
- [ ] Expected: background task tests pass.

### Task 2.2: Implement LocalTaskRunner

- [ ] Add in-process async runner with an independent DB session per task.
- [ ] Runner must mark task running before work, completed with result on success, failed with error on exception.
- [ ] Runner must not swallow task persistence errors silently.
- [ ] Add focused tests using a tiny async function and a failing async function.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_background.py -q`.
- [ ] Expected: runner tests pass.

### Task 2.3: Migrate consistency deep check

- [ ] Replace direct `asyncio.ensure_future` logic in `backend/app/api/consistency.py` with `BackgroundTaskService` and `LocalTaskRunner`.
- [ ] Keep response shape `{ "task_id": "...", "status": "pending" }`.
- [ ] Preserve `GET /api/v1/background-tasks/{task_id}` UI hint behavior.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_consistency.py tests/test_background.py -q`.
- [ ] Expected: consistency and task tests pass.

### Task 2.4: Full phase gate

- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Run browser smoke for consistency task if servers are available.
- [ ] Commit: `refactor: unify local background tasks`.

## Phase 3: Persistent Writing Scheduler

**Purpose:** Remove process-local writing state and make writing controls survive scheduler instance recreation.

**Files:**

- Create: `backend/app/services/writing/__init__.py`
- Create: `backend/app/services/writing/writing_state_service.py`
- Modify: `backend/app/core/writing_scheduler.py`
- Modify: `backend/app/api/writing.py`
- Test: `backend/tests/test_writing.py`

### Task 3.1: Add WritingStateService

- [ ] Store writing state in SQLite using the existing local task/state source. Prefer `background_tasks` only if the state naturally maps to task lifecycle; otherwise add a minimal SQLite model with Alembic migration.
- [ ] Preserve response model `WritingStateOut`.
- [ ] Add tests proving a fresh service instance can read prior `start/pause/resume` state.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_writing.py -q`.
- [ ] Expected: writing state tests pass.

### Task 3.2: Migrate retry chapter execution

- [ ] Replace direct `asyncio.ensure_future` in `retry_chapter` with `LocalTaskRunner`.
- [ ] Return current writing state plus task visibility through background task endpoints.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_writing.py tests/test_background.py -q`.
- [ ] Expected: writing and task tests pass.

### Task 3.3: Full phase gate

- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Commit: `refactor: persist writing scheduler state`.

## Phase 4: Action Pipeline Refactor

**Purpose:** Make Hermes action proposal, resolution, execution, task status, and UI refresh deterministic.

**Files:**

- Create: `backend/app/services/actions/__init__.py`
- Create: `backend/app/services/actions/action_execution_service.py`
- Create: `backend/app/services/actions/action_result_service.py`
- Create: `backend/app/services/actions/action_proposal_service.py`
- Create: `backend/app/services/actions/refresh_targets.py`
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/core/ui_hints.py`
- Test: `backend/tests/test_dialogs.py`
- Test: `backend/tests/test_prompting_generation_migration.py`
- Test: `frontend/src/views/hermesActionReplay.test.ts`
- Test: `frontend/src/stores/chat.workspace.test.ts`

### Task 4.1: Extract action execution

- [ ] Move generate setup/storyline/outline/chapter execution from `dialogs.py` into `ActionExecutionService`.
- [ ] Preserve trace linking behavior.
- [ ] Preserve action result payload fields: `type`, `status`, `data`, `trace_id` when available.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_dialogs.py tests/test_prompting_generation_migration.py -q`.
- [ ] Expected: dialog and generation migration tests pass.

### Task 4.2: Run actions through local tasks

- [ ] `resolve-action` confirm path creates a `BackgroundTask`.
- [ ] `LocalTaskRunner` executes the action.
- [ ] `ActionResultService` writes the final system message.
- [ ] Response remains backwards compatible and may include `task_id`.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_dialogs.py tests/test_background.py -q`.
- [ ] Expected: confirm/cancel/revise paths still pass.

### Task 4.3: Full phase gate

- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Run browser smoke for Hermes action confirm when local AI key is available.
- [ ] Commit: `refactor: formalize hermes action pipeline`.

## Phase 5: Frontend Workspace State Convergence

**Purpose:** Keep Hermes, Athena, and Manuscript fast and predictable after backend refactor.

**Files:**

- Modify: `frontend/src/stores/projectWorkspace.ts`
- Modify: `frontend/src/stores/requestCache.ts`
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/stores/athena.ts`
- Modify: `frontend/src/stores/manuscript.ts`
- Modify: `frontend/src/views/HermesView.vue`
- Modify: `frontend/src/views/AthenaView.vue`
- Modify: `frontend/src/views/ManuscriptView.vue`
- Test: `frontend/src/stores/projectWorkspace.test.ts`
- Test: `frontend/src/stores/requestCache.test.ts`
- Test: `frontend/src/stores/chat.workspace.test.ts`
- Test: `frontend/src/stores/athena.chat.test.ts`
- Test: `frontend/src/stores/manuscript.test.ts`

### Task 5.1: Normalize refresh target consumption

- [ ] Route all backend `refresh_targets` through `projectWorkspace.markDirty`.
- [ ] Module stores consume only their own dirty targets.
- [ ] Run `cd frontend && npm run test:unit -- projectWorkspace chat.workspace athena.chat manuscript`.
- [ ] Expected: workspace and module store tests pass.

### Task 5.2: Add task-status driven refresh

- [ ] Add frontend polling helper for a returned `task_id` where the current flow needs it.
- [ ] On task completion, apply backend `refresh_targets`.
- [ ] Do not add global polling.
- [ ] Run focused frontend tests for task completion refresh.
- [ ] Expected: no duplicate refresh when multiple task status responses report the same completed task.

### Task 5.3: Browser performance gate

- [ ] Start backend and frontend locally.
- [ ] Run workspace perf smoke against Hermes/Athena/Manuscript switching.
- [ ] Check console errors with agent-browser.
- [ ] Expected: request counts do not exceed the previous optimized baseline.
- [ ] Commit: `refactor: converge workspace state refresh`.

## Phase 6: API File Slimming

**Purpose:** Finish the structural cleanup after services are stable.

**Files:**

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/api/athena.py`
- Modify: `backend/app/api/world_model.py`
- Modify or create services under `backend/app/services/dialog/`, `backend/app/services/athena/`, `backend/app/services/world/`
- Test: all backend tests.

### Task 6.1: Remove orchestration from dialogs.py

- [ ] Keep only route declarations, dependency injection, HTTP errors, and response shaping in `dialogs.py`.
- [ ] Move helpers that are not route-specific into services.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_dialogs.py tests/test_athena_dialog.py -q`.
- [ ] Expected: dialog tests pass.

### Task 6.2: Remove orchestration from athena.py

- [ ] Move Athena chat/retrieval/optimization orchestration into services.
- [ ] Keep route contracts unchanged.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_athena_dialog.py tests/test_athena_retrieval.py tests/test_self_optimization.py -q`.
- [ ] Expected: Athena tests pass.

### Task 6.3: Remove orchestration from world_model.py

- [ ] Move remaining world proposal orchestration into focused service modules.
- [ ] Keep route contracts unchanged.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_world_proposals.py tests/test_world_frontend_api.py -q`.
- [ ] Expected: world model tests pass.

### Task 6.4: Full phase gate

- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Commit: `refactor: slim api route modules`.

## Phase 7: Local Diagnostics

**Purpose:** Make local failures observable without adding infrastructure.

**Files:**

- Create: `backend/app/core/local_diagnostics.py`
- Modify: `backend/app/main.py`
- Modify: task/action services.
- Test: `backend/tests/test_background.py`
- Test: `backend/tests/test_dialogs.py`

### Task 7.1: Add request and task logging helpers

- [ ] Add a lightweight logging helper that prints structured key-value lines.
- [ ] Add request duration middleware.
- [ ] Add task/action duration logs.
- [ ] Run focused backend tests.
- [ ] Expected: tests pass and logs include `event`, `project_id`, `task_id` or `request_id` when relevant.

### Task 7.2: Add recent-task local debug surface

- [ ] Extend existing background task list response if needed; do not add a complex UI.
- [ ] Ensure failed task errors are visible.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_background.py -q`.
- [ ] Expected: failed task details are queryable.

### Task 7.3: Final gate

- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Run browser smoke for workspace switching.
- [ ] Run browser smoke for one successful or intentionally failed task.
- [ ] Commit: `chore: add local diagnostics`.

## Completion Checklist

- [ ] `scripts/verify_local_quality.sh` passes.
- [ ] Backend full pytest passes.
- [ ] Frontend unit tests pass.
- [ ] Frontend production build passes.
- [ ] Workspace perf smoke passes without request-count regression.
- [ ] Browser console has no unexpected errors.
- [ ] `dialogs.py`, `athena.py`, and `world_model.py` no longer contain primary orchestration logic.
- [ ] Background tasks are the source of truth for local async work.
- [ ] Writing state survives scheduler instance recreation.
- [ ] Hermes action execution is task-backed and UI refresh targets remain stable.
