# Phase142 Mutation Fingerprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Writing Agent tool that computes stable mutation fingerprints for planned write actions.

**Architecture:** Create a focused `mutation_fingerprint` service that maps known mutating tools to deterministic target components and SHA-256 fingerprints. Register a new internal preflight tool, `inspect_agent_mutation_fingerprints`, so recovery and approval planning can bind a write action to a concrete project target before execution.

**Tech Stack:** Python, pytest, existing Writing Agent tool registry and static adapter executor.

---

## Scope

This phase is intentionally read-only. It does not change write execution, approval enforcement, task scheduling, or chapter generation behavior.

Covered tools:
- `generate_chapter`
- `generate_chapter_range`
- `apply_world_model_proposal_resolution`

Out of scope:
- Persisting fingerprints on runs or background tasks.
- Enforcing fingerprint matches during execution.
- Reworking approval contract hashes.

## Files

- Create: `backend/app/services/writing_agent/mutation_fingerprint.py`
- Create: `backend/tests/test_writing_agent_mutation_fingerprint.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase142-mutation-fingerprint.md`

## Task 1: Service Tests

- [ ] **Step 1: Add failing service tests**

Create `backend/tests/test_writing_agent_mutation_fingerprint.py` with tests for:
- stable fingerprint for the same `generate_chapter` target
- distinct fingerprint for different chapter targets
- blocked diagnostic for invalid/missing `generate_chapter_range` range
- world model proposal bundle target extraction

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_mutation_fingerprint.py -q
```

Expected: fails because `app.services.writing_agent.mutation_fingerprint` does not exist.

- [ ] **Step 3: Implement minimal service**

Create `backend/app/services/writing_agent/mutation_fingerprint.py` with:
- `MUTATION_FINGERPRINT_VERSION`
- `build_mutation_fingerprint(project_id, tool_name, params)`
- `inspect_agent_mutation_fingerprints(project_id, tools)`
- stable JSON serialization with sorted keys
- SHA-256 fingerprint over version, project id, tool name, action, target type, and target id

- [ ] **Step 4: Run GREEN for service**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_mutation_fingerprint.py -q
```

Expected: all tests pass.

## Task 2: Registry Contract

- [ ] **Step 1: Add failing registry test**

Add `test_agent_tool_registry_includes_inspect_agent_mutation_fingerprints` to `backend/tests/test_writing_agent_tool_registry.py`.

Assertions:
- descriptor exists
- `internal is True`
- `non_blocking_report is True`
- `category == "preflight"`
- `target_type == "agent_mutation_fingerprint"`
- input schema exposes `tools` array
- tool appears in `allowed_tool_names()` and `non_blocking_report_tool_names()`

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_inspect_agent_mutation_fingerprints -q
```

Expected: fails because the descriptor is missing.

- [ ] **Step 3: Register descriptor**

Modify `backend/app/services/writing_agent/tool_registry.py` to add `inspect_agent_mutation_fingerprints` near other preflight inspection tools.

- [ ] **Step 4: Run GREEN for registry**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_inspect_agent_mutation_fingerprints -q
```

Expected: test passes.

## Task 3: Executor Adapter

- [ ] **Step 1: Add failing executor test**

Add `test_tool_executor_dispatches_inspect_agent_mutation_fingerprints_adapter` to `backend/tests/test_writing_agent_tool_executor.py`.

Use `WritingAgentToolRequest(tool_name="inspect_agent_mutation_fingerprints", params={"tools": [{"tool_name": "generate_chapter", "params": {"chapter_index": "4"}}]})`.

Assert:
- result handled is true
- output status is `completed`
- first result has target id `chapter:4`
- adapter metadata mutability is `read`

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py::test_tool_executor_dispatches_inspect_agent_mutation_fingerprints_adapter -q
```

Expected: fails because no static adapter exists.

- [ ] **Step 3: Add executor adapter**

Modify `backend/app/services/writing_agent/tool_executor.py`:
- add `_inspect_agent_mutation_fingerprints`
- register it in `_STATIC_TOOL_ADAPTERS`
- keep mutability `read`

- [ ] **Step 4: Run GREEN for executor**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py::test_tool_executor_dispatches_inspect_agent_mutation_fingerprints_adapter -q
```

Expected: test passes.

## Task 4: Regression and Report

- [ ] **Step 1: Run targeted regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_mutation_fingerprint.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_write_gate_coverage.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
```

Run:

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: no whitespace errors and no committed API key leaks.

- [ ] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase142-mutation-fingerprint.md` with:
- phase objective
- implementation summary
- verification evidence
- known limits
- next phase recommendation

- [ ] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/mutation_fingerprint.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_mutation_fingerprint.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase142-mutation-fingerprint.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase142-mutation-fingerprint.md
git commit -m "feat: inspect mutation fingerprints"
git push origin main
```

Expected: commit succeeds and push updates `origin/main`.
