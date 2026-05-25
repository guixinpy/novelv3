# Phase55 Report: Context Recovery Chain

## Summary

Phase55 turns the Phase54 single repair recommendation into a confirmed recovery chain.

When a chapter run is blocked by stale longform memory/retrieval maintenance, recovery preview now plans:

```text
repair_longform_maintenance
  -> summarize_longform_context
  -> preflight_writing
  -> generate_chapter
```

Execution still requires `confirm_execute=true` and a matching `recovery_plan_hash`. The chain re-runs context diagnostics before preflight and generation, so if maintenance is still not ready the normal report-stop gate blocks before `generate_chapter`.

## Reference Assimilation

The implementation adapts three reference patterns:

- `openclaw`: recovery should be a continuation route from the current blocked run, not a request for the user to manually repeat the original task. novelv3 now carries a full recovery tool sequence in the plan.
- `hermes-agent`: after repair or compression, the agent should re-check state before continuing. novelv3 now inserts `summarize_longform_context` and `preflight_writing` before resuming generation.
- `openhuman`: multi-step execution should be bounded, stateful, and auditable. novelv3 keeps preview read-only and hashes the project, source run/step, reason, affected chapter, and full selected tool list before execution.

Not copied:

- OpenClaw gateway/session restart complexity.
- Hermes provider fallback and broad conversation retry stack.
- OpenHuman task board, memory tree, or desktop trigger architecture.

## Changes

- Updated `backend/app/services/writing_agent/recovery_policy.py`.
  - `summarize_longform_context` recovery now includes `affected_chapter_indexes`.
  - When the blocked chapter is known, the recovery recommendation includes continuation tools for context re-check, preflight, and generation.
- Updated `backend/app/services/writing_agent/recovery_planner.py`.
  - Recovery recommendations are converted into full tool sequences instead of one tool.
  - `plan_hash` now covers `project_id`, source run/step, source tool, reason code, affected chapters, and all tool requests.
  - Guardrails validate every selected tool is registered and currently visible.
  - `safe_auto_execute` is true only when every selected tool is in the safe recovery execution set; context recovery chains that include `generate_chapter` remain confirmation-only.
- Updated `backend/tests/test_writing_agent_runs.py`.
  - Added preview assertions for the context recovery chain.
  - Added confirmed execution coverage for repair -> context re-check -> preflight -> generation.
- Added plan:
  - `docs/superpowers/plans/long-memory-agent/2026-05-20-phase55-context-recovery-chain.md`

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or longform_context_recovery_chain"
```

Observed before implementation:

- preview returned only `repair_longform_maintenance`;
- confirmed recovery execution ran only the repair tool.

Implementation debugging:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or longform_context_recovery_chain or auto_plan_executes_recovery_after_hash_confirmation"
```

Intermediate failure:

- `NameError: name 'tool' is not defined` in `recovery_planner.py` after replacing the single-tool variable with `tools`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or longform_context_recovery_chain or auto_plan_executes_recovery_after_hash_confirmation"
```

Result: `3 passed, 126 deselected`.

T1 verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

Result: `152 passed in 9.80s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

- `git diff --check` completed with only the existing CRLF warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Boundary

Phase55 only applies the continuation-chain pattern to longform context maintenance blockers. It does not yet generalize multi-step recovery to world-model proposal blockers, knowledge-base gaps, review failures, or task queue failures.

Confirmed execution can resume generation, but it does not yet persist a dedicated `ExecutionContinuationState`. The current source of truth is still the Writing Agent run, step list, recovery plan hash, and tool outputs.

## Novel Progress

No new longform chapter was generated in this phase. The change improves the safety and autonomy of future chapter generation by letting the Agent repair a context blocker and continue through the standard generation gate after explicit confirmation.

## Next Recommendation

Phase56 should introduce a lightweight continuation state or batch state for long-running writing workflows. It should record:

- active task and target chapter;
- last successful tool;
- next expected tool;
- retry or recovery count;
- failure reason;
- whether generated text, review findings, longform memory, and world-model proposals have been consumed.

This would move novelv3 closer to the reference projects' durable Agent execution model without importing their general-purpose runtime complexity.
