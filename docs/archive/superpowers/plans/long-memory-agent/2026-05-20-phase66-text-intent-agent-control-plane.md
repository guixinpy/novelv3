# Text Intent Agent Control Plane Phase66 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route ordinary free-form creative chat intent into the Agent control plane instead of requiring slash commands.

**Architecture:** Reuse the existing `IntentRouter` and `PendingAction` confirmation UI. Text inputs that clearly ask for setup/storyline/outline/chapter creation should create a pending preview action with the original text preserved as `command_args`; confirmation then uses the Phase65 `WritingAgentRun` control plane. Non-action chat stays a normal Hermes chat message.

**Tech Stack:** FastAPI backend, existing dialog API, `IntentRouter`, `PendingAction`, Phase65 `dialog_control_plane`, pytest.

---

## Reference Assimilation

- `openclaw`: local command shortcuts and natural language intents should both normalize into a control-plane intent before execution.
- `hermes-agent`: the agent loop should preserve original user intent as task input, not lose it during routing.
- `openhuman`: parent chat should receive compact action prompts/results while detailed execution stays in structured run records.

## File Structure

- Modify `backend/app/api/dialogs.py`
  - Let text input use `IntentRouter`.
  - Only preview actions create pending actions.
  - Preserve free-form text as `command_args`.
  - Ensure `project_id` from payload cannot be overwritten by candidate params.
  - Return diagnosis directly for `query_diagnosis`.
- Modify `backend/tests/test_dialogs.py`
  - Add red tests for free-form setup intent, confirm-to-Agent run, regular chat fallback, and diagnosis query.
- Add Phase66 report under `docs/superpowers/notes/long-memory-agent/`.

## Task 1: Free-Form Preview Action

- [x] Add failing test: text `创建主角设定，主角是植物学家` creates `preview_setup`.
- [x] Assert `pending_action.params.project_id` is the real project id.
- [x] Assert `pending_action.params.command_args` preserves the original user text.
- [x] Assert `dialog.state == "pending_action"`.
- [x] Run RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "text_intent_creates_pending_setup"
```

Expected before implementation: fails because text input falls through to free chat.

## Task 2: Confirmation Reuses Agent Control Plane

- [x] Add failing test: after a text-created `preview_setup`, confirming creates `WritingAgentRun`.
- [x] Patch `LocalTaskRunner.start` so the test does not launch a real background task.
- [x] Assert the created run is `entrypoint == "dialog_pending_action"`.
- [x] Assert the run tool is `generate_setup` and carries the free-form text as `command_args`.
- [x] Run focused test:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "text_intent_confirm_routes_to_agent_run"
```

Expected before implementation: fails because no pending action exists from text intent.

## Task 3: Preserve Non-Action Chat

- [x] Add regression test: text `随便聊聊` does not create a pending action.
- [x] Assert response `pending_action is None`.
- [x] Assert dialog does not enter `pending_action`.

## Task 4: Diagnosis Query Is Not A Pending Action

- [x] Add regression test: text `接下来做什么` returns a diagnosis response instead of a pending `query_diagnosis` action.
- [x] Assert `pending_action is None`.
- [x] Assert response mentions missing/completed project state.

## Task 5: Implementation And Verification

- [x] Update `dialogs.py` routing:

```python
if payload.input_type in {"text", "command"} and effective_text:
    candidate = router.resolve(effective_text, dialog.state, dialog.pending_action_id, diagnosis)
```

- [x] Add helper-level guard:

```python
if candidate.type.startswith("preview_"):
    params = {**candidate.params, "project_id": payload.project_id}
    params["command_args"] = effective_text
```

- [x] Handle `query_diagnosis` with direct chat response.
- [x] Run focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "text_intent"
```

- [x] Run T1 dialog + Agent control plane:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

- [x] Run static checks and secret scan:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

- [x] Write Phase66 report.
- [x] Commit and push to `main`.

## Boundaries

Do:

- make clear natural-language creative requests enter the same confirmation and Agent control plane as slash commands;
- preserve original text as generation feedback;
- keep non-action chat as chat;
- avoid auto-executing text intent without confirmation;
- keep `/clear` and `/compact` behavior unchanged.

Do not:

- add a broad LLM intent classifier in this phase;
- auto-confirm typed `好的` yet;
- migrate continuous writing endpoints yet;
- rewrite frontend chat UI;
- treat vague discussion as an action.
