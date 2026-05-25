# Phase26 Backend Command Catalog Report

## Goal

Make the backend Agent command catalog the authoritative source for the Hermes slash-command UI.

## What Changed

- Added backend command catalog projection:
  - `GET /api/v1/dialog/chat-commands`
  - Version: `phase26.agent_chat_command_catalog.v1`
  - Public commands: `/continue`, `/status`, `/clear`, `/compact`
  - Hidden legacy aliases: `/setup`, `/storyline`, `/outline`, `/chapter`
- `ChatCommandSpec` now carries catalog metadata:
  - `example`
  - `supports_args`
  - `public`
  - `legacy`
  - optional `agent_intent_text`
- Frontend command parser/filter now accepts a backend-provided command catalog.
- `HermesView` loads the backend command catalog on initialization and passes normalized commands into `ChatInput`.
- `ChatInput` uses the provided command catalog for both menu candidates and slash-command parsing.
- Static frontend command registry remains as a fallback when the backend catalog request fails.

## RED Evidence

- `pytest backend/tests/test_dialogs.py -k "chat_command_catalog_endpoint" -q`
  - Failed because `/api/v1/dialog/chat-commands` did not return JSON and fell through to frontend HTML.
- From `frontend/`: `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts src/views/HermesView.test.ts`
  - Failed because `normalizeChatCommandDefinitions` did not exist.
  - Failed because `HermesView` did not call `api.getChatCommandCatalog`.

## GREEN Evidence

- `pytest backend/tests/test_dialogs.py -k "chat_command_catalog_endpoint or chat_command_registry_helpers or command_with_args_enters_preview_pending_action_and_message" -q`
  - `5 passed`
- From `frontend/`: `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts src/views/HermesView.test.ts src/stores/chat.workspace.test.ts`
  - `49 passed`
- From `frontend/`: `.\node_modules\.bin\vue-tsc.cmd --noEmit`
  - Passed with no output.
- `pytest backend/tests/test_dialogs.py -q`
  - `102 passed`
- `git diff --check`
  - Passed; only existing CRLF warning for `backend/tests/test_writing_agent_runs.py`.

## Remaining Risk

- The command catalog is now backend-owned, but it is still a dialog-level catalog. A later phase should connect it to the broader Agent capability registry so future commands such as `/memory`, `/review`, `/repair`, or `/focus` are exposed only when backed by real Agent tools.
