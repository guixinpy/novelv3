# Phase51 Report: Recovery Guardrails

## Summary

Phase51 adds execution guardrails to recovery preview. A recovery plan can now be blocked before execution even when its hash matches, if the current project state no longer supports the recovery tool, the recovery needs user input, or the same plan already failed.

This continues the Agent direction from Phase50: recovery is not blind retry. It is a visible, auditable writing workflow repair path.

## Reference Assimilation

The implementation adapts three reference patterns:

- `openclaw`: execution follows a durable planned context and rejects stale follow-up.
- `hermes-agent`: guardrails return structured rejection reasons instead of silent retries.
- `openhuman`: current state is revalidated before execution, and repeated failed work is not automatically repeated.

novelv3-specific translation:

- recovery preview uses the current Writing Agent tool projection to check whether the recovery tool is visible now;
- recovery requiring missing user input is preview-only;
- failed recovery executions with the same `plan_hash` block future blind execution.

## Changes

- Added recovery guardrails in `backend/app/services/writing_agent/recovery_planner.py`.
- Guardrails now check:
  - `requires_user_input`;
  - `tool_not_allowed`;
  - `tool_not_visible`;
  - `repeat_failed_recovery`.
- Preview output now includes `guardrails`.
- `execution_policy.status` now reflects the exact guardrail blocker.
- `WritingAgentRunService.build_auto_plan_tools()` preserves that guardrail status when falling back to preview.
- Added API tests for user-input blockers, state drift, and repeated failed plans.

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "recovery_preview_blocks_requires_user_input or hidden_tool_after_state_drift or repeated_failed_plan"
```

Result before implementation: `3 failed, 122 deselected`; failures showed missing `guardrails`, direct execution after state drift, and repeated failed plans still executable.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "recovery_preview_blocks_requires_user_input or hidden_tool_after_state_drift or repeated_failed_plan"
```

Result: `3 passed, 122 deselected in 0.37s`.

T1 module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result: `144 passed in 10.00s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result: diff check passed with only the existing CRLF warning; secret scan returned no matches.

## Next Recommendation

Phase52 should start turning more modules into explicit Agent tools beyond recovery:

- expose a read-only longform context summary tool;
- expose a knowledge/memory recall placeholder tool contract;
- route generated chapter planning through those tools before writing.

That would move the goal from recovery orchestration into broader long-memory Agent autonomy.
