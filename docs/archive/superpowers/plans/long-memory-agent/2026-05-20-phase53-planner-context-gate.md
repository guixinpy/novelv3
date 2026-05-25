# Phase53 Planner Context Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `plan_writing_agent_run` consume `summarize_longform_context` as a standard pre-generation step for continuing chapters.

**Architecture:** Keep the deterministic planner small: when intent is `continue_next_chapter`, insert a read-only longform context gate after tool projection and any required outline expansion, before `preflight_writing` and `generate_chapter`. This turns Phase52 from a standalone report into part of the Agent's normal tool chain without changing generation behavior or adding a broad new planner subsystem.

**Tech Stack:** FastAPI backend, SQLAlchemy-backed planner state, existing Writing Agent tool registry/executor, pytest.

---

## Reference Assimilation

- `openclaw`: context should be projected into runtime/tool planning before action, with provenance instead of hidden ad hoc prompt text. Its descriptor-first tool catalog supports the current `describe_agent_tools -> summarize_longform_context -> preflight -> generate` sequence.
- `hermes-agent`: generation should perform context preflight before the actual model/tool action. Its context compression and memory prefetch patterns map to a bounded, auditable Agent step rather than hidden prompt mutation.
- `openhuman`: planner recall should be read-only and conservative. Its memory loader pattern supports automatic small summaries and diagnostics, while details remain opt-in through tools.

novelv3 adaptation:

- The planner inserts `summarize_longform_context`; it does not inline the full prompt context.
- `generate_chapter` remains the writing tool; context summary is a read-only gate.
- If outline expansion is required, expansion happens before summary so the target chapter outline can be reflected.
- The tool chain stays deterministic and auditable through existing planner metadata.

## Files

- Modify: `backend/app/services/writing_agent/planner.py`
  - Insert `summarize_longform_context` into continue-next-chapter plans.
- Modify: `backend/tests/test_writing_agent_planner.py`
  - Update expected tool sequence and planner metadata.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Update auto-plan API expectations so actual runs execute the context gate before generation.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase53-planner-context-gate.md`
  - Record implementation, reference absorption, verification, and next phase.

## Task 1: Planner RED

- [ ] **Step 1: Write failing planner expectation**

Update `test_planner_builds_ready_next_chapter_tool_chain()` to expect:

```python
[
    "describe_agent_tools",
    "summarize_longform_context",
    "preflight_writing",
    "generate_chapter",
    "review_chapter_quality",
    "review_chapter_continuity",
    "analyze_chapter_world_model",
]
```

Update `test_planner_adds_outline_expansion_when_target_outline_is_missing()` so context summary appears after `expand_outline_window` and before `preflight_writing`.

- [ ] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py -q -k "ready_next_chapter or outline_expansion"
```

Expected: fail because planner has not inserted `summarize_longform_context`.

## Task 2: Planner GREEN

- [ ] **Step 1: Insert context gate**

In `_build_continue_chapter_plan()`, after outline dependency handling and before `preflight_writing`, append:

- tool: `summarize_longform_context`
- params: `{"chapter_index": chapter_index, "query": "续写第{chapter_index}章前汇总长篇上下文。"}`
- reason: "生成前读取长篇记忆、检索证据和上下文诊断。"
- `on_missing="record_issue"`
- `on_failure="record_issue"`
- expected output: "长篇上下文摘要。"

- [ ] **Step 2: Run planner GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py -q -k "ready_next_chapter or outline_expansion"
```

Expected: pass.

## Task 3: API Auto-Plan RED/GREEN

- [ ] **Step 1: Update API expectation**

In `test_agent_run_auto_plan_continues_next_chapter_with_metrics()`, assert the first four tools are:

```python
["describe_agent_tools", "summarize_longform_context", "preflight_writing", "generate_chapter"]
```

Also assert the context step target type is `longform_context_summary` and adapter mutability is `read`.

- [ ] **Step 2: Run focused API test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_continues_next_chapter"
```

Expected: pass after implementation.

## Task 4: Verification and Report

- [ ] **Step 1: Run T1 Agent verification**

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

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase53-planner-context-gate.md` with:

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
git commit -m "feat: route planner through longform context"
git push origin main
```
