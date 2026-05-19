# Phase29 Review Baseline and Chapter 15 Report

## Scope

Phase29 continued the real longform dogfood loop from Chapter 14 to Chapter 15 and fixed two deterministic review gaps exposed by Phase28.

Project:

```text
project_id: 25fa2b20-5b9f-473b-918b-f4ea491cbb60
```

Starting state:

```text
main synced with origin/main
chapter_14_title: 门后回声
chapter_14_word_count: 2298
chapter_15_preflight: blocked only by missing_outline_chapter
longform_maintenance: current
pending_actionable_proposals: 0
```

## Review Baseline Fix

Phase28 showed that automatic quality review missed:

- duplicate non-generic chapter titles;
- obvious typo pattern `戴着眼睛`.

TDD RED command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_duplicate_specific_title tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_known_typo_pattern -q
```

RED result:

```text
2 failed
```

Implementation:

- `backend/app/core/chapter_quality_review.py`
  - added `KNOWN_TYPO_PATTERNS = {"戴着眼睛": "戴着眼镜"}`;
  - added duplicate-title warning for non-empty, non-generic titles;
  - added known typo warning with suggestion and excerpt.
- `backend/tests/test_writing_agent_runs.py`
  - added tests for `duplicate_chapter_title`;
  - added tests for `known_typo_pattern`.

GREEN command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_duplicate_specific_title tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_known_typo_pattern -q
```

GREEN result:

```text
2 passed in 0.25s
```

Review regression command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k review_chapter_quality
```

Result:

```text
10 passed, 95 deselected in 0.75s
```

## Chapter 15 Outline and Preflight

Expanded Chapter 15 outline:

```text
run_id: da2afa5a-dbc7-498a-99a8-4055ec9e9d4c
status: success
tool: expand_outline_window
added_chapter_count: 1
trace_id: 381273c8-0388-4a9e-9704-32da3c87b81d
```

New outline:

```text
title: 向下螺旋
summary: 林深、苏晚晴、顾衍沿着狭窄的螺旋楼梯向下，进入废弃实验室的深层。顾衍发现墙上的涂鸦与军牌编号N-017有关，而苏晚晴因雾感体质感应到大量痛苦记忆的回声。林深注意到楼梯台阶上刻有实验体编号，其中出现N-07的标记，与他父母失踪案有关联。
```

Preflight:

```text
run_id: 4eb741ba-2816-4116-868e-b0e84f336789
status: success
preflight: ready
previous_chapter_state_card: ready, title 门后回声
longform_maintenance: ready, issue_count 0
retrieval: ready, total_documents 57, total_chunks 103
```

## Chapter 15 Generation

Generation run:

```text
run_id: 11b19ee2-f4d5-42f9-87a1-96cde6c52646
status: success
chapter: 第15章《向下螺旋》
trace_id: 3428a3ea-5c54-4e1d-88e4-1b359740bd9d
initial_word_count: 2720
quality_review: warning
continuity_review: ready, 0 findings
world_model_analysis: created 5 proposal items
```

Initial quality warnings:

- `chapter_over_target`: 2720 > target max 2300.
- `pending_world_model_proposals`: 5 pending proposal items.

Proposal maintenance:

```text
draft_run_id: f150b4e6-d114-41b6-abd7-b1e952169962
draft_decision_count: 5
actions: event_summary -> mark_uncertain; mentioned_in_chapter/presence_count -> reject

apply_run_id: 324812af-e461-4bc6-8e17-365f9b053a56
before_actionable_items: 5
after_actionable_items: 0
applied_count: 5
```

Compression and review:

```text
run_id: 5ca13a70-a678-4b77-b0fe-99314dae8ebc
status: success
previous_word_count: 2720
word_count: 2297
target_range: 2000-2300
deterministic_trim_applied: true
quality_review: ready, 0 findings
continuity_review: ready, 0 findings
world_model_analysis: completed, created 0, updated 0, skipped duplicates 5
pending_actionable_proposals: 0
```

Final Chapter 15 state:

```text
title: 向下螺旋
word_count: 2297
longform_maintenance: current, issue_count 0
latest_synced_chapter_index: 15
chapter15_memory: exists
outline16_exists: false
```

Chapter 15 tail:

```text
三个人冲上楼梯，身后的房间开始坍塌，灰尘和碎石从上方掉落。他们一路向上跑，不知道跑了多久，直到看到一扇铁门。雾已经散了。林深躺在地上，大口大口地喘着气。他转过头，看到苏晚晴躺在旁边，脸色苍白，但还活着。顾衍站在他们身边，手里握着匕首，目光警惕地看着四周。“我们出来了。”顾衍说。林深闭上眼睛，感受着阳光照在脸上的温暖。但即使阳光再暖，他依然感到一种深入骨髓的寒冷——因为他知道，他们刚刚发现的，只是冰山一角。
```

## Subagent Review

Read-only subagent:

```text
agent_id: 019e3f88-385f-7873-81a1-872268707603
task: read-only Chapter 15 reader and continuity review
```

Result:

- Chapter 15 continues Chapter 14's downward-stair hook.
- `N-07` remains an experiment/subject marker and is not confused with 顾衍's confirmed `N-017` military tag.
- 林建国 as 林深's father is not contradicted.
- Chapter 15 is 2000+ words and reads like a usable web-novel chapter.

Findings fixed in this phase:

- Reworded `B7` so it no longer says it is the same as the `N-07` graffiti. It now reads as another `7`-related basement guidepost.
- Replaced `两个字母` with `两个字符` for `B7`.
- Clarified that the N-07 girl appears on the monitor screen, not physically in the room.
- Replaced the generic tail hook with a more concrete one: `N-07同步完成`.

Post-subagent fix state:

```text
title: 向下螺旋
word_count: 2293
longform_maintenance: current, issue_count 0
latest_synced_chapter_index: 15
updated_scope_keys: chapter:15, arc:1-15, volume:1-15, global
synced_scope_keys: arc:1-15, chapter:15, global, volume:1-15
```

Post-subagent review run:

```text
run_id: a020b707-11fd-413d-8c82-eed62dd80606
quality_review: ready, 0 findings
continuity_review: ready, 0 findings
world_model_analysis: completed, created 0, updated 0, skipped duplicates 5
pending_actionable_proposals: 0
```

## Verification

Completed:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k review_chapter_quality
```

Result:

```text
10 passed, 95 deselected in 0.75s
```

Final verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "review_chapter_quality or compress_chapter_to_target"
```

Result:

```text
22 passed, 83 deselected in 1.92s
```

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_chapters.py -q
```

Result:

```text
37 passed in 3.56s
```

Hygiene:

- `git diff --check`: exit 0; only CRLF-to-LF warning for `backend/tests/test_writing_agent_runs.py`.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"`: exit 1, no matches.

## Phase30 Recommendation

Phase30 should continue from Chapter 16. Current expected blocker:

```text
outline16_exists: false
```

Recommended next loop:

1. expand Chapter 16 outline from actual Chapter 15 state;
2. generate Chapter 16;
3. review quality and continuity;
4. resolve world-model proposal maintenance;
5. decide whether the repeated `event_summary -> mark_uncertain` pattern should become a curated chapter-summary memory lane.
