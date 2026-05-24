# Phase216 Profile Policy Audit Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Keep this phase as observability only; do not enable runtime delegation or change tool filtering behavior.

**Goal:** Surface Phase215 `agent_profile_policy_audit` in run details and compact dialog/detail views so Agent profile policy inconsistencies are visible during writing-agent operation.

**Architecture:** Extract the audit from the `describe_agent_tools` step output (`agent_profile_tool_projection.consistency_audit`) and expose it as `agent_profile_policy_audit` in run detail payloads. Reuse a small shared-style projection in backend action result view and frontend fallback/detail drawer: passed audits render compactly, non-passed audits show `需关注` with issue count.

**Tech Stack:** Python, pytest, TypeScript, Vitest, Vue.

---

## Reference Project Inputs

- OpenClaw: policy/audit findings are machine-readable and compact; Phase216 adopts compact status + issue count in run and dialog surfaces.
- Hermes Agent: runtime tool progress exposes concise toolset/delegation state; Phase216 surfaces audit state without exposing full child-agent internals.
- OpenHuman: AgentDefinition/tool visibility should be observable in agent harness; Phase216 makes profile definition/policy consistency visible from UI surfaces.

## Files

- Modify: `backend/app/services/writing_agent/run_service.py`
  - Extract `agent_profile_policy_audit` from `describe_agent_tools` step output.
- Modify: `backend/app/schemas/writing_agent.py`
  - Add `agent_profile_policy_audit` to `WritingAgentRunDetail`.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Assert auto-plan run detail exposes audit.
- Modify: `backend/app/services/actions/action_result_view.py`
  - Add compact detail item for `agent_profile_policy_audit`.
- Modify: `backend/tests/test_dialogs.py`
  - Assert action result view displays audit status/issue count.
- Modify: `frontend/src/api/types.ts`
  - Add `agent_profile_policy_audit` to run detail type.
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
  - Add compact audit detail item.
- Modify: `frontend/src/components/chat/agentRunProjection.test.ts`
  - Assert fallback views include audit status.
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - Render audit status and issue count.
- Modify: `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
  - Assert drawer renders audit.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase216-profile-policy-audit-visibility.md`

## Tasks

### Task 1: RED Tests

- [x] **Step 1: Run detail RED**

Extend `test_agent_run_detail_exposes_agent_profile_projection_for_auto_plan()`:

```python
audit = payload["agent_profile_policy_audit"]
assert audit["version"] == "phase215.agent_profile_policy_audit.v1"
assert audit["status"] == "passed"
assert audit["summary"]["issues"] == 0
assert audit["summary"]["delegate_edges"] == 4
assert detail_payload["agent_profile_policy_audit"] == audit
```

Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q
```

Expected: FAIL because run detail does not expose the audit yet.

- [x] **Step 2: Backend dialog RED**

Add a `test_get_messages_includes_agent_profile_policy_audit_detail_item()` with `action_result.data.agent_profile_policy_audit`:

```python
assert {"label": "策略审计", "value": "需关注：2 个问题"} in detail_items
```

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "profile_policy_audit" -q
```

Expected: FAIL because action result view ignores the audit.

- [x] **Step 3: Frontend projection RED**

Add a fallback projection test with `agent_profile_policy_audit.status = "needs_attention"` and `summary.issues = 2`.

Run:

```powershell
npm run test:unit -- agentRunProjection
```

Expected: FAIL because fallback projection ignores the audit.

- [x] **Step 4: Drawer RED**

Add `agent_profile_policy_audit` to an `AgentRunDrawer` run and assert `策略审计` plus `通过` for passed audit.

Run:

```powershell
npm run test:unit -- AgentRunDrawer
```

Expected: FAIL because drawer ignores the audit.

### Task 2: Backend Projection

- [x] In `run_service.detail_payload()`, include `agent_profile_policy_audit`.
- [x] Add `_agent_profile_policy_audit_from_steps(steps)` that finds the latest `describe_agent_tools` output with `agent_profile_tool_projection.consistency_audit`.
- [x] Add schema field.
- [x] Add `_agent_profile_policy_audit_detail_items(data)` or inline helper in `action_result_view.py`.
- [x] Re-run backend targeted tests.

### Task 3: Frontend Projection

- [x] Add `agent_profile_policy_audit?: Record<string, unknown> | null` to `WritingAgentRunDetail`.
- [x] Add audit detail item to `agentDiscoveryDetailItems()`.
- [x] Add drawer computed values and render summary fact.
- [x] Re-run frontend targeted tests.

### Task 4: Validation, Report, Commit

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py -k "profile_projection" -q
pytest backend/tests/test_dialogs.py -k "profile_policy_audit or agent_discovery_view" -q
npm run test:unit -- agentRunProjection
npm run test:unit -- AgentRunDrawer
python -m compileall backend/app/services/writing_agent backend/app/services/actions
npm run build
git diff --check
```

- [x] Run DeepSeek key prefix scan without embedding a key in files:

```powershell
$pat='sk-'+'f6aa'; rg -n $pat backend frontend docs --glob '!frontend/node_modules/**'
```

- [x] Write phase report with reference-project mapping and validation evidence.
- [x] Commit and push:

```text
feat: surface agent profile policy audit
```
