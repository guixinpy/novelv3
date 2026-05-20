# Phase44 Tool Adapter Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the Phase43 executor wrapper from hand-written branch dispatch into a registry-checked adapter map, then migrate low-risk read/report tools out of `run_service.py`.

**Architecture:** `run_service.py` remains the run lifecycle owner. `tool_executor.py` owns Agent-native tool adapter dispatch. Adapters are explicit functions keyed by tool name and guarded by `tool_registry` descriptors, so unsupported or public legacy generation tools still fall back to existing behavior.

---

## Why This Phase

Phase43 introduced the executor boundary. If it remains another local `if` chain, future module toolization will repeat the same problem in a new file. This phase creates a scalable adapter map and migrates tools that are mostly read/report orchestration.

## Scope

In scope:

- Add a static adapter map to `tool_executor.py`.
- Expose `static_writing_agent_tool_adapter_names()` for diagnostics/tests.
- Migrate:
  - `review_chapter_quality`;
  - `review_chapter_continuity`;
  - `plan_chapter_revision`;
  - `review_world_model_proposals`;
  - `plan_world_model_proposal_resolution`;
  - `preview_world_model_proposal_resolution`;
  - `draft_world_model_proposal_resolution_decisions`.
- Keep existing run lifecycle, blocking semantics, and report-followup stop logic in `run_service.py`.

Out of scope:

- `generate_chapter`.
- world-model mutation/apply tools.
- revision draft/apply tools.
- async chapter expansion/compression tools.
- retry/recovery planner.

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [x] **Step 1: Test adapter registry shape**

Assert `static_writing_agent_tool_adapter_names()` includes the migrated report tools and does not include public generation tools.

- [x] **Step 2: Test chapter report adapters dispatch with normalized params**

Monkeypatch core review/planner functions and assert:

- `review_chapter_quality` passes `chapter_index`;
- `review_chapter_continuity` defaults `lookback` to `20`;
- `plan_chapter_revision` passes `chapter_index`.

- [x] **Step 3: Test world proposal report adapters dispatch with normalized params**

Monkeypatch core world proposal report functions and assert:

- offset defaults to `0`;
- limit defaults to `50`;
- decisions fallback to `[]`;
- predicate policies are passed only when a dict.

- [x] **Step 4: Verify red**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -q
```

Expected: FAIL because adapter map helpers and migrated handlers do not exist yet.

## Task 2: Implement Adapter Map

**Files:**

- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [x] **Step 1: Add adapter map**

Create `_STATIC_TOOL_ADAPTERS` keyed by tool name.

- [x] **Step 2: Add handler helper**

Allow handler functions to return dict outputs. Keep executor async but adapter handlers can be sync.

- [x] **Step 3: Add diagnostics helper**

Expose `static_writing_agent_tool_adapter_names()`.

## Task 3: Remove Migrated Branches from Run Service

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Delete migrated read/report branches**

Remove branches now handled by executor:

- chapter review/report tools;
- world proposal report/plan/preview/draft tools.

- [x] **Step 2: Keep mutation-heavy branches untouched**

Leave generation, revision draft/apply, world model apply, continuity anchor seeding, and chapter expansion/compression in place.

## Task 4: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase44-tool-adapter-map.md`

- [x] **Step 1: Run focused GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -q
```

- [x] **Step 2: Run T1 module verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 3: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 4: Write report, commit, push**
