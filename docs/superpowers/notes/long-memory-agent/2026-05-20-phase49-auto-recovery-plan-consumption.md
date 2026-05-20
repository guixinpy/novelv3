# Phase49 Report: Auto Recovery Plan Consumption

## Summary

Phase49 lets `input.auto_plan` consume a prior blocked or failed run's recovery plan through an explicit `recovery_run_id`.

This is a small Agent-orchestration step: Phase48 could produce a recovery tool plan, while Phase49 lets the run-level auto-planner turn that recovery plan into actual executable tool requests.

## Changes

- Added a recovery branch to `WritingAgentRunService.build_auto_plan_tools()`.
- The branch only triggers when:
  - `payload.tools` is empty;
  - `input.auto_plan is True`;
  - `input.recovery_run_id` is present.
- The branch calls `build_recovery_tool_plan()` directly and converts returned `tools` into `WritingAgentToolRequest` instances.
- Added API coverage proving a blocked preflight run can be recovered into an executable `expand_outline_window` step.

## Behavior

Request shape:

```json
{
  "goal": "恢复上一轮阻塞",
  "input": {
    "auto_plan": true,
    "recovery_run_id": "<blocked-run-id>"
  }
}
```

For a missing chapter outline blocker, the new run stores the recovery planner output in `input.planner`, stores the executable recovery tool in `input.tools`, and executes:

```json
[
  {
    "tool_name": "expand_outline_window",
    "params": {
      "start_chapter": 3,
      "end_chapter": 3
    }
  }
]
```

This does not change `execute_run()` into a dynamic tool appender. The run still executes the tool list that was fixed before execution starts.

## Reference Alignment

This phase follows the Agent-engineering direction from the reference projects without copying them as dependencies:

- from `openclaw`: keep tool planning explicit and inspectable before execution;
- from `hermes-agent`: preserve a clear boundary between planning output and tool execution;
- from `openhuman`: treat recovery context as memory-bearing state that a later run can consume.

The novelv3 adaptation is domain-specific: recovery is not a generic retry loop. It is a writing workflow transition from a blocked longform run to the exact writing tool needed to repair the blocker, such as outline expansion before chapter generation.

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_consumes_recovery"
```

Result before implementation: failed with `KeyError: 'source_run_id'`, proving `recovery_run_id` was ignored and ordinary auto-plan was used.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_consumes_recovery"
```

Result: `1 passed, 119 deselected in 0.18s`.

T1 module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result: `139 passed in 9.11s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result: diff check passed with only the existing CRLF warning; secret scan returned no matches.

## Next Recommendation

Phase50 should add a reference-assimilation checkpoint before implementation, then add a safer preview/execution split for recovery planning. The Agent can first surface `plan_recovery_tools` output to the user or queue layer, then run a second `auto_plan + recovery_run_id` only when policy says the recovery action is safe to execute.
