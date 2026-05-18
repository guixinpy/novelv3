# Longform Scale Phase 75

## Goal

Move Athena proposal detail item windowing from frontend-only rendering to backend payload pagination.

## Success Criteria

1. Proposal detail defaults to returning at most 100 items.
2. Proposal detail exposes `items_total`, `items_offset`, and `items_limit`.
3. The world-model and Athena evolution proposal detail endpoints both accept `item_offset` and `item_limit`.
4. The frontend loads the first page by default and fetches more items on demand.
5. Review insight metrics use the full item total when available.

## Steps

1. Add a failing backend API test for a 150-item proposal bundle.
2. Add backend item pagination metadata and query limits.
3. Add a failing ProposalWorkbench test for loading the next item page.
4. Update the API client, world model store, ProposalWorkbench, and ReviewInsightPanel.
5. Run targeted tests, backend full tests, frontend full tests, build, diff check, and secret scan.

## Verification

1. `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -q` -> 23 passed.
2. `backend\.venv\Scripts\python.exe -m pytest backend\tests -q --basetemp .tmp\pytest` -> 503 passed.
3. `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run test:unit` -> 60 files passed, 364 tests passed.
4. `D:\DevTools\Nodejs\Nodejs22.18\npm.cmd run build` -> passed after rerunning with elevated filesystem permissions because sandbox blocked writing `backend/static/assets`.
5. `git diff --check` -> clean.
6. DeepSeek key exact scan -> no matches.
