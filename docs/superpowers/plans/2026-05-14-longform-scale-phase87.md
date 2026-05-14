# Longform Scale Phase 87: Scalable Dialog Trace Clearing

## Goal

Clear long dialog histories without materializing every `dialog_messages.id` in Python. Longform writing sessions can produce large histories, so cleanup paths need to be database-side batch operations.

## Change

- Added a regression test with 250 dialog messages and an external trace linked to those messages.
- Replaced the clear-path message id list load with a SQL subquery.
- Kept dialog-owned trace deletion behavior unchanged.
- Kept external trace safety by detaching `request_message_id` and `response_message_id` via bulk updates.

## Verification

- Red: `python -m pytest backend/tests/test_model_call_traces.py -k "without_materializing_message_ids" -q --basetemp .tmp/pytest`
- Green: `python -m pytest backend/tests/test_model_call_traces.py -k "without_materializing_message_ids" -q --basetemp .tmp/pytest`
- Trace suite: `python -m pytest backend/tests/test_model_call_traces.py -q --basetemp .tmp/pytest`
- Dialog suite: `python -m pytest backend/tests/test_dialogs.py -q --basetemp .tmp/pytest`
