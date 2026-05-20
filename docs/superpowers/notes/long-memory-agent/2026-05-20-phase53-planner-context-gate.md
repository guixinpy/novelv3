# Phase53 Report: Planner Context Gate

## Summary

Phase53 routes `plan_writing_agent_run` through the Phase52 longform context summary tool before chapter generation.

For `continue_next_chapter`, the deterministic planner now emits:

```text
describe_agent_tools
  -> optional expand_outline_window
  -> summarize_longform_context
  -> preflight_writing
  -> generate_chapter
  -> post-generation review/world-model tools
```

This makes longform memory and retrieval context a normal Agent planning step instead of a standalone report the user or operator must remember to call.

## Reference Assimilation

The implementation adapts three reference patterns:

- `openclaw`: descriptor-first tools and runtime context projection before action. novelv3 keeps this as an auditable tool step instead of hidden runtime messages.
- `hermes-agent`: generation preflight should include bounded context and memory prefetch. novelv3 maps that to `summarize_longform_context` before `generate_chapter`.
- `openhuman`: planner recall should be read-only, conservative, and source-aware. novelv3 keeps the summary non-blocking and does not auto-inject full prompt context.

Not copied:

- OpenClaw hook/custom-message infrastructure.
- Hermes generic chat compaction and broad toolset system.
- OpenHuman external memory daemon or Memory Tree backend.

## Changes

- Updated `backend/app/services/writing_agent/planner.py`.
  - `continue_next_chapter` now inserts `summarize_longform_context` after outline expansion and before `preflight_writing`.
  - Planner version is now `phase53.context_gate.v1`.
- Updated `backend/tests/test_writing_agent_planner.py`.
  - Ready and outline-expansion plans now assert the context gate order.
  - Planner metadata now expects the Phase53 version.
- Updated `backend/tests/test_writing_agent_runs.py`.
  - Auto-plan run now asserts the context summary step executes before generation.
  - It verifies `target_type == "longform_context_summary"` and adapter mutability is `read`.
- Added `docs/superpowers/plans/long-memory-agent/2026-05-20-phase53-planner-context-gate.md`.

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py -q -k "ready_next_chapter or outline_expansion"
```

Result before implementation: `2 failed, 2 deselected`; planner still went directly from tool description or outline expansion to `preflight_writing`.

Planner version RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py -q -k "ready_next_chapter"
```

Result before version update: `1 failed, 3 deselected`; planner metadata still reported `phase41.deterministic.v1`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py -q -k "ready_next_chapter or outline_expansion"
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_executes_high_level_next_chapter_goal"
```

Result:

- planner: `2 passed, 2 deselected`.
- API auto-plan: `1 passed, 125 deselected`.

T1 Agent verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result: `146 passed in 9.38s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

- `git diff --check` passed with only the existing CRLF warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Boundary

Phase53 only makes context summary part of the normal plan. It does not yet dynamically re-plan based on summary diagnostics.

## Next Recommendation

Phase54 should make the planner or run service consume the context summary result. The next practical step is a deterministic decision gate:

- if longform memory is stale, recommend or insert repair;
- if world-model proposals block generation, route to proposal review/resolution;
- if context is healthy, continue to generation.

That would move the Agent from fixed pre-generation recall toward diagnostics-driven orchestration.
