# Phase 1 Report: Runtime Loop Contract

## Status

Completed.

## Reference Project Lessons

- `hermes-agent` treats each conversation as a loop with an iteration budget and explicit stop conditions. novelv3 currently has persisted steps, but no first-class loop diagnostics.
- `openclaw` highlights loop detection and tool-call history as safety primitives. novelv3 should first expose the ordered tool-call sequence in a stable projection before adding detectors.
- `openhuman` shows that bounded context and recall diagnostics must be inspectable. The same principle applies to writing-agent run state: users and future Agent code need to see why a run stopped.

## Current novelv3 Gap

Current writing-agent runs expose step counts and continuation state, but the run does not explicitly say:

- what kind of Agent loop executed;
- how much iteration budget was planned or consumed;
- why the loop exited;
- whether user action is required;
- what next action the Agent expects;
- what exact tool sequence was attempted.

This keeps the system closer to a scripted executor than an Agent runtime.

## Implementation Notes

- Added `AGENT_LOOP_CONTRACT_VERSION = "phase219.agent_loop_contract.v1"`.
- Added `continuation_state.agent_loop` to writing-agent run output.
- The projection is read-only and derived from persisted `WritingAgentRun` / `WritingAgentStep` state.
- The current loop is labeled `sequential_tool_plan` because runtime execution is still static-plan based. This is intentional: later phases can replace the executor while keeping the output contract stable.
- The loop contract exposes:
  - budget: planned max iterations, used iterations, remaining iterations;
  - exit reason: `completed`, `blocked`, `tool_failed`, `cancelled`, `running`, `pending`;
  - whether user action is required;
  - next action: none, continue, recover, request input, resolve blocker, inspect failure;
  - tool-call sequence with step index, tool name, status, tool call id, target type and chapter index.
- Extended recovery state projection to preserve `action` and `requires_user_input`, so the loop can distinguish automatic recovery from user-input recovery.

## Verification

- `cd backend; pytest tests/test_writing_agent_runs.py -k "agent_loop" -q`
  - Result: `3 passed, 176 deselected`
- `cd backend; pytest tests/test_writing_agent_runs.py -k "agent_loop or recovery or agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q`
  - Result: `16 passed, 163 deselected`

## Next Recommendation

After this projection is stable, the next phase should convert planner output from a one-shot static plan into a bounded Agent loop envelope with tool-call validation and loop-risk diagnostics.
