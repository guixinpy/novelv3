# Longform Scale Phase 69

## Goal

Prevent repeated longform smoke runs from permanently polluting the local database with synthetic million-word projects.

## Success Criteria

1. The smoke CLI accepts `--cleanup`.
2. Cleanup runs after report generation, including threshold-failure paths.
3. Existing threshold parsing behavior remains unchanged.
4. CLI tests and a real small smoke run with cleanup pass.

## Steps

1. Add a failing CLI test for `--cleanup`.
2. Add the cleanup flag and cleanup helper.
3. Re-run CLI tests.
4. Run a real small smoke command with `--cleanup`.
