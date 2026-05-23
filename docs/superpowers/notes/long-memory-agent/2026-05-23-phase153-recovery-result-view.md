# Phase153 Recovery Result View Report

## Summary

Dialog message history now returns a stable `action_result_view` for `plan_recovery_tools` recovery previews. The view uses Chinese labels and compact details instead of exposing only the raw tool name.

## Changes

- Added `plan_recovery_tools` to `TYPE_LABELS`.
- Added recovery-preview-specific labels:
  - success/completed: `恢复预览已生成`
  - failed: `恢复预览失败`
- Added detail items for:
  - source run id.
  - recovery status.
  - execution policy.
  - recovery tool count.
- Added a message-history regression test that verifies `DialogMessageService.list_messages()` returns this view.

## Validation

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_recovery_preview -q
```

Result: failed because current label was `plan_recovery_tools执行成功` and no recovery detail items were produced.

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_recovery_preview -q
```

Result: `1 passed in 0.15s`.

Targeted regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_recovery_preview backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_approval_required backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Result: `3 passed in 0.39s`.

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result: diff check passed; secret scan found no matches.

## Long-Goal Implication

Recovery preview is now not only planned by the Agent control plane, but also shaped for stable user-facing history. This reduces frontend coupling to raw tool payloads and makes Agent orchestration steps easier to inspect.

## Next Recommendation

Extend the dialog recovery path with a direct `/agent-runs` reference or UI hint metadata so the frontend can navigate from a recovery preview message to the corresponding Writing Agent run detail.
