# Longform Scale Phase 50

## Goal

Keep Athena longform maintenance diagnostics cheap on thousand-chapter projects by avoiding wide ORM loads.

## Success Criteria

1. Diagnostics still reports stale/current state correctly.
2. The diagnostics path does not select chapter content.
3. The diagnostics path does not select longform memory summary or metadata.
4. The diagnostics path does not select retrieval document metadata or content hashes.
5. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a SQL projection regression test for maintenance diagnostics.
2. Narrow the longform memory query to `id`, `scope_key`, and `updated_at`.
3. Narrow the retrieval document query to `source_ref`, `source_id`, `updated_at`, and `id` for ordering.
4. Run targeted and full verification.
