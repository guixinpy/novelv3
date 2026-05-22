# Phase120 Action Result View Contract Plan

> **For agentic workers:** Keep this phase narrow. Do not redesign chat state or background task polling.

## Goal

Move dialog-visible action result labels toward a stable API projection so frontend components do not need to infer every user-facing status from raw `type/status` pairs.

## Why

Phase119 fixed `approval_required` in `ChatMessage`, but that is still component-local mapping. For an Agent-oriented UI, action states should be a contract produced by the control plane/API and consumed consistently by Hermes, Athena, history hydration, and future trace views.

## Scope

1. Add a backend helper that projects an `action_result` dict into a small user-facing view payload.
2. Include that projection in dialog history messages as `action_result_view`.
3. Include the same projection in `/api/v1/dialog/resolve-action` responses.
4. Teach the chat store and `ChatMessage` to prefer `action_result_view`, while preserving current fallback behavior.
5. Add focused backend and frontend tests.

## Out Of Scope

- Removing all existing frontend fallback mappings.
- Changing persisted `DialogMessage.action_result` shape.
- Changing background task polling semantics.
- Redesigning pending action cards or trace UI.

## Verification Plan

- RED:
  - backend test: message listing exposes `action_result_view` for `approval_required`;
  - backend test: resolve-action response includes `action_result_view` for `generating`;
  - frontend test: `ChatMessage` renders provided `action_result_view.label` instead of local fallback.
- GREEN/T1:
  - targeted backend dialog tests;
  - targeted frontend component/store tests.
- T2 only if frontend types/build are affected:
  - `npm run build`.
- Always:
  - `git diff --check`;
  - secret scan.

## Success Criteria

- Existing clients can keep reading `action_result`.
- New clients can read `action_result_view.label`, `variant`, and `status`.
- `approval_required` has a backend-projected Chinese label.
- Frontend still displays sensible text when `action_result_view` is absent.
