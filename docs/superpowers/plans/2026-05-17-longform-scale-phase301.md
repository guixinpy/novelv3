# Longform Scale Phase 301 - Cover Continuous Writing Worker Smoke

## Goal

Add scale smoke coverage for the continuous writing worker path, not only memory, retrieval, context, and synthetic task progress.

## Finding

The existing longform smoke validated a 1000 chapter synthetic project, batched task progress, retrieval reindexing, context assembly, and narrative windows. It did not execute `build_generate_chapter_work()`, so regressions in continuous writing range progression could slip past the scale gate.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_writing_worker_range -q
```

Observed failure:

```text
KeyError: 'writing_worker'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_writing_worker_range -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_stage_timings backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_writing_worker_range backend\tests\test_longform_scale.py::test_longform_scale_smoke_uses_batched_task_progress -q
```

Observed result:

```text
1 passed
4 passed
```

## Change

- `run_longform_scale_smoke()` now optionally executes a real `generate_chapter` chapter-range task through `build_generate_chapter_work()`.
- The smoke uses a local fake chapter generator to avoid external model calls while keeping task progress and writing state transitions real.
- The report now includes a compact `writing_worker` block and a `writing_worker` timing stage.
- The batched synthetic progress test can disable worker smoke to keep its assertion focused on batched checkpoint writes.

## Scale Smoke

Full 1000 chapter smoke with worker coverage passed:

```powershell
backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --target-chapter 500 --cleanup --max-elapsed-ms 30000 --max-stage-ms seed_project=15000 --max-stage-ms memory_rebuild=10000 --max-stage-ms retrieval_reindex=15000 --max-stage-ms context_build=10000 --max-stage-ms writing_worker=10000
```

Observed key results:

```text
total_words: 1000000
writing_worker.status: completed
writing_worker.progress.completed_count: 1000
writing_worker.pending_chapter_count: 0
writing_worker.state.status: completed
writing_worker timing: 3393 ms
elapsed_ms: 12214
```

## Verification

Full phase gate passed:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` - 692 passed
- `npm run build` - passed
- `npm run test:unit -- --run` - 440 passed
- `git diff --check` - passed
- DeepSeek key scan - `NO_MATCH`
