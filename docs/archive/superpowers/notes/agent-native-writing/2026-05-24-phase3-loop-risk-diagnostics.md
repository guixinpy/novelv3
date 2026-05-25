# Phase 3 Report: Loop Risk Diagnostics

## Status

Completed.

## Reference Project Lessons

- `openclaw` detects repeated tool calls and global loop patterns to keep autonomous Agents from spinning.
- novelv3 does not yet run a fully dynamic LLM tool loop, so the first useful adaptation is a read-only risk projection on existing persisted run steps.

## Current novelv3 Gap

`continuation_state.agent_loop` exposes the tool sequence, but does not identify repeated no-progress patterns. Future autonomous tool selection needs a contract that can warn or stop when repeated calls emerge.

## Implementation Notes

- Added read-only `loop_risk` under `continuation_state.agent_loop`.
- The detector uses a stable signature from tool name and normalized params.
- Current detector is intentionally scoped to adjacent repeated identical tool calls:
  - `clear`: max adjacent repeat count below 3;
  - `warning`: 3-4 repeats;
  - `critical`: 5+ repeats.
- Execution behavior is unchanged. Risk is reported but does not yet stop a run.
- This adapts `openclaw` loop detection into novelv3's current static-plan runtime without prematurely building a full dynamic Agent loop.

## Verification

- RED: `cd backend; pytest tests/test_writing_agent_runs.py -k "loop_risk" -q`
  - Result before implementation: `1 failed`
  - Evidence: `continuation_state.agent_loop.loop_risk` was missing.
- GREEN: `cd backend; pytest tests/test_writing_agent_runs.py -k "loop_risk" -q`
  - Result: `1 passed, 181 deselected`
- Regression: `cd backend; pytest tests/test_writing_agent_runs.py -k "loop_risk or agent_loop or tool_input_validation or recovery" -q`
  - Result: `18 passed, 164 deselected`

## Next Recommendation

After read-only loop risk is visible, later phases can convert critical risks into a runtime stop condition when dynamic Agent tool loops are introduced.
