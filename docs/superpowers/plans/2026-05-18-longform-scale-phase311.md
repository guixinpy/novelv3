# Longform Scale Phase 311 - Record Post Generation Warnings

## Goal

Keep chapter generation resilient while making non-blocking maintenance failures visible in the model-call trace.

## Finding

Chapter generation intentionally does not fail when follow-up maintenance fails: consistency check, Athena analysis, retrieval indexing, longform memory refresh, and event emission are all secondary to saving the chapter. That behavior is correct for long writing runs, but silent failure makes later diagnosis difficult after hundreds or thousands of chapters.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_does_not_fail_when_longform_maintenance_fails -q
```

Observed failure:

```text
KeyError: 'post_generation_warning_count'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_does_not_fail_when_longform_maintenance_fails -q
```

Observed result:

```text
1 passed
```

## Change

- Chapter generation now collects non-blocking post-generation warnings.
- Successful traces append `trace_metadata.post_generation_warning_count` and `trace_metadata.post_generation_warnings` when a maintenance step fails.
- Warning entries include stage, error type, and sanitized/truncated message.
- The chapter response remains successful when maintenance fails.

## Verification

Stage gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q` -> `36 passed`

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `703 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `443 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
