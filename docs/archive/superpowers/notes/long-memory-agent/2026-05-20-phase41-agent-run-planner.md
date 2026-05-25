# Phase41 Report: Agent Run Planner

## Phase Goal

Add the first deterministic Writing Agent planner so a high-level writing intent can become an explainable tool-chain plan.

This phase advances the goal from "tools are registered" to "Agent can select a bounded tool sequence from intent and project state".

## Implemented

- Added `backend/app/services/writing_agent/planner.py`.
- Added `build_writing_agent_run_plan(...)` with:
  - deterministic intent classification;
  - next-chapter inference;
  - dependency-aware tool selection;
  - selected/rejected tool trace;
  - missing dependency and risk flag reporting;
  - structured `steps` and executable `tools`.
- Added `tools_from_plan(...)` to convert a planner result into `WritingAgentToolRequest` objects.
- Registered `plan_writing_agent_run` in `tool_registry.py`.
- Added `plan_writing_agent_run` execution branch in `run_service.py`.
- Added explicit `input.auto_plan=true` support for empty tool lists.
- Updated `create_agent_run` API flow to:
  - build an auto plan only when explicitly requested;
  - store planner output in run input;
  - execute the planner-derived tool list.
- Added tests for:
  - ready next-chapter planning;
  - missing outline fallback via `expand_outline_window`;
  - missing previous chapter blocking;
  - setup-project intent;
  - planner tool API execution;
  - explicit auto-plan execution.

## Reference Patterns Applied

- `openclaw`: deterministic parse first, compact plan structure, rejected tools and missing dependency diagnostics.
- `hermes-agent`: tool registry as the source of available tools, bounded execution rather than open-ended tool loops.
- `openhuman`: step/task style state, explicit failure strategy fields, trace-oriented planner output.

## Behavior Boundary

- Existing explicit tool runs are unchanged.
- Auto planning is only enabled with `input.auto_plan=true`.
- The planner is deterministic and bounded; it does not call an LLM.
- The planner does not write world facts directly.
- Post-generation review/world-model tools are included as follow-up steps so the system moves toward a full chapter pipeline.

## Validation

Validation level: T1/T2 boundary.

Reason:

- The change touches backend Agent API flow and Writing Agent service behavior.
- No database schema or frontend change.
- Full Writing Agent related tests were run.

Commands run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py -q
```

Result:

```text
4 passed
```

Then:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_run_can_plan_writing_tool_chain tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_high_level_next_chapter_goal -q
```

Result:

```text
2 passed
```

Then:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q
```

Result:

```text
121 passed
```

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

```text
git diff --check: passed
secret scan: no matches
```

## Current Limitations

- Planner is still deterministic rules, not a model/subagent planner.
- Planner does not yet persist per-step planner trace as first-class DB rows beyond run input/step output.
- Planner can include post-generation tools, but deeper recovery strategies are still encoded as output fields rather than a reusable retry engine.
- Knowledge base and拆书 tools are not yet available, so planner cannot include them.

## Next Phase Recommendation

Phase42 should move from "plan and execute a bounded chain" to "traceable tool loop":

- Add a normalized Agent tool result envelope.
- Persist planner trace and per-step selection reason in a more queryable structure.
- Add recovery behavior for blocked preflight:
  - missing setup -> generate setup;
  - missing storyline -> generate storyline;
  - missing outline -> generate/expand outline;
  - pending world proposals -> review/resolve before writing when severe.
- Start splitting `_execute_tool` into registry-backed executor objects.
