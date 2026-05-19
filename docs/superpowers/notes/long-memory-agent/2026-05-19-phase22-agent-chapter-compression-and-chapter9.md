# Phase 22 Agent Chapter Compression and Chapter 9 Report

## Summary

Phase22 added an Agent-owned chapter compression tool and used it in the dogfood novel to repair the latest over-target drift before continuing generation.

The phase completed the core repair path:

- `compress_chapter_to_target` was added to the Writing Agent toolchain.
- Chapter 7 was compressed from 2670 to 2025 words after one safe blocked attempt.
- Chapter 8 was compressed from 2647 to 2142 words.
- Chapter 7/8 review and world-model analysis passed with no blockers and no new actionable proposals.
- Chapter 9 was generated after expanding the outline window.
- Chapter 9 remains over target at 2433 words; compression outputs were rejected because they fell below the target range, so no unsafe overwrite occurred.

## Code Changes

- Added `backend/app/core/chapter_compression.py`.
- Registered `compress_chapter_to_target` in `WritingAgentRunService`.
- Added tests for:
  - successful compression with revision and version records;
  - review after compression clearing `chapter_over_target`;
  - blocking direct follow-up generation until review;
  - skipping chapters already within target;
  - blocking compression when actionable world-model proposals exist.

## RED/GREEN Evidence

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review -q
```

Result: failed as expected with `ModuleNotFoundError: No module named 'app.core.chapter_compression'`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_updates_chapter_versions_and_requires_review tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_then_review_clears_over_target_warning tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_direct_followup_generation tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_skips_when_chapter_already_within_target tests\test_writing_agent_runs.py::test_agent_compress_chapter_to_target_blocks_pending_world_model_proposals -q
```

Result: `5 passed in 0.61s`.

T2 backend verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result: `138 passed in 9.74s`.

Hygiene:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
git status --short --branch
```

Result:

- `git diff --check`: exit 0; Git reported only a CRLF normalization warning for `backend/tests/test_writing_agent_runs.py`.
- Secret scan: no matches.
- Git status: only intended Phase22 files changed, with the existing Phase22 plan commit ahead of origin.

## Dogfood Evidence

Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

Chapter 7:

- First compression run: `29f9ebd9-24f7-42b4-81fb-c4ce2b950bbc`.
- Result: blocked safely, reason `compressed_content_outside_target`, model output 1168 words, no write.
- Retry compression run: `7f2d9d05-d9d3-48c1-a56b-d4adfb891d51`.
- Result: completed, 2670 -> 2025 words.

Chapter 8:

- Compression run: `7c91d6d6-7db8-4606-a92f-c351405ed011`.
- Result: completed, 2647 -> 2142 words.

Review/analyze:

- Run: `b1915d63-6144-47d4-8b9e-e4b9555d3073`.
- Chapter 7 review: ready, finding count 0, blocker count 0.
- Chapter 8 review: ready, finding count 0, blocker count 0.
- Chapter 7 world-model analysis: completed, created 0, skipped duplicates 3.
- Chapter 8 world-model analysis: completed, created 0, skipped duplicates 7.
- Pending actionable proposals after this step: 0.

Chapter 9:

- Initial preflight/generation attempt: `ce3ffd85-227a-41ed-ac90-fc0791e8fdc4`.
- Result: blocked because Chapter 9 outline was missing; length-policy warning remained.
- Outline expansion run: `76b5e6a3-e912-492c-b922-60d28b1bd221`.
- Result: added Chapter 9 outline, subsequent preflight ready with only repeated over-target warning.
- Generation run: `6a28efb8-7fe1-4dd6-9d81-1c468da4ecfa`.
- Result: generated Chapter 9 `暗河引路`, 2433 words; review had `chapter_over_target`, blocker count 0; analysis created 6 world-model proposals.
- Proposal decision run: `59db2d5f-884b-4c38-9c54-3dd4071af287`.
- Proposal apply run: `1c6b7fec-be96-4457-8d43-ad3cf3b4dd6d`.
- Result: 6 proposals applied, actionable proposals 0.
- Compression attempt: `7294b2f4-000d-4efb-9daa-7f4439306611`.
- Result: blocked safely, model output 1729 words, no write.
- Compression retry: `6f9b42ca-c36b-41c6-8ba8-71b3efdb22b8`.
- Result: blocked safely, model output 1745 words, no write.
- Final review/analyze run: `9b5168c0-03cb-4c8c-9af1-e6172dfc34bc`.
- Result: Chapter 9 still only has over-target warning, blocker count 0; analysis created no duplicate actionable pressure.

## Current Novel State

Fresh database check after dogfood:

- Project current word count: 23434.
- Pending actionable world-model proposals: 0.
- Chapter 1 `雾中回声`: 3735.
- Chapter 2 `第2章`: 3511.
- Chapter 3 `雾中童谣`: 3080.
- Chapter 4 `顾衍的警告`: 1861.
- Chapter 5 `空白信的秘密`: 2482.
- Chapter 6 `黑市雾晶`: 2165.
- Chapter 7 `苏晚晴的梦境`: 2025.
- Chapter 8 `废弃实验室`: 2142.
- Chapter 9 `暗河引路`: 2433.

## Decisions

- The compression tool writes only when output lands inside the configured target range. This prevented Chapter 7 and Chapter 9 from being overwritten by under-target model outputs.
- Prompt guidance was tightened for mild over-target chapters, but Chapter 9 showed that prompt-only control is not reliable enough for 600+ chapter scale.
- Chapter 9 is kept as generated because it has no quality blocker and no pending world-model proposal pressure, but its over-target warning remains explicit.

## Phase23 Recommendation

Phase23 should improve the compression repair loop before generating many more chapters:

- Add a bounded retry strategy for `compress_chapter_to_target` when the model under-shoots.
- Consider a second-pass "restore density" repair that can expand an under-target compressed candidate back into range before writing.
- Consider deterministic light-trim support for mild over-target cases, where only 100-200 words must be removed.
- Keep the safety guard that rejects out-of-range output.
- After the compression loop is stable, address older over-target Chapters 1-3 and 5, then continue Chapter 10 generation.
