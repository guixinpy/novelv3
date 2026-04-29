#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="${E2E_BACKEND_PORT:-}"
BACKEND_PID=""
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/novelv3-e2e.XXXXXX")"
BACKEND_LOG="$TEMP_DIR/backend.log"
DB_PATH="$TEMP_DIR/mozhou.db"
export MOZHOU_DATABASE_URL="sqlite:///$DB_PATH"

cleanup() {
  set +e
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT INT TERM

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing command: $1" >&2
    exit 1
  fi
}

pick_free_port() {
  python3 - <<'PY'
import socket

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
}

wait_for_http() {
  local url="$1"
  local attempts="${2:-60}"
  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Timed out waiting for $url" >&2
  echo "Backend log: $BACKEND_LOG" >&2
  cat "$BACKEND_LOG" >&2 || true
  return 1
}

section() {
  printf '\n== %s ==\n' "$1"
}

require_command curl
require_command python3
require_command npm
require_command google-chrome

if [[ ! -f "$BACKEND_DIR/.venv/bin/activate" ]]; then
  echo "Missing backend/.venv. Run backend dependency setup first." >&2
  exit 1
fi
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Missing frontend/node_modules. Run frontend dependency setup first." >&2
  exit 1
fi

BACKEND_PORT="${BACKEND_PORT:-$(pick_free_port)}"
E2E_BASE_URL="http://$BACKEND_HOST:$BACKEND_PORT"
export E2E_BASE_URL
mkdir -p "$ROOT_DIR/.tmp"

section "Alembic temporary database"
(
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  alembic upgrade head
)

section "Frontend build"
(
  cd "$FRONTEND_DIR"
  npm run build
)

section "Start backend"
(
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) >"$BACKEND_LOG" 2>&1 &
BACKEND_PID="$!"
wait_for_http "$E2E_BASE_URL/api/v1/health"

section "Playwright E2E"
(
  cd "$FRONTEND_DIR"
  npm run test:e2e
)
