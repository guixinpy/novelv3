# Truth Anchored Chapter 14 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and validate dogfood Chapter 14 with confirmed world-model truth anchors injected into the writing context.

**Architecture:** Treat Phase27 confirmed `WorldFactClaim` rows as the authoritative continuity source. First verify they are present in the Chapter 14 generation context, then generate the chapter, review quality and continuity, analyze world-model proposals, and only patch code if dogfood exposes a repeatable system failure.

**Tech Stack:** FastAPI backend, Writing Agent run service, Athena world context, confirmed `WorldFactClaim`, pytest, local dogfood SQLite data.

---

## Context

Phase27 confirmed five high-risk stable truth anchors:

- `林深.father_name = 林建国`
- `顾衍.military_tag_number = N-017`
- `identifier.N-07.identifier_meaning = 实验代号/实验体编号，不是顾衍军牌编号`
- `event.fog_disaster.event_date = 2045年8月12日`
- `event.fog_disaster.minus_3_days.relative_event_date = 2045年8月9日`

Chapter 14 outline is already present and preflight is ready. This phase tests whether those facts actually constrain live generation.

## Scope

In scope:

- Verify Chapter 14 generation context includes the five confirmed facts.
- Generate Chapter 14.
- Run quality review and continuity review.
- Run world-model analysis and resolve classification-safe proposals.
- Dispatch a subagent for reader/continuity review.
- Repair dogfood content if the chapter violates stable anchors or quality gates.
- Add code/tests only when a repeatable system failure is found.

Out of scope:

- Generalizing the Phase27 seed tool.
- Building the full knowledge-base module.
- Frontend UI work.
- Generating multiple chapters in one phase.
- Full frontend/backend T3 verification unless code changes become high-risk.

## Task 1: Context Gate

- [x] **Step 1: Inspect Chapter 14 world context**

Run:

```powershell
cd backend
@'
import sys, json
sys.path.insert(0, r'D:\MyOP\CODE\NovelCodeSpace\novelv3\backend')
from app.db import SessionLocal
from app.core.world_context_assembler import WorldContextAssembler
project_id='25fa2b20-5b9f-473b-918b-f4ea491cbb60'
with SessionLocal() as db:
    package=WorldContextAssembler(db, project_id).chapter_context_package(14)
print(package['prompt_context'])
'@ | .venv\Scripts\python.exe -
```

Expected: output contains `【已确认事实】`, `林深.father_name = 林建国`, `顾衍.military_tag_number = N-017`, and both fog-disaster dates.

- [x] **Step 2: If facts are missing, add a failing test**

If Step 1 fails, add a test in `backend/tests/test_chapters.py` proving `build_chapter_prompt_context_blocks()` must inject confirmed stable truth facts into the model prompt, then implement the minimal fix.

If Step 1 passes, do not add speculative code.

## Task 2: Generate Chapter 14

- [x] **Step 1: Run Writing Agent chapter generation**

Use project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 14}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 14}},
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 14}},
  {"tool_name": "review_chapter_continuity", "params": {"chapter_index": 14}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 14}}
]
```

Expected:

- preflight ready;
- generated chapter is正文, not outline;
- word count is at least 2000;
- quality review is ready or has actionable findings;
- continuity review has no stable truth conflicts;
- world-model analysis creates or skips proposals without leaving stale maintenance.

- [x] **Step 2: Resolve immediate blockers**

If word count is outside the target range, use the existing expansion/compression tool and re-run quality and continuity review.

If continuity review reports a stable truth conflict, repair the chapter before proceeding.

If world-model proposals remain, use `draft_world_model_proposal_resolution_decisions` and `apply_world_model_proposal_resolution` only for classification-safe non-merge decisions.

## Task 3: Subagent Reader/Continuity Review

- [x] **Step 1: Dispatch read-only subagent**

Ask a subagent to inspect Chapter 14 in `data/mozhou.db` and report:

- stable anchor violations;
- N-017 / N-07 / N-00 confusion;
- fog-disaster date drift;
- whether Chapter 14 works as a readable web-novel chapter;
- whether a code-level system issue is exposed.

- [x] **Step 2: Fix or document findings**

Fix dogfood content or code for clear blockers. Record non-blocking quality observations in the phase report.

## Task 4: Verification and Report

- [x] **Step 1: Choose verification tier**

If no production code changes are made, use T0/T1:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

If production code changes are made, run at least:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_chapters.py -q
```

- [x] **Step 2: Write Phase28 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase28-truth-anchored-chapter14.md` with:

- context-gate evidence;
- generation run IDs;
- Chapter 14 word count and title;
- quality/continuity/world-model review results;
- subagent review findings;
- fixes or follow-ups;
- next phase recommendation.

- [ ] **Step 3: Commit and push**

Commit the Phase28 plan separately, then commit implementation/report/dogfood documentation. Attempt to push `main`; if GitHub remains unreachable, document the local ahead state.
