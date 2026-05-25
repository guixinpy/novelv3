# Phase 23 Compression Retry and Chapter 10 Report

## Summary

Phase23 strengthened the Agent-owned chapter compression path and continued the dogfood novel from Chapter 9 to Chapter 10.

Completed:

- Added bounded retry for `compress_chapter_to_target`.
- Added retry prompts that distinguish under-target and over-target failed candidates.
- Added trace-per-attempt behavior with failed attempt summaries.
- Added deterministic under-target repair from source text for near-target candidates.
- Added deterministic over-target sentence trim for near-target candidates while protecting opening and ending sentences.
- Compressed Chapter 9 from 2433 to 2015 words.
- Reviewed and analyzed Chapter 9 with no quality blockers.
- Expanded the outline window for Chapter 10 and generated Chapter 10.
- Cleared all actionable world-model proposals produced by Chapter 9 and Chapter 10 analysis.

Not completed:

- Chapter 10 remains over target at 2878 words.
- Chapter 10 compression still failed after 3 attempts; best model candidate remained 2822 words, outside the deterministic trim threshold.

## Code Changes

- Modified `backend/app/core/chapter_compression.py`.
  - Added `MAX_COMPRESSION_ATTEMPTS = 3`.
  - Added retry-aware compression prompts.
  - Created one `AIModelCallTrace` per compression attempt.
  - Added failed attempt metadata to blocked and successful outputs.
  - Added near-under-target deterministic repair from source sentences.
  - Added near-over-target deterministic sentence trimming.
- Modified `backend/tests/test_writing_agent_runs.py`.
  - Added retry success test.
  - Added retry exhaustion test.
  - Added near-under-target source repair test.
  - Added near-over-target deterministic trim test.

## RED/GREEN Evidence

Initial RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_under_target_retry tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion -q
```

Result: `2 failed`; current implementation stopped after the first out-of-range candidate and did not expose attempt metadata.

Retry GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_under_target_retry tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion -q
```

Result: `2 passed in 0.27s`.

Near-under-target RED/GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_near_target_candidate_from_source -q
```

Result before implementation: failed with blocked status. Result after implementation and threshold adjustment: `1 passed in 0.19s`.

Near-over-target RED/GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_near_over_target_candidate -q
```

Result before implementation: failed with blocked status. Result after implementation: `1 passed in 0.20s`.

Compression regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_then_review_clears_over_target_warning tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_direct_followup_generation tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_under_target_retry tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_near_target_candidate_from_source tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_near_over_target_candidate -q
```

Result: `9 passed in 0.89s`.

T2 backend verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result: `142 passed in 10.12s`.

Hygiene:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
git status --short --branch
```

Result:

- `git diff --check`: exit 0; Git reported only a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`.
- Secret scan: no matches.
- Git status: only intended Phase23 implementation, tests, plan, and report files changed, with the existing Phase23 plan commit ahead of origin.

## Dogfood Evidence

Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

### Chapter 9 Compression

Failed attempts before final repair:

- `187b6016-57ea-42ea-acc3-56ca03425249`: blocked after 3 attempts; last candidate 1968 words.
- `90fa7418-134e-434f-b714-49527b0a1f2b`: blocked after 3 attempts; last candidate 1879 words.
- `b1fc66f6-587f-4e91-8d8c-eb05bad22427`: blocked after 3 attempts; model repeatedly returned 2433 words.

Successful run:

- `c4bc7194-4b2a-4bee-952f-1faf9389f61a`
- Result: completed.
- Word count: 2433 -> 2015.
- Attempt count: 1.
- `deterministic_repair_applied=True`.
- `deterministic_trim_applied=False`.
- Revision: `5a17e58c-da4c-4fd2-87f6-4fafc0ef8b91`.
- Trace: `b1e4be7f-47c6-450e-8875-959cb910959c`.

### Chapter 9 Review and World Model

- Review/analyze run: `db6e973e-f7a4-4452-b9e7-f5932bb319cd`.
- Review result: ready, finding count 0, blocker count 0.
- Analysis created 1 actionable proposal.
- Draft/apply runs: `6c48f42f-741b-4c56-9d24-7dad2b70fc88`, `7645a0c9-a7cc-47b4-961b-a8752f07dbc2`.
- Decision: rejected `mentioned_in_chapter` metadata proposal.
- After actionable items: 0.

### Chapter 10 Generation

- Initial preflight run: `149156fb-87db-4829-95f4-039cf225ad12`.
- Result: blocked because Chapter 10 outline was missing.
- Outline expansion run: `e71f6f0d-8989-4319-97c5-3f7da4fb1830`.
- Result: added Chapter 10; preflight ready with repeated length drift warning.
- Generation/review/analyze run: `ace2a5f4-36cb-438b-8b7a-bde4e9f66b3a`.
- Chapter 10 title: `空白信纸`.
- Word count: 2878.
- Review findings:
  - `chapter_over_target`, severity `blocker`.
  - `pending_world_model_proposals`, severity `warning`, 6 proposals.
- Draft/apply runs: `43be33af-d44a-4942-8b37-a8431403489c`, `f8629c60-051c-41bb-8b2f-0cb98958d9ea`.
- Applied guarded proposal decisions: 6.
- After actionable items: 0.

### Chapter 10 Compression

- Compression run: `b8f144f6-1200-4ef8-9935-8e95e101f0f3`.
- Result: blocked after 3 attempts.
- Previous word count: 2878.
- Best/last candidate word count: 2822.
- Failed attempt trace ids:
  - `bc1d66f1-c926-4dee-a537-4b6c8eeacc24`
  - `fb863cb0-ea98-4b19-bfef-1493b471abea`
  - `febf39ab-c26f-4973-87b7-96d734f55565`
- Chapter 10 remains a Phase24 blocker.

## Current Novel State

Fresh database check:

- Project current word count: 25894.
- Pending actionable world-model proposals: 0.
- Chapter 1 `雾中回声`: 3735.
- Chapter 2 `第2章`: 3511.
- Chapter 3 `雾中童谣`: 3080.
- Chapter 4 `顾衍的警告`: 1861.
- Chapter 5 `空白信的秘密`: 2482.
- Chapter 6 `黑市雾晶`: 2165.
- Chapter 7 `苏晚晴的梦境`: 2025.
- Chapter 8 `废弃实验室`: 2142.
- Chapter 9 `暗河引路`: 2015.
- Chapter 10 `空白信纸`: 2878.

## Decisions

- Bounded retry is now part of the compression tool, but final writes remain guarded by the target range.
- Deterministic under-target repair is allowed only for near-target candidates and restores source sentences instead of inventing new content.
- Deterministic over-target trim is allowed only for near-target candidates and protects opening/ending sentences.
- Chapter 10 is not force-trimmed because the overage is too large for the current deterministic trim safety boundary.

## Phase24 Recommendation

Phase24 should focus on robust over-target repair for larger chapters:

- Add a stronger over-target retry prompt that computes required cut size and explicitly forbids returning the source unchanged.
- Consider a paragraph-level planner for large compression rather than sentence-level deterministic trimming.
- Add tests for persistent over-target candidates around 2800 -> 2200 words.
- Compress Chapter 10 after improving that path.
- Then continue Chapter 11 only after Chapter 10 has no length blocker and proposal pressure is clear.
