# Phase66 Report: Text Intent Agent Control Plane

## Summary

Phase66 extends the Phase65 Agent Service migration from slash-command compatibility paths to ordinary free-form creative text.

The important contract change is that clear creative requests such as `创建主角设定` or `请开始写正文，从第1章开始生成` no longer fall through to normal Hermes chat. They now normalize through `IntentRouter`, create a `PendingAction`, wait for user confirmation, and then reuse the Phase65 `WritingAgentRun` control plane.

This is still not the whole-project Agent Service migration. It is the next vertical slice: text intent -> pending confirmation -> Agent run. The slash-command layer is now only one shortcut into the same path, not the center of the architecture.

## Reference Assimilation

Adopted:

- `openclaw`: natural-language and command shortcuts should normalize into the same control-plane intent.
- `hermes-agent`: preserve original user text as task input so the Agent run keeps user intent, not just a reduced action label.
- `openhuman`: keep chat-facing output compact while durable execution details live in structured run records.

Not adopted:

- broad LLM intent classification;
- auto-confirming text such as `好的`;
- migrating direct generation APIs;
- migrating continuous writing;
- frontend Agent run inspection.

## Changes

- Updated `backend/app/api/dialogs.py`.
- Text and command fallback input now both pass through `IntentRouter` when `effective_text` exists.
- Clear `preview_*` candidates create `PendingAction` records from text input.
- Original free-form text is preserved as `pending_action.params.command_args`.
- Confirming a text-created pending action reuses the Phase65 `WritingAgentRun` control plane.
- `query_diagnosis` is returned as a direct diagnosis response instead of becoming a pending action.
- Button and routed candidate params now preserve the real request `project_id` instead of allowing incoming params to override it.
- Running-state creative text intents return the existing running guard instead of creating another pending action.
- Updated old regression tests that encoded the pre-Agent behavior where text creative intent was handled as ordinary model chat.

## Behavior Contract

Text that should become Agent-controlled pending actions:

- `创建主角设定，主角是植物学家` -> `preview_setup`
- `创建主角设定` -> `preview_setup`
- `请开始写正文，从第1章开始生成。` -> `preview_chapter`

Text that should not become pending actions:

- `随便聊聊` -> normal chat fallback
- `接下来做什么` -> direct diagnosis response

Confirmation path:

- `PendingAction(preview_setup)` created from text
- `/api/v1/dialog/resolve-action` confirm
- `WritingAgentRun(entrypoint="dialog_pending_action")`
- `generate_setup` tool request carries the original free-form text as `command_args`

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "text_intent"
```

Result before implementation: `4 failed`, because text input still fell through to free chat and did not create `PendingAction`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "text_intent or chat_text_that_matches_action_intent or chat_text_start_writing"
```

Result: `6 passed, 50 deselected in 2.50s`.

T1 dialog + Agent control plane regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

Result: `253 passed in 43.16s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. This phase was intentionally architectural: it moved ordinary creative text intent into the Agent control plane before spending additional model calls on long-running dogfood generation.

## Discovered Issues

- Text input explicitly skipped `IntentRouter`, so ordinary user requests could not become Agent-controlled work.
- Two regression tests locked the old assumption that creative text should be handled by ordinary model chat.
- `query_diagnosis` could have been treated as a pending action if text routing were enabled without a direct response branch.
- Candidate/button params could overwrite the real request `project_id`.

## Fixed Issues

- Clear creative text intent now creates pending actions.
- Text-created pending actions confirm into durable Agent runs.
- Original text intent is preserved in `command_args`.
- Diagnosis query stays lightweight and non-mutating.
- Regular chat remains non-action chat.
- `project_id` is now controlled by the request path, not by candidate/button params.

## Remaining Boundary

The whole project is still not yet fully Agent Service based. Remaining migration targets:

- direct setup/storyline/outline/chapter generation APIs;
- continuous writing start/resume;
- Athena/world-model generation and review endpoints;
- knowledge-base ingestion and book-disassembly workflows;
- frontend Agent run visibility;
- unified Trace linking across dialog, background task, Agent run, model calls, and artifacts;
- converting the old slash-command module into only one intent shortcut among many.

Next phase should migrate one non-dialog generation entrypoint into the same Agent Service contract so the architecture continues moving from module APIs toward a tool-orchestrating writing Agent.
