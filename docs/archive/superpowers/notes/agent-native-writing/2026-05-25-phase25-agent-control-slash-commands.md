# Phase25 Agent Control Slash Commands Report

## Goal

Refactor slash commands away from manual module shortcuts and toward an Agent control surface.

## What Changed

- Public slash menu now exposes:
  - `/continue`: ask the writing Agent to continue from current project state.
  - `/status`: ask the writing Agent for current project status.
  - `/clear`: clear the dialog session.
  - `/compact`: compact dialog history.
- Legacy `/setup`, `/storyline`, `/outline`, and `/chapter` are hidden from autocomplete.
- Legacy commands remain parseable only as migration aliases:
  - They are converted into natural-language Agent intents.
  - They route through `text_intent`, not `slash_command`.
  - Pending action params include `legacy_command` and `agent_intent_text` for traceability.
  - Tool `command_args` preserve the user's original argument text.
- Slash route projection no longer advertises legacy module commands as direct Agent tool routes.
- IntentRouter now accepts exact `继续`, aligning `/continue` with the API low-detail continue detector.

## RED Evidence

- `pytest backend/tests/test_dialogs.py -k "chat_command_registry_helpers or continue_command_routes_through_low_detail_agent_continue or status_command_routes_through_agent_diagnosis or legacy_chapter_command_routes_as_agent_intent" -q`
  - Failed first on missing command contract helpers.
- `.\frontend\node_modules\.bin\vitest.cmd run frontend/src/components/workspace/chatCommands.test.ts`
  - Failed because `/continue` and hidden legacy command behavior did not exist.
- Broader backend checks then exposed stale assumptions that `/chapter` did not require outline readiness and that route source remained `slash_command`.

## GREEN Evidence

- `pytest backend/tests/test_dialogs.py -q`
  - `101 passed`
- `pytest backend/tests/test_writing_agent_tool_executor.py -q`
  - `155 passed`
- From `frontend/`: `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts src/stores/chat.workspace.test.ts`
  - `38 passed`
- From `frontend/`: `.\node_modules\.bin\vue-tsc.cmd --noEmit`
  - Passed with no output.
- `git diff --check`
  - Passed; only existing CRLF warning for `backend/tests/test_writing_agent_runs.py`.

## Notes

- This phase intentionally does not add `/review`, `/memory`, `/repair`, or `/focus` yet. Those should be added only after each has a concrete Agent-backed route, not as fake chat shortcuts.
- A future phase should expose the public command catalog from backend to frontend, so the UI does not maintain a separate static registry.
