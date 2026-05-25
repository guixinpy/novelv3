# Phase 9 Revision Draft Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe Agent tool that turns Phase 8 revision plans into non-destructive `ChapterRevision` drafts.

**Architecture:** Keep `plan_chapter_revision` read-only. Add a separate draft bridge that converts revision actions into `RevisionAnnotation` rows, creates or reuses an open draft revision, and never calls regeneration or writes chapter prose.

**Tech Stack:** FastAPI service layer, SQLAlchemy models, existing Writing Agent run service, existing chapter revision models, pytest.

---

## Phase Metadata

- **Phase:** 9
- **Date:** 2026-05-18
- **Verification Tier:** T1 for targeted Agent/core tests; T2 for runtime dogfood draft creation on `《雾港回声》` Chapter 2.
- **Primary Output:** Agent tool `create_revision_draft`.
- **Dogfood Output:** Create a non-destructive draft revision for Chapter 2 from the existing blocked revision plan.
- **Secret Handling:** Do not write API keys to docs, commits, `.env`, or logs.

## Success Criteria

- Agent supports `create_revision_draft`.
- `plan_chapter_revision` remains read-only.
- Draft creation:
  - creates `ChapterRevision(status="draft")`;
  - writes only `RevisionAnnotation` rows;
  - writes no `RevisionCorrection` rows;
  - does not update `ChapterContent.content`;
  - does not update `ChapterContent.title`;
  - does not create `result_version_id`;
  - does not call `regenerate_revision`.
- Existing draft revisions created by this tool are reused instead of duplicated.
- Chapters with no revision actions do not create a draft.
- A drafted but unapplied revision still blocks follow-up `generate_chapter` in the same Agent run.

## Explicit Non-Goals

- Do not regenerate or overwrite chapter prose.
- Do not submit drafts automatically.
- Do not auto-approve or reject world-model proposals.
- Do not create a new database table.
- Do not build frontend UI.
- Do not migrate the whole revision API into a service layer in this phase.

## Files

- Create: `backend/app/core/chapter_revision_drafts.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase9-revision-draft-bridge.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase9-revision-draft-bridge.md`

## Task 1: Add Draft Builder Core

**Files:**

- Create: `backend/app/core/chapter_revision_drafts.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing draft creation test**

Add a test where Chapter 2 has `retitle_chapter` and `compress_chapter` actions. Expected:

```python
assert output["status"] == "drafted"
assert output["revision_id"]
assert output["annotation_count"] >= 2
assert output["correction_count"] == 0
assert chapter_after.content == original_content
assert chapter_after.title == "第2章"
assert revision.status == "draft"
assert revision.result_version_id is None
```

- [x] **Step 2: Implement draft core**

Create:

```python
def create_revision_draft_from_plan(db: Session, project_id: str, chapter_index: int, plan: dict[str, Any]) -> dict[str, Any]:
    ...
```

Rules:

- If `revision_actions` is empty, return `status="skipped"` and do not create a revision.
- Reuse an existing `draft` for the same chapter.
- Do not rewrite `submitted`, `failed`, or `completed` revisions.
- Build annotations with stable action markers:
  - `[PLAN_ACTION:retitle_chapter]`
  - `[PLAN_ACTION:compress_chapter]`
  - `[PLAN_ACTION:defer_future_reveals]`
- Keep `corrections=[]`.

- [x] **Step 3: Run targeted test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_create_revision_draft_from_plan_is_non_destructive -q
```

Expected after implementation: pass.

## Task 2: Wire Agent Tool

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing Agent wiring tests**

Add tests for:

- `create_revision_draft` records target type `revision` and target id.
- repeated `create_revision_draft` reuses the same active draft.
- ready chapters with no revision actions return `skipped` and create no draft.
- `create_revision_draft -> generate_chapter` blocks follow-up generation when `should_generate_next_chapter=false`.

- [x] **Step 2: Add tool wiring**

Add `create_revision_draft` to:

- `ALLOWED_TOOLS`;
- `INTERNAL_TOOLS`;
- `_execute_tool`;
- `_target_type_for_tool`;
- `_find_target_id`;
- follow-up generation gate.

- [x] **Step 3: Run targeted Agent tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_create_revision_draft_from_plan_is_non_destructive tests\test_writing_agent_runs.py::test_agent_create_revision_draft_reuses_existing_draft tests\test_writing_agent_runs.py::test_agent_create_revision_draft_skips_ready_chapter tests\test_writing_agent_runs.py::test_agent_create_revision_draft_blocks_followup_generation -q
```

Expected: pass.

- [x] **Step 4: Add code-review feedback tests**

Added tests for:

- existing user/manual draft is not modified;
- existing submitted revision blocks automatic draft creation;
- planner-owned draft can be reused without creating duplicates.

## Task 3: Runtime Dogfood Draft

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase9-revision-draft-bridge.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase9-revision-draft-bridge.md`

- [x] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_chapter_revisions.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no committed secrets.

- [x] **Step 2: Create Chapter 2 draft through Agent**

Use Agent run against project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`:

```json
{
  "goal": "为《雾港回声》第2章创建非破坏性修订草稿。",
  "tools": [{"tool_name": "create_revision_draft", "params": {"chapter_index": 2}}]
}
```

Expected:

- run status `success`;
- tool output status `drafted`;
- active revision exists for Chapter 2;
- Chapter 2 content and title remain unchanged.

- [x] **Step 3: Record report and next phase recommendation**

The phase report must include:

- dogfood novel progress;
- draft revision id and annotation count;
- confirmation that Chapter 2 was not overwritten;
- verification evidence;
- next phase recommendation.

## Phase Report

Report saved to:

- `docs/superpowers/notes/long-memory-agent/2026-05-18-phase9-revision-draft-bridge.md`

Summary:

- Added `create_revision_draft` Agent tool.
- Added non-destructive draft bridge in `backend/app/core/chapter_revision_drafts.py`.
- Draft creation writes planner annotations only and no corrections.
- Existing manual drafts and submitted/failed active revisions block automatic draft creation.
- Runtime dogfood created a Chapter 2 draft with 3 annotations and 0 corrections.
- Follow-up generation gate blocked before Chapter 4 generation; Chapter 4 remains ungenerated.
