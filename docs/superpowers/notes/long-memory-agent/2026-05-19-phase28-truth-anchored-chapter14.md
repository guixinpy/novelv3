# Phase28 Truth Anchored Chapter 14 Report

## Scope

Phase28 generated and validated Dogfood Chapter 14 after Phase27 promoted the highest-risk continuity anchors into confirmed world facts.

The phase used the real writing loop as the driver:

1. verify confirmed facts are injected into Chapter 14 context;
2. generate Chapter 14;
3. resolve world-model proposal maintenance;
4. compress over-target content;
5. review quality, continuity, and world-model analysis;
6. patch code only for a repeatable tool failure exposed by dogfood.

## Context Gate

Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

`WorldContextAssembler.chapter_context_package(14)` contained all required stable facts:

```text
【已确认事实】: true
林深.father_name = 林建国: true
顾衍.military_tag_number = N-017: true
identifier.N-07.identifier_meaning: true
2045年8月12日: true
2045年8月9日: true
prompt_context_chars: 2202
```

No prompt/context injection fix was needed.

## Generation Evidence

Initial Chapter 14 generation run:

```text
run_id: 5ab8c91c-8f34-4a40-85e1-24fa09247596
status: success
chapter: 第14章《废弃实验室》
trace_id: f7923a8b-f43e-4bd0-8508-7e611d944288
word_count: 2706
quality_review: warning
continuity_review: ready, 0 findings
world_model_analysis: created 5 proposal items
```

The generated chapter was valid正文 and preserved the Chapter 13 hook into 林建国/废弃实验室, but exceeded the 2000-2300 target range.

Immediate compression was correctly blocked while proposals were pending:

```text
run_id: 20db14c9-8bdb-413e-96a6-7475ee6569a4
status: blocked
reason: pending_world_model_proposals
pending_world_model_proposal_count: 5
```

Proposal cleanup:

```text
draft_run_id: fbb24023-4f62-4416-9205-563d09489df4
draft_decision_count: 5
actions: event_summary -> mark_uncertain; mentioned_in_chapter/presence_count -> reject

apply_run_id: 363658d9-dd20-49c1-ae07-3e73b7e2dbba
before_actionable_items: 5
after_actionable_items: 0
applied_count: 5
```

## Tool Failure and Fix

After proposal cleanup, the first compression retry exposed a repeatable system issue:

```text
run_id: 421337e2-e164-48a4-bee4-15776d56542f
status: blocked
reason: compressed_content_outside_target
previous_word_count: 2706
target_min_word_count: 2000
target_max_word_count: 2300
attempts:
- 1600, under_target
- 1600, under_target
- 1597, under_target
deterministic_repair_applied: false
deterministic_trim_applied: false
```

Root cause: `compress_chapter_to_target` only repaired near-under-target model candidates and trimmed over-target model candidates. When the model repeatedly returned a substantially under-target candidate, the tool never attempted a safe deterministic trim from the original over-target chapter, even though the original was only moderately above target and structurally trim-able.

Fix:

- Added a TDD regression test for repeated under-target model candidates with a safe source-trim fallback.
- Updated `backend/app/core/chapter_compression.py` so the final under-target attempt can fall back to `_trim_over_target_candidate(chapter.content)` when the original chapter can be conservatively trimmed into range.
- Kept the blocking behavior for chapters that are too far over target or cannot be safely trimmed.

Targeted compression test command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k compress_chapter_to_target
```

Result:

```text
11 passed, 91 deselected in 1.39s
```

## Final Dogfood State

Compression after the fix:

```text
run_id: d30bd236-7be9-4690-98d6-c52e57026c51
status: success
revision_id: 8a4def5d-95a6-4d1a-9015-b32f58c208b3
previous_word_count: 2706
word_count: 2278
target_range: 2000-2300
deterministic_trim_applied: true
warnings: []
```

Compressed Chapter 14 tail:

```text
苏晚晴站在他身边，脸色苍白，但眼神坚定。“我们是一起的。”苏晚晴说。林深点了点头。他深吸一口气，伸手去推那扇门。门缓缓打开，灰蓝色的光涌出来，照亮了他们的脸。门后是一条向下的楼梯，黑暗而深邃，看不到尽头。林深迈出第一步，走进了那道光中。
```

Post-compression review:

```text
run_id: 1685f01f-38d8-477d-a937-f633e2f9db7d
quality_review: ready, 0 findings
continuity_review: ready, 0 findings
world_model_analysis: completed, created 0, updated 0, skipped duplicates 5
pending_actionable_proposals: 0
confirmed_fact_count: 5
```

## Subagent Review

Read-only subagent:

```text
agent_id: 019e3f72-9102-7a83-950f-6116dc056258
task: read-only Chapter 14 quality and stable-anchor review
```

Result:

- Chapter 14 is 2000+ words and has a clear closing hook through the opened door and downward stair.
- No hard violation of the stable facts was found.
- `N-07` is used as an experiment code / subject marker, not as 顾衍's military tag.
- `林建国` remains 林深's father.
- Dates `2045年8月12日` and `2045年8月9日` are not contradicted.

Subagent findings addressed in this phase:

- Fixed typo: `戴着眼睛` -> `戴着眼镜`.
- Renamed Chapter 14 from duplicate title `废弃实验室` to `门后回声`; the outline chapter title was updated to match.
- Softened a too-definitive `她是N-07` line to keep the reveal as `她和N-07有关`, reducing risk against the existing 顾衍/N-07 ambiguity.
- Refreshed Chapter 14 longform memory and synced longform-memory retrieval after the text/title edits.

Follow-up system issues:

- The automated quality/continuity review did not catch the typo, duplicate title, or outline drift. This should become a later review-rule phase rather than blocking Chapter 14.
- The Chapter 14 outline still describes a physical infiltration / patrol scene, while the generated chapter follows the Chapter 13 memory-space hook. The generation choice was readable, but Phase29 should expand/repair Chapter 15 outline from actual Chapter 14 state before writing.

Final Chapter 14 state after subagent fixes:

```text
title: 门后回声
word_count: 2298
longform_maintenance: current, issue_count 0
updated_scope_keys: chapter:14, arc:1-14, volume:1-14, global
synced_scope_keys: arc:1-14, chapter:14, global, volume:1-14
```

Final post-fix review run:

```text
run_id: ff9b527f-ec9c-4bf2-bdc8-e7bd0ea0b310
quality_review: ready, 0 findings
continuity_review: ready, 0 findings
world_model_analysis: completed, created 0, updated 0, skipped duplicates 5
pending_actionable_proposals: 0
preflight_chapter_15: blocked only by missing_outline_chapter
previous_chapter_state_card: ready, title 门后回声
longform_maintenance: ready, issue_count 0
```

## Verification

Completed so far:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k compress_chapter_to_target
```

Result:

```text
12 passed, 91 deselected in 1.29s
```

Full T2 verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_chapters.py -q
```

Result:

```text
140 passed in 11.74s
```

Hygiene:

- `git diff --check`: exit 0; only CRLF-to-LF warning for `backend/tests/test_writing_agent_runs.py`.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"`: exit 1, no matches.

## Phase29 Recommendation

Continue with Chapter 15 after committing Phase28. Recommended next loop:

1. preflight Chapter 15;
2. generate Chapter 15 with stable facts active;
3. immediately run quality/continuity/world-model review;
4. if Chapter 15 again drifts over target, use the improved compression tool;
5. track whether `event_summary` proposals should stay `mark_uncertain` or become a curated chapter-summary memory lane in a later phase.
