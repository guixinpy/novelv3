# Phase 6 Agent Safety Gates

## Runtime

- Date: 2026-05-18.
- Verification tier: T1 plus T2 runtime dogfood preflight/backfill.
- Backend base URL: `http://127.0.0.1:8001`.
- Secret handling: the model API key was used only as a runtime environment variable and was not written to source, docs, or `.env`.

## Implementation

- Added historical outline gap detection:
  - generated chapters with no outline entry are now visible in Agent preflight.
  - the check only looks at already generated chapters before the target chapter.
- Added deterministic outline backfill:
  - Agent tool: `backfill_outline_gaps`.
  - backfills missing outline entries from existing `ChapterContent` rather than asking the model to invent a retroactive plan.
- Added duplicate Athena-analysis skip:
  - if a `generate_chapter` step already returned completed `athena_analysis`, a following same-run `analyze_chapter_world_model` step is skipped with provenance.
- Added repeated length-drift policy diagnostics:
  - repeated same-direction drift count >= 3 returns `requires_policy_review` in generation output.
  - preflight now blocks when repeated length drift requires review.

## Dogfood Backfill

Dogfood project:

- Name: `雾港回声`.
- Project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

Initial Chapter 4 preflight:

- Agent run id: `140d063c-3b8e-4cba-93f1-60f7b1e17743`.
- status: `blocked`.
- blockers:
  - `missing_historical_outline_chapters`, chapter indexes `[2]`.
  - `repeated_chapter_length_drift`, reason `repeated_over_target`.

Backfill run:

- Agent run id: `466cbae4-6ff5-4561-8023-d0f547bf931b`.
- status: `success`.
- tool: `backfill_outline_gaps`.
- output:

```json
{
  "status": "completed",
  "outline_id": "49229388-f2d6-4bdb-bfa0-f4e8b9aa0beb",
  "backfilled_chapter_indexes": [2],
  "missing_before": [2]
}
```

Outline coverage after backfill:

- Chapter 1: `雾中回声`.
- Chapter 2: `第2章`, backfilled from existing content.
- Chapter 3: `雾中童谣`.
- Chapter 4: `顾衍的警告`.
- Chapter 5: `空白信的秘密`.
- Chapter 6: `黑市雾晶`.
- Chapter 7: `苏晚晴的梦境`.
- Chapter 8: `废弃实验室`.

## Chapter 4 Gate And Generation

Second Chapter 4 preflight:

- Agent run id: `38e75fe6-1b67-4c52-a597-eb2d6dc226ae`.
- status: `blocked`.
- historical outline gaps: ready, no missing generated chapter indexes.
- length policy:

```json
{
  "status": "blocked",
  "reason": "repeated_over_target",
  "repeated_drift_count": 3,
  "recommended_actions": ["revise_or_adjust_project_target"]
}
```

Chapter 4 was not generated in this phase.

Verification:

- `GET /api/v1/projects/{project_id}/chapters/4` returned `404`.
- This is intentional: Phase 6 exposed a policy blocker and stopped before writing more manuscript.

## Quality Review

Read-only dogfood quality review found these issues in Chapters 1-3:

- Chapter 1 and Chapter 2 disagree on whether Lin Shen and Su Wanqing just met or already have an established assistant/shelter relationship.
- Chapter 2 lacked an outline entry and therefore used the fallback title `第2章`.
- Chapter 3 introduces a fog-crystal fragment in Su Wanqing's pocket without clear transfer from Chapter 2.
- Chapter 3 advances too far beyond its outline by revealing material planned for later chapters, including Gu Yan, the underground lab, orphanage experiments, and fog-disaster causes.
- Gu Yan's role is inconsistent between setup and prose: former special-ops/intelligence broker versus active enforcement figure.
- Su Wanqing is 20 in setup, but Chapter 3 dialogue implies she is a minor.
- All first three chapters exceed the configured 1700-2300 word range.
- World-model proposal queue has 24 pending items, while canonical truth claims remain unmaterialized.

## Issues Found

- Backfilled Chapter 2 still has a generic title because the existing generated content title was already generic.
- Deterministic backfill is safer than model backfill, but its summary is only a short excerpt-derived placeholder.
- Chapter 3 likely needs review/revision before Chapter 4 should be generated.
- Pending world-model proposals are accumulating and need triage.
- Direct non-Agent writing paths may still bypass the new Agent preflight gates.

## Issues Fixed

- Agent preflight now catches generated chapters missing outline entries.
- Agent can deterministically backfill historical outline gaps from existing chapter content.
- Agent can avoid same-run duplicate Athena chapter analysis after `generate_chapter`.
- Repeated chapter-length drift is no longer a hidden warning; it is a structured preflight blocker.
- Dogfood project no longer has the Chapter 2 outline coverage gap.

## Verification

- TDD red check:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_blocks_when_generated_chapter_outline_gap_exists tests\test_writing_agent_runs.py::test_agent_backfill_outline_gaps_uses_existing_chapter_content_then_preflight_ready tests\test_writing_agent_runs.py::test_agent_skips_analyze_when_generate_step_already_auto_analyzed_same_chapter tests\test_writing_agent_runs.py::test_agent_chapter_length_decision_flags_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_preflight_blocks_when_repeated_over_target_drift_requires_review -q`.
  - Initial result: `5 failed`.
- T1 targeted after implementation:
  - Same command.
  - Result: `5 passed`.
- T1 Agent suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q`.
  - Result: `17 passed`.
- T1 related suite:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q`.
  - Result: `32 passed`.
- Diff hygiene:
  - Command: `git diff --check`.
  - Result: exit code `0`.
- Secret scan:
  - Command: `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`.
  - Result: no matches.
- Runtime:
  - Backend health on `8001`: `{"status":"ok"}`.
  - Preflight blocked before backfill.
  - Backfill run succeeded.
  - Preflight blocked after backfill only because of repeated length drift.
  - Chapter 4 endpoint returned `404`.

## Next Phase Recommendation

Phase 7 should focus on quality-review and revision before continuing generation:

- Add or use an Agent review tool for generated chapters, starting with Chapters 2 and 3.
- Turn review findings into structured revision tasks.
- Decide whether to revise Chapters 2-3 or adjust project chapter target/word target.
- Triage the 24 pending world-model proposals and materialize safe canonical facts.
- Add a plot-budget or outline-adherence check so one chapter cannot consume later chapter reveals.
- Generate Chapter 4 only after length policy and quality review blockers are cleared.
