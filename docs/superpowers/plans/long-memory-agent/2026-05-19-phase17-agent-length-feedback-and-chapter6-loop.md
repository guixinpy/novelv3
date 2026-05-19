# Phase 17 Agent Length Feedback and Chapter 6 Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Writing Agent automatically inject corrective length feedback into chapter generation after repeated drift, then generate Chapter 6 of `《雾港回声》`.

**Architecture:** Keep the chapter generator and prompt provider intact. Add a small Writing Agent orchestration layer that augments `generate_chapter` command arguments with deterministic feedback derived from current length policy diagnostics.

**Tech Stack:** Writing Agent run service, existing ActionExecutionService, chapter prompt provider range policy, SQLAlchemy, pytest.

---

## Phase Metadata

- **Phase:** 17
- **Date:** 2026-05-19
- **Verification Tier:** T1 for Agent auto-feedback tests; T2 for real Chapter 6 dogfood generation and world-model proposal loop.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Primary Output:** Chapter 6 of `《雾港回声》`, generated with automatic Agent length feedback.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Starting State

- Generated chapters: 5
- Latest chapter: Chapter 5 `空白信的秘密`
- Chapter 5 stored word count: 2482
- Chapter 5 quality status: warning only, no blocker
- Pending world-model proposals: 0
- Proposal reviews: 39
- World fact claims: 0
- Next outline chapter: Chapter 6 `黑市雾晶`

## Problem

Phase16 proved the stricter 2000+ lower bound works, but Chapter 5 still needed manual runtime feedback to stay near range and ended mildly over target.

Current weakness:

- The Agent can detect repeated length drift.
- The Agent does not automatically convert that diagnosis into the next `generate_chapter` tool call.
- The operator had to manually add text such as "2100-2300字".

This is misaligned with the goal of a writing Agent that can orchestrate tools and self-correct longform production.

## Success Criteria

- When repeated over-target drift exists, Writing Agent `generate_chapter` passes augmented `command_args` to `ActionExecutionService`.
- Existing user `command_args` are preserved and the Agent feedback is appended.
- The generated step output records a small `agent_generation_feedback` diagnostic.
- The auto-feedback mentions the active target range, for the dogfood project `2000-2300`.
- Repeated under-target drift gets corresponding "do not underwrite" feedback.
- Chapter 6 is generated with no manual length command from this session.
- Chapter 6 stored `word_count >= 2000`.
- Chapter 6 quality review has blocker count 0 after proposal queue cleanup.

## Explicit Non-Goals

- Do not change database schema.
- Do not regenerate Chapter 5.
- Do not add a frontend control.
- Do not add LLM-based reflection in this phase.
- Do not generate Chapter 7.

## Files

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase17-agent-length-feedback-and-chapter6-loop.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase17-agent-length-feedback-and-chapter6-loop.md`

## Task 1: Add Agent Length Feedback

- [x] **Step 1: Write failing over-target auto-feedback test**

Add a test in `backend/tests/test_writing_agent_runs.py`:

- Seed a 1.2M / 600 longform project with three generated over-target chapters.
- Monkeypatch `ActionExecutionService.execute` to capture `command_args`.
- Run an Agent `generate_chapter` tool with user command args such as `保留悬疑压迫感`.
- Assert captured `command_args` contains both:
  - the original user text;
  - Agent text mentioning repeated over-target drift and `2000-2300`.
- Assert step output includes `agent_generation_feedback.reason == "repeated_over_target"`.

- [x] **Step 2: Write failing under-target auto-feedback test**

Seed three under-target chapters and assert generated command args contain under-target corrective wording and the active target range.

- [x] **Step 3: Run RED tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift -q
```

Expected: fail because feedback is not appended.

- [x] **Step 4: Implement minimal run service augmentation**

In `WritingAgentRunService._execute_tool`:

- special-case `generate_chapter` before the generic external tool path;
- build `agent_generation_feedback` from `_length_policy_check`;
- append feedback text to existing command args;
- call `ActionExecutionService.execute` with effective command args;
- attach feedback diagnostic to result only when feedback exists.

- [x] **Step 5: Run GREEN tests**

Run the same tests and the existing length-policy tests.

## Task 2: Dogfood Chapter 6

- [x] **Step 1: Confirm preconditions**

Record:

- generated chapter count;
- Chapter 6 outline title;
- API key configured without printing it;
- pending proposal count.

- [x] **Step 2: Run preflight and generation with no manual length command**

Tools:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 6}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 6}}
]
```

Expected:

- run status `success`;
- generated step output includes `agent_generation_feedback`;
- Chapter 6 exists;
- stored `word_count >= 2000`.

- [x] **Step 3: Review and analyze Chapter 6**

Run:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 6}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 6}}
]
```

Expected:

- no hard content blocker except possible pending world proposals.

- [x] **Step 4: Resolve proposal queue if needed**

Use draft/apply low-risk proposal resolution if pending items exist.

- [x] **Step 5: Final Chapter 6 quality check**

Expected:

- blocker count 0;
- pending proposal count 0.

## Task 3: Verification and Report

- [x] **Step 1: Run targeted verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

- [x] **Step 2: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase17-agent-length-feedback-and-chapter6-loop.md`.

Record:

- code changes;
- auto-feedback test evidence;
- Chapter 6 run IDs and word count;
- proposal queue results;
- final quality result;
- next phase recommendation.

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
- only intended Phase17 files are changed.

- [x] **Step 4: Commit and push**

Commit the Phase17 plan first. Commit implementation/report after verification. Push `main` to `origin`.
