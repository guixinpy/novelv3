# Phase 24 Large Over-Target Compression and Chapter 11 Report

## Summary

Phase24 fixed the larger over-target compression blocker exposed by Chapter 10 and continued the dogfood novel to Chapter 11.

Completed:

- Added a large-overage deterministic trim path for over-target compression candidates.
- Improved over-target retry guidance with required cut size and an explicit no-unchanged-candidate instruction.
- Compressed Chapter 10 from 2878 to 2292 words.
- Reviewed Chapter 10 after compression with no findings or blockers.
- Generated Chapter 11 `隐形墨水` at 2285 words, inside the 2000-2300 target range.
- Resolved all actionable world-model proposals produced by Chapter 11.

Remote status:

- Local `main` is ahead of `origin/main` because GitHub HTTPS push was still failing before this phase with connection reset / port 443 timeout.
- Push should be retried at the end of this phase.

## Code Changes

- Modified `backend/app/core/chapter_compression.py`.
  - Added `LARGE_OVER_TRIM_MAX_OVERAGE = 900`.
  - Added `TRIM_PROTECTED_EDGE_SENTENCE_COUNT = 2`.
  - Broadened deterministic over-target trim to handle larger overages while protecting first/last edge sentences.
  - Kept dialogue and protected plot terms high-ranked for retention.
  - Improved retry prompt for over-target candidates with explicit required cut size and no unchanged return.
- Modified `backend/tests/test_writing_agent_runs.py`.
  - Added `test_agent_compress_chapter_to_target_trims_large_over_target_candidate`.

## RED/GREEN Evidence

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_large_over_target_candidate -q
```

Result: failed with blocked run status because the large over-target candidate exceeded the existing deterministic trim threshold.

GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_large_over_target_candidate -q
```

Result: `1 passed in 0.21s`.

Compression regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_then_review_clears_over_target_warning tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_direct_followup_generation tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_under_target_retry tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_after_retry_exhaustion tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_repairs_near_target_candidate_from_source tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_near_over_target_candidate tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_trims_large_over_target_candidate -q
```

Result: `10 passed in 0.99s`.

T2 backend verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result: `143 passed in 10.45s`.

Hygiene:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
git status --short --branch
```

Result:

- `git diff --check`: exit 0; Git reported only a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`.
- Secret scan: no matches.
- Git status: only intended Phase24 implementation, tests, plan, and report files changed; branch remains ahead of origin because earlier push attempts failed.

## Dogfood Evidence

Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

### Chapter 10 Compression

- Run: `7f176132-8f3-4383-a597-b460a98996bb`.
- Result: completed.
- Chapter: `空白信纸`.
- Word count: 2878 -> 2292.
- Attempt count: 1.
- `deterministic_repair_applied=False`.
- `deterministic_trim_applied=True`.
- Revision: `34f649bf-0451-41be-ab6e-31c52afc3887`.
- Trace: `bec0e99f-a271-421c-80ad-bf57d632c09c`.

### Chapter 10 Review and World Model

- Run: `d689fd43-a5b0-4bdd-aaca-1c1b00e852a8`.
- Review result: ready.
- Finding count: 0.
- Blocker count: 0.
- World-model analysis: completed.
- Pending actionable proposals after analysis: 0.

### Chapter 11 Generation

- Preflight run: `d66b2918-fa6b-4130-bc60-717f46546fe8`.
- Result: blocked because Chapter 11 outline was missing.
- Outline expansion run: `98f233d8-752b-486e-a4cf-bc6bbcff9677`.
- Result: added Chapter 11; preflight ready with repeated length drift warning.
- Generation/review/analyze run: `b51cfa1d-850b-4eb1-8855-04c3ac7edf20`.
- Chapter: `隐形墨水`.
- Word count: 2285.
- Length decision: within target, accepted.
- Review result: warning only for pending world-model proposals; blocker count 0.
- Draft/apply runs: `cdd675b5-7970-48dd-96ae-69158a6163fb`, `63e1141f-adfc-4efb-b4cf-8735eb8e2812`.
- Applied guarded decisions: 7.
- After actionable items: 0.

## Current Novel State

Fresh database check:

- Project current word count: 27593.
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
- Chapter 10 `空白信纸`: 2292.
- Chapter 11 `隐形墨水`: 2285.

## Decisions

- Large deterministic trim is capped at 900 over target, not unbounded.
- The first and last two sentences are protected for larger trims.
- Final target-range guard remains unchanged; no out-of-range candidate can write.
- We did not address older over-target Chapters 1-3 and 5 in this phase to keep scope focused.

## Phase25 Recommendation

Phase25 should reduce repeated future length drift at generation time, not only after compression:

- Tune chapter-generation length calibration so the model produces 2000-2300 words more reliably.
- Add tests for generation feedback prompt content when repeated over-target history exists.
- Continue with Chapter 12 only after confirming Chapter 11 remains clean and proposal pressure is zero.
- Plan a separate cleanup phase for old over-target Chapters 1-3 and 5.
