# Phase154 Recovery Response Metadata Report

## Summary

Dialog recovery-preview responses now include stable metadata for client navigation and history inspection. The same metadata is persisted on the assistant message.

## Changes

- Added `ChatOut.meta` for recovery-preview dialog responses:
  - `agent_run_id`
  - `source_run_id`
  - `agent_action_type`
- Persisted the same metadata in `DialogMessage.meta`.
- Extended the low-detail recovery-preview regression test to verify response and persisted metadata.

## Validation

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Result: failed because `body["meta"]` was `None`.

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists -q
```

Result: `1 passed in 0.21s`.

Targeted regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chat_text_low_detail_continue_prefers_recovery_preview_when_blocked_run_exists backend\tests\test_dialogs.py::test_get_messages_includes_action_result_view_for_recovery_preview -q
```

Result: `2 passed in 0.26s`.

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result: diff check passed; secret scan found no matches.

## Long-Goal Implication

The Agent recovery bridge now has a clearer contract for clients: response metadata points to the generated Agent run, while `action_result` remains the detailed payload. This is a small step toward treating Agent operations as first-class inspectable artifacts.

## Next Recommendation

Add a frontend-side affordance for recovery-preview messages that uses `meta.agent_run_id` or `action_result.data.agent_run_id` to open the Writing Agent run detail when that view is available.
