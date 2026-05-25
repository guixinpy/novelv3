# Phase47 Report: Recovery Policy

## Phase Goal

Add deterministic recovery advice to Writing Agent blocked/failed step results, starting with `preflight_writing` blocker cases.

## Implemented

- Added `backend/app/services/writing_agent/recovery_policy.py`.
- Added `build_writing_agent_recovery(...)`.
- Added `agent_tool_result.recovery`.
- Added recovery policy version: `phase47.recovery_policy.v1`.
- Covered `preflight_writing` blockers:
  - `missing_setup` -> recommend `generate_setup`, request `command_args`;
  - `missing_outline_chapter` -> recommend `expand_outline_window`;
  - `missing_historical_outline_chapters` -> recommend `backfill_outline_gaps`;
  - `missing_previous_chapter` -> recommend generating the previous chapter;
  - `repeated_chapter_length_drift` -> recommend policy review.
- Kept recovery read-only. It does not automatically execute tools.

## Subagent Review

A read-only subagent confirmed the lowest-risk design:

- attach recovery advice at the existing envelope boundary;
- keep raw `preflight_writing` checks/issues unchanged;
- do not modify planner behavior yet;
- do not auto-run recovery tools in this phase.

The implementation follows that boundary.

## Why This Helps Agentization

The Agent can now consume structured recovery decisions instead of parsing error strings.

This is a necessary step toward:

- planner retry/recovery logic;
- task queue continuation after blocked steps;
- user-facing “next action” UI;
- long-running chapter generation loops that can pause, repair prerequisites, and resume safely.

## Validation

Validation level: T1.

Initial RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "preflight_blocks_when_target_outline_is_missing or preflight_blocks_when_generated_chapter_outline_gap_exists or missing_previous_chapter_recovery"
```

Result:

```text
3 failed; KeyError: 'recovery'
```

Additional RED after subagent review:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "missing_setup_recovery"
```

Result:

```text
1 failed; KeyError: 'policy_version'
```

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "preflight_blocks_when_target_outline_is_missing or preflight_blocks_when_generated_chapter_outline_gap_exists or missing_previous_chapter_recovery or missing_setup_recovery"
```

Result:

```text
4 passed, 114 deselected
```

T1 module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result:

```text
136 passed
```

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

```text
git diff --check: exit 0; warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF the next time Git touches it
secret scan: exit 1; no matches
```

## Current Limits

- Recovery advice is not automatically executed.
- Policies currently focus on `preflight_writing`.
- Successful steps receive `recovery.status == "none"` rather than omitting the field.
- Planner does not yet consume recovery decisions.

## Next Phase Recommendation

Phase48 should make planner/run creation able to consume recovery decisions in a controlled way. A safe first slice is a read-only `plan_recovery_tools` helper or tool that turns a blocked run detail into a proposed recovery tool chain without executing it.
