# Longform Scale Phase 66

## Goal

Remove avoidable per-chapter transaction overhead from batch-style longform progress updates.

## Success Criteria

1. Background tasks can mark many completed chapter indexes with one commit.
2. Existing single-chapter progress behavior remains available.
3. The longform scale smoke path uses the batched progress method.
4. Targeted backend tests and a real 1000-chapter smoke command pass.

## Steps

1. Add a failing service test for one-commit batch progress.
2. Add a failing smoke test that rejects the single-chapter progress path.
3. Implement the batch progress method.
4. Wire the longform smoke runner to use the batch method.
5. Re-run targeted tests and the 1000-chapter smoke gate.
