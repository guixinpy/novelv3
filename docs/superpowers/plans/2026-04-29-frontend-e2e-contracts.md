# Frontend E2E Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable local Playwright E2E coverage for the core frontend journeys without making UI maintenance brittle.

**Architecture:** Keep `verify_local_quality.sh` fast by default and add a separate E2E gate that starts FastAPI against a temporary SQLite database. Playwright tests use `data-testid`, API/network assertions, console/page-error capture, and critical workflow contracts rather than CSS selectors or visual layout assumptions.

**Tech Stack:** Vue 3, Vite, Pinia, FastAPI, SQLite, Alembic, Playwright, shell scripts, pytest, Vitest.

---

## Delivery Rules

- Do not depend on real model success; missing API key failure states are valid test contracts.
- Do not use long blind sleeps; wait for URL, test ids, API responses, or explicit task states.
- Do not add CI, Docker, Redis, PostgreSQL, or remote services.
- Each phase must pass its focused test before moving on.
- Commit each phase separately.

## Phase 0: E2E Infrastructure Contracts

**Files:**

- Create: `backend/app/core/database_url.py`
- Modify: `backend/app/db.py`
- Modify: `backend/alembic/env.py`
- Test: `backend/tests/test_database_url.py`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/playwright.config.ts`
- Create: `scripts/verify_frontend_e2e.sh`
- Modify: `scripts/verify_local_quality.sh`

### Task 0.1: Write failing backend env database URL tests

- [ ] Create `backend/tests/test_database_url.py`.
- [ ] Add tests:

```python
from pathlib import Path

from app.core.database_url import database_url, ensure_sqlite_parent_dir


def test_database_url_uses_env_override(monkeypatch):
    monkeypatch.setenv("MOZHOU_DATABASE_URL", "sqlite:////tmp/novelv3-e2e/mozhou.db")

    assert database_url().endswith("/tmp/novelv3-e2e/mozhou.db")


def test_database_url_defaults_to_local_data(monkeypatch):
    monkeypatch.delenv("MOZHOU_DATABASE_URL", raising=False)

    assert database_url().endswith("/data/mozhou.db")


def test_ensure_sqlite_parent_dir_creates_parent(tmp_path):
    db_path = tmp_path / "nested" / "mozhou.db"
    ensure_sqlite_parent_dir(f"sqlite:///{db_path}")

    assert db_path.parent.exists()
```

- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_database_url.py -q`.
- [ ] Expected: fail because `app.core.database_url` does not exist.

### Task 0.2: Implement DB URL override

- [ ] Create `backend/app/core/database_url.py` with:

```python
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'data' / 'mozhou.db'}"


def database_url() -> str:
    return os.getenv("MOZHOU_DATABASE_URL") or DEFAULT_DATABASE_URL


def ensure_sqlite_parent_dir(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    raw_path = url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return
    Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
```

- [ ] Modify `backend/app/db.py` to use `database_url()` and `ensure_sqlite_parent_dir()`.
- [ ] Modify `backend/alembic/env.py` to override `sqlalchemy.url` from `MOZHOU_DATABASE_URL` when present.
- [ ] Run `cd backend && source .venv/bin/activate && pytest tests/test_database_url.py -q`.
- [ ] Expected: pass.

### Task 0.3: Add Playwright dependency and config

- [ ] Run `cd frontend && npm install -D @playwright/test`.
- [ ] Add `test:e2e` script:

```json
"test:e2e": "playwright test"
```

- [ ] Create `frontend/playwright.config.ts`:

```ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 7_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: '../.tmp/playwright-results.json' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
```

- [ ] Run `cd frontend && npm run test:e2e`.
- [ ] Expected: fails with "No tests found".

### Task 0.4: Add E2E verification script

- [ ] Create `scripts/verify_frontend_e2e.sh`.
- [ ] Script must:
  - require `curl`, `python3`, `npm`;
  - create temp dir and temp SQLite URL;
  - run Alembic with `MOZHOU_DATABASE_URL`;
  - run `npm run build`;
  - start backend on a free port with `MOZHOU_DATABASE_URL`;
  - run `E2E_BASE_URL=http://127.0.0.1:$PORT npm run test:e2e`;
  - kill backend and remove temp dir on exit.
- [ ] Modify `scripts/verify_local_quality.sh` so `RUN_E2E=1` runs the new script after existing checks.
- [ ] Run `scripts/verify_frontend_e2e.sh`.
- [ ] Expected: reaches Playwright and fails only because no tests exist.
- [ ] Commit: `test: add frontend e2e harness`.

## Phase 1: Stable UI Test IDs

**Files:**

- Modify: `frontend/src/views/ProjectListView.vue`
- Modify: `frontend/src/views/HermesView.vue`
- Modify: `frontend/src/views/AthenaView.vue`
- Modify: `frontend/src/views/ManuscriptView.vue`
- Modify: `frontend/src/components/layout/ActivityBar.vue`
- Modify: `frontend/src/components/chat/ChatInput.vue`
- Modify: `frontend/src/components/chat/ActionCard.vue`
- Test: `frontend/src/views/ProjectListView.test.ts`
- Test: `frontend/src/components/layout/ActivityBar.test.ts`

### Task 1.1: Write failing component tests for stable test ids

- [ ] Add assertions that ProjectListView exposes `project-create-button`, `project-create-modal`, `project-name-input`, and `project-create-submit`.
- [ ] Add assertions that ActivityBar exposes `workspace-nav-hermes`, `workspace-nav-athena`, `workspace-nav-manuscript`.
- [ ] Run `cd frontend && npm run test:unit -- src/views/ProjectListView.test.ts src/components/layout/ActivityBar.test.ts`.
- [ ] Expected: fail because test ids are missing.

### Task 1.2: Add stable test ids

- [ ] Add:
  - `data-testid="project-create-button"`
  - `data-testid="project-create-modal"`
  - `data-testid="project-name-input"`
  - `data-testid="project-create-submit"`
  - `data-testid="workspace-hermes"`
  - `data-testid="workspace-athena"`
  - `data-testid="workspace-manuscript"`
  - `data-testid="workspace-nav-hermes"`
  - `data-testid="workspace-nav-athena"`
  - `data-testid="workspace-nav-manuscript"`
  - `data-testid="chat-input"`
  - `data-testid="chat-send"`
  - `data-testid="pending-action-card"`
  - `data-testid="pending-action-confirm"`
- [ ] Run the focused frontend unit tests again.
- [ ] Expected: pass.
- [ ] Commit: `test: add stable e2e selectors`.

## Phase 2: Core Playwright Journeys

**Files:**

- Create: `frontend/e2e/helpers.ts`
- Create: `frontend/e2e/project-workspaces.spec.ts`
- Create: `frontend/e2e/hermes-action.spec.ts`

### Task 2.1: Write Playwright helpers

- [ ] Create helpers that:
  - collect console errors;
  - collect page errors;
  - collect `/api/` responses with status >= 400;
  - create a project through the UI;
  - delete a project through API cleanup when possible.
- [ ] Add `expectNoBrowserErrors()` helper that throws with collected details.

### Task 2.2: Add project creation and workspace switching E2E

- [ ] Test creates a project from `/`.
- [ ] Test verifies Hermes workspace loads.
- [ ] Test clicks Athena and Manuscript workspace nav.
- [ ] Test verifies URL and workspace test id for each module.
- [ ] Test asserts no browser errors.
- [ ] Run `scripts/verify_frontend_e2e.sh`.
- [ ] Expected: this journey passes.

### Task 2.3: Add workspace request-budget E2E

- [ ] Test instruments `window.fetch`.
- [ ] Test navigates Hermes -> Athena -> Hermes and rapid switches.
- [ ] Test asserts request counts:
  - cold Hermes <= 1;
  - Hermes -> Athena <= 2;
  - Athena -> Hermes <= 1;
  - rapid switch <= 8.
- [ ] Test asserts no duplicate URL storm within each phase.
- [ ] Run `scripts/verify_frontend_e2e.sh`.
- [ ] Expected: request-budget journey passes.

### Task 2.4: Add Hermes action task E2E

- [ ] Test creates a project.
- [ ] Test enters `/setup 主角是植物学家`.
- [ ] Test waits for `pending-action-card`.
- [ ] Test confirms pending action.
- [ ] Test waits for either a failed task message with API key missing or a completed task message if the local machine has an API key.
- [ ] Test asserts chat input becomes enabled again.
- [ ] Test asserts no page freeze and no browser errors.
- [ ] Run `scripts/verify_frontend_e2e.sh`.
- [ ] Expected: action task journey passes in no-API-key local environment.
- [ ] Commit: `test: cover core frontend e2e journeys`.

## Phase 3: Quality Gate Integration And Legacy Script Cleanup

**Files:**

- Modify: `scripts/verify_local_quality.sh`
- Modify: `scripts/verify_full_app_ui.sh` or add deprecation note if it remains.
- Modify: `docs/superpowers/README.md`

### Task 3.1: Verify full local quality with optional E2E

- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Expected: backend pytest, frontend unit tests, frontend build pass; E2E skipped by default.
- [ ] Run `RUN_E2E=1 scripts/verify_local_quality.sh`.
- [ ] Expected: default gate plus Playwright E2E pass.

### Task 3.2: Mark old full UI script as legacy

- [ ] If `scripts/verify_full_app_ui.sh` is still needed for prior manual checks, add a top comment saying it is legacy and new coverage belongs in Playwright E2E.
- [ ] Do not expand the legacy script.
- [ ] Commit: `test: wire frontend e2e quality gate`.

## Final Verification

- [ ] Run `scripts/verify_local_quality.sh`.
- [ ] Run `RUN_E2E=1 scripts/verify_local_quality.sh`.
- [ ] Run `git status --short`.
- [ ] Confirm no backend server remains running from the E2E script.
