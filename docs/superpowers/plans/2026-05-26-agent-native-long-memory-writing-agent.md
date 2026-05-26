# Agent-Native Long-Memory Writing Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade novelv3 into a domain-specific long-memory writing Agent that can generate, review, diagnose, recover, and persist long-term writing memory across sustained web-novel work.

**Architecture:** Build vertical slices around existing Writing Agent tools instead of replacing the system wholesale. Each slice adds an Agent-callable projection or policy, then wires it into `inspect_agent_health_projection`, `run_service`, tool descriptors/adapters, and dogfood notes only after tests prove the behavior.

**Tech Stack:** Python/FastAPI/SQLAlchemy backend, existing Writing Agent tool registry, pytest, Vue/Vitest for UI surfaces only when a backend contract becomes visible to users.

---

## Scope Map

This plan consumes `docs/agent-native-guide/01-reference-patterns-report.md` beyond the already-committed control-loop hardening.

Already committed in `bd23d38a`:
- Five-level loop risk diagnostics.
- Recent-window creative quality projection for quality/continuity reviews.
- Lightweight memory provenance field convention.
- Closed-loop fixture for generate/review/diagnose/recovery suggestion.

Remaining directions to finish:
- Context layered compression pre-diagnostics.
- Memory Tree vertical slice.
- Config-driven AgentDefinition worker slice.
- StopHooks or equivalent strategy layer.
- Pre/post tool hook mechanism.
- Event/task queue boundary decision and minimal event projection.
- Formal provenance schema beyond a helper.
- Long-term drift, foreshadowing, and quality trend monitoring.
- Recovery/checkpoint resume for multi-chapter generation.
- Real dogfood loop with run/chapter/trace/provenance evidence.

## Architecture Decisions To Lock During Execution

1. Context compression granularity starts as `chapter_window`, not token-only. Evidence: web-novel state has natural chapter/volume boundaries and current chapter must remain protected.
2. Memory Tree node levels start as `volume -> chapter -> scene -> beat`. `paragraph` is too fine for first implementation; exact text stays in retrieval.
3. Sub Agent depth starts at 2 below orchestrator: `orchestrator -> reviewer/worker`. No recursive worker spawning in the first slice.
4. `run_service.py` is split by extracting strategy modules first; no large rewrite until StopHooks tests cover current behavior.
5. Provenance becomes a typed schema module used by memory/context/knowledge/tree/workers before adding database persistence.

---

### Task 1: Context Compression Projection

**Files:**
- Create: `backend/app/services/writing_agent/agent_context_compression_projection.py`
- Modify: `backend/app/services/writing_agent/agent_memory_trace_tool_descriptors.py`
- Modify: `backend/app/services/writing_agent/agent_memory_trace_tool_adapters.py`
- Modify: `backend/app/services/writing_agent/agent_health_projection.py`
- Test: `backend/tests/test_writing_agent_context_compression_projection.py`
- Test: `backend/tests/test_writing_agent_health_projection.py`

- [x] **Step 1: Write failing projection tests**

Create tests for:
- no generated context returns `status == "ready"` and `granularity == "chapter_window"`;
- oversized prompt context returns `status == "warning"`, risk `context_window_pressure`, and next tool `summarize_longform_context`;
- three compression failures return `status == "blocked"`, risk `context_guard_open`, and next tool `inspect_agent_memory_route`.

Run:
```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_context_compression_projection.py -q
```
Expected: fails because the module does not exist.

- [x] **Step 2: Implement minimal projection**

Implement `inspect_agent_context_compression_projection(db, project_id, chapter_index=None, max_chars=None, context_guard_failure_count=0)` by calling `summarize_longform_context(..., include_prompt_context=False)` and projecting:
- `strategy.granularity = "chapter_window"`
- `summary.prompt_context_chars`
- `summary.max_chars`
- `summary.usage_ratio`
- `summary.truncated_section_count`
- `risks`
- `recommended_next_tools`
- `memory_provenance`

- [x] **Step 3: Register Agent tool**

Add `inspect_agent_context_compression_projection` to memory/trace descriptors and adapters as a read-only internal tool.

- [x] **Step 4: Wire health projection**

When `chapter_index` is provided, include `context_compression` in `inspect_agent_health_projection`; if warning/blocked, add diagnostics and recommended tools.

- [x] **Step 5: Verify**

Run:
```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_context_compression_projection.py backend\tests\test_writing_agent_health_projection.py -q
```

Completed first-slice verification:
```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_context_compression_projection.py backend\tests\test_writing_agent_health_projection.py backend\tests\test_writing_agent_tool_registry.py -q
# 81 passed

backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py -q
# 159 passed
```

### Task 2: Formal Provenance Schema

**Files:**
- Modify: `backend/app/services/writing_agent/memory_provenance_contract.py`
- Modify: `backend/app/services/writing_agent/agent_memory_route.py`
- Modify: `backend/app/services/writing_agent/agent_knowledge_base_route.py`
- Modify: `backend/app/services/writing_agent/longform_context_summary.py`
- Test: `backend/tests/test_writing_agent_memory_provenance_contract.py`

- [ ] **Step 1: Write failing schema tests**

Assert `build_memory_provenance(...)` validates required fields, normalizes `sources`, `windows`, `recovery`, and rejects missing `trace.source`.

- [ ] **Step 2: Replace helper-only usage with schema builder**

Expose a small typed builder:
```python
build_memory_provenance(
    version: str,
    status: str,
    sources: list[dict[str, Any]],
    windows: dict[str, Any],
    recovery: dict[str, Any],
    trace: dict[str, Any],
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]
```

- [ ] **Step 3: Verify route compatibility**

Run:
```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_provenance_contract.py backend\tests\test_writing_agent_memory_route.py backend\tests\test_writing_agent_knowledge_base_route.py backend\tests\test_writing_agent_runs.py -k provenance -q
```

### Task 3: StopHooks Strategy Layer

**Files:**
- Create: `backend/app/services/writing_agent/agent_stop_hooks.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Test: `backend/tests/test_writing_agent_stop_hooks.py`
- Test: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing tests for existing behavior**

Cover loop risk critical, missing approval, blocked memory provenance, and context guard blocked as separate stop decisions.

- [ ] **Step 2: Extract strategy layer**

Implement:
```python
evaluate_agent_stop_hooks(run, steps, latest_output) -> dict[str, Any]
```
Return `status`, `reason`, `severity`, `recommended_tools`, `allow_continue`.

- [ ] **Step 3: Wire into `run_service.py`**

Replace inline stop checks only where tests prove equivalence. Preserve existing output shape.

### Task 4: Tool Lifecycle Hooks

**Files:**
- Create: `backend/app/services/writing_agent/tool_lifecycle_hooks.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Test: `backend/tests/test_writing_agent_tool_lifecycle_hooks.py`

- [ ] **Step 1: Write failing tests**

Cover pre-tool denial for child-agent guarded writes, post-tool event envelope, and hook output appearing in step metadata.

- [ ] **Step 2: Implement hook registry**

Implement deterministic built-in hooks only:
- `before_tool_call`
- `after_tool_call`
- `on_tool_error`

No plugin loading yet.

### Task 5: AgentDefinition Worker Slice

**Files:**
- Create: `backend/app/services/writing_agent/agent_definitions.py`
- Create: `backend/app/services/writing_agent/agent_worker_dispatch.py`
- Create: `backend/app/services/writing_agent/agent_definitions/reviewer.yaml`
- Test: `backend/tests/test_writing_agent_agent_definitions.py`

- [ ] **Step 1: Write failing tests**

Assert reviewer worker config loads with allowed tools `review_chapter_quality`, `review_chapter_continuity`, `inspect_agent_world_model_route`, and cannot dispatch children.

- [ ] **Step 2: Implement config loader**

Support repo-local YAML definitions with explicit `name`, `role`, `max_depth`, `allowed_tools`, and `write_policy`.

- [ ] **Step 3: Implement dispatch preview**

Add a read-only preview function that returns planned worker task envelopes without executing LLM calls.

### Task 6: Memory Tree Vertical Slice

**Files:**
- Create: `backend/app/services/writing_agent/memory_tree.py`
- Create: `backend/app/services/writing_agent/memory_tree_tool_descriptors.py`
- Create: `backend/app/services/writing_agent/memory_tree_tool_adapters.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Test: `backend/tests/test_writing_agent_memory_tree.py`

- [ ] **Step 1: Write failing tree tests**

Seed chapters and longform memories. Assert tree levels `volume`, `chapter`, `scene`, `beat` and source refs point back to chapter/memory IDs.

- [ ] **Step 2: Implement in-memory projection first**

Build deterministic tree projection from existing `ChapterContent`, `Outline`, `LongformMemory`, and `Storyline` data. Do not add tables until dogfood shows persistence is needed.

- [ ] **Step 3: Add drill-down tool**

Expose `inspect_agent_memory_tree` with params `level`, `node_id`, `chapter_index`, `query`.

### Task 7: Long-Term Narrative Trend Monitor

**Files:**
- Create: `backend/app/services/writing_agent/narrative_trend_projection.py`
- Modify: `backend/app/services/writing_agent/agent_health_projection.py`
- Test: `backend/tests/test_writing_agent_narrative_trend_projection.py`

- [ ] **Step 1: Write failing tests**

Cover:
- style drift findings from review output;
- world-model contradiction findings;
- unresolved/overdue foreshadowing from Storyline/Athena data;
- trend status `ready`, `watch`, `needs_human_judgment`.

- [ ] **Step 2: Implement projection**

Aggregate existing review step outputs and available storyline/world-model records. Do not invent rhythm automation; mark pacing risks as `requires_human_judgment`.

### Task 8: Recovery And Checkpoint Resume

**Files:**
- Modify: `backend/app/services/writing_agent/recovery_policy.py`
- Modify: `backend/app/services/writing_agent/recovery_planner.py`
- Modify: `backend/app/services/writing_agent/batch_execution.py`
- Test: `backend/tests/test_writing_agent_recovery_checkpoint_resume.py`

- [ ] **Step 1: Write failing tests**

Seed a batch run with chapters 1-3 completed, chapter 4 blocked, chapter 5 pending. Assert recovery preview resumes at chapter 4 and skips completed chapters.

- [ ] **Step 2: Implement resume policy**

Use persisted `WritingAgentStep`, `BackgroundTask`, and chapter records as checkpoint evidence. Return explicit skipped/completed/next ranges.

### Task 9: Event And Task Queue Boundary

**Files:**
- Create: `backend/app/services/writing_agent/agent_event_projection.py`
- Modify: `backend/app/services/writing_agent/agent_job_projection.py`
- Test: `backend/tests/test_writing_agent_event_projection.py`

- [ ] **Step 1: Write failing projection tests**

Assert tool start/complete/error events can be projected from existing run/step/job data without adding a new event bus.

- [ ] **Step 2: Implement minimal event projection**

Prefer projection over new event bus. Escalate to persistence only if dogfood shows missing causality.

### Task 10: Real Dogfood Loop

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-26-full-agent-native-dogfood.md`
- Optional modify: backend/frontend files only for bugs surfaced by dogfood

- [ ] **Step 1: Restore local services**

Run existing Windows chain: check ports 8000/5173, run migrations, start backend/frontend, verify `/api/v1/health` and frontend 200.

- [ ] **Step 2: Execute multi-chapter loop**

Run at least one loop:
generate chapters -> review quality/continuity -> inspect health/context/memory/tree -> plan recovery -> apply safe recovery -> regenerate or continue.

- [ ] **Step 3: Record evidence**

Record run IDs, chapter indexes, trace IDs, provenance statuses, recovery actions, and observed UX/API issues.

### Task 11: Verification And Completion Audit

**Files:**
- Modify: `docs/agent-native-guide/01-reference-patterns-report.md`
- Modify: dogfood note from Task 10

- [ ] **Step 1: Run focused tests per slice**

Each task must include its focused pytest command and result in the notes.

- [ ] **Step 2: Run full local quality**

Run:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_local_quality.ps1
```

- [ ] **Step 3: E2E or substitute evidence**

Run E2E when service credentials and browser state are available. If not, record exact missing env vars or setup reason and provide backend/API/browser-smoke substitute evidence.

- [ ] **Step 4: Completion audit**

Map every objective item to evidence:
- 4.1 five direct patterns;
- 4.2 six formerly deferred patterns;
- section six five decisions;
- real dogfood loop;
- full verification.
