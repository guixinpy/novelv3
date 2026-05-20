# Phase48 Report: Recovery Tool Planner

## Summary

Phase48 adds a read-only `plan_recovery_tools` Writing Agent tool. It converts a blocked or failed prior run's structured recovery advice into a proposed tool request chain. The tool does not execute recovery actions.

This moves recovery one step closer to Agent orchestration:

```text
blocked run -> recovery policy -> plan_recovery_tools -> proposed tools
```

## Changes

- Added `backend/app/services/writing_agent/recovery_planner.py`.
- Registered `plan_recovery_tools` as an internal, non-blocking report tool with `target_type == "agent_tool_plan"`.
- Added a static read-only executor adapter for `plan_recovery_tools`.
- Added registry and API coverage for missing-outline recovery.

## Behavior

When a prior run contains a blocked or failed step with `agent_tool_result.recovery.status == "recommended"`, the planner returns:

- the source run and source step;
- the recovery payload from the previous step;
- a proposed next tool request;
- trace data showing selected or rejected tools.

For a missing chapter outline blocker, the planned recovery tool is:

```json
{
  "tool_name": "expand_outline_window",
  "params": {
    "start_chapter": 3,
    "end_chapter": 3
  }
}
```

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q -k "plan_recovery_tools"
```

Result before implementation: failed because `plan_recovery_tools` was unsupported.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q -k "plan_recovery_tools"
```

Result: `2 passed, 121 deselected in 0.19s`.

T1 module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result: `138 passed in 10.43s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result: diff check passed with only the existing CRLF warning; secret scan returned no matches.

## Next Recommendation

Phase49 should consume recovery plans in the auto-planning path or task-queue path. The first safe step is still read-only planning: when a run is blocked, the Agent can append `plan_recovery_tools` to its next plan and show the proposed recovery chain before execution. Automatic execution should remain gated by explicit policy.
