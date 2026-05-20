# Phase46 Backfill Tool Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the mutation-light maintenance tool `backfill_outline_gaps` from `run_service.py` into the Writing Agent executor adapter map.

**Architecture:** `run_service.py` keeps lifecycle and blocking semantics. `tool_executor.py` owns the maintenance adapter and parameter normalization. Existing API behavior is preserved by running the current Writing Agent run tests.

---

## Why This Phase

Phase45 exposed unhandled internal tools as migration diagnostics. `backfill_outline_gaps` is a good next adapter candidate because:

- it has a narrow parameter contract;
- it delegates to one core maintenance function;
- it is already covered by API behavior tests;
- it does not depend on run ID, chapter generation feedback, or private preflight checks.

## Scope

In scope:

- Add `backfill_outline_gaps` to the executor adapter map.
- Mark its adapter metadata as:
  - `category == "maintenance"`;
  - `mutability == "write"`.
- Remove the corresponding branch from `run_service.py`.
- Update migration diagnostics tests.

Out of scope:

- `expand_outline_window`;
- `analyze_chapter_world_model`;
- revision draft/apply tools;
- world-model apply tools;
- async expansion/compression tools.

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [x] **Step 1: Test adapter metadata**

Assert `backfill_outline_gaps` has:

- `adapter_type == "static"`;
- `category == "maintenance"`;
- `mutability == "write"`.

- [x] **Step 2: Test parameter normalization**

Monkeypatch `backfill_missing_outline_chapters_from_content` and assert:

- `before_chapter` is converted to int when provided as string;
- fallback to `chapter_index` works;
- missing value passes `None`.

- [x] **Step 3: Update unhandled diagnostics**

Assert `backfill_outline_gaps` is no longer in `unhandled_internal_writing_agent_tool_names()`.

- [x] **Step 4: Verify red**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -q -k "backfill"
```

Expected: FAIL because the adapter is not implemented yet.

## Task 2: Implement Adapter

**Files:**

- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Add static adapter handler**

Move the existing parameter logic from `run_service.py` to `tool_executor.py`.

- [x] **Step 2: Register metadata**

Add `backfill_outline_gaps` to `_STATIC_TOOL_ADAPTERS`.

- [x] **Step 3: Remove run-service branch**

Delete the old `if tool.tool_name == "backfill_outline_gaps"` branch.

## Task 3: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase46-backfill-tool-adapter.md`

- [x] **Step 1: Run focused GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -q -k "backfill"
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
