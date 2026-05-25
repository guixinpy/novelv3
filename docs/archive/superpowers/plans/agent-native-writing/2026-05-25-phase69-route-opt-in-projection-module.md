# Phase69 Route Opt-In Projection Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move route-upgrade opt-in chat projection descriptors out of the aggregate `agentRunProjection.ts` file into a dedicated module while preserving the public aggregation API.

**Architecture:** `agentRunProjection.ts` remains the single registry used by chat UI code. The new `routeOptInAgentRunProjection.ts` owns the three route opt-in action descriptors, labels, detail item builders, and local value helpers. This keeps future route approval UI changes isolated from recovery, diagnostics, writing-tool, and longform projections.

**Tech Stack:** Vue frontend, TypeScript, Vitest, Vite build.

---

### Task 1: Route Opt-In Projection Boundary

**Files:**
- Create: `frontend/src/components/chat/routeOptInAgentRunProjection.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase69-route-opt-in-projection-module.md`

- [ ] **Step 1: Write the failing test**

Add imports for `ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES` and `ROUTE_OPT_IN_AGENT_RUN_ACTION_DESCRIPTORS` from `./routeOptInAgentRunProjection`, then add a test that expects the module to expose exactly:

```ts
[
  'prepare_route_upgrade_contract',
  'preview_pending_action_route_approval_opt_in_apply_contract',
  'apply_pending_action_route_approval_opt_in',
]
```

Each descriptor must have matching `type` and a `buildView` function.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: fail because `./routeOptInAgentRunProjection` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `routeOptInAgentRunProjection.ts` and move the existing route opt-in projection code from `agentRunProjection.ts`:

- `buildRouteOptInContractActionResultView`
- `buildRouteOptInApplyActionResultView`
- `routeOptInContractLabel`
- `routeOptInApplyLabel`
- `routeOptInContractDetailItems`
- `routeOptInApplyDetailItems`
- `routeOptInContractStatusLabel`
- `routeOptInApplyStatusLabel`
- local `recordValue`, `stringValue`, and `numberValue`

Then import/spread the exported route opt-in action types and descriptors from `agentRunProjection.ts`.

- [ ] **Step 4: Run targeted frontend verification**

Run:

```powershell
npm run test:unit -- agentRunProjection
npm run test:unit -- ChatMessage
npm run build
git diff --check
```

Expected:
- `agentRunProjection` passes with the new module-boundary test.
- `ChatMessage` passes to cover action card rendering integration.
- `npm run build` succeeds so the SPA bundle in `backend/static/` reflects the frontend changes.
- `git diff --check` reports no new whitespace issues; the known CRLF warning in `backend/tests/test_writing_agent_runs.py` is unrelated to this phase.

- [ ] **Step 5: Write phase report**

Create `docs/superpowers/notes/agent-native-writing/2026-05-25-phase69-route-opt-in-projection-module.md` with:

- Scope.
- Files changed.
- Verification evidence.
- Remaining risk and next suggested phase.
