# Phase81 Plan: Continuity And World Signal

## Phase Goal

Turn the concrete Chapter 25 dogfood findings into focused Agent capabilities:

1. detect adjacent-chapter transition gaps and identifier semantic drift during continuity review;
2. promote high-value chapter facts above low-value extracted metadata in Athena world-model proposals.

## Why This Phase

Phase80 proved the Agent can continue from low-detail input, expand a missing outline, generate Chapter 25, and close proposal pressure. It also exposed two stability gaps:

- continuity review missed a mild Chapter 24 -> Chapter 25 location/time jump;
- continuity review missed the semantic drift risk around `G-07`;
- Athena proposals over-emphasized `presence_count`, `mentioned_in_chapter`, and location co-occurrence while missing high-value plot facts.

## Scope

### Continuity Review

Modify `backend/app/core/chapter_continuity_review.py`.

Add warning-level findings:

- `adjacent_chapter_transition_gap`
  - compares only Chapter N-1 and Chapter N;
  - looks at previous ending and current opening;
  - warns when location/time markers shift without an explicit transition phrase;
  - does not block writing.

- `identifier_semantic_drift`
  - supports identifiers like `G-07`, `E-0047`, and `EV-2045-0812-07`;
  - classifies local context into known semantic kinds such as `evidence_locker`, `project_number`, `experiment_code`, `event_record`;
  - warns only when the same identifier moves between two known semantic kinds;
  - records whether the current chapter frames the new meaning as a hypothesis.

Tests go near the existing `test_agent_review_chapter_continuity_*` group in `backend/tests/test_writing_agent_runs.py`.

### Athena Proposal Signal

Modify:

- `backend/app/core/athena_chapter_candidates.py`
- `backend/app/core/athena_longform.py`
- `backend/app/core/world_proposal_review_queue.py`

Add high-value deterministic candidates:

- `identifier_meaning_hypothesis`
  - captures a character's hypothesis that an identifier has a new meaning;
  - must preserve speaker/hypothesis/evidence and not become confirmed truth.

- `access_permission_anomaly`
  - captures identity/permission anomalies such as Lin Shen's iris opening a restricted door.

- `investigation_lead`
  - captures actionable investigation leads such as Zhou Mingyuan / Qingdaofu.

Prioritize these predicates in proposal review without reading heavy JSON fields.

Tests:

- add `test_analyze_chapter_creates_high_value_plot_signal_candidates` in `backend/tests/test_athena_longform.py`;
- add or adjust queue tests in `backend/tests/test_world_frontend_api.py`;
- add resolution-draft guard in `backend/tests/test_writing_agent_runs.py` if the new predicates appear in default resolver behavior.

## Verification Level

T1/T2 related verification:

- focused continuity tests;
- focused Athena longform tests;
- proposal queue tests;
- world proposal resolution draft tests if touched;
- one live Chapter 25 re-analysis or read-only check if useful and safe.

No frontend validation is needed unless frontend files change.

## Not Doing

- No schema migration.
- No LLM-based extraction.
- No automatic approval of high-value facts.
- No broad rewrite of Athena proposal intake.
- No Chapter 26 generation until these checks are in place.
