# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Mozhou AI Writer — FastAPI backend + Vue 3 frontend. Dual-package monorepo with no workspace tool.

## Build & Test

Backend (from `backend/`):
```bash
uvicorn app.main:app --reload --port 8000
pytest
alembic upgrade head
```

Frontend (from `frontend/`):
```bash
npm run dev        # Vite dev server, proxies /api to :8000
npm run build      # vue-tsc --noEmit && vite build → writes to ../backend/static/
npm run test:unit  # vitest run
```

**Important:** `npm run build` writes the SPA bundle to `backend/static/`, which FastAPI serves with SPA fallback. Rebuild after frontend changes before the backend can serve them.

## Code Style

- **Python:** 4-space indent, `snake_case`, type hints encouraged, `__init__.py` in every package.
- **TypeScript:** Strict mode (`noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`).
- **Vue:** PascalCase `.vue` filenames, `<script setup lang="ts">`, Tailwind utility classes from `frontend/src/style.css`.
- **No formatter configured** — match surrounding formatting exactly. Do not add Prettier/black configs unless explicitly asked.
- **Linting:** Python uses ruff (`backend/ruff.toml`), frontend uses ESLint 10 (`frontend/eslint.config.js`). New code must pass both linters.

## Testing

Backend tests use pytest with shared fixtures in `backend/tests/conftest.py`. Name new tests `test_<feature>.py`.
Frontend uses vitest — run `npm run test:unit` in `frontend/`.

## Database

SQLite (`data/mozhou.db`), foreign keys enabled. Alembic uses a relative path from inside `backend/alembic.ini`, so run migrations from the `backend/` directory.

## API Key Resolution

`DEEPSEEK_API_KEY` is read from (1) env var, (2) system keyring, (3) `.env` file. The `.env` file is committed.

## Branching

Feature branches from `main`, PR merge back to `main`. Branch naming: `feature/<name>`, `fix/<name>`, `wip/<name>`.

## Commit Style

Conventional Commits: `feat:`, `fix:`, `chore:`, `test:`, `docs:`. Keep subjects short and scoped to one change.

## PR Guidelines

State the problem, main files changed, and verification commands. Include screenshots for UI changes. Call out schema, migration, or API contract changes explicitly.

## Verification

Before marking work complete, run the full verification: pytest (backend), vitest (frontend), vue-tsc type check, and `npm run build`. Use `/verify` to run all at once. For UI changes, also verify in browser.

## Gotchas

- Do not hand-edit `backend/static/` — rebuild from `frontend/` instead.
- Do not commit `data/mozhou.db`.
- SQLite engine uses `check_same_thread=False`.
