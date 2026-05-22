# Phase119 Dialog Approval Browser Check Report

## Summary

Verified the dialog-driven chapter approval flow in a real browser and fixed two immediate UX/API gaps found during the flow.

The first confirmation still prepares a chapter-generation approval contract without writing the chapter. The follow-up pending action now uses a specific Chinese description, and the chat result no longer exposes the raw `approval_required` status.

## Browser Findings

- The Browser plugin tool was not available through the current tool surface, and `agent-browser` failed to launch Chrome in this Windows session.
- Playwright was used as the fallback browser driver after installing its Chromium runtime.
- Browser flow used project `00d16adc-519e-4969-9a6e-845e7bb4825f` on `http://127.0.0.1:5173`.
- Backend ran with `MOZHOU_DISABLE_API_KEY=1`, so the final execute step intentionally reached a clear failed terminal state instead of calling a real model.

Initial browser check exposed:

- follow-up pending action description was generic: `已准备好执行操作。`;
- chat result rendered raw status text: `生成正文: approval_required`.

After the fix, the browser check confirmed:

- first pending card includes `第2章正文`;
- second pending card includes `第2章正文` and `确认后`;
- second pending card no longer includes `已准备好执行操作`;
- visible chat text includes `生成正文等待确认`;
- visible chat text no longer includes `approval_required`;
- no console errors or page errors were observed.

## Changes

- `action_description()` now handles `generate_chapter` with params:
  - approval follow-up actions show chapter-specific confirmation copy;
  - non-approval generation actions still use generation copy.
- `DialogMessageService` now passes `pending.params` into `action_description()` when exposing pending actions.
- `ChatMessage` now renders `approval_required` as a user-facing Chinese status.
- Added regression coverage for:
  - chapter approval pending messages using a specific description;
  - frontend rendering of `approval_required` without exposing raw status.

## Verification

- RED evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -k "chapter_approval_pending_message_uses_specific_description" -q`
  - Result: failed because pending action description was `已准备好执行操作。`.
  - `npm run test:unit -- ChatMessage.test.ts`
  - Result: failed because UI rendered `生成正文: approval_required`.
- GREEN/T1 evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -k "chapter_approval_pending_message_uses_specific_description" -q`
  - Result: `1 passed, 62 deselected`.
  - `npm run test:unit -- ChatMessage.test.ts`
  - Result: `8 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
  - Result: `63 passed`.
  - `npm run build`
  - Result: `vue-tsc --noEmit && vite build` passed.
  - Playwright browser check:
    - `firstCardHasChapter: true`
    - `secondCardHasSpecificDescription: true`
    - `secondCardAvoidsGenericText: true`
    - `approvalRequiredLocalized: true`
    - `executeReachedExpectedTerminalState: true`
    - `consoleErrors: []`
    - `pageErrors: []`
  - `git diff --check`
  - Result: no whitespace errors.
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`
  - Result: no matches.

## Novel Progress

No durable novel chapter was generated. The browser flow intentionally used API-key-disabled execution to validate the dialog approval UX without model spend or accidental chapter writes.

## Next Phase Recommendation

Continue agentization work from the dialog surface into a broader control-plane contract:

1. make dialog-visible action state a stable API contract instead of component-local status mapping;
2. add a read-only trace projection for pending approval contracts so users can inspect what will be executed before confirming;
3. keep generic planner chapter generation unchanged until the approved dialog chain has more browser coverage.
