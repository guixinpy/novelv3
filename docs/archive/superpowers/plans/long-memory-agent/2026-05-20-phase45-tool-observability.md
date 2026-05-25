# Phase45 Tool Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add adapter metadata, migration diagnostics, and execution-size/timing metrics to Writing Agent tool results so the Agent tool layer is observable enough for later recovery, task queue, and self-optimization work.

**Architecture:** Keep `run_service.py` as the step lifecycle owner. `tool_executor.py` owns adapter metadata and migration diagnostics. `agent_tool_result` remains the normalized step result envelope and gains compact metrics.

---

## Why This Phase

Phase43 introduced an executor wrapper. Phase44 added an adapter map. The next missing capability is observability:

- Which tools are adapter-backed?
- Which internal tools still run through legacy branches?
- Which adapter is read-only/reporting vs mutation-capable?
- How large is each tool output?
- How long did each step take?

Without these fields, later retry/recovery/task-queue logic would need to infer too much from ad hoc tool output.

## Scope

In scope:

- Add adapter metadata in `tool_executor.py`.
- Expose:
  - `writing_agent_tool_adapter_metadata(tool_name)`;
  - `unhandled_internal_writing_agent_tool_names()`.
- Include adapter metadata in `agent_tool_result`.
- Include `elapsed_ms` and `output_size_bytes` in `agent_tool_result`.
- Add tests for adapter metadata, unhandled migration diagnostics, and result metrics.

Out of scope:

- Moving additional business tools into the executor.
- Persisting metrics as first-class database columns.
- Retry/recovery behavior.
- Frontend timeline display.
- Full benchmark or load test.

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Test adapter metadata**

Assert:

- `review_chapter_quality` has metadata with `adapter_type == "static"`, `mutability == "read"`, `category == "review"`;
- `preflight_writing` has metadata with `adapter_type == "injected"`;
- `generate_chapter` has no adapter metadata.

- [x] **Step 2: Test unhandled internal tool diagnostics**

Assert unhandled internal list includes mutation-heavy tools such as:

- `analyze_chapter_world_model`;
- `apply_world_model_proposal_resolution`;
- `create_revision_draft`.

Assert it excludes:

- `review_chapter_quality`;
- `plan_writing_agent_run`;
- `preflight_writing`.

- [x] **Step 3: Test `agent_tool_result` metrics**

Use an API run with `describe_agent_tools` and assert envelope includes:

- `adapter.adapter_type == "static"`;
- `adapter.mutability == "read"`;
- `elapsed_ms >= 0`;
- `output_size_bytes > 0`.

- [x] **Step 4: Verify red**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "adapter_metadata or unhandled_internal or result_metrics"
```

Expected: FAIL because metadata helpers and envelope metrics do not exist yet.

## Task 2: Implement Tool Adapter Metadata

**Files:**

- Modify: `backend/app/services/writing_agent/tool_executor.py`

- [x] **Step 1: Add adapter metadata dataclass**

Add metadata fields:

- `tool_name`;
- `adapter_type`;
- `category`;
- `mutability`;
- `handler_name`.

- [x] **Step 2: Store metadata next to static handlers**

Replace the bare handler map with adapter objects.

- [x] **Step 3: Add diagnostics helpers**

Implement:

- `static_writing_agent_tool_adapter_names()`;
- `writing_agent_tool_adapter_metadata(tool_name)`;
- `unhandled_internal_writing_agent_tool_names()`.

## Task 3: Add Result Metrics

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Measure finished time once**

In success/fail/block handlers, compute `finished_at` before building the envelope.

- [x] **Step 2: Add envelope fields**

Add:

- `elapsed_ms`;
- `output_size_bytes`;
- `adapter`.

Keep output-size calculation non-recursive by measuring output before `agent_tool_result` is added.

## Task 4: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase45-tool-observability.md`

- [x] **Step 1: Run focused GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "adapter_metadata or unhandled_internal or result_metrics"
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
