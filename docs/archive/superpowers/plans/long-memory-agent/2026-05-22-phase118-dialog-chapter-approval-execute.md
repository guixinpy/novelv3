# Phase118 Dialog Chapter Approval Execute Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. This phase finishes the backend dialog approval loop for single-chapter generation.

**Goal:** After dialog chapter prepare returns `approval_required`, create a second pending action and dispatch `execute_generate_chapter_with_approval` only after the user confirms again.

**Architecture:** Keep the public pending action type as `generate_chapter` for compatibility. Use params to distinguish prepare from execute: a chapter action with an approval contract dispatches `execute_generate_chapter_with_approval`; otherwise it dispatches `prepare_generate_chapter_execution`. Store the follow-up pending action on the dialog so existing message APIs can surface it.

**Tech Stack:** Python, pytest, existing dialog pending-action and Writing Agent tool executor.

---

## Assumptions

- Phase117 already dispatches the first dialog chapter confirmation to `prepare_generate_chapter_execution`.
- `prepare_generate_chapter_execution` output includes `agent_plan_approval_contract` and `agent_plan_approval_contract_hash`.
- Existing `resolve-action` can reuse the same `generate_chapter` action type if dispatch is driven by params.

## Scope

1. Add a dispatch helper in `dialog_control_plane`:
   - `generate_chapter` without approval params -> `prepare_generate_chapter_execution`;
   - `generate_chapter` with approval params -> `execute_generate_chapter_with_approval`.
2. On `approval_required`, create a new `PendingAction` on the same dialog.
3. Store execute params:
   - `chapter_index`;
   - `confirm_execute=True`;
   - `approval_contract_hash`;
   - `approval_contract`;
   - optional `command_args`.
4. Record the approval-required message as assistant-visible so message listing can attach the pending action.
5. Add tests proving:
   - prepare work creates a follow-up pending action;
   - follow-up confirmation dispatches `execute_generate_chapter_with_approval`;
   - existing setup dispatch remains unchanged;
   - direct chapter API generation remains unchanged.

## Out Of Scope

- Frontend visual design changes.
- Browser E2E confirmation flow.
- Longform batch approval migration.
- Changing slash command route metadata.
- Generating novel chapters.

## Verification Plan

- T0 RED:
  - Add tests for follow-up pending action and execute dispatch; verify they fail.
- T0 GREEN:
  - Implement follow-up pending creation and param-sensitive dispatch.
- T1:
  - targeted dialog tests;
  - full `test_dialogs.py`;
  - approved chapter execution tests;
  - chapter API generation subset.
- Hygiene:
  - `git diff --check`;
  - secret scan over `backend` and active `docs`.

## Success Criteria

- First chapter confirmation prepares approval and creates a new pending action.
- Second confirmation dispatches `execute_generate_chapter_with_approval`.
- The generated follow-up pending action carries the exact approval contract hash and snapshot.
- No manuscript write happens before the second confirmation.
