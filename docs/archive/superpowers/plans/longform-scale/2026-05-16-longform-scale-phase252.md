# Phase 252 - Athena Chat Longform Maintenance Context

## Goal

Make Athena chat show whether long-form memory/retrieval maintenance is current.
In thousand-chapter projects, stale long-form memory can make answers rely on an
old context even when chapter count and word count look correct.

## TDD Evidence

- RED:
  - `npm run test:unit -- --run src/components/athena/AthenaChatPanel.test.ts -t "stale longform maintenance"`
  - Failed because the current-context snapshot did not show long-form
    maintenance state.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `npm run test:unit -- --run src/components/athena/AthenaChatPanel.test.ts`
    passed with `6 passed`.

## Changes

- Athena chat context snapshot now includes a long-form memory label:
  - `长篇记忆 未读取`
  - `长篇记忆 已同步`
  - `长篇记忆 待维护 N 项`
- The stale count combines missing/stale memory and missing/stale retrieval
  counts, matching the maintenance diagnostics model.

## Verification Evidence

Fresh verification before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with `647 passed`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `417 passed`.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
