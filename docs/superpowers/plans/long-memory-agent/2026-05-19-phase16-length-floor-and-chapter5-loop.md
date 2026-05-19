# Phase 16 Length Floor and Chapter 5 Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align chapter length gates with the longform goal of 2000+ words per chapter, then continue the real dogfood loop by generating Chapter 5 of `《雾港回声》`.

**Architecture:** Keep `ChapterContent.word_count` as the authoritative stored project statistic to avoid a schema migration. Tighten the generated-chapter target floor only for longform projects whose average target is at least 2000, so the Agent no longer treats 1700-1999 as acceptable for the 600-chapter / 1.2M-word dogfood novel.

**Tech Stack:** FastAPI chapter generation path, prompt provider length constraints, chapter quality review, Writing Agent run service, SQLAlchemy, pytest.

---

## Phase Metadata

- **Phase:** 16
- **Date:** 2026-05-19
- **Verification Tier:** T1 for the chapter length policy behavior; T2 for real Chapter 5 dogfood generation and Writing Agent/world proposal tests.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Chapter 5 of `《雾港回声》`, generated under the stricter 2000+ length floor.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Current State

- Generated chapters: 4
- Latest chapter: Chapter 4 `顾衍的警告`
- Chapter 4 stored `word_count`: 1861
- Chapter 4 raw content length: 2373
- Pending world-model proposals: 0
- Proposal reviews: 32
- World fact claims: 0
- Next outline chapter: Chapter 5 `空白信的秘密`

## Decision

Use stored `ChapterContent.word_count` as the authoritative count for project progress, trace metadata, and quality gates in this phase.

Reason:

- Existing project totals, exports, longform memory, trace metadata, and tests already depend on `word_count`.
- Changing the database meaning to raw character count would be a migration-level change.
- For the current 600-chapter / 1.2M-word goal, the practical failure is that the lower bound allows `1700-1999`, not that the counter is unavailable.

Policy:

- If `target_word_count / target_chapter_count >= 2000`, the chapter lower bound is the average target, not `average * 0.85`.
- The upper bound remains `average * 1.15`.
- For smaller projects, keep the existing 85%-115% flexibility.

## Success Criteria

- `project_chapter_word_range` for a 1.2M / 600 project returns `2000-2300`.
- Chapter prompt for that project says the chapter should be controlled in `2000-2300` words.
- Trace metadata and review gates use the same range.
- Existing smaller-project behavior remains unchanged, for example 1M / 1000 still returns `850-1150`.
- Chapter 5 is generated with stored `word_count >= 2000`.
- Chapter 5 quality review returns no blocker after world-model proposal queue is processed.
- Any new world-model proposals from Chapter 5 are resolved through the Phase14 draft/apply path when they are low-risk non-merge metadata.

## Explicit Non-Goals

- Do not migrate the `chapter_contents` schema.
- Do not rewrite project totals or historical Chapter 1-4 counts.
- Do not regenerate Chapter 4 in this phase.
- Do not generate Chapter 6.
- Do not approve world-model facts from automatic extraction without a separate curation phase.

## Files

- Modify: `backend/app/prompting/providers/chapter.py`
- Modify: `backend/tests/test_prompting_chapter_migration.py`
- Modify: `backend/tests/test_chapters.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase16-length-floor-and-chapter5-loop.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase16-length-floor-and-chapter5-loop.md`

## Task 1: Tighten Longform Length Floor

- [x] **Step 1: Write failing prompt-provider expectation**

Update `backend/tests/test_prompting_chapter_migration.py::test_chapter_payload_injects_project_word_target_without_user_range` to keep the existing 1M / 1000 expectation as `850-1150`, then add a 1.2M / 600 project expectation that the prompt contains `2000-2300`.

- [x] **Step 2: Write failing trace/review expectations**

Update Writing Agent or chapter trace tests so a 1.2M / 600 project expects:

```python
assert length_decision["target_min_word_count"] == 2000
assert length_decision["target_max_word_count"] == 2300
```

- [x] **Step 3: Run targeted RED tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py::test_chapter_payload_injects_project_word_target_without_user_range tests\test_writing_agent_runs.py::test_agent_run_records_chapter_length_and_world_model_diagnostics -q
```

Expected: fail on the new 2000 lower-bound expectation.

- [x] **Step 4: Implement minimal policy change**

Modify `project_chapter_word_range(project)`:

```python
average = max(1, round(target_words / target_chapters))
target_min = average if average >= 2000 else round(average * 0.85)
target_max = round(average * 1.15)
return max(1, target_min), max(1, target_max)
```

- [x] **Step 5: Run GREEN tests**

Run the same targeted tests and any directly affected chapter tests.

## Task 2: Dogfood Chapter 5

- [x] **Step 1: Confirm preconditions**

Record:

- generated chapter count;
- Chapter 5 outline title;
- API key configured without printing it;
- pending proposal count.

- [x] **Step 2: Run Writing Agent preflight and generation**

Tools:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 5}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 5}}
]
```

Expected:

- run status `success`;
- Chapter 5 exists;
- stored `word_count >= 2000`;
- trace length decision is `within` or `over`, not `under`.

- [x] **Step 3: Review and analyze Chapter 5**

Tools:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 5}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 5}}
]
```

Expected:

- no chapter-quality blocker except pending world proposals;
- analysis either creates proposals or skips duplicates with clear evidence.

- [x] **Step 4: Resolve low-risk proposal queue if needed**

If pending proposals exist, use:

```json
[
  {"tool_name": "draft_world_model_proposal_resolution_decisions", "params": {"limit": 50}},
  {"tool_name": "apply_world_model_proposal_resolution", "params": {"confirm_apply": true, "decisions": "<draft_decisions>"}}
]
```

Expected:

- pending proposals return to 0;
- no world facts created from low-risk metadata-only decisions.

- [x] **Step 5: Final Chapter 5 quality check**

Run `review_chapter_quality` again for Chapter 5.

Expected:

- blocker count 0;
- warning-only mild length drift is acceptable without `revise_chapter`.

## Task 3: Verification and Report

- [x] **Step 1: Run targeted verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py tests\test_chapters.py tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

- [x] **Step 2: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase16-length-floor-and-chapter5-loop.md` with:

- policy decision;
- code changes;
- dogfood run IDs;
- Chapter 5 title and word count;
- proposal queue results;
- verification evidence;
- next-phase recommendation.

- [x] **Step 3: Hygiene checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
git status --short --branch
```

Expected:

- whitespace check passes;
- secret scan returns no matches;
- only intended Phase16 files are changed.

- [x] **Step 4: Commit and push**

Commit the Phase16 plan first. Commit implementation/report after verification. Push `main` to `origin`.
