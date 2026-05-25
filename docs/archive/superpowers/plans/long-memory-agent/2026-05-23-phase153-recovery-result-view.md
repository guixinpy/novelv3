# Phase153 Recovery Result View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give dialog message history a stable Chinese `action_result_view` for `plan_recovery_tools` recovery previews.

**Architecture:** Extend the existing action-result view mapper with a narrow recovery-preview branch. Keep raw `action_result` unchanged and only add presentation metadata derived from existing preview data.

**Tech Stack:** Python, existing dialog message service, pytest.

---

## Scope

In scope:
- Add a message-history regression test for `plan_recovery_tools`.
- Add a user-facing label for recovery preview success/failure.
- Add compact detail items for source run, recovery status, execution policy, and recovery tool count.

Out of scope:
- Frontend rendering changes.
- Changing recovery planning payloads.
- Executing recovery tools.

## Files

- Modify: `backend/app/services/actions/action_result_view.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase153-recovery-result-view.md`

## Task 1: RED Test

- [x] **Step 1: Add failing message-history test**

Add `test_get_messages_includes_action_result_view_for_recovery_preview` in `backend/tests/test_dialogs.py`:
- create a project and dialog.
- save an assistant message with `action_result.type == "plan_recovery_tools"`.
- call `DialogMessageService(db_session).list_messages(project.id)`.
- assert `action_result_view` is:
  - `type == "plan_recovery_tools"`
  - `status == "success"`
  - `label == "恢复预览已生成"`
  - `variant == "success"`
  - detail items include source run, recovery status, execution policy, and tool count.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_recovery_preview -q
```

Expected: fails because current generic view labels `plan_recovery_tools` as raw action type and has no recovery detail items.

## Task 2: Recovery Preview View Mapping

- [x] **Step 1: Add label mapping**

Modify `backend/app/services/actions/action_result_view.py`:
- add `TYPE_LABELS["plan_recovery_tools"] = "恢复预览"`.
- add a special `_label()` branch so success/completed becomes `"恢复预览已生成"` and failed becomes `"恢复预览失败"`.

- [x] **Step 2: Add detail item mapping**

Modify `_detail_items()`:
- if action type is `plan_recovery_tools`, return `_recovery_preview_detail_items(data)`.
- add helpers for:
  - source run id short display.
  - recovery status labels.
  - execution policy labels.
  - tool count.

- [x] **Step 3: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_recovery_preview -q
```

Expected: passes.

## Task 3: Regression, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_recovery_preview backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_approval_required backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Expected: all selected tests pass.

- [x] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: diff check passes; secret scan returns no matches.

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase153-recovery-result-view.md` with validation evidence and next recommendation.

- [x] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/actions/action_result_view.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase153-recovery-result-view.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase153-recovery-result-view.md
git commit -m "feat: add recovery preview result view"
git push
```
