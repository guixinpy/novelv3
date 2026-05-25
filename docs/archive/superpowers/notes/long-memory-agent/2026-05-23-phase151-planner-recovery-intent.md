# Phase151 Planner Recovery Intent Report

## Objective

Allow the Writing Agent to infer a recovery preview from high-level user language such as "恢复上一轮阻塞", instead of requiring the user to manually select `plan_recovery_tools` or provide a `recovery_run_id`.

## Implementation

- Added planner intent class `recover_blocked_run`.
- Added explicit recovery wording detection for goals containing:
  - `恢复`
  - `上一轮阻塞`
  - `上次阻塞`
  - `上一轮失败`
  - `上次失败`
- Added latest recoverable run lookup:
  - project-scoped
  - status in `blocked` or `failed`
  - contains a step output with `agent_tool_result.recovery.status == "recommended"`
- Added recovery planning step:
  - `plan_recovery_tools`
  - params include the discovered blocked/failed `run_id`
  - read-only preview, no recovery execution.
- Verified API `auto_plan` now routes "恢复上一轮阻塞" into `describe_agent_tools -> plan_recovery_tools`.

## TDD Evidence

- Planner RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_planner.py::test_planner_routes_recovery_intent_to_latest_recoverable_run -q`
  - Failed because intent was `inspect_tools`.
- Planner GREEN:
  - Same command.
  - `1 passed in 0.12s`.
- API integration:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_recovers_latest_blocked_run_from_goal -q`
  - `1 passed in 0.87s`.

## Verification

- Targeted regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_planner.py::test_planner_routes_recovery_intent_to_latest_recoverable_run backend\tests\test_writing_agent_planner.py::test_planner_builds_ready_next_chapter_tool_chain backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_recovers_latest_blocked_run_from_goal backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_previews_recovery_tool_plan_by_default -q`
  - `4 passed in 0.41s`.
- Hygiene:
  - `git diff --check` passed.
  - API key scan found no matches in non-archived backend/frontend/docs paths.

## Novel Progress

No new novel chapter was generated. This phase improves long-running creation reliability by letting the Agent understand recovery intent and route to a safe preview flow automatically.

## Known Limits

- This phase only handles explicit recovery/block/failure wording. Low-detail "继续吧" still routes to normal chapter continuation unless the caller provides `recovery_run_id`.
- Latest recoverable run lookup uses recent blocked/failed runs and recommended recovery envelopes; it does not yet inspect job projection recovery options.

## Next Recommendation

Add a lightweight dialog/control-plane bridge so low-detail "继续吧" can prefer recovery preview when the latest project run is blocked with a recommended recovery, while still continuing the next chapter when no recovery is pending.
