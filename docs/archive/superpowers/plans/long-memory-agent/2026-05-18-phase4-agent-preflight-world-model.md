# Phase 4 Agent Preflight And World Model Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Agent-readable readiness gates so novelv3 stops continuing longform generation when required outline/world-model state is missing.

**Architecture:** Phase 4 extends the thin Agent run service with domain tools for preflight checks, Setup-to-world-model import, and chapter world-model analysis. It does not generate Chapter 3 unless preflight confirms the target chapter has enough outline/world context.

**Tech Stack:** FastAPI, SQLAlchemy, existing Writing Agent run service, existing Athena longform/world-model import, existing longform/retrieval diagnostics, pytest.

---

## Phase Metadata

- **Phase:** 4
- **Date:** 2026-05-18
- **Verification Tier:** T1 for service/API tests; T2 for runtime dogfood preflight and world-model import.
- **Primary Output:** Agent preflight and world-model readiness tools plus a Phase 4 report.
- **Dogfood Output:** Run Agent preflight for Chapter 3. Generate Chapter 3 only if the preflight is ready.
- **Secret Handling:** Do not write API keys to docs, commits, or `.env`.

## Phase 4 Success Criteria

- Agent runs support `preflight_writing`.
- Agent runs support `import_setup_world_model`.
- Agent runs support `analyze_chapter_world_model`.
- `preflight_writing` checks at least:
  - setup exists.
  - current world-model profile exists.
  - target chapter outline exists.
  - previous chapter exists when chapter index is greater than 1.
  - longform maintenance is ready.
  - retrieval diagnostics are available.
- If target chapter outline is missing, preflight returns `status=blocked` and the Agent run does not continue to `generate_chapter`.
- Importing setup through Agent creates or reuses a world-model profile.
- After world-model profile exists, analyzing existing chapters can create or update proposal items.
- Phase 4 report records whether Chapter 3 was generated or intentionally blocked.

## Explicit Non-Goals

- Do not design rolling outline generation in this phase.
- Do not rewrite outline generation.
- Do not auto-approve Athena proposals.
- Do not generate Chapter 3 if Chapter 3 outline is absent.
- Do not add frontend UI yet.
- Do not change the world-model schema.

## Files

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase4-agent-preflight-world-model.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase4-agent-preflight-world-model.md`

## Task 1: Add Preflight Tool

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing preflight tests**

Add tests:

```python
def test_agent_preflight_blocks_when_target_outline_is_missing(client, db_session):
    ...

def test_agent_preflight_ready_when_required_context_exists(client, db_session):
    ...
```

The first test should create a project with setup, outline containing only chapter 1, and chapter 2, then run:

```json
{
  "goal": "检查第3章是否可写",
  "tools": [
    {
      "tool_name": "preflight_writing",
      "params": {"chapter_index": 3}
    },
    {
      "tool_name": "generate_chapter",
      "params": {"chapter_index": 3}
    }
  ]
}
```

Expected:

- run status is `blocked`.
- only the preflight step exists.
- preflight output includes an issue with `code=missing_outline_chapter`.

- [ ] **Step 2: Implement `preflight_writing`**

Add `preflight_writing` to the Agent tool registry. Implement it inside `WritingAgentRunService` rather than `ActionExecutionService`.

Required output shape:

```json
{
  "status": "ready|blocked|warning",
  "chapter_index": 3,
  "checks": {
    "setup": {"status": "ready|missing"},
    "world_model_profile": {"status": "ready|missing", "profile_version": 1},
    "outline_chapter": {"status": "ready|missing"},
    "previous_chapter": {"status": "ready|missing|not_required"},
    "longform_maintenance": {"status": "ready|warning|unknown"},
    "retrieval": {"status": "ready|warning|unknown"}
  },
  "issues": [
    {"code": "missing_outline_chapter", "severity": "blocker", "message": "第3章缺少章节大纲。"}
  ]
}
```

- [ ] **Step 3: Stop run on blocked preflight**

If a tool returns `status=blocked`, mark the step `blocked`, mark the run `blocked`, write `run.error`, and do not execute later tools.

- [ ] **Step 4: Run preflight tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Expected: pass.

## Task 2: Add World Model Import Tool

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing import tool test**

Add:

```python
def test_agent_import_setup_world_model_creates_profile(client, db_session):
    ...
```

Expected:

- run status is `success`.
- step tool is `import_setup_world_model`.
- output contains `profile_version=1`.
- project has one `ProjectProfileVersion`.

- [ ] **Step 2: Implement `import_setup_world_model`**

Call:

```python
from app.core.athena_longform import import_setup_to_world_model
```

Store the returned payload as step output.

- [ ] **Step 3: Run import tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_import_setup_world_model_creates_profile -q
```

Expected: pass.

## Task 3: Add Chapter World-Model Analysis Tool

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing analysis tool test**

Add:

```python
def test_agent_analyze_chapter_world_model_records_proposal_output(client, db_session):
    ...
```

Expected:

- step tool is `analyze_chapter_world_model`.
- output includes `chapter_index`.
- output includes proposal item counts from `created` or `updated`.

- [ ] **Step 2: Implement `analyze_chapter_world_model`**

Call:

```python
from app.core.athena_longform import analyze_chapter_to_world_proposals
```

Use `params.chapter_index`, defaulting to `1`.

- [ ] **Step 3: Run analysis tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Expected: pass.

## Task 4: Runtime Dogfood Preflight For Chapter 3

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase4-agent-preflight-world-model.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase4-agent-preflight-world-model.md`

- [ ] **Step 1: Run targeted tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_athena_longform.py::test_import_setup_creates_formal_profile_entities_and_rules -q
```

Expected: pass.

- [ ] **Step 2: Run diff and secret checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: no diff whitespace errors and no secrets.

- [ ] **Step 3: Use Agent to import Setup to world model**

Call `/agent-runs` with:

```json
{
  "goal": "为《雾港回声》导入Setup到Athena世界模型，为后续章节生成建立profile。",
  "tools": [{"tool_name": "import_setup_world_model"}]
}
```

Expected: step output reports `profile_version`.

- [ ] **Step 4: Use Agent to analyze Chapters 1 and 2**

Call `/agent-runs` with two `analyze_chapter_world_model` tools:

```json
{
  "goal": "分析《雾港回声》前两章并生成Athena世界事实候选。",
  "tools": [
    {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 1}},
    {"tool_name": "analyze_chapter_world_model", "params": {"chapter_index": 2}}
  ]
}
```

Expected: analysis outputs are recorded as Agent steps.

- [ ] **Step 5: Run Chapter 3 preflight**

Call `/agent-runs` with:

```json
{
  "goal": "检查《雾港回声》第3章是否具备生成条件。",
  "tools": [
    {"tool_name": "preflight_writing", "params": {"chapter_index": 3}},
    {"tool_name": "generate_chapter", "params": {"chapter_index": 3}}
  ]
}
```

Expected if Chapter 3 outline is still missing:

- run status is `blocked`.
- generation step is not executed.
- Chapter 3 is not generated.

- [ ] **Step 6: Write Phase 4 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-18-phase4-agent-preflight-world-model.md` with:

```markdown
# Phase 4 Agent Preflight And World Model Readiness

## Runtime
## Implementation
## Dogfood Evidence
## World Model Import
## Chapter 3 Preflight
## Issues Found
## Issues Fixed
## Verification
## Next Phase Recommendation
```

## Task 5: Commit Phase 4

**Files:**
- All files changed in this phase.

- [ ] **Step 1: Commit code**

```powershell
git add backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_runs.py
git commit -m "feat: add writing agent preflight tools"
```

- [ ] **Step 2: Commit docs**

```powershell
git add docs/superpowers/plans/long-memory-agent/2026-05-18-phase4-agent-preflight-world-model.md docs/superpowers/notes/long-memory-agent/2026-05-18-phase4-agent-preflight-world-model.md
git commit -m "docs: record long memory agent phase 4"
```

## Self-Review

- Spec coverage: This phase strengthens Agent orchestration, world-model readiness, and dogfood-driven blocking.
- Placeholder scan: No `TBD` markers are left.
- Scope check: Rolling outline expansion is deliberately deferred because preflight should first make the missing outline problem explicit.

## Phase 4 Completion Notes

Phase 4 completed Agent readiness gates and world-model tools. Chapter 3 generation was intentionally blocked because the current outline contains only Chapter 1 despite claiming `total_chapters=600`.

## Actual Completed Work

- Added `preflight_writing` Agent tool.
- Added `import_setup_world_model` Agent tool.
- Added `analyze_chapter_world_model` Agent tool.
- Added run and step `blocked` state handling.
- Added `blocked_step_count` to Agent run output.
- Added preflight checks for setup, outline coverage, profile readiness, previous chapter, longform maintenance, and retrieval.
- Stopped Agent execution after blocked preflight so later `generate_chapter` tools do not run.

## Novel Progress

- Novel: `《雾港回声》`.
- Generated chapters remain `2 / 600`.
- Chapter 3 was not generated.
- Setup was imported into Athena world model.
- Chapter 1 and Chapter 2 were analyzed into world-model proposal items.
- Athena proposal queue now has `15` reviewable items.

## Issues Found

- Current outline has only one concrete chapter entry.
- Chapter 3 lacks target chapter outline.
- Further generation should stop until rolling outline expansion exists.
- The project now needs proposal review or triage before large-scale writing.

## Issues Fixed

- Missing world-model profile no longer blocks analysis once Agent imports Setup.
- Missing outline coverage now blocks generation instead of being silently ignored.
- Agent run summary now reports blocked steps.

## Verification

- `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q` -> `11 passed`.
- `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_athena_longform.py::test_import_setup_creates_formal_profile_entities_and_rules -q` -> `12 passed`.
- `git diff --check` -> exit code `0`.
- `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references` -> no matches.
- Runtime Agent import setup run succeeded.
- Runtime Agent chapter analysis run succeeded.
- Runtime Agent Chapter 3 preflight blocked generation.
- Runtime Chapter 3 fetch returned `404`.

## Next Phase Recommendation

Phase 5 should implement rolling outline expansion and proposal triage before generating Chapter 3:

- Add an Agent tool for expanding outline coverage without overwriting existing entries.
- Have preflight recommend/call outline expansion when `missing_outline_chapter` is found.
- Add tests that preserve Chapter 1 outline while adding Chapters 2-10 or 3-12.
- Only generate Chapter 3 after preflight returns `ready`.
