# Phase121 Pending Action Execution Preview Plan

> **For agentic workers:** Keep this phase focused on previewing existing approval contracts. Do not change execution or approval validation.

## Goal

Expose a compact, user-facing execution preview on pending actions created from Agent approval contracts, then render it in the pending action card.

## Why

After Phase118-120, the dialog flow can prepare a write action, ask for a second confirmation, and project action-result labels. The remaining UX gap is that a user still cannot see what the Agent will execute before pressing confirm, except for a one-line description.

For long-memory writing Agent work, confirmations should expose the planned write operations in a stable, inspectable form.

## Scope

1. Add a backend projection helper for `PendingAction.params.approval_contract`.
2. Attach `execution_preview` to `PendingActionOut` when available.
3. Render `execution_preview` in `ActionCard` as compact text, not raw JSON.
4. Add focused backend and frontend tests.

## Out Of Scope

- Editing approval contracts.
- Changing `execute_generate_chapter_with_approval`.
- Rendering a full trace inspector.
- Changing pending action storage schema.

## Verification Plan

- RED:
  - backend test: approval follow-up pending action exposes `execution_preview`;
  - frontend test: `ActionCard` renders preview title and step labels.
- GREEN/T1:
  - targeted backend dialog tests;
  - targeted frontend ActionCard test.
- T2:
  - `npm run build` because a Vue component changes.
- Always:
  - `git diff --check`;
  - secret scan.

## Success Criteria

- Pending action payloads remain backward compatible.
- Approval follow-up pending actions expose:
  - preview title;
  - write step count;
  - approval contract hash;
  - compact step labels and reasons.
- Existing pending actions without approval contracts render unchanged.
