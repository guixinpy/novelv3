# Phase 8 Revision Decision Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe Writing Agent revision-decision tool that turns chapter-quality findings into explicit revision actions before Chapter 4 generation can resume.

**Architecture:** Phase 8 reuses the deterministic chapter review core, existing chapter revision models, and existing world-model proposal queue. It records structured decision output in Agent step output and does not overwrite chapter prose.

**Tech Stack:** FastAPI service layer, SQLAlchemy, existing Writing Agent run service, existing chapter-quality review, existing world proposal review queue, pytest.

---

## Phase Metadata

- **Phase:** 8
- **Date:** 2026-05-18
- **Verification Tier:** T1 for targeted Agent tests; T2 for runtime dogfood planning on `《雾港回声》` Chapters 2 and 3.
- **Primary Output:** Agent tool `plan_chapter_revision`.
- **Dogfood Output:** Produce revision decisions for Chapters 2 and 3 and keep Chapter 4 blocked until revision/proposal decisions are explicit.
- **Secret Handling:** Do not write API keys to docs, commits, or `.env`.

## Success Criteria

- Agent supports `plan_chapter_revision`.
- The tool calls or reuses chapter-quality review output for the selected chapter.
- The tool returns:
  - `status`.
  - `chapter_index`.
  - `should_generate_next_chapter`.
  - `revision_actions`.
  - `world_model_proposal_pressure`.
  - `recommended_next_tools`.
- Generic titles map to `retitle_chapter`.
- Over-target chapters map to `compress_chapter`.
- Future outline overlap maps to `defer_future_reveals`.
- Pending world-model proposals map to `review_world_model_proposals`.
- The tool does not regenerate or overwrite `ChapterContent`.
- A blocked revision plan stops follow-up writing tools in the same Agent run.

## Explicit Non-Goals

- Do not auto-rewrite Chapters 2 or 3.
- Do not auto-approve or reject world-model proposals.
- Do not add a new persistence table for review findings.
- Do not build frontend UI.
- Do not call a model for semantic revision planning in this phase.
- Do not allow `plan_chapter_revision -> generate_chapter` to bypass a blocked revision decision.

## Files

- Create: `backend/app/core/chapter_revision_planner.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase8-revision-decision-loop.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase8-revision-decision-loop.md`

## Task 1: Add Revision Planner Core

**Files:**

- Create: `backend/app/core/chapter_revision_planner.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Write failing planner test**

Add a test where Chapter 2 has a generic title and excessive word count. Expected output:

```python
assert output["status"] == "blocked"
assert output["should_generate_next_chapter"] is False
assert {action["action"] for action in output["revision_actions"]} >= {
    "retitle_chapter",
    "compress_chapter",
}
assert "revise_chapter" in output["recommended_next_tools"]
```

- [x] **Step 2: Implement planner core**

Create `plan_chapter_revision(db, project_id, chapter_index)` that:

- calls `review_chapter_quality`;
- maps findings to revision actions;
- includes a compact world-model proposal queue summary;
- returns a structured plan without changing chapter content.

- [x] **Step 3: Run targeted red/green test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_maps_review_findings_to_actions -q
```

Expected after implementation: pass.

## Task 2: Wire Agent Tool

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add failing Agent tool contract test**

The Agent request:

```json
{
  "goal": "规划第2章修订",
  "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 2}}]
}
```

Expected:

- run status remains `success`;
- step target type is `revision_plan`;
- output status is `blocked` when blockers exist.
- if a blocked revision plan is followed by `generate_chapter`, the Agent run stops before generation.

- [x] **Step 2: Add tool wiring**

Add `plan_chapter_revision` to:

- `ALLOWED_TOOLS`;
- `INTERNAL_TOOLS`;
- `_execute_tool`;
- `_target_type_for_tool`.

- [x] **Step 3: Run targeted Agent tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_maps_review_findings_to_actions tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_records_revision_plan_target_type -q
```

Expected: pass.

- [x] **Step 4: Add code-review feedback tests**

Added tests for:

- blocked planner output gates follow-up generation in the same Agent run;
- world-model proposal pressure is reported without changing proposal item status.

## Task 3: Runtime Dogfood Planning

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase8-revision-decision-loop.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase8-revision-decision-loop.md`

- [x] **Step 1: Run focused verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_outlines.py -q
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: tests pass, no whitespace errors, no committed secrets.

- [x] **Step 2: Run dogfood revision planning**

Use Agent runs against project `25fa2b20-5b9f-473b-918b-f4ea491cbb60`:

```json
{
  "goal": "规划《雾港回声》第2章修订。",
  "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 2}}]
}
```

```json
{
  "goal": "规划《雾港回声》第3章修订。",
  "tools": [{"tool_name": "plan_chapter_revision", "params": {"chapter_index": 3}}]
}
```

- [x] **Step 3: Record report and next phase recommendation**

The phase report must include:

- generated novel progress;
- Chapter 2 and 3 revision decisions;
- world-model proposal pressure;
- verification evidence;
- next phase recommendation.

## Phase Report

Report saved to:

- `docs/superpowers/notes/long-memory-agent/2026-05-18-phase8-revision-decision-loop.md`

Summary:

- Added read-only Agent tool `plan_chapter_revision`.
- Added structured revision action mapping from deterministic review findings.
- Added world-model proposal pressure summary.
- Added safety gate so a blocked revision plan stops follow-up writing tools in the same Agent run.
- Runtime dogfood produced blocked revision plans for Chapters 2 and 3.
- Runtime gate run blocked before Chapter 4 generation; Chapter 4 remains ungenerated.
