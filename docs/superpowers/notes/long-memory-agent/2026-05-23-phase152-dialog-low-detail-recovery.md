# Phase152 Dialog Low-Detail Recovery Report

## Summary

Low-detail dialog continuation now checks for a recoverable blocked/failed Writing Agent run before creating a normal chapter pending action. When such a run exists, the dialog path creates a `dialog_auto_plan` Writing Agent run and executes the read-only `describe_agent_tools -> plan_recovery_tools` preview chain.

The normal chapter continuation path remains unchanged when no recoverable run exists.

## Changes

- Exposed `latest_recoverable_run_id()` from the Writing Agent planner so dialog control-plane code can share the same recovery selection rule as planner auto-plan.
- Added a narrow `_is_low_detail_continue_text()` guard in `backend/app/api/dialogs.py`.
- Added `_handle_dialog_recovery_preview()` to create and execute a read-only recovery preview run from dialog.
- Persisted the assistant recovery-preview message with `action_result.type == "plan_recovery_tools"` and the preview payload for message history/UI consumers.
- Added regression coverage for `"继续吧"` preferring recovery preview only when a recoverable blocked run exists.

## Validation

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Result: failed because `"继续吧"` still created a `preview_chapter` pending action.

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Result: `1 passed in 0.21s`.

Targeted regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_creates_pending_chapter_action backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_uses_first_unwritten_outline_chapter backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_recovers_latest_blocked_run_from_goal -q
```

Result: `4 passed in 0.48s`.

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result: diff check passed; secret scan found no matches.

## Long-Goal Implication

This phase moves another low-detail user utterance from static intent routing into Agent control-plane behavior. The important constraint is preserved: the system previews recovery tools but does not execute write/recovery tools without the existing confirmation gates.

## Next Recommendation

Add a small user-facing message-history/view model test for recovery-preview `action_result_view`, so the frontend can present these Agent recovery previews consistently with other tool results.
