# Phase73 Route Opt-In Projection Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move route opt-in projection detail tests out of the aggregate `agentRunProjection.test.ts` file into a dedicated module test.

**Architecture:** `agentRunProjection.test.ts` keeps aggregate registry/runtime checks. `routeOptInAgentRunProjection.test.ts` covers route opt-in descriptors, contract preview card, and apply result card directly through the route opt-in module API.

**Tech Stack:** Vue frontend, TypeScript, Vitest, Vite build.

---

### Task 1: Route Opt-In Projection Test Boundary

**Files:**
- Create: `frontend/src/components/chat/routeOptInAgentRunProjection.test.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase73-route-opt-in-projection-tests.md`

- [ ] **Step 1: Write the failing structure test**

In `agentRunProjection.test.ts`, extend the structure test so the aggregate test source must not contain route opt-in detail specs:

- `builds route opt-in contract preview fallback views without leaking approval hashes`
- `builds route opt-in apply fallback views without leaking approval hashes`

Expected initial state: the test fails because those detail specs still live in the aggregate test file.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: fail because `agentRunProjection.test.ts` still contains route opt-in detail specs.

- [ ] **Step 3: Move route opt-in detail tests**

Create `routeOptInAgentRunProjection.test.ts` and move these behaviors there:

- route opt-in module descriptors.
- route opt-in contract preview card.
- route opt-in apply result card.

Update tests to call `ROUTE_OPT_IN_AGENT_RUN_ACTION_DESCRIPTORS[type].buildView(...)` directly.

- [ ] **Step 4: Run targeted frontend verification**

Run:

```powershell
npm run test:unit -- agentRunProjection routeOptInAgentRunProjection
npm run test:unit -- ChatMessage
npm run build
git diff --check
```

Expected:
- aggregate and route opt-in tests pass.
- `ChatMessage` passes to cover action card rendering integration.
- `npm run build` succeeds.
- `git diff --check` has no new whitespace issue; the known CRLF warning in `backend/tests/test_writing_agent_runs.py` is unrelated.

- [ ] **Step 5: Write phase report**

Create `docs/superpowers/notes/agent-native-writing/2026-05-25-phase73-route-opt-in-projection-tests.md` with scope, files changed, red/green evidence, verification evidence, and next suggested phase.
