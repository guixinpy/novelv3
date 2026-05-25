# Phase81 Report: Continuity And World Signal

## Summary

Phase81 converted the Chapter 25 dogfood findings into two concrete Agent capability upgrades:

1. continuity review now warns about adjacent-chapter transition gaps and identifier semantic drift;
2. Athena chapter analysis now extracts high-value plot-signal proposals and prioritizes them ahead of low-value metadata in the review queue.

This phase did not generate Chapter 26. It intentionally stopped before generation because the new analysis surfaced high-risk Chapter 25 world-model proposals that should be reviewed first.

## Changes

### Continuity Review

Modified `backend/app/core/chapter_continuity_review.py`.

New warning findings:

- `adjacent_chapter_transition_gap`
  - compares only Chapter N-1 and Chapter N;
  - checks previous ending and current opening;
  - warns when time/location markers shift without an explicit transition cue;
  - does not block writing.

- `identifier_semantic_drift`
  - supports identifiers like `G-07`, `E-0047`, and `EV-2045-0812-07`;
  - classifies known local semantics such as `evidence_locker`, `project_number`, `experiment_code`, and `event_record`;
  - warns when the same identifier moves between known semantic meanings;
  - records whether the current chapter frames the new meaning as a hypothesis.

### Athena High-Value Plot Signals

Modified:

- `backend/app/core/athena_chapter_candidates.py`
- `backend/app/core/athena_longform.py`

New deterministic proposal predicates:

- `identifier_meaning_hypothesis`
  - captures identifier meaning changes such as `G-07` becoming a project/experiment code;
  - preserves hypothesis/evidence instead of treating it as confirmed truth.

- `access_permission_anomaly`
  - captures identity or permission anomalies such as a character's iris unlocking a restricted door.

- `investigation_lead`
  - captures actionable investigation leads such as `清道夫` and `周明远`.

The proposal bundle summary now says `世界事实候选` instead of `低风险世界事实候选`, because these candidates may be high-risk.

### Proposal Review Queue

Modified `backend/app/core/world_proposal_review_queue.py`.

- New high-value predicates are classified as high risk.
- High-risk predicates are ordered at the SQL query level before pagination.
- The ordering uses predicate fields only and does not read heavy JSON payloads.

### Guarded Resolution

The default world proposal resolution draft does not auto-decide these high-value predicates. They remain unclassified and should go through explicit review/planning.

## Runtime Dogfood Check

Re-ran Chapter 25 Athena analysis on live dogfood project:

- project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- chapter: `25`
- title: `暗流之下`

First runtime pass created 4 high-value proposals but exposed one false positive:

- false positive: `access_permission_anomaly` treated "打开终端查看虹膜门编号" as a permission anomaly.

Fix applied:

- access anomaly extraction now requires a cross-sentence window containing iris/eye/scan evidence and a door-open or validation signal.
- added a regression test to ensure iris-door references alone do not become permission anomalies.

Live DB cleanup:

- rejected the false positive item `8086ad0c-440c-4fb9-be72-0e65d4a79bea` with reviewer `writing_agent.phase81.runtime_fix`;
- re-ran Chapter 25 analysis;
- created corrected pending access anomaly item `369df335-ea3f-482b-8ad8-80b8c437e94c` for `char.林深`.

Live high-value pending queue after fix:

- `access_permission_anomaly`: Lin Shen iris/permission anomaly;
- `identifier_meaning_hypothesis`: `G-07`;
- `identifier_meaning_hypothesis`: `E-0047`;
- `investigation_lead`: `清道夫`.

Queue top clusters are all `high` and `individual`, ahead of low-value metadata.

## Continuity Dogfood Check

Re-ran Chapter 25 continuity review after the new rules:

- status: `warning`
- blocker count: `0`
- findings: `3`

Warnings:

- `EV-2045-0812-07` semantic drift from evidence/locker context to event record context;
- `E-0047` semantic drift from event record context to experiment code context;
- `G-07` semantic drift from evidence locker context to experiment code context.

This matches the Phase80 independent review: the issue is not an immediate blocker, but the Agent should treat these meanings as hypotheses or provide evidence before hardening them into world truth.

## Verification

Focused continuity tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -k "adjacent_transition_gap or explicit_adjacent_transition or identifier_semantic_drift" -q
```

Result:

- `3 passed, 155 deselected`

Related continuity/resolution tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -k "review_chapter_continuity or draft_world_model_proposal_resolution_decisions" -q
```

Result:

- `16 passed, 143 deselected`

Focused Athena and queue tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_longform.py -k "high_value_plot_signal or iris_door_reference or event_and_character_location or non_character_entity_mentions" -q
.venv\Scripts\python.exe -m pytest tests\test_world_frontend_api.py -k "proposal_review_queue" -q
```

Result:

- `4 passed, 12 deselected`
- `6 passed, 41 deselected`

T2 related full files:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_athena_longform.py tests\test_world_frontend_api.py -q
```

Result:

- `222 passed in 19.82s`

## Remaining Issues

1. High-value plot-signal extraction is still deterministic and pattern-based. It is useful for surfacing obvious issues, but not a complete semantic extractor.
2. `access_permission_anomaly` evidence windows are still approximate. The false-positive regression is covered, but later phases should improve evidence window selection.
3. Chapter 25 now has high-risk world-model proposals pending explicit review. The next phase should create or use an Agent path for reviewing these high-value candidates before Chapter 26.
4. Adjacent transition detection is conservative. It catches explicit marker shifts, not all narrative jump cuts.

## Next Phase Recommendation

Phase82 should focus on high-value proposal review:

- inspect the 4 live Chapter 25 high-risk proposals;
- design guarded review actions for `identifier_meaning_hypothesis`, `access_permission_anomaly`, and `investigation_lead`;
- avoid auto-approving role/identity truths without explicit evidence;
- after review pressure is handled, continue dogfood toward Chapter 26 with low-detail input.
