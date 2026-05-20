# Phase56 Report: Continuation State

## Summary

Phase56 adds a lightweight `continuation_state` to Writing Agent run output.

The state is derived from the canonical `WritingAgentRun` and `WritingAgentStep` records. It does not add a new table or queue worker. This gives the Agent and UI a compact checkpoint for recovery, compaction handoff, and future batch orchestration.

Example fields now available under `run.output.continuation_state`:

- active task and planner mode;
- target chapter index;
- executed/planned step progress;
- last successful tool;
- blocked tool;
- next expected tool;
- recovery recommendation;
- failure reason;
- consumed outputs such as longform context, maintenance, preflight, generated chapter, review, and world-model proposal state.

## Reference Assimilation

The implementation adapts prior reference patterns:

- `openclaw`: canonical execution records should be the source of truth. novelv3 derives continuation state from run/step rows instead of UI state.
- `hermes-agent`: compact handoff state should include active task, completed actions, blocked reason, and remaining work. novelv3 exposes those through status, last tool, blocked tool, next expected tool, recovery, and consumed flags.
- `openhuman`: long-running plans need bounded state and explicit next action. novelv3 exposes `next_expected_tool` and avoids bringing in a full task board in this phase.

Not copied:

- OpenClaw transcript branching and gateway restart model.
- Hermes generic conversation compression stack.
- OpenHuman task board, memory tree, or background trigger runtime.

## Changes

- Updated `backend/app/services/writing_agent/run_service.py`.
  - `_run_output()` now includes `continuation_state`.
  - Added helpers for:
    - continuation status;
    - planner mode;
    - planned and executed step progress;
    - target chapter inference;
    - last successful step;
    - blocked/failed step;
    - latest recommended recovery;
    - failure state;
    - consumed output flags;
    - resume hint.
- Updated `backend/tests/test_writing_agent_runs.py`.
  - Blocked longform context run now asserts `continuation_state` points to `repair_longform_maintenance`.
  - Confirmed context recovery chain now asserts completed state after `generate_chapter`.
- Added plan:
  - `docs/superpowers/plans/long-memory-agent/2026-05-20-phase56-continuation-state.md`

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or longform_context_recovery_chain"
```

Observed before implementation:

- both tests failed with `KeyError: 'continuation_state'`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or longform_context_recovery_chain"
```

Result: `2 passed, 127 deselected`.

T1 verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

Result: `152 passed in 9.89s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

- `git diff --check` completed with only the existing CRLF warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Boundary

This phase exposes continuation state as a read model only. It does not yet:

- add a durable batch table;
- resume background jobs;
- manage retry budgets;
- persist separate JSONL transcripts;
- expose a dedicated UI panel.

The current source of truth remains Writing Agent run and step rows.

## Novel Progress

No new chapter was generated in this phase. The change supports future longform generation by making each Agent run self-describing and recoverable after blocks, failures, or context compaction.

## Next Recommendation

Phase57 should use `continuation_state` as input for a small longform batch planning tool. The next step should be a read-only tool that proposes a bounded chapter batch DAG, for example:

```text
summarize context -> generate chapter -> review quality -> review continuity -> analyze world model -> repair/continue
```

That would move novelv3 from per-run recovery toward task-queue-ready chapter batches while still avoiding a premature full task queue rewrite.
