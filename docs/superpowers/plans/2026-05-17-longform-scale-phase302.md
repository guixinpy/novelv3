# Longform Scale Phase 302 - Cover Post-Generation Maintenance Smoke

## Goal

Make the scale smoke validate the incremental maintenance path that runs after a chapter is generated.

## Finding

The smoke covered full memory rebuilds, retrieval reindexing, context assembly, and continuous writing range progression. Real writing also performs per-chapter maintenance after every generated chapter: chapter retrieval indexing, long-form memory refresh, and long-form memory retrieval sync. Without smoke coverage, a thousand-chapter project could regress into stale or drifting retrieval documents even when full rebuilds still passed.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_post_generation_maintenance -q
```

Observed failure:

```text
KeyError: 'post_generation_maintenance'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_post_generation_maintenance -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_stage_timings backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_post_generation_maintenance backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_writing_worker_range backend\tests\test_longform_scale.py::test_longform_scale_smoke_uses_batched_task_progress -q
```

Observed result:

```text
1 passed
5 passed
```

## Change

- `run_longform_scale_smoke()` now simulates a target chapter update after retrieval indexing exists.
- The smoke executes real chapter retrieval indexing, long-form memory refresh, and long-form memory retrieval sync.
- The report includes `post_generation_maintenance` with chapter index, indexed chapter document count, memory scope counts, and before/after retrieval document totals.
- `timings_ms` includes a `post_generation_maintenance` stage.

## Verification

Full 1000 chapter smoke with post-generation maintenance passed:

```powershell
backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --target-chapter 500 --cleanup --max-elapsed-ms 30000 --max-stage-ms seed_project=15000 --max-stage-ms memory_rebuild=10000 --max-stage-ms retrieval_reindex=15000 --max-stage-ms context_build=10000 --max-stage-ms post_generation_maintenance=10000 --max-stage-ms writing_worker=10000
```

Observed key results:

```text
total_words: 1000000
post_generation_maintenance.chapter_index: 500
post_generation_maintenance.chapter_indexed.documents: 1
post_generation_maintenance.memory_updated_scope_count: 4
post_generation_maintenance.memory_synced_scope_count: 4
post_generation_maintenance.retrieval_total_documents_before: 2061
post_generation_maintenance.retrieval_total_documents_after: 2061
post_generation_maintenance timing: 1993 ms
elapsed_ms: 14326
```

Full phase gate passed:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` - 693 passed
- `npm run build` - passed
- `npm run test:unit -- --run` - 440 passed
- `git diff --check` - passed
- DeepSeek key scan - `NO_MATCH`
