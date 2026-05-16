# Phase 245 - Faster Retrieval Term Compaction

## Goal

Reduce full reindex cost for million-word projects without changing retrieval
semantics. Profiling showed the remaining bottleneck is SQLite bulk writes, but
retrieval term compaction still spent measurable CPU repeatedly classifying CJK
tokens.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_retrieval.py -q -k "avoid_repeated_full_cjk_token_checks"`
  - Failed with `606 <= 4`, confirming the current term compaction path repeatedly
    ran the full CJK token check.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_retrieval.py -q`
    passed with `43 passed`.

## Changes

- Added a cheap CJK retrieval n-gram shape check for `_indexable_retrieval_terms`.
- Preserved the existing rule: when CJK trigrams exist, do not persist CJK
  bigrams as lexical index rows.
- Kept retrieval behavior covered by existing search and lexical term tests.

## Scale Smoke

- Command:
  - `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
- Result:
  - `total_words`: 1,000,000
  - `elapsed_ms`: 8,391
  - `retrieval_reindex`: 7,635 ms
  - `total_documents`: 2,061
  - `total_chunks`: 3,061
  - `total_terms`: 249,022

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
