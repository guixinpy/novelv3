# Phase 144 - Trace failure error truncation

## Goal

Bound model-call trace failure messages so upstream errors cannot store arbitrarily large response bodies in `ai_model_call_traces.error_message`.

## Why

Long-running novel generation can hit provider, network, or parsing failures. Some errors include large raw payloads. Trace messages and context blocks were already capped, but failure text was only sanitized, not length-limited.

## TDD

RED:

- `test_mark_trace_failed_truncates_large_error_message` created a trace and failed it with a large provider error.
- It failed because the full error was stored.

GREEN:

- Added `MAX_TRACE_ERROR_MESSAGE_CHARS`.
- `mark_trace_failed(...)` now uses existing `truncate_text(...)`, preserving secret redaction and adding the standard truncation notice.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_model_call_traces.py::test_mark_trace_failed_truncates_large_error_message -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_model_call_traces.py -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
