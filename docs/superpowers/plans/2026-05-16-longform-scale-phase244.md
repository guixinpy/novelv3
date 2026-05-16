# Phase 244 - Lightweight Recent Chapter Memory Context

## Goal

Keep long-form context assembly lightweight when injecting recent chapter memory.
The prompt only needs memory identity, scope, chapter range, title, summary, and
metadata, so the recent chapter query should not load full `LongformMemory` rows.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q -k "recent_chapters_projects_only_prompt_fields"`
  - Failed because the recent chapter memory query selected `project_id`, `status`, `created_at`, and `updated_at`.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q` passed with `41 passed`.

## Changes

- Projected recent chapter memories to prompt-required fields only.
- Added `LongformMemory.id.desc()` as a stable tie-breaker for the recent memory window.
- Preserved existing prompt section ordering from older to newer recent chapters.

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
