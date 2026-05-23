# Phase154 Recovery Response Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return stable metadata from dialog recovery-preview responses so clients can navigate to the created Writing Agent run without parsing raw message text.

**Architecture:** Reuse the existing `ChatOut.meta` and `DialogMessage.meta` fields. The recovery-preview handler will attach `agent_run_id`, `source_run_id`, and `agent_action_type` to both the immediate response and persisted assistant message.

**Tech Stack:** Python, FastAPI dialog endpoint, pytest.

---

## Scope

In scope:
- Add response `meta` for low-detail recovery preview.
- Persist the same metadata on the assistant message.
- Keep `action_result` as the authoritative payload.

Out of scope:
- Adding new frontend navigation UI.
- Changing `UiHintOut` schema.
- Changing recovery execution behavior.

## Files

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase154-recovery-response-meta.md`

## Task 1: RED Test

- [x] **Step 1: Extend recovery-preview dialog test**

In `test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists`, assert:
- response `meta.agent_run_id` equals the created recovery run id.
- response `meta.source_run_id` equals the blocked source run id.
- response `meta.agent_action_type == "plan_recovery_tools"`.
- persisted assistant message has the same `meta`.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Expected: fails because the response and message currently do not include recovery-preview metadata.

## Task 2: Recovery Preview Metadata

- [x] **Step 1: Add response metadata**

Modify `_handle_dialog_recovery_preview()` in `backend/app/api/dialogs.py`:
- build `response_meta = {"agent_run_id": run.id, "source_run_id": output.get("source_run_id"), "agent_action_type": "plan_recovery_tools"}`.
- pass it into `ChatOut(meta=response_meta, ...)`.

- [x] **Step 2: Persist message metadata**

Modify the assistant `_save_message()` call in `_handle_dialog_recovery_preview()`:
- pass `meta=response_meta`.

- [x] **Step 3: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Expected: passes.

## Task 3: Regression, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_recovery_preview -q
```

Expected: selected tests pass.

- [x] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: diff check passes; secret scan returns no matches.

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase154-recovery-response-meta.md`.

- [x] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/api/dialogs.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase154-recovery-response-meta.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase154-recovery-response-meta.md
git commit -m "feat: expose recovery preview response metadata"
git push
```
