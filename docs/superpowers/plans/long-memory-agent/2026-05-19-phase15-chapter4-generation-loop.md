# Phase 15 Chapter 4 Generation Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the next real longform dogfood loop by generating Chapter 4 of `《雾港回声》`, reviewing quality, and feeding the result back into the world-model proposal flow.

**Architecture:** This phase does not introduce a new runtime feature unless the dogfood loop exposes a concrete bug. It exercises the existing Writing Agent tools in sequence: preflight, chapter generation, chapter quality review, and world-model chapter analysis.

**Tech Stack:** FastAPI service layer, SQLAlchemy data model, existing Writing Agent run service, existing DeepSeek-compatible AI service configuration, pytest.

---

## Phase Metadata

- **Phase:** 15
- **Date:** 2026-05-19
- **Verification Tier:** T0 for planning/report docs; T2 for real dogfood chapter generation and related backend tests.
- **Primary Output:** Chapter 4 of the dogfood longform novel `《雾港回声》`.
- **Dogfood Project:** `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Current State

- Generated chapters: 3
- Next outline chapter: Chapter 4 `顾衍的警告`
- Actionable world-model proposal items: 0
- Proposal reviews: 24
- World fact claims: 0
- Phase14 recommendation: run `preflight_writing`, generate Chapter 4, review quality, analyze Chapter 4 into world-model proposals, then use the draft/apply path if low-value proposal metadata blocks later generation.

## Success Criteria

- `preflight_writing` for Chapter 4 returns ready or produces a concrete fixable blocker.
- Chapter 4 exists in the database after generation.
- Chapter 4 word count is recorded and is at least 2000 Chinese characters/words by the system counter.
- Chapter 4 title is not generic if the generator has enough outline context.
- `review_chapter_quality` records Chapter 4 quality evidence.
- `analyze_chapter_world_model` records proposal output for Chapter 4.
- Any newly exposed blocker is either fixed in this phase or documented with a next-phase recommendation.
- The phase report records run IDs, chapter progress, quality findings, proposal counts, validation commands, and next step.

## Explicit Non-Goals

- Do not generate Chapter 5 in this phase.
- Do not approve or merge world-model facts unless Chapter 4 analysis produces a small, clearly safe queue and the existing guarded path can handle it without new design work.
- Do not build frontend UI.
- Do not rewrite the Agent architecture.
- Do not store API keys in repository files or phase documents.

## Files

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-19-phase15-chapter4-generation-loop.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-19-phase15-chapter4-generation-loop.md`
- Modify only if a concrete bug is found: backend files directly responsible for the failing tool.

## Task 1: Confirm Runtime Preconditions

- [x] **Step 1: Check dogfood project state**

Run:

```powershell
cd D:\MyOP\CODE\NovelCodeSpace\novelv3
cd backend
.venv\Scripts\python.exe -c "from app.db.session import SessionLocal; from app.models.chapter import Chapter; from app.models.outline import OutlineChapter; from app.models.world_model import WorldProposalItem, WorldProposalReview, WorldFactClaim; project_id='25fa2b20-5b9f-473b-918b-f4ea491cbb60'; db=SessionLocal(); print('chapters', [(c.chapter_index,c.title,c.word_count,c.status) for c in db.query(Chapter).filter_by(project_id=project_id).order_by(Chapter.chapter_index).all()]); print('next_outline', [(o.chapter_index,o.title) for o in db.query(OutlineChapter).filter_by(project_id=project_id).filter(OutlineChapter.chapter_index<=5).order_by(OutlineChapter.chapter_index).all()]); print('pending_world_proposals', db.query(WorldProposalItem).filter_by(project_id=project_id,item_status='pending').count()); print('reviews', db.query(WorldProposalReview).filter_by(project_id=project_id).count()); print('facts', db.query(WorldFactClaim).filter_by(project_id=project_id).count()); db.close()"
```

Expected: 3 generated chapters, Chapter 4 outline available, zero pending actionable proposal items.

- [x] **Step 2: Confirm AI key can be loaded without printing it**

Run a local check that prints only `configured` or `missing`, never the key value.

Expected: configured. If missing, provide the key only as process-local runtime configuration for generation commands and never write it to disk.

## Task 2: Generate Chapter 4 Through Writing Agent

- [x] **Step 1: Run preflight and generation**

Use the existing Writing Agent run endpoint/service with these tools:

```json
[
  {"tool_name": "preflight_writing", "params": {"chapter_index": 4}},
  {"tool_name": "generate_chapter", "params": {"chapter_index": 4}}
]
```

Expected: run status `success`; preflight ready; generation ready; Chapter 4 created.

- [x] **Step 2: Record generation result**

Record:

- run ID;
- step statuses;
- Chapter 4 title;
- word count;
- warnings;
- trace identifier if present.

## Task 3: Review and World-Model Feedback

- [x] **Step 1: Run quality review and world-model analysis**

Use the existing Writing Agent run endpoint/service with these tools:

```json
[
  {"tool_name": "review_chapter_quality", "params": {"chapter_index": 4}},
  {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 4}}
]
```

Expected: quality review produces actionable evidence; world-model analysis produces proposal output or a clear no-op report.

- [x] **Step 2: Inspect queue after analysis**

Record:

- proposal item count by status;
- proposal predicate distribution;
- review count;
- fact count;
- whether Phase14 draft/apply path is needed before Chapter 5.

## Task 4: Fix Only Concrete Blockers

- [x] **Step 1: Classify any failure**

If a tool fails, classify it as:

- configuration issue;
- generation/provider issue;
- validation/quality issue;
- world-model extraction issue;
- database/state issue.

- [x] **Step 2: Apply the smallest direct fix**

Only modify backend code if the failure is a reproducible system bug. Add or update targeted tests for the failing behavior.

- [x] **Step 3: Re-run the failed tool path**

Expected: the same dogfood path completes or the remaining blocker is documented with evidence.

## Task 5: Report and Verification

- [x] **Step 1: Write the phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-19-phase15-chapter4-generation-loop.md` with:

- actual chapter progress;
- dogfood run IDs;
- quality findings;
- world-model proposal findings;
- system issues found/fixed;
- validation evidence;
- next-phase recommendation.

- [x] **Step 2: Run targeted verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Expected: pass.

- [x] **Step 3: Run repository hygiene checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
git status --short --branch
```

Expected: whitespace check passes; secret scan returns no matches; only intentional docs/code changes remain.

- [x] **Step 4: Commit and push**

Commit the plan before dogfood execution. Commit the final report and any code fixes after verification. Push `main` to `origin`.
