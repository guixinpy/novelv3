# Phase 253 - Athena Chat Context Diagnostics Autoload

## Goal

When Athena chat opens, it should refresh the lightweight diagnostics that make
the current context snapshot meaningful. Previously the panel could show
`索引文档 未读取` and `长篇记忆 未读取` unless the user had first visited specific
Athena sections.

## TDD Evidence

- RED:
  - `npm run test:unit -- --run src/components/athena/AthenaChatPanel.test.ts -t "loads retrieval and longform diagnostics"`
  - Failed because opening the panel did not call `loadRetrievalDiagnostics` or
    `loadLongformMaintenanceDiagnostics`.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `npm run test:unit -- --run src/components/athena/AthenaChatPanel.test.ts`
    passed with `7 passed`.

## Changes

- Athena chat now loads retrieval diagnostics and long-form maintenance
  diagnostics when opened or when the project changes.
- Existing diagnostics for the same project are reused, so the panel does not
  force redundant requests.
- Component tests now initialize the Athena store with the active project first,
  matching the real `AthenaView` initialization path.

## Verification Evidence

Fresh verification before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with `647 passed`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `418 passed`.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
