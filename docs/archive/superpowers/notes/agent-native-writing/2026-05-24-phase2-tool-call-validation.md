# Phase 2 Report: Tool Call Validation

## Status

Completed.

## Reference Project Lessons

- `hermes-agent` validates tool calls before dispatch, so unknown tools and malformed arguments stop at the runtime boundary.
- `openclaw` treats tool safety as a policy layer around visible tools, not as scattered handler checks.
- For novelv3, the first useful adaptation is a descriptor-driven validation gate over existing Agent tool schemas.

## Current novelv3 Gap

`WritingAgentRunService` checked whether a tool was allowed, but did not validate params against the registered descriptor before execution. Known tools could receive malformed params and fail inside adapter code.

## Implementation Notes

- Added `backend/app/services/writing_agent/tool_request_validation.py`.
- Added descriptor-driven validation before tool execution in `WritingAgentRunService.execute_run`.
- Validation currently covers the high-value runtime boundary cases:
  - unknown tool descriptor;
  - missing required param;
  - top-level JSON type mismatch;
  - numeric minimum violation.
- Validation failure becomes a normal failed Agent run rather than a backend 500.
- Failed validation output is structured under `step.output.validation` and still flows into `continuation_state.agent_loop.exit_reason = "tool_failed"`.
- This follows `hermes-agent` for the runtime boundary, while keeping novelv3's existing tool descriptor registry as the source of truth.

## Verification

- RED: `cd backend; pytest tests/test_writing_agent_runs.py -k "tool_input_validation" -q`
  - Result before implementation: `2 failed`
  - Evidence:
    - missing `plan` on `preview_agent_plan_approval_contract` incorrectly returned run success;
    - invalid `chapter_index="abc"` reached `_preflight_writing` and caused HTTP 500.
- GREEN: `cd backend; pytest tests/test_writing_agent_runs.py -k "tool_input_validation" -q`
  - Result: `2 passed, 179 deselected`
- Regression: `cd backend; pytest tests/test_writing_agent_runs.py -k "tool_input_validation or agent_loop or recovery" -q`
  - Result: `17 passed, 164 deselected`

## Next Recommendation

After top-level validation is stable, add loop-risk diagnostics for repeated identical tool calls and schema validation coverage in `inspect_agent_health_projection`.
