# Longform Scale Phase 310 - Trace Chapter Word Target Drift

## Goal

Make chapter generation traces record whether the generated chapter matched the project's planned chapter length.

## Finding

Phase 309 made word-count drift visible in the manuscript sidebar, but the backend model-call trace only stored prompt and token data. For long projects, that made it harder to diagnose when a model repeatedly under-writes or over-writes chapters relative to the project plan.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_records_model_call_trace -q
```

Observed failure:

```text
KeyError: 'chapter_word_target'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py::test_generate_chapter_records_model_call_trace -q
```

Observed result:

```text
1 passed
```

## Change

- Successful chapter-generation traces now include `trace_metadata.chapter_word_target`.
- The metadata records actual word count, project target word count, target chapter count, derived average/range, deviation from average, and `under` / `within` / `over` / `untracked` status.
- Existing chapter trace lookup and response behavior remain unchanged.

## Verification

Stage gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q` -> `36 passed`

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `703 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `443 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
