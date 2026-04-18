#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_VENV="/home/guixin/project_workspace/novelv3/backend/.venv"
BACKEND_PYTEST="$BACKEND_VENV/bin/pytest"
BACKEND_PYTHON="$BACKEND_VENV/bin/python"
BACKEND_ALEMBIC="$BACKEND_VENV/bin/alembic"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT=""
BACKEND_BASE_URL=""
FRONTEND_BASE_URL=""
AB_SESSION="verify-full-app-ui-$$"

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/verify-full-app-ui.XXXXXX")"
BACKEND_LOG="$LOG_DIR/backend.log"
AGENT_BROWSER_ERRORS_JSON="$LOG_DIR/agent-browser-errors.json"
AGENT_BROWSER_CONSOLE_JSON="$LOG_DIR/agent-browser-console.json"

BACKEND_PID=""
PROJECT_ID=""
PROJECT_NAME=""
SETUP_ID=""

cleanup() {
  set +e
  if [[ -n "${PROJECT_ID:-}" && -n "${BACKEND_BASE_URL:-}" ]]; then
    curl -fsS -X DELETE "${BACKEND_BASE_URL}/api/v1/projects/${PROJECT_ID}" >/dev/null 2>&1 || true
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

pick_free_port() {
  python3 - <<'PY'
import socket

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
}

create_temp_project() {
  local payload
  local ts
  local project_json

  ts="$(date +%s)"
  payload="$(python3 - <<'PY' "${ts}"
import json
import sys

ts = sys.argv[1]
print(json.dumps({"name": f"UI Slash Smoke {ts}"}))
PY
)"

  project_json="$(curl -fsS \
    -H 'Content-Type: application/json' \
    -X POST \
    -d "${payload}" \
    "${BACKEND_BASE_URL}/api/v1/projects")"

  python3 - <<'PY' "${project_json}"
import json
import sys

data = json.loads(sys.argv[1])
pid = data.get("id")
name = data.get("name")
if not pid or not name:
    raise SystemExit("创建临时项目失败：返回中缺少 id 或 name")
print(f"{pid}\t{name}")
PY
}

create_temp_setup() {
  local project_id="$1"
  local setup_payload
  local setup_record

  setup_payload="$(python3 - <<'PY'
import json

print(json.dumps({
    "world_building": {
        "background": "灾后第三纪元，旧城废墟与档案机关并存。",
        "geography": "群岛与雾海之间由浮桥和旧航道连接。",
        "society": "档案机关垄断记忆修复，民间巡夜人维持边境秩序。",
        "rules": "记忆碎片可以被交易，但篡改会引发城市级回响。",
        "atmosphere": "潮湿、肃静、带着持续失真的钟声。"
    },
    "characters": [
        {
            "name": "沈砚",
            "age": 28,
            "gender": "男",
            "personality": "冷静克制，但对真相近乎偏执。",
            "background": "旧城档案馆的修复员。",
            "goals": "查清师父失踪与记忆税黑市的关联。",
            "character_status": "alive"
        },
        {
            "name": "周岚",
            "age": 31,
            "gender": "女",
            "personality": "果断直接，擅长在混乱中做交易。",
            "background": "边境调查员。",
            "goals": "在秩序崩坏前找出雾海异动源头。",
            "character_status": "alive"
        }
    ],
    "core_concept": {
        "theme": "记忆决定身份，篡改记忆是否等于篡改人生。",
        "premise": "记忆能被征税和买卖。",
        "hook": "主角修复的档案会反过来改写现实。",
        "unique_selling_point": "档案修复决定现实。"
    }
}, ensure_ascii=False))
PY
)"

  setup_record="$(
    cd "${BACKEND_DIR}" && "${BACKEND_PYTHON}" - <<'PY' "${project_id}" "${setup_payload}"
import json
import sys

from app.db import SessionLocal
from app.models import Project, Setup

project_id = sys.argv[1]
payload = json.loads(sys.argv[2])

db = SessionLocal()
try:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise SystemExit(f"项目不存在: {project_id}")

    existing = db.query(Setup).filter(Setup.project_id == project_id).first()
    if existing:
        db.delete(existing)
        db.flush()

    setup = Setup(
        project_id=project_id,
        world_building=payload["world_building"],
        characters=payload["characters"],
        core_concept=payload["core_concept"],
        status="generated",
    )
    db.add(setup)
    project.status = "setup_approved"
    project.current_phase = "setup"
    db.commit()
    db.refresh(setup)
    print(setup.id)
finally:
    db.close()
PY
)"

  if [[ -z "${setup_record}" ]]; then
    echo "无法创建临时设定" >&2
    exit 1
  fi

  echo "${setup_record}"
}

assert_eval() {
  local description="$1"
  local js="$2"
  echo "==> 断言: ${description}"
  run agent-browser --session "${AB_SESSION}" eval "${js}"
}

wait_for_eval_true() {
  local description="$1"
  local expression="$2"
  local attempts="${3:-60}"
  local sleep_seconds="${4:-1}"
  local last_result=""
  local last_status=0

  echo "==> 等待: ${description}"
  for ((i = 1; i <= attempts; i++)); do
    local result
    local status
    set +e
    result="$(agent-browser --session "${AB_SESSION}" eval "${expression}" 2>&1)"
    status=$?
    set -e

    last_result="${result}"
    last_status="${status}"

    if [[ "${status}" -eq 0 && "${result}" == "true" ]]; then
      return 0
    fi
    sleep "${sleep_seconds}"
  done

  echo "等待超时: ${description}" >&2
  echo "最后一次 eval 退出码: ${last_status}" >&2
  if [[ -n "${last_result}" ]]; then
    echo "最后一次 eval 输出: ${last_result}" >&2
  else
    echo "最后一次 eval 输出: <empty>" >&2
  fi
  return 1
}

run() {
  echo "==> $*"
  "$@"
}

require_command curl
require_command python3
require_command npm
require_command agent-browser

BACKEND_PORT="${VERIFY_BACKEND_PORT:-$(pick_free_port)}"
BACKEND_BASE_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
FRONTEND_BASE_URL="${BACKEND_BASE_URL}"

if [[ ! -x "${BACKEND_PYTEST}" ]]; then
  echo "找不到可执行 pytest: ${BACKEND_PYTEST}" >&2
  exit 1
fi
if [[ ! -x "${BACKEND_PYTHON}" ]]; then
  echo "找不到可执行 python: ${BACKEND_PYTHON}" >&2
  exit 1
fi
if [[ ! -x "${BACKEND_ALEMBIC}" ]]; then
  echo "找不到可执行 alembic: ${BACKEND_ALEMBIC}" >&2
  exit 1
fi

echo "日志目录: ${LOG_DIR}"

run bash -lc "cd '${BACKEND_DIR}' && '${BACKEND_PYTEST}' tests/test_dialogs.py tests/test_background.py tests/test_projects.py tests/test_setups.py tests/test_storylines.py tests/test_outlines.py"
run bash -lc "cd '${BACKEND_DIR}' && '${BACKEND_ALEMBIC}' upgrade head"
run bash -lc "cd '${FRONTEND_DIR}' && npm run test:unit -- src/stores/workspace.test.ts src/stores/chat.workspace.test.ts src/stores/project.workspace.test.ts src/components/list/projectListMeta.test.ts src/components/workspace/chatCommands.test.ts src/components/workspace/ChatWorkspace.commands.test.ts"
run bash -lc "cd '${FRONTEND_DIR}' && npm run build"

echo "==> 启动 backend 服务"
bash -lc "cd '${BACKEND_DIR}' && '${BACKEND_PYTHON}' -m uvicorn app.main:app --host '${BACKEND_HOST}' --port '${BACKEND_PORT}'" >"${BACKEND_LOG}" 2>&1 &
BACKEND_PID="$!"
sleep 1
if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
  echo "backend 进程启动失败，日志: ${BACKEND_LOG}" >&2
  cat "${BACKEND_LOG}" >&2
  exit 1
fi
wait_for_http "${BACKEND_BASE_URL}/api/v1/projects" "backend"

PROJECT_RECORD="$(create_temp_project)"
PROJECT_ID="${PROJECT_RECORD%%$'\t'*}"
PROJECT_NAME="${PROJECT_RECORD#*$'\t'}"
if [[ -z "${PROJECT_ID}" || -z "${PROJECT_NAME}" ]]; then
  echo "无法创建临时项目" >&2
  exit 1
fi
echo "临时项目: ${PROJECT_NAME} (${PROJECT_ID})"

SETUP_ID="$(create_temp_setup "${PROJECT_ID}")"
if [[ -z "${SETUP_ID}" ]]; then
  echo "无法创建临时设定记录" >&2
  exit 1
fi
echo "临时设定: ${SETUP_ID}"

run bash -lc "agent-browser skills get core >/dev/null"
run agent-browser --session "${AB_SESSION}" errors --clear
run agent-browser --session "${AB_SESSION}" console --clear

run agent-browser --session "${AB_SESSION}" open "${FRONTEND_BASE_URL}/projects/${PROJECT_ID}"
run agent-browser --session "${AB_SESSION}" wait ".chat-workspace__input"

assert_eval "新建临时项目详情页已打开" "(() => { const title = document.querySelector('.chat-workspace__title')?.textContent?.trim() || ''; const expected = ${PROJECT_NAME@Q}; if (title !== expected) { throw new Error('项目标题不匹配: ' + title + ' != ' + expected); } if (!location.pathname.endsWith('/projects/' + ${PROJECT_ID@Q})) { throw new Error('项目详情页路径不正确: ' + location.pathname); } return true; })()"

assert_eval "点击右侧设定 tab" "(() => { const tabs = Array.from(document.querySelectorAll('[data-testid=\"inspector-primary-tabs\"] .workspace-tabs__button')); const setupTab = tabs.find((tab) => (tab.textContent || '').trim() === '设定'); if (!setupTab) { throw new Error('未找到右侧设定 tab'); } setupTab.click(); return true; })()"
wait_for_eval_true "切到设定后出现二级 tabs" "(() => { const tablist = document.querySelector('[data-testid=\"setup-section-tabs\"]'); if (!tablist) { return false; } const labels = ['角色', '世界观', '核心概念']; return labels.every((label) => Array.from(tablist.querySelectorAll('button')).some((button) => (button.textContent || '').trim() === label)); })()"
assert_eval "默认显示角色详情且包含第一名角色信息" "(() => { const detail = document.querySelector('[data-testid=\"setup-character-detail\"]'); if (!detail) { throw new Error('未找到角色详情区域'); } const firstCharacter = document.querySelector('[data-testid=\"setup-character-item-沈砚\"]'); if (!firstCharacter) { throw new Error('未找到首个角色条目'); } const pressed = firstCharacter.getAttribute('aria-pressed'); if (pressed !== 'true') { throw new Error('首个角色未默认选中: ' + pressed); } const detailText = detail.textContent || ''; const expected = ['沈砚', '冷静克制，但对真相近乎偏执。', '旧城档案馆的修复员。', '查清师父失踪与记忆税黑市的关联。']; for (const text of expected) { if (!detailText.includes(text)) { throw new Error('角色详情缺少文本: ' + text + '; 当前: ' + detailText); } } const forbidden = ['age', 'gender', 'personality', 'goals', 'character_status']; const hits = forbidden.filter((key) => detailText.includes(key)); if (hits.length > 0) { throw new Error('角色详情暴露 setup JSON key: ' + hits.join(',')); } return true; })()"

assert_eval "切到世界观 tab" "(() => { const tab = document.querySelector('[data-testid=\"setup-section-tab-world\"]'); if (!tab) { throw new Error('未找到世界观 tab'); } tab.click(); return true; })()"
wait_for_eval_true "世界观展示 5 张字段卡且不暴露 JSON key" "(() => { const panel = document.querySelector('[data-testid=\"setup-section-panel-world\"]'); if (!panel || panel.getAttribute('aria-hidden') !== 'false') { return false; } const cards = panel.querySelectorAll('[data-testid=\"setup-world-card\"]'); if (cards.length !== 5) { return false; } const text = panel.textContent || ''; const forbidden = ['background', 'geography', 'society', 'rules', 'atmosphere']; return forbidden.every((key) => !text.includes(key)); })()"

assert_eval "切到核心概念 tab" "(() => { const tab = document.querySelector('[data-testid=\"setup-section-tab-concept\"]'); if (!tab) { throw new Error('未找到核心概念 tab'); } tab.click(); return true; })()"
wait_for_eval_true "核心概念展示 4 张字段卡且不暴露 JSON key" "(() => { const panel = document.querySelector('[data-testid=\"setup-section-panel-concept\"]'); if (!panel || panel.getAttribute('aria-hidden') !== 'false') { return false; } const cards = panel.querySelectorAll('[data-testid=\"setup-concept-card\"]'); if (cards.length !== 4) { return false; } const text = panel.textContent || ''; const forbidden = ['theme', 'premise', 'hook', 'unique_selling_point']; return forbidden.every((key) => !text.includes(key)); })()"

assert_eval "设定面板页面文本不出现 setup JSON key" "(() => { const text = document.body?.innerText || ''; const forbidden = ['background', 'geography', 'society', 'rules', 'atmosphere', 'age', 'gender', 'personality', 'goals', 'character_status', 'theme', 'premise', 'hook', 'unique_selling_point']; const hits = forbidden.filter((key) => text.includes(key)); if (hits.length > 0) { throw new Error('页面暴露 setup JSON key: ' + hits.join(',')); } return true; })()"

run agent-browser --session "${AB_SESSION}" fill ".chat-workspace__input" "/"
wait_for_eval_true "输入 / 后出现 slash 菜单" "(() => Boolean(document.querySelector('[data-testid=\"chat-command-menu\"]')))()"
assert_eval "slash 菜单至少包含 /compact" "(() => { const names = Array.from(document.querySelectorAll('.chat-command-menu__name')).map((el) => (el.textContent || '').trim()); if (!names.includes('/compact')) { throw new Error('slash 菜单不包含 /compact，当前: ' + names.join(',')); } return true; })()"

assert_eval "页面不再出现旧 QuickActions 文案" "(() => { const text = document.body?.innerText || ''; const legacy = ['生成设定', '生成故事线', '生成大纲']; const hits = legacy.filter((word) => text.includes(word)); if (hits.length > 0) { throw new Error('发现旧文案: ' + hits.join(',')); } return true; })()"

run agent-browser --session "${AB_SESSION}" fill ".chat-workspace__input" "/setup 主角是植物学家"
run agent-browser --session "${AB_SESSION}" click ".chat-workspace__send"
wait_for_eval_true "执行 /setup 后进入 pending action" "(() => { const text = document.body?.innerText || ''; return text.includes('同意执行') && text.includes('附加要求：主角是植物学家'); })()" 60 1

run agent-browser --session "${AB_SESSION}" fill ".chat-workspace__input" "/clear"
run agent-browser --session "${AB_SESSION}" click ".chat-workspace__send"
wait_for_eval_true "pending 状态执行 /clear 后待处理动作被清除" "(() => { const text = document.body?.innerText || ''; const hasPending = text.includes('同意执行') || text.includes('取消') || text.includes('修改后再执行'); return text.includes('已清空当前对话上下文。') && !hasPending; })()" 60 1

run agent-browser --session "${AB_SESSION}" fill ".chat-workspace__input" "请回复：已收到，用于 compact smoke。"
run agent-browser --session "${AB_SESSION}" press Enter
wait_for_eval_true "普通会话消息产生" "(() => document.querySelectorAll('.message-row').length >= 2)()" 90 1
wait_for_eval_true "普通会话完成后输入框重新可用" "(() => { const input = document.querySelector('.chat-workspace__input'); const loading = document.querySelector('.chat-workspace__loading'); return Boolean(input) && !input.disabled && !loading; })()" 90 1

run agent-browser --session "${AB_SESSION}" fill ".chat-workspace__input" "/co"
wait_for_eval_true "slash 菜单过滤后可选 /compact" "(() => Array.from(document.querySelectorAll('.chat-command-menu__name')).some((el) => (el.textContent || '').trim() === '/compact'))()"
run agent-browser --session "${AB_SESSION}" press Enter
assert_eval "已在输入框选中 /compact 命令" "(() => { const input = document.querySelector('.chat-workspace__input'); const value = input && 'value' in input ? String(input.value || '') : ''; if (!value.startsWith('/compact')) { throw new Error('输入框不是 /compact 命令: ' + value); } return true; })()"
run agent-browser --session "${AB_SESSION}" click ".chat-workspace__send"

wait_for_eval_true "执行 /compact 后出现 summary card" "(() => Boolean(document.querySelector('[data-testid=\"chat-summary-toggle\"]')))()" 120 1
assert_eval "summary card 文案使用标题与压缩条数" "(() => { const text = document.querySelector('[data-testid=\"chat-summary-toggle\"]')?.textContent || ''; if (!text.includes('摘要（') || !text.includes('已压缩')) { throw new Error('summary card 文案不正确: ' + text); } return true; })()"

run agent-browser --session "${AB_SESSION}" reload
run agent-browser --session "${AB_SESSION}" wait ".chat-workspace__input"
wait_for_eval_true "刷新后 summary card 仍存在" "(() => Boolean(document.querySelector('[data-testid=\"chat-summary-toggle\"]')))()" 30 1

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
