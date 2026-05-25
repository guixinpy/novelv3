# Phase121 Pending Action Execution Preview Report

## Summary

Added a compact `execution_preview` projection for approval-backed pending actions and rendered it in `ActionCard`.

The dialog second-confirmation card now shows what the Agent is about to execute, without exposing raw approval-contract JSON or hashes in the UI.

## Changes

- Added `pending_action_execution_preview()` backend projection helper.
- Added optional `execution_preview` to `PendingActionOut`.
- `DialogMessageService` now attaches execution previews to pending action payloads when an approval contract is present.
- Frontend `PendingAction` types now include execution preview fields.
- `ActionCard` renders:
  - preview title;
  - compact summary;
  - step label;
  - step reason.
- Added `ActionCard` unit coverage for execution previews.

## Runtime Boundary

- Pending action storage remains unchanged.
- Approval contract verification and execution remain unchanged.
- Pending actions without approval contracts render as before.
- The approval hash remains available in the API payload for traceability, but is not shown in the compact card UI.

## Verification

- RED evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -k "chapter_approval_pending_message_uses_specific_description" -q`
  - Result: failed because `execution_preview` was missing.
  - `npm run test:unit -- ActionCard.test.ts`
  - Result: failed because `ActionCard` did not render preview content.
- GREEN/T1 evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -k "chapter_approval_pending_message_uses_specific_description" -q`
  - Result: `1 passed, 63 deselected`.
  - `npm run test:unit -- ActionCard.test.ts`
  - Result: `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - Result: `64 passed`.
  - `npm run test:unit -- ActionCard.test.ts ChatMessage.test.ts chat.workspace.test.ts`
  - Result: `35 passed`.
  - `npm run build`
  - Result: `vue-tsc --noEmit && vite build` passed.
- Browser evidence:
  - `previewTitleVisible: true`
  - `previewSummaryVisible: true`
  - `previewStepReasonVisible: true`
  - `hashHidden: true`
  - `consoleErrors: []`
  - `pageErrors: []`

## Novel Progress

No durable chapter was generated. The browser flow used API-key-disabled execution to validate the approval preview without model spend or accidental writes.

## Next Phase Recommendation

Continue strengthening the Agent control-plane UI:

1. add a compact trace link from pending action preview to the underlying approval contract or model-call trace;
2. expose source projection IDs where available;
3. keep execution unchanged until the preview/trace contract is stable.
