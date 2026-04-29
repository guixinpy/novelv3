#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

section() {
  printf '\n== %s ==\n' "$1"
}

section "Backend pytest"
if [[ ! -f "$ROOT_DIR/backend/.venv/bin/activate" ]]; then
  echo "Missing backend/.venv. Run: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi
(
  cd "$ROOT_DIR/backend"
  source .venv/bin/activate
  pytest
)

section "Frontend unit tests"
if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Missing frontend/node_modules. Run: cd frontend && npm install" >&2
  exit 1
fi
(
  cd "$ROOT_DIR/frontend"
  npm run test:unit
)

section "Frontend build"
(
  cd "$ROOT_DIR/frontend"
  npm run build
)

section "Workspace perf smoke"
if [[ -n "${PERF_SMOKE_BASE_URL:-}" && -n "${PERF_SMOKE_PROJECT_ID:-}" && -n "${PERF_SMOKE_SESSION:-}" ]]; then
  node "$ROOT_DIR/scripts/workspace_perf_smoke.mjs" \
    --base-url "$PERF_SMOKE_BASE_URL" \
    --project-id "$PERF_SMOKE_PROJECT_ID" \
    --session "$PERF_SMOKE_SESSION"
else
  echo "Skipped: set PERF_SMOKE_BASE_URL, PERF_SMOKE_PROJECT_ID, and PERF_SMOKE_SESSION to enable."
fi
