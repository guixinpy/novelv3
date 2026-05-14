# Phase 155 - Harden SQLite runtime pragmas

## Goal

Improve Windows/local SQLite stability for longform writing workloads.

## Why

The app uses SQLite by default. Long sessions combine foreground UI reads, background generation tasks, retrieval indexing, world-model writes, and diagnostics. File-backed SQLite should use runtime pragmas that reduce lock contention and avoid short busy failures.

## TDD

RED:

- Added a temporary file-backed SQLite engine test.
- The test asserts connected file databases enable foreign keys, WAL journal mode, at least 30 seconds of busy timeout, and synchronous NORMAL.
- It failed because only foreign keys were configured and journal mode stayed `delete`.

GREEN:

- The existing SQLite connect hook now also sets `busy_timeout=30000`, `journal_mode=WAL`, and `synchronous=NORMAL`.
- The hook still applies to the app engine and test engines that call `enable_sqlite_foreign_keys`.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_database_url.py::test_sqlite_file_connections_enable_longform_runtime_pragmas -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_database_url.py backend\tests\test_world_profiles.py -q` -> 31 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 577 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 8,761 ms, elapsed 9,550 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
