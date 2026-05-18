# Phase 99 - Light Ontology Counts

## Goal

Keep Athena ontology pagination efficient for long projects by preventing total-count queries from selecting entity and rule JSON columns.

## Changes

- Ontology entity, relation, and rule totals now use explicit `count(id)` queries.
- Existing paginated ontology rows and response shape are unchanged.

## Verification

- Added SQL-level regression coverage proving ontology count queries do not select large character or rule JSON columns.
- Re-ran focused ontology tests and the complete world frontend API test file.
- Re-ran the full backend pytest suite.
