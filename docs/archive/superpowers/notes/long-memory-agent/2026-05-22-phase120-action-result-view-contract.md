# Phase120 Action Result View Contract Report

## Summary

Added a backward-compatible `action_result_view` API projection for dialog action results.

This moves visible action-state labels one step out of component-local inference and into a shared backend projection. The frontend now prefers that projection when present, while keeping its previous fallback mapping for older responses.

## Changes

- Added `backend/app/services/actions/action_result_view.py`.
- `DialogMessageService` now adds `action_result_view` for history messages that have `action_result`.
- `/api/v1/dialog/resolve-action` now returns `action_result_view` beside the raw `action_result`.
- Frontend API types now include `ActionResultView`.
- Chat store now preserves `action_result_view` from history and resolve-action responses.
- `ChatMessage` now prefers `action_result_view.label` and `action_result_view.variant`.
- Added regression coverage for backend history, backend resolve-action response, component rendering, and store passthrough.

## Contract

`action_result_view` is intentionally small:

- `type`: original action type;
- `status`: original action status;
- `label`: user-facing Chinese label;
- `variant`: `success`, `error`, or `neutral`.

Raw `action_result` remains unchanged and remains the source of task IDs, agent run IDs, diagnostics, and control-plane evidence.

## Verification

- RED evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -k "action_result_view or resolve_chapter_action_confirm_dispatches_prepare_tool" -q`
  - Result: failed because `action_result_view` was missing in history and resolve-action response.
  - `npm run test:unit -- ChatMessage.test.ts`
  - Result: failed because `ChatMessage` rendered the raw fallback instead of the backend label.
  - `npm run test:unit -- chat.workspace.test.ts -t "action_result_view"`
  - Result: failed because the chat store dropped `action_result_view`.
- GREEN/T1 evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -k "action_result_view or resolve_chapter_action_confirm_dispatches_prepare_tool" -q`
  - Result: `2 passed, 62 deselected`.
  - `npm run test:unit -- ChatMessage.test.ts`
  - Result: `9 passed`.
  - `npm run test:unit -- chat.workspace.test.ts -t "action_result_view"`
  - Result: `1 passed, 24 skipped`.
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - Result: `64 passed`.
  - `npm run test:unit -- ChatMessage.test.ts chat.workspace.test.ts`
  - Result: `34 passed`.
  - `npm run build`
  - Result: `vue-tsc --noEmit && vite build` passed.

## Novel Progress

No novel chapter was generated. This phase improved the Agent dialog state contract needed for reliable long-running chapter generation sessions.

## Next Phase Recommendation

Add an inspectable approval-contract projection for pending chapter execution so users can see what the Agent will execute before confirming:

1. expose a compact `pending_action.preview` or `pending_action.execution_preview` payload;
2. render the preview in the pending action card without exposing raw JSON;
3. keep execute behavior unchanged.
