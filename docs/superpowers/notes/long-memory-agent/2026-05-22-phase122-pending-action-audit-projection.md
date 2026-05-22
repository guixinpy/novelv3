# Phase122 Pending Action Audit Projection Report

## Summary

Extended approval-backed pending action previews with a bounded `audit` projection and rendered the audit summary in the pending action card.

The UI now shows why the Agent is asking for confirmation: intent class, planner version, and plan id. It does not pretend approval contracts are model-call traces, and it does not expose the approval hash as user-facing card text.

## Changes

- `pending_action_execution_preview()` now derives `execution_preview.audit` from the approval contract.
- Frontend `PendingExecutionPreview` type now includes optional `audit`.
- `ActionCard` renders compact audit rows:
  - intent;
  - source projection when present;
  - planner;
  - plan id.
- Added regression expectations to existing backend approval-pending test and frontend `ActionCard` test.

## External Reference Notes

Subagent reference review identified these transferable patterns:

- Hermes keeps approval state as structured backend state, with UI consuming the state instead of owning approval logic.
- Hermes writes approval evidence into tool execution result paths after approval.
- Hermes/OpenClaw treat tool started/completed as traceable events with argument previews and duration/error.
- OpenClaw distinguishes normal trace from raw/sensitive trace.
- OpenHuman routes unsolicited write actions through analysis -> approval card -> full-permission execution.

Applied in this phase:

- Kept backend as source of approval/audit state.
- Added bounded, non-raw audit projection.
- Avoided fake trace drawer links before a real approval/audit trace endpoint exists.

Deferred:

- Dedicated approval/audit trace endpoint.
- Decision id / action trace table.
- Raw trace mode and permission model.
- Applying the same preview contract to world-model proposal write paths.

## Verification

- RED evidence:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -k "chapter_approval_pending_message_uses_specific_description" -q`
  - Result: failed because `execution_preview.audit` was missing.
  - `npm run test:unit -- ActionCard.test.ts`
  - Result: failed because `ActionCard` did not render `审批依据`.
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
  - Fresh project: `b6b2c99e-e4f7-4321-889c-8584ce1ce775`.
  - Command path: `/chapter 2 检查审批依据`.
  - Pending card showed `审批依据`.
  - Pending card showed `direct_generate_chapter`.
  - Pending card showed `phase114.generate_chapter_execution_prepare.v1`.
  - Pending card showed `direct-generate:...`.
  - Pending card did not show `approval:`.
  - Console errors: none.
  - Page errors: none.

## Dogfood Observation

A natural-language browser attempt on a fresh seeded project did not reliably create a chapter pending action, while `/chapter 2 ...` did. This reinforces the broader goal requirement: low-detail user input should be routed by the Agent without requiring slash commands. Do not fix this inside Phase122; use it as input for a future intent-router / dialog-planner phase.

## Novel Progress

No durable chapter was generated. Browser validation used API-key-disabled execution and stopped at approval preview.

## Next Phase Recommendation

Move from preview-only audit projection toward a reusable approval/action trace spine:

1. add a stable approval decision id or action audit id when resolving pending actions;
2. write approval decision metadata into the eventual action result;
3. extend the same preview/audit contract to guarded world-model write paths such as `apply_world_model_proposal_resolution`.
