# Phase155 Recovery Agent Run Drawer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users open the Writing Agent run detail directly from a recovery-preview chat message.

**Architecture:** Add a narrow UI affordance on `plan_recovery_tools` action-result messages. The chat message emits the target run id, `HermesView` fetches `/projects/{id}/agent-runs/{run_id}`, and a lightweight modal renders the run status and step list.

**Tech Stack:** Vue 3, TypeScript, Vitest, existing FastAPI Writing Agent run detail endpoint.

---

## Scope

In scope:
- Render a "查看运行" action on recovery-preview chat result cards when an `agent_run_id` is available.
- Forward the run id through `ChatMessageList` to `HermesView`.
- Add `api.getAgentRun(projectId, runId)`.
- Add a minimal `AgentRunDrawer` modal showing run goal/status/id and steps.
- Wire Hermes to fetch and display the drawer.

Out of scope:
- Full Agent run management UI.
- Editing, cancelling, or replaying Agent runs.
- Route-level Agent run page.
- Changing backend payloads.

## Files

- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/chat/ChatMessage.vue`
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
- Modify: `frontend/src/components/chat/ChatMessageList.vue`
- Modify: `frontend/src/components/chat/ChatMessageList.test.ts`
- Create: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
- Create: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
- Modify: `frontend/src/views/HermesView.vue`
- Modify: `frontend/src/views/HermesView.test.ts`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase155-recovery-agent-run-drawer.md`

## Task 1: RED Chat Message Tests

- [x] **Step 1: Add failing `ChatMessage` test**

Add a test that mounts `ChatMessage` with:
- `action_result.type == "plan_recovery_tools"`
- `action_result.data.agent_run_id == "run-1"`
- `action_result_view.label == "恢复预览已生成"`

Assert:
- `[data-testid="open-agent-run"]` exists.
- clicking it emits `openAgentRun` with `"run-1"`.

- [x] **Step 2: Add failing `ChatMessageList` forwarding test**

Add a test that mounts `ChatMessageList` with a recovery-preview message and asserts child click emits `openAgentRun` with the run id.

- [x] **Step 3: Run RED**

Run:

```powershell
Set-Location frontend; npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/chat/ChatMessageList.test.ts
```

Expected: fails because no open-agent-run button/event exists.

## Task 2: Message Affordance

- [x] **Step 1: Implement `ChatMessage` run id extraction and event**

Modify `ChatMessage.vue`:
- add `openAgentRun: [runId: string]` to emits.
- compute `agentRunId` from `msg.meta.agent_run_id` first, then `msg.action_result.data.agent_run_id`.
- show the button only for `plan_recovery_tools` result messages with a non-empty run id.
- emit `openAgentRun(agentRunId)` on click.

- [x] **Step 2: Forward through `ChatMessageList`**

Modify `ChatMessageList.vue`:
- add `openAgentRun` emit.
- forward child event.

- [x] **Step 3: Run GREEN for chat components**

Run:

```powershell
Set-Location frontend; npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/chat/ChatMessageList.test.ts
```

Expected: tests pass.

## Task 3: Agent Run Drawer and Hermes Wiring

- [x] **Step 1: Add failing drawer test**

Create `AgentRunDrawer.test.ts`:
- mount open drawer with a run detail and two steps.
- assert goal/status/id and step tool/status text render.
- mount loading state and assert loading copy.
- mount error state and assert error copy.

- [x] **Step 2: Add failing Hermes wiring test**

Extend `HermesView.test.ts`:
- add `api.getAgentRun` mock.
- stub `ChatMessageList` with a button that emits `openAgentRun`.
- stub `AgentRunDrawer` to expose `run.id`.
- assert clicking the stub button calls `api.getAgentRun("project-1", "run-1")` and renders the drawer stub with `run-1`.

- [x] **Step 3: Run RED for drawer/Hermes**

Run:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Expected: fails because the drawer and API client wiring do not exist.

- [x] **Step 4: Implement drawer, API types/client, Hermes wiring**

Modify:
- `types.ts`: add `WritingAgentRunDetail` and `WritingAgentStep`.
- `client.ts`: add `getAgentRun(id, runId)`.
- `AgentRunDrawer.vue`: use `BaseModal`, show loading/error/empty/detail states.
- `HermesView.vue`: import drawer, maintain active run state, fetch via `api.getAgentRun`, render drawer.

- [x] **Step 5: Run GREEN for drawer/Hermes**

Run:

```powershell
Set-Location frontend; npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Expected: tests pass.

## Task 4: Regression, Report, Commit

- [x] **Step 1: Run targeted frontend regression**

Run:

```powershell
Set-Location frontend; npm run test:unit -- src/components/chat/ChatMessage.test.ts src/components/chat/ChatMessageList.test.ts src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Expected: selected tests pass.

- [x] **Step 2: Run T1 build/type check**

Run:

```powershell
Set-Location frontend; npm run build
```

Expected: build passes.

- [x] **Step 3: Run hygiene checks**

Run from repo root:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: diff check passes; secret scan returns no matches.

- [x] **Step 4: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-23-phase155-recovery-agent-run-drawer.md`.

- [x] **Step 5: Commit and push**

Run:

```powershell
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/components/chat/ChatMessage.vue frontend/src/components/chat/ChatMessage.test.ts frontend/src/components/chat/ChatMessageList.vue frontend/src/components/chat/ChatMessageList.test.ts frontend/src/components/writingAgent/AgentRunDrawer.vue frontend/src/components/writingAgent/AgentRunDrawer.test.ts frontend/src/views/HermesView.vue frontend/src/views/HermesView.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase155-recovery-agent-run-drawer.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase155-recovery-agent-run-drawer.md
git commit -m "feat: open agent run from recovery preview"
git push
```
