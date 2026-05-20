# Phase52 Longform Context Summary Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a read-only `summarize_longform_context` Writing Agent tool so the Agent can inspect longform project context before planning or generating chapters.

**Architecture:** Reuse the existing deterministic `build_longform_context_package()` path as the source of truth, then add a thin summary/projection layer for Agent consumption. The new tool is internal, read-only, non-blocking, and returns provenance, diagnostics, and bounded context instead of raw unlimited prompt dumps.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing Writing Agent tool registry/executor, pytest.

---

## Reference Assimilation

- `openclaw`: absorb runtime-only context projection, source provenance, and auditable context traces. Do not copy its multi-channel chat routing or executable tool-search sandbox.
- `hermes-agent`: absorb head/tail protection, structured context summary, and bounded tool-result previews. Do not copy generic chat compaction as the novel context model.
- `openhuman`: absorb read-only planner posture, recall options, and source-of-truth separation. Do not copy its external personal memory daemon or full Memory Tree backend.

novelv3 adaptation:

- World model facts remain authoritative.
- Longform memories and retrieval hits are context accelerators, not truth.
- The tool returns compact sections and source keys; full prompt context is opt-in.
- Missing/stale context becomes diagnostics and next-step hints, not automatic repair.

## Files

- Create: `backend/app/services/writing_agent/longform_context_summary.py`
  - Converts `build_longform_context_package()` output plus project/outline/chapter/memory diagnostics into a bounded Agent summary.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Register `summarize_longform_context` as an internal, read-only, non-blocking report tool.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Add a static adapter with `mutability="read"`.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Assert registry contract and target type.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Assert API execution returns bounded, sourced longform context and adapter metadata.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase52-longform-context-summary.md`
  - Record implementation, reference absorption, verification, and next phase.

## Task 1: Registry Contract

- [ ] **Step 1: Write failing registry test**

Add assertions that `summarize_longform_context` exists, is internal, non-blocking, and targets `longform_context_summary`.

- [ ] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py -q -k "summarize_longform_context or contracts"
```

Expected: fail because the descriptor does not exist.

- [ ] **Step 3: Register descriptor**

Add descriptor after `plan_recovery_tools`, with input params:

- `chapter_index`
- `query`
- `max_chars`
- `include_prompt_context`

Expected output includes `status`, `chapter_index`, `summary`, `sections`, `diagnostics`, `source_section_keys`.

- [ ] **Step 4: Run GREEN**

Run the same registry command. Expected: pass.

## Task 2: Read-Only Summary Adapter

- [ ] **Step 1: Write failing API test**

Add a test that seeds a longform project with setup, storyline, outline, generated chapters, and longform memories; then runs:

```json
{
  "goal": "查看长篇上下文",
  "tools": [
    {
      "tool_name": "summarize_longform_context",
      "params": {
        "chapter_index": 3,
        "query": "续写下一章",
        "max_chars": 1200
      }
    }
  ]
}
```

Assert:

- step `target_type == "longform_context_summary"`
- adapter mutability is `read`
- output contains project progress and section source keys
- output does not include full `prompt_context` unless requested
- output is bounded by `max_chars` with diagnostics if truncated

- [ ] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "summarize_longform_context"
```

Expected: fail because no adapter exists.

- [ ] **Step 3: Implement summary service**

Create `longform_context_summary.py` that:

- calls `build_longform_context_package()`;
- computes target chapter, generated chapter count, latest generated chapter, and word count;
- includes compact recent chapter memory and context sections;
- includes `source_section_keys` and diagnostics;
- returns `prompt_context_chars`;
- only includes `prompt_context` when `include_prompt_context` is true;
- caps textual fields using `max_chars`.

- [ ] **Step 4: Add executor adapter**

Add `_summarize_longform_context()` to `tool_executor.py` and register it in `_STATIC_TOOL_ADAPTERS` with category `longform_memory` and `mutability="read"`.

- [ ] **Step 5: Run GREEN**

Run the focused API test. Expected: pass.

## Task 3: Verification and Report

- [ ] **Step 1: Run T1 backend Agent verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

- [ ] **Step 2: Run static checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [ ] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase52-longform-context-summary.md` with:

- summary;
- reference assimilation;
- changed files;
- RED/GREEN/T1 evidence;
- next recommendation.

- [ ] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend docs
git commit -m "feat: add longform context summary tool"
git push origin main
```
