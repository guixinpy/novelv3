# Phase 116 - Light Proposal Impact Scope Reads

## Goal
Keep proposal impact-scope calculation responsive when longform projects produce large candidate bundles and large existing truth claims.

## Changes
- Impact-scope candidate reads now project only `id`, `subject_ref`, `predicate`, and `chapter_index`.
- Existing truth lookups now project only `claim_id`.
- Snapshot content and impact-scope semantics are unchanged.

## Verification
- Added SQL-level regression coverage proving impact-scope calculation does not select heavy candidate/truth fields.
- Re-ran world proposal tests: `53 passed`.
- Re-ran world frontend API tests: `33 passed`.
- Re-ran the full backend pytest suite: `540 passed`.
