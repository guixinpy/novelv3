#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_VENV="/home/guixin/project_workspace/novelv3/backend/.venv"
BACKEND_PYTEST="$BACKEND_VENV/bin/pytest"
BACKEND_PYTHON="$BACKEND_VENV/bin/python"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
FRONTEND_HOST="127.0.0.1"
FRONTEND_PORT="5173"
BACKEND_BASE_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
FRONTEND_BASE_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"
AB_SESSION="verify-full-app-ui-$$"

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/verify-full-app-ui.XXXXXX")"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
AGENT_BROWSER_ERRORS_JSON="$LOG_DIR/agent-browser-errors.json"
AGENT_BROWSER_CONSOLE_JSON="$LOG_DIR/agent-browser-console.json"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  set +e
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null
    wait "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
  if command -v agent-browser >/dev/null 2>&1; then
    agent-browser --session "${AB_SESSION}" close >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1" >&2
    exit 1
  fi
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local attempts="${3:-60}"

  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "${name} 启动失败，${attempts}s 内未就绪: ${url}" >&2
  return 1
}

get_or_create_project_id() {
  local projects_json
  local project_id

  projects_json="$(curl -fsS "${BACKEND_BASE_URL}/api/v1/projects")"
  project_id="$(python3 - "${projects_json}" <<'PY'
import json
import sys

data = json.loads(sys.argv[1] if len(sys.argv) > 1 else "[]")
if isinstance(data, list) and data:
    first = data[0]
    pid = first.get("id") if isinstance(first, dict) else None
    if pid:
        print(pid)
PY
)"

  if [[ -n "${project_id}" ]]; then
    echo "${project_id}"
    return 0
  fi

  project_id="$(curl -fsS \
    -H 'Content-Type: application/json' \
    -X POST \
    -d '{"name":"UI Regression Auto Project"}' \
    "${BACKEND_BASE_URL}/api/v1/projects" | python3 -c '
import json
import sys

data = json.loads(sys.stdin.read())
pid = data.get("id")
if not pid:
    raise SystemExit("创建项目失败：返回中没有 id")
print(pid)
')"

  echo "${project_id}"
}

run() {
  echo "==> $*"
  "$@"
}

require_command curl
require_command python3
require_command npm
require_command agent-browser

if [[ ! -x "${BACKEND_PYTEST}" ]]; then
  echo "找不到可执行 pytest: ${BACKEND_PYTEST}" >&2
  exit 1
fi
if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  echo "找不到可执行 python: ${BACKEND_PYTHON}" >&2
  exit 1
fi

echo "日志目录: ${LOG_DIR}"

run bash -lc "cd '${BACKEND_DIR}' && '${BACKEND_PYTEST}' tests/test_dialogs.py tests/test_background.py tests/test_projects.py"
run bash -lc "cd '${FRONTEND_DIR}' && npm run test:unit -- src/stores/workspace.test.ts src/stores/chat.workspace.test.ts src/stores/project.workspace.test.ts src/components/list/projectListMeta.test.ts"
run bash -lc "cd '${FRONTEND_DIR}' && npm run build"

echo "==> 启动 backend 服务"
bash -lc "cd '${BACKEND_DIR}' && '${BACKEND_PYTHON}' -m uvicorn app.main:app --host '${BACKEND_HOST}' --port '${BACKEND_PORT}'" >"${BACKEND_LOG}" 2>&1 &
BACKEND_PID="$!"
wait_for_http "${BACKEND_BASE_URL}/api/v1/projects" "backend"

echo "==> 启动 frontend 服务"
bash -lc "cd '${FRONTEND_DIR}' && npm run dev -- --host '${FRONTEND_HOST}' --port '${FRONTEND_PORT}' --strictPort" >"${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID="$!"
wait_for_http "${FRONTEND_BASE_URL}/" "frontend"

PROJECT_ID="$(get_or_create_project_id)"
if [[ -z "${PROJECT_ID}" ]]; then
  echo "无法获取项目 ID" >&2
  exit 1
fi
echo "使用项目 ID: ${PROJECT_ID}"

run bash -lc "agent-browser skills get core >/dev/null"
run agent-browser --session "${AB_SESSION}" errors --clear
run agent-browser --session "${AB_SESSION}" console --clear

run agent-browser --session "${AB_SESSION}" open "${FRONTEND_BASE_URL}/"
run agent-browser --session "${AB_SESSION}" wait 1500
run agent-browser --session "${AB_SESSION}" open "${FRONTEND_BASE_URL}/projects/${PROJECT_ID}"
run agent-browser --session "${AB_SESSION}" wait 1500
run agent-browser --session "${AB_SESSION}" open "${FRONTEND_BASE_URL}/settings"
run agent-browser --session "${AB_SESSION}" wait 1500

agent-browser --session "${AB_SESSION}" errors --json >"${AGENT_BROWSER_ERRORS_JSON}"
agent-browser --session "${AB_SESSION}" console --json >"${AGENT_BROWSER_CONSOLE_JSON}"

echo "==> agent-browser errors"
cat "${AGENT_BROWSER_ERRORS_JSON}"
echo
echo "==> agent-browser console"
cat "${AGENT_BROWSER_CONSOLE_JSON}"
echo

python3 - <<'PY' "${AGENT_BROWSER_ERRORS_JSON}" "${AGENT_BROWSER_CONSOLE_JSON}"
import json
import sys
from pathlib import Path

errors_file = Path(sys.argv[1])
console_file = Path(sys.argv[2])

errors_payload = json.loads(errors_file.read_text(encoding="utf-8"))
console_payload = json.loads(console_file.read_text(encoding="utf-8"))

errors = errors_payload.get("data", {}).get("errors", [])
messages = console_payload.get("data", {}).get("messages", [])
console_error_messages = [
    msg for msg in messages
    if str(msg.get("type", "")).lower() in {"error", "assert"}
    or str(msg.get("level", "")).lower() == "error"
]

print(f"agent-browser errors 数量: {len(errors)}")
print(f"agent-browser console 数量: {len(messages)}")
print(f"agent-browser console(error) 数量: {len(console_error_messages)}")

if errors:
    raise SystemExit("存在 agent-browser page errors，回归失败")
if console_error_messages:
    raise SystemExit("存在 agent-browser console error，回归失败")
PY

echo "回归完成"
