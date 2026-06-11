#!/usr/bin/env bash
# 重构期验证脚本（claude-guide 04-development-rules.md §5）
# 用法: scripts/verify_refactor.sh [kernel|kept|all]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-all}"

section() { printf '\n== %s ==\n' "$1"; }

run_pytest() {
  (cd "$ROOT_DIR/backend" && python -m pytest "$@")
}

case "$MODE" in
  kernel)
    section "Agent kernel tests (providers / loop / guards / dependency rules)"
    run_pytest tests/agent/ -q
    ;;
  kept)
    section "Kept-module regression (world checker / retrieval / proposals)"
    run_pytest tests/test_world_checkers.py tests/test_athena_retrieval.py tests/test_world_proposals.py -q
    ;;
  all)
    section "Agent kernel tests"
    run_pytest tests/agent/ -q
    section "Full backend regression"
    run_pytest tests/ -q
    ;;
  *)
    echo "unknown mode: $MODE (expected kernel|kept|all)" >&2
    exit 1
    ;;
esac
