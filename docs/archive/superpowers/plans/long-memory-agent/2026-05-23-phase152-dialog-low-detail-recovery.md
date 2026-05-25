# Phase152 Dialog Low-Detail Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let low-detail dialog input such as "继续吧" prefer a read-only Writing Agent recovery preview when the latest project run is recoverably blocked.

**Architecture:** Add a narrow dialog control-plane bridge before normal text-intent pending action creation. It reuses the planner's recoverable-run lookup and executes an auto-planned `describe_agent_tools -> plan_recovery_tools` run, while preserving existing chapter continuation behavior when no recoverable run exists.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest, existing dialog endpoint and Writing Agent run service.

---

## Scope

In scope:
- Detect only low-detail continuation text such as "继续吧".
- If the project has a blocked/failed Writing Agent run with `agent_tool_result.recovery.status == "recommended"`, create and execute a read-only recovery-preview Writing Agent run.
- Persist the assistant message with an `action_result` containing the recovery preview data.
- Keep the existing `preview_chapter` pending-action path unchanged when no recoverable run exists.

Out of scope:
- Automatically executing recovery tools.
- Broad natural-language recovery inference for detailed chapter requests.
- Frontend UI changes.
- Changing existing approval and execution gates.

## Files

- Modify: `backend/app/services/writing_agent/planner.py`
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/tests/test_dialogs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase152-dialog-low-detail-recovery.md`

## Task 1: RED Test

- [x] **Step 1: Add failing dialog test**

Add `test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists` in `backend/tests/test_dialogs.py`:
- seed setup, storyline, and outline so normal "继续吧" could create `preview_chapter`.
- create a blocked `WritingAgentRun`.
- create a blocked `WritingAgentStep` whose output contains `agent_tool_result.recovery.status == "recommended"`.
- call `/api/v1/dialog/chat` with text `"继续吧"`.
- assert:
  - response has no `pending_action`.
  - no `PendingAction` is persisted.
  - a new dialog auto-plan `WritingAgentRun` was created.
  - the run planner intent is `recover_blocked_run`.
  - the run tools are `["describe_agent_tools", "plan_recovery_tools"]`.
  - the assistant message stores `action_result.type == "plan_recovery_tools"` and references the blocked source run.

- [x] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Expected: fails because current dialog routing creates a `preview_chapter` pending action for `"继续吧"`.

## Task 2: Dialog Recovery Bridge

- [x] **Step 1: Expose recoverable-run lookup**

Modify `backend/app/services/writing_agent/planner.py`:
- rename `_latest_recoverable_run_id` to `latest_recoverable_run_id`.
- update `_build_recover_blocked_run_plan()` to call the public helper.

- [x] **Step 2: Add narrow low-detail continuation guard**

Modify `backend/app/api/dialogs.py`:
- import `WritingAgentStep`, `WritingAgentRunCreate`, `WritingAgentRunService`, and `latest_recoverable_run_id`.
- add `_is_low_detail_continue_text(text)` with exact/narrow matches.
- after saving the user text and before normal `IntentRouter` preview handling, if the text is low-detail and `latest_recoverable_run_id(...)` returns a run id, invoke the recovery-preview handler.

- [x] **Step 3: Add recovery-preview handler**

Modify `backend/app/api/dialogs.py`:
- build `WritingAgentRunCreate(goal="恢复上一轮阻塞", entrypoint="dialog_auto_plan", input={"auto_plan": True, "intent": "recover_blocked_run"})`.
- call `WritingAgentRunService.build_auto_plan_tools(...)`.
- create the run with the current dialog id and request message id.
- execute the run.
- read the latest step output.
- save an assistant message with `action_result.type == "plan_recovery_tools"`.
- return `ChatOut` with `pending_action=None` and an idle UI hint.

- [x] **Step 4: Run GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Expected: passes.

## Task 3: Regression, Report, Commit

- [x] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_creates_pending_chapter_action backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_uses_first_unwritten_outline_chapter backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_recovers_latest_blocked_run_from_goal -q
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

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase152-dialog-low-detail-recovery.md` with:
- change summary.
- validation evidence.
- current long-goal implication.
- next recommended phase.

- [x] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/planner.py backend/app/api/dialogs.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase152-dialog-low-detail-recovery.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase152-dialog-low-detail-recovery.md
git commit -m "feat: prefer recovery preview for low detail continue"
git push
```
