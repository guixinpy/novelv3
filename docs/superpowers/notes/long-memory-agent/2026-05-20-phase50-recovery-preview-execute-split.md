# Phase50 Report: Recovery Preview Execute Split

## Summary

Phase50 splits recovery into two paths:

- preview: `auto_plan + recovery_run_id` runs `plan_recovery_tools` only;
- execute: `auto_plan + recovery_run_id + execute_recovery + confirm_execute + recovery_plan_hash` converts the verified recovery plan into executable tools.

This reverses the risky Phase49 default where a recovery run id immediately became a write operation. The Agent now exposes the recovery plan first, then requires explicit confirmation plus a matching plan hash before executing recovery tools.

## Reference Assimilation

Reference review was done with three read-only explorers:

- `openclaw`: plans should be first-class artifacts; preview/apply paths should be separate; execution should bind to the planned context.
- `hermes-agent`: planning output and tool execution should stay separate; guardrails should reject stale or unsafe execution rather than silently continuing.
- `openhuman`: preview should be read-only; execution should revalidate current state and require explicit confirmation.

What was adapted into novelv3:

- `plan_hash` binds the recovery execution to a specific source run, source step, reason code, and planned tool list.
- default recovery auto-plan is preview-only and runs `plan_recovery_tools`.
- confirmed execution requires `confirm_execute: true` and a matching `recovery_plan_hash`.
- mismatched hashes fall back to preview instead of executing.

What was not copied:

- no generic host-command approval system;
- no new heavy recovery-plan table yet;
- no dynamic tool insertion inside `execute_run()`;
- no universal retry loop.

The domain-specific interpretation is: recovery repairs longform writing blockers such as missing outlines before the Agent resumes writing.

## Changes

- Added deterministic preview hashes in `backend/app/services/writing_agent/recovery_planner.py`.
- Enriched recovery preview output with:
  - `preview_version`;
  - `preview_only`;
  - `plan_hash`;
  - `source_step_id`;
  - `reason_code`;
  - `can_execute`;
  - `requires_confirmation`;
  - `execution_policy`.
- Updated `WritingAgentRunService.build_auto_plan_tools()`:
  - default recovery mode returns a `plan_recovery_tools` preview request;
  - confirmed recovery execution re-computes the preview and verifies hash;
  - hash mismatch or missing confirmation returns preview mode.
- Added tests for preview default, confirmed execution, and hash mismatch rejection.

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "recovery_tool_plan or recovery_after_hash or recovery_execute_hash"
```

Result before implementation: `3 failed, 119 deselected`; failures showed missing `mode` and missing `plan_hash`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "recovery_tool_plan or recovery_after_hash or recovery_execute_hash"
```

Result: `3 passed, 119 deselected in 0.41s`.

T1 module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result: `141 passed in 10.30s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result: diff check passed with only the existing CRLF warning; secret scan returned no matches.

## Next Recommendation

Phase51 should add a small recovery guardrail layer before execution:

- validate planned recovery tools against current registry visibility;
- reject tools that require user input;
- reject repeated failed recovery attempts for the same source step and plan hash.

This continues the same reference-aligned direction: visible plan, explicit execution, durable trace, no blind retry.
