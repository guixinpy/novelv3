# Phase122 Pending Action Audit Projection Plan

> **For agentic workers:** Keep this phase to read-only audit projection. Do not add new approval execution behavior.

**Goal:** Make approval-backed pending actions expose compact audit references so the user can see why the Agent is asking for confirmation.

**Architecture:** Extend the existing `execution_preview` projection with an `audit` object derived from the approval contract. Render the audit object in `ActionCard` as concise text. Keep raw `action.params.approval_contract` unchanged and avoid inventing a trace drawer link before a real trace endpoint exists.

**Tech Stack:** FastAPI/Pydantic, Vue 3, Vitest, pytest.

---

## Scope

1. Add `audit` fields to `pending_action_execution_preview()`:
   - approval contract hash;
   - approval contract version;
   - plan id;
   - source projection id;
   - planner version;
   - intent class.
2. Render compact audit details in `ActionCard`.
3. Add focused backend and frontend tests.
4. Record external-agent reference findings in the phase report.

## Out Of Scope

- Creating a new approval-contract detail API.
- Creating a fake model trace id or opening `ModelTraceDrawer` for non-model-call traces.
- Changing approval verification or execution.
- Showing raw approval contract JSON in the UI.

## Verification Plan

- RED:
  - backend pending-action test expects `execution_preview.audit`;
  - frontend `ActionCard` test expects audit details to render.
- GREEN/T1:
  - targeted backend dialog test;
  - targeted frontend `ActionCard` test.
- T2:
  - `backend\tests\test_dialogs.py -q`;
  - `npm run test:unit -- ActionCard.test.ts ChatMessage.test.ts chat.workspace.test.ts`;
  - `npm run build`.
- Always:
  - `git diff --check`;
  - secret scan.

## Success Criteria

- Existing pending actions still render without audit when no approval contract exists.
- Approval follow-up pending actions expose a bounded, stable audit projection.
- The UI shows audit details without exposing raw contract JSON or the approval hash as the primary content.
