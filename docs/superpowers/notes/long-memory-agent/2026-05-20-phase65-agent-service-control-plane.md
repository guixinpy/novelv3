# Phase65 Report: Agent Service Control Plane

## Summary

Phase65 started migrating novelv3 from module-specific control paths toward an Agent Service control plane.

The concrete vertical slice is the confirmed Hermes creation flow. Existing `/setup`, `/storyline`, `/outline`, `/chapter` command and button flows still use the same user-facing confirmation card, but confirmed creative actions now create a `WritingAgentRun` and execute the mapped Agent tool through a `writing_agent_run` background task. The old slash-command module is now treated as a compatibility intent shortcut, not as the real execution control plane.

This does not complete the whole-project Agent migration. It establishes the first user-facing path where dialog confirmation, background execution, Agent run, Agent step, and terminal chat message are linked by durable IDs.

## Reference Assimilation

Adopted:

- `openclaw` local-command boundary: slash commands remain lightweight intent shortcuts, while execution moves into typed tools.
- `hermes-agent` durable run state: confirmed work now has an Agent run record with explicit entrypoint and step output.
- `openhuman` compact parent result: chat receives a concise terminal message with `agent_run_id`; full internal steps stay in Agent run records.

Not adopted:

- generic command/plugin runtime;
- full LLM-directed tool loop for every chat message;
- frontend Agent run panel;
- migration of all direct generation APIs;
- migration of continuous writing start/resume.

## Changes

- Added `backend/app/services/writing_agent/dialog_control_plane.py`.
- Confirmed creative dialog actions now route through:
  - `PendingAction`;
  - `WritingAgentRun(entrypoint="dialog_pending_action")`;
  - `BackgroundTask(task_type="writing_agent_run")`;
  - `LocalTaskRunner`;
  - `WritingAgentRunService.execute_run()`;
  - compact terminal dialog message.
- Extended `WritingAgentRunService.create_run()` with optional linkage fields:
  - `dialog_id`;
  - `request_message_id`;
  - `response_message_id`;
  - `background_task_id`.
- Updated `backend/app/api/dialogs.py` so confirmed supported creative actions return:
  - `task_id`;
  - `agent_run_id`;
  - `control_plane.version`.
- Extended `ActionResultService.record_completion()` with opt-in failure data so Agent-backed blocked/failed terminal messages can keep `agent_run_id` provenance without changing legacy callers.
- Updated dialog tests from legacy `_execute_action_background` assertions to Agent control-plane assertions.
- Preserved legacy behavior for:
  - `/clear`;
  - `/compact`;
  - pending action creation;
  - cancellation;
  - revise;
  - unsupported actions.

## Control Plane Contract

Version:

- `phase65.agent_control_plane.v1`

Supported dialog action mapping:

- `generate_setup -> generate_setup`
- `generate_storyline -> generate_storyline`
- `generate_outline -> generate_outline`
- `generate_chapter -> generate_chapter`

Background task:

- `task_type: "writing_agent_run"`
- payload includes:
  - `agent_run_id`;
  - `action_type`;
  - `dialog_id`;
  - serialized Agent tools;
  - `control_plane.version`.

Dialog terminal result:

- includes `agent_run_id`;
- includes `background_task_id`;
- preserves `blocked` status for Agent-gated blockers;
- excludes raw step transcript.

## Verification

RED test 1:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "agent_control_plane_routes_confirmed_setup"
```

Result before implementation: failed because no `WritingAgentRun` existed.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "agent_control_plane"
```

Result: `2 passed, 49 deselected in 0.23s`.

Blocked terminal result check:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "agent_control_plane_background_work_records_blocked or background_completion_restores_dialog_state_to_chatting"
```

Result: `3 passed, 49 deselected in 0.34s`.

Agent API smoke:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "create_agent_run_records_steps_and_returns_detail"
```

Result: `1 passed, 153 deselected in 0.24s`.

Dialog focused compatibility:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "chat_command_registry_helpers or chapter_command_leading_index or agent_control_plane"
```

Result: `4 passed, 47 deselected in 0.47s`.

Dialog suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q
```

Result: `52 passed in 21.31s`.

Agent run suite:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Result: `154 passed in 16.73s`.

T1 related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

Result: `249 passed in 46.74s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. This was a control-plane migration phase: it makes future user-facing generation requests pass through Agent run records before spending more model calls on long-running dogfood generation.

## Discovered Issues

- Confirmed Hermes creation actions were still bypassing `WritingAgentRun`.
- Existing tests encoded the old assumption that confirmation must call `_execute_action_background` directly.
- Chat terminal messages had no durable `agent_run_id`, making it hard to inspect which Agent steps produced a result.
- The backend Agent API existed, but Hermes confirmed actions were not yet using it as the execution control plane.

## Fixed Issues

- Confirmed creative dialog actions now create linked Agent runs.
- Background execution now uses `writing_agent_run` tasks for those actions.
- Terminal dialog messages now include Agent run provenance.
- Agent-backed blocked dialog results can preserve `status: "blocked"` instead of being flattened into legacy failure-only status.
- `WritingAgentRunService.create_run()` can persist dialog/background linkage.
- Regression tests now assert Agent control-plane behavior instead of legacy background action coupling.

## Remaining Boundary

The project is not fully Agent Service based yet. Remaining control-plane migrations include:

- ordinary free-form chat intent routing into Agent planning where appropriate;
- direct setup/storyline/outline/chapter generation APIs;
- continuous writing `/writing/start` and `/writing/resume`;
- Athena evolution and ontology generation compatibility endpoints;
- frontend API/client visibility for Agent run inspection;
- Trace event unification across Agent run, model trace, background task, and dialog history.

The next phase should choose one of those entrypoints and repeat the same pattern: preserve compatibility, route durable execution through Agent Service, and keep user-facing output compact.
