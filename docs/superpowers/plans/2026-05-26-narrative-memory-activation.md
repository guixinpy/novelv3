# Narrative Memory Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn longform memory from passive inspection into an active writing decision surface for the long-memory web-novel Agent.

**Architecture:** Add a read-only `memory_activation` projection that selects bounded prior memory, open foreshadowing, world-model state, and style anchors for a target chapter. Wire it into preflight, health projection, and chapter generation command args without changing persistence schema unless tests prove a write-side gap.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing Writing Agent tool registry/adapters, pytest.

---

### Task 1: Read-Only Memory Activation Plan

**Files:**
- Create: `backend/app/services/writing_agent/memory_activation.py`
- Create: `backend/tests/test_writing_agent_memory_activation.py`

- [x] **Step 1: Write failing projection tests**

Cover:
- target chapter 3 activates global/arc/recent chapter memory from chapters 1-2;
- open foreshadowing introduced before chapter 3 is selected;
- missing/stale longform maintenance produces `memory_coverage_debt`;
- activated items never include future chapters.

- [x] **Step 2: Implement `build_memory_activation_plan`**

Return a JSON-safe payload:
- `status`: `ready`, `degraded`, or `blocked`
- `activation`: categories `longform`, `foreshadowing`, `world_model`, `style`
- `coverage`: counts and `memory_coverage_debt`
- `prompt_block`: bounded Chinese text suitable for generation command args
- `memory_provenance`: standard provenance fields
- `recommended_next_tools`: maintenance or generation follow-ups

- [x] **Step 3: Run focused tests**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_activation.py -q
# 2 passed
```

- [ ] **Step 4: Commit**

```powershell
git add backend\app\services\writing_agent\memory_activation.py backend\tests\test_writing_agent_memory_activation.py docs\superpowers\plans\2026-05-26-narrative-memory-activation.md
git commit -m "Add narrative memory activation projection"
```

### Task 2: Tool Surface And Health Projection

**Files:**
- Modify: `backend/app/services/writing_agent/agent_memory_trace_tool_descriptors.py`
- Modify: `backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py`
- Modify: `backend/app/services/writing_agent/agent_health_projection.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_health_projection.py`

- [x] **Step 1: Register `inspect_agent_memory_activation_plan`**

Add a read-only internal longform memory tool with `non_blocking_report=True`.

- [x] **Step 2: Surface activation risk in health**

When `chapter_index` is present, health projection includes `memory_activation`.
If activation is degraded/blocked, diagnostics include `agent_memory_activation_degraded` or `agent_memory_activation_blocked` and recommend exact next tools.

- [x] **Step 3: Run focused tests**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_activation.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_tool_executor.py -k "memory_activation or agent_memory_trace_tool or health_projection" -q
# Superset run:
# backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_activation.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_health_projection.py -k "memory_activation or agent_memory_trace_tool or context_compression or creative_quality" -q
# 9 passed, 231 deselected
```

- [ ] **Step 4: Commit**

```powershell
git add backend\app\services\writing_agent\agent_memory_trace_tool_descriptors.py backend\app\services\writing_agent\agent_memory_trace_tool_adapters.py backend\app\services\writing_agent\agent_health_projection.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_health_projection.py docs\superpowers\plans\2026-05-26-narrative-memory-activation.md
git commit -m "Surface narrative memory activation to agents"
```

### Task 3: Generation Context Injection

**Files:**
- Modify: `backend/app/services/writing_agent/chapter_generation_tool.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Add activation to preflight**

`preflight_writing` includes `checks["memory_activation"]`. It warns, not blocks, when activation is degraded due bounded coverage; it blocks only if longform maintenance reports write-unsafe missing memory.

- [ ] **Step 2: Add activation command feedback**

`execute_generate_chapter_tool` appends `prompt_block` after continuity and length feedback. On success, output includes `agent_memory_activation` with source counts and provenance, not full prompt text.

- [ ] **Step 3: Prove no future leak**

Tests seed chapter 4 memory while generating chapter 3 and assert activation/generation feedback excludes chapter 4.

- [ ] **Step 4: Run focused tests**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_activation.py backend\tests\test_writing_agent_runs.py -k "memory_activation or preflight or generate_chapter" -q
```

- [ ] **Step 5: Commit**

```powershell
git add backend\app\services\writing_agent\chapter_generation_tool.py backend\app\services\writing_agent\run_service.py backend\tests\test_writing_agent_runs.py docs\superpowers\plans\2026-05-26-narrative-memory-activation.md
git commit -m "Inject narrative memory into chapter generation"
```

### Task 4: Write-After Memory Evidence And Dogfood

**Files:**
- Modify: `backend/app/core/longform_memory.py` only if tests reveal missing metadata in refreshed chapter memory
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-26-narrative-memory-activation-dogfood.md`
- Modify: `docs/superpowers/plans/2026-05-26-narrative-memory-activation.md`

- [ ] **Step 1: Verify write-after memory refresh evidence**

Focused tests must prove refreshed chapter memory records whether it used reviewed event summary, chapter content, outline, and activation-relevant metadata.

- [ ] **Step 2: Run dogfood**

Use an isolated SQLite DB. Generate or simulate at least chapters 1-3 with a planted clue in chapter 1 and chapter 3 target requiring that clue. Evidence must show activation selected the clue before generation/review.

- [ ] **Step 3: Run verification**

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_activation.py backend\tests\test_writing_agent_context_compression_projection.py backend\tests\test_writing_agent_health_projection.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_local_quality.ps1
```

- [ ] **Step 4: Completion audit and commit**

Record:
- activation selected prior memory and excluded future memory;
- generation trace/provenance captured activation evidence;
- health projection surfaced memory coverage debt;
- dogfood run IDs or exact substitute evidence.

```powershell
git add backend docs\superpowers\plans\2026-05-26-narrative-memory-activation.md docs\superpowers\notes\long-memory-agent\2026-05-26-narrative-memory-activation-dogfood.md
git commit -m "Complete narrative memory activation loop"
```
