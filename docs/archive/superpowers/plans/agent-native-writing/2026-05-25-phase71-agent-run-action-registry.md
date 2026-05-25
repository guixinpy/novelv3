# Phase71 Agent Run Action Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the Agent run action registry from `agentRunProjection.ts` into a dedicated registry module so the projection entrypoint only handles runtime message projection.

**Architecture:** `agentRunActionRegistry.ts` imports the recovery, diagnostic, writing-tool, route opt-in, and longform projection modules, then exports the unified action type list and descriptor map. `agentRunProjection.ts` imports this registry, re-exports the existing public registry API, and keeps message/run-id/view projection helpers.

**Tech Stack:** Vue frontend, TypeScript, Vitest, Vite build.

---

### Task 1: Registry Boundary

**Files:**
- Create: `frontend/src/components/chat/agentRunActionRegistry.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase71-agent-run-action-registry.md`

- [ ] **Step 1: Write the failing test**

Add imports for:

```ts
AGENT_RUN_ACTION_DESCRIPTORS as REGISTRY_AGENT_RUN_ACTION_DESCRIPTORS
AGENT_RUN_ACTION_TYPES as REGISTRY_AGENT_RUN_ACTION_TYPES
```

from `./agentRunActionRegistry`, then add a test that verifies:

- the registry list begins with `RECOVERY_AGENT_RUN_ACTION_TYPES`;
- it contains the diagnostic, writing-tool, route opt-in, and longform module action lists;
- every registered action type has a descriptor with matching `type` and a `buildView` function.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: fail because `./agentRunActionRegistry` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `agentRunActionRegistry.ts` with:

- unified `AGENT_RUN_ACTION_TYPES`;
- `AgentRunActionType`;
- `AgentRunActionDescriptor`;
- unified `AGENT_RUN_ACTION_DESCRIPTORS`.

Update `agentRunProjection.ts` to import descriptor map and re-export `AGENT_RUN_ACTION_TYPES`, `AgentRunActionType`, and `AgentRunActionDescriptor` from the registry module.

- [ ] **Step 4: Run targeted frontend verification**

Run:

```powershell
npm run test:unit -- agentRunProjection
npm run test:unit -- ChatMessage
npm run build
git diff --check
```

Expected:
- `agentRunProjection` passes with the registry-boundary test.
- `ChatMessage` passes to cover action card rendering integration.
- `npm run build` succeeds.
- `git diff --check` has no new whitespace issue; the known CRLF warning in `backend/tests/test_writing_agent_runs.py` is unrelated.

- [ ] **Step 5: Write phase report**

Create `docs/superpowers/notes/agent-native-writing/2026-05-25-phase71-agent-run-action-registry.md` with scope, files changed, red/green evidence, verification evidence, and next suggested phase.
