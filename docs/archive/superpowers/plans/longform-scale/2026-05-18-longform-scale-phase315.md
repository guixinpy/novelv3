# Longform Scale Phase 315 - Aggregate Writing Task Diagnostics

## Goal

Make range writing tasks summarize per-chapter generation diagnostics.

## Finding

Single-chapter traces now carry word-target drift and post-generation warning metadata, but continuous writing tasks still only reported progress. For long writing runs, the task result needs aggregate signals so users can see whether a batch produced short/long chapters or non-blocking maintenance failures.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_generate_chapter_work_summarizes_generation_diagnostics -q
```

Observed failure:

```text
KeyError: 'generation_diagnostics'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_generate_chapter_work_summarizes_generation_diagnostics -q
```

Observed result:

```text
1 passed
```

## Change

- Continuous chapter generation now reads each completed chapter's generation trace metadata.
- Background task `result.generation_diagnostics` aggregates word-target under/within/over/untracked counts.
- The task result also aggregates post-generation warning count and a bounded warning sample with chapter index, stage, error type, and message.
- Existing writing progress payload remains unchanged.

## Verification

Stage gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q` -> `28 passed`

Full gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `705 passed`
- `npm run build` in `frontend` -> passed
- `npm run test:unit -- --run` in `frontend` -> `445 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
