# Repository Guidelines

## Project Structure & Module Organization
`backend/` contains the FastAPI app, SQLite access, and migrations. Keep routes in `backend/app/api/`, shared logic in `backend/app/core/`, ORM models in `backend/app/models/`, and Pydantic schemas in `backend/app/schemas/`. Put tests in `backend/tests/` and Alembic revisions in `backend/alembic/versions/`.

`frontend/` is a Vue 3 + Vite app. Place reusable UI in `frontend/src/components/`, route pages in `frontend/src/views/`, Pinia stores in `frontend/src/stores/`, router setup in `frontend/src/router/`, and API calls in `frontend/src/api/`. Persistent data lives in `data/`. Product notes and plans live in `docs/`.

## Build, Test, and Development Commands
Backend setup:
`cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

Run the API locally:
`cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`

Run migrations:
`cd backend && source .venv/bin/activate && alembic upgrade head`

Frontend setup and dev server:
`cd frontend && npm install && npm run dev`

Production build:
`cd frontend && npm run build`
This writes the SPA bundle to `backend/static/`, which FastAPI serves.

Backend tests:
`cd backend && source .venv/bin/activate && pytest`

## Coding Style & Naming Conventions
Use 4 spaces in Python, keep type hints on new code, and follow the existing split across `api/`, `models/`, and `schemas/`. Use `snake_case` for modules and functions.

Use TypeScript with `strict` compatibility in the frontend. Vue components and views use PascalCase file names such as `ProjectCard.vue`; stores and helpers use `camelCase` exports. Prefer `<script setup lang="ts">` and existing Tailwind utility patterns in `frontend/src/style.css`. No ESLint or Prettier config is checked in, so match surrounding formatting exactly.

## Testing Guidelines
Backend tests use `pytest` with shared fixtures in `backend/tests/conftest.py`. Name new tests `test_<feature>.py` and add route-level coverage when changing API behavior, persistence, or export logic. No frontend test runner is configured; at minimum, verify `npm run build` after UI changes.

## Commit & Pull Request Guidelines
Follow the repository’s Conventional Commit pattern: `feat: ...`, `fix: ...`, `chore: ...`. Keep subjects short and scoped to one change.

PRs should state the problem, the main files changed, and the commands run to verify the work. Include screenshots or GIFs for UI changes, and call out schema, migration, or API contract changes explicitly.

## Security & Configuration Tips
Store secrets in `.env` or the local keyring via `DEEPSEEK_API_KEY`; do not commit secrets or the generated SQLite database in `data/mozhou.db`. Do not hand-edit files under `backend/static/`; rebuild from `frontend/` instead.
