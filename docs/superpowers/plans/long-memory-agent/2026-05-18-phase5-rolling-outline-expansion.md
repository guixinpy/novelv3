# Phase 5 Rolling Outline Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rolling outline expansion so the Agent can safely fill missing chapter plans before generating the next longform chapter.

**Architecture:** Phase 5 adds an outline window expansion API and an Agent tool that calls it. Expansion appends missing chapter outlines for a requested range and preserves existing outline entries by default.

**Tech Stack:** FastAPI, existing outline generation prompt infrastructure, SQLAlchemy JSON outline storage, Writing Agent run service, pytest.

---

## Phase Metadata

- **Phase:** 5
- **Date:** 2026-05-18
- **Verification Tier:** T1 for outline merge/API tests; T2 for runtime dogfood expansion plus Chapter 3 preflight.
- **Primary Output:** Rolling outline expansion API and Agent tool.
- **Dogfood Output:** Expand `《雾港回声》` outline to cover Chapter 3, then generate Chapter 3 only if preflight returns `ready`.
- **Secret Handling:** Do not write API keys to docs, commits, or `.env`.

## Phase 5 Success Criteria

- Existing outline entries are preserved.
- Missing chapter outlines can be appended for a requested window.
- Expansion ignores out-of-window generated chapters.
- Expansion normalizes structured scene/character items using the existing normalization logic.
- Agent supports `expand_outline_window`.
- Agent preflight for Chapter 3 becomes `ready` after expansion.
- Chapter 3 is generated only after successful expansion and ready preflight.

## Explicit Non-Goals

- Do not generate a full 600-chapter outline in one call.
- Do not overwrite existing outline chapters unless a later phase adds explicit review/approval.
- Do not auto-approve Athena proposals in this phase.
- Do not build frontend UI for outline expansion yet.

## Files

- Modify: `backend/app/api/outlines.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_outlines.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase5-rolling-outline-expansion.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase5-rolling-outline-expansion.md`

## Task 1: Add Outline Merge Helper And API

**Files:**
- Modify: `backend/app/api/outlines.py`
- Modify: `backend/tests/test_outlines.py`

- [ ] **Step 1: Write failing merge/API tests**

Add tests:

```python
def test_expand_outline_window_appends_missing_chapters_without_overwriting_existing(...):
    ...

def test_expand_outline_window_ignores_out_of_window_chapters(...):
    ...
```

Expected:

- Existing Chapter 1 title remains unchanged.
- Chapters 2 and 3 are appended.
- Returned outline includes chapters 1, 2, 3 in order.
- A model-returned Chapter 99 is ignored when requested window is 2-3.

- [ ] **Step 2: Add merge helper**

Add helper:

```python
def _merge_outline_chapter_window(existing_chapters: object, incoming_chapters: object, *, start_chapter: int, end_chapter: int) -> tuple[list[dict], dict]:
    ...
```

It must:

- preserve existing chapter entries.
- append only incoming chapters whose `chapter_index` is within the requested window.
- skip incoming chapters whose index already exists.
- sort by `chapter_index`.
- return merge stats: `added`, `skipped_existing`, `skipped_out_of_window`.

- [ ] **Step 3: Add expansion endpoint**

Add:

```python
@router.post("/expand-window", response_model=OutlineOut)
async def expand_outline_window(project_id: str, start_chapter: int, end_chapter: int, ...):
    ...
```

Use existing setup/storyline bounded context and outline prompt builder with explicit `command_args` describing the requested chapter window.

Trace type: `outline_expansion`.

- [ ] **Step 4: Run outline tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_outlines.py -q
```

Expected: pass.

## Task 2: Add Agent Tool

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing Agent tool test**

Add:

```python
def test_agent_expand_outline_window_adds_missing_outline_then_preflight_ready(...):
    ...
```

Use monkeypatch for `app.api.outlines.ai_service.complete` and `parse_json` so the test does not call an external model.

Expected:

- Agent run status is `success`.
- First step `expand_outline_window` adds Chapter 3.
- Second step `preflight_writing` returns `ready`.

- [ ] **Step 2: Implement `expand_outline_window` Agent tool**

Add tool to `WritingAgentRunService`.

Parameters:

```json
{
  "start_chapter": 3,
  "end_chapter": 8,
  "command_args": "补齐第3-8章滚动大纲。"
}
```

Output should include:

```json
{
  "status": "completed",
  "start_chapter": 3,
  "end_chapter": 8,
  "added_chapter_count": 6,
  "merge": {...}
}
```

- [ ] **Step 3: Run Agent tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q
```

Expected: pass.

## Task 3: Runtime Dogfood Chapter 3

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase5-rolling-outline-expansion.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase5-rolling-outline-expansion.md`

- [ ] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no secrets.

- [ ] **Step 2: Expand dogfood outline**

Use Agent run:

```json
{
  "goal": "补齐《雾港回声》第3-8章滚动大纲，为第3章生成做准备。",
  "tools": [
    {
      "tool_name": "expand_outline_window",
      "params": {
        "start_chapter": 3,
        "end_chapter": 8,
        "command_args": "请只生成第3章到第8章的滚动章节大纲，承接已生成前两章。"
      }
    }
  ]
}
```

Expected: Chapter 3 outline exists after the run.

- [ ] **Step 3: Generate Chapter 3 through Agent gated path**

Use Agent run:

```json
{
  "goal": "在preflight通过后生成《雾港回声》第3章。",
  "tools": [
    {"tool_name": "preflight_writing", "params": {"chapter_index": 3}},
    {
      "tool_name": "generate_chapter",
      "command_args": "请生成《雾港回声》第3章，承接前两章，保持都市悬疑轻科幻风格，正文不少于2000字。",
      "params": {"chapter_index": 3}
    },
    {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 3}}
  ]
}
```

Expected:

- preflight step is ready.
- Chapter 3 is generated.
- Chapter 3 analysis creates or updates proposal items.
- Agent run records length decision.

- [ ] **Step 4: Write Phase 5 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-18-phase5-rolling-outline-expansion.md` with:

```markdown
# Phase 5 Rolling Outline Expansion

## Runtime
## Implementation
## Dogfood Outline Expansion
## Chapter 3 Generation
## Issues Found
## Issues Fixed
## Verification
## Next Phase Recommendation
```

## Task 4: Commit Phase 5

- [ ] **Step 1: Commit code**

```powershell
git add backend/app/api/outlines.py backend/app/services/writing_agent/run_service.py backend/tests/test_outlines.py backend/tests/test_writing_agent_runs.py
git commit -m "feat: add rolling outline expansion"
```

- [ ] **Step 2: Commit docs**

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-18-phase5-rolling-outline-expansion.md docs/superpowers/notes/long-memory-agent/2026-05-18-phase5-rolling-outline-expansion.md
git commit -m "docs: record long memory agent phase 5"
```

## Self-Review

- Spec coverage: The plan addresses the blocker found in Phase 4.
- Placeholder scan: No unresolved `TBD` markers.
- Scope check: This phase keeps expansion windowed and does not attempt a full 600-chapter plan.
