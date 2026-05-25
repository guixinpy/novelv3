# Phase202 Pending Action Agent Safe Hint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a safe, user-facing Agent recommendation on pending action cards when a legacy dialog route can be upgraded through the Phase201 route opt-in contract path.

**Architecture:** Add a sanitized `safety_view` projection to `PendingActionOut`. The backend derives it from existing pending-action route metadata without computing or exposing approval hashes; the frontend renders only title/message/severity text in `ActionCard`.

**Tech Stack:** FastAPI/Pydantic backend, existing dialog message projection, Vue ActionCard, pytest, Vitest.

---

### Task 1: Backend Pending Action Projection

**Files:**
- Modify: `backend/app/schemas/dialog.py`
- Modify: `backend/app/services/actions/pending_action_projection.py`
- Modify: `backend/app/services/dialog/messages.py`
- Modify: `backend/app/api/dialogs.py`
- Test: `backend/tests/test_dialogs.py`

- [x] **Step 1: Write failing backend test**

Add a test to `backend/tests/test_dialogs.py`:

```python
def test_pending_action_exposes_route_opt_in_safety_view_without_contract_hash(client):
    project_id = client.post("/api/v1/projects", json={"name": "Agent Hint"}).json()["id"]

    response = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": project_id,
            "input_type": "command",
            "command_name": "setup",
            "command_args": "雾港悬疑",
        },
    )

    pending = response.json()["pending_action"]
    view = pending["safety_view"]
    recommendation = view["recommendations"][0]
    assert view["kind"] == "pending_action_safety"
    assert recommendation["kind"] == "route_upgrade_preview"
    assert recommendation["title"] == "可先生成路由升级审批契约"
    assert recommendation["auto_execute"] is False
    assert recommendation["guarded_apply"] is False
    assert "approval:" not in str(view)
    assert "approval_contract" not in str(view)
```

Add a second assertion through `GET /messages` so historical message projection matches immediate chat response.

- [x] **Step 2: Run RED**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "safety_view or get_messages_includes_current_pending_action" -q
```

Expected: fails because `PendingActionOut` has no `safety_view`.

- [x] **Step 3: Implement backend projection**

Add `safety_view: dict | None = None` to `PendingActionOut`.

In `pending_action_projection.py`, add:

```python
def pending_action_safety_view(action_type: str | None, params: dict | None) -> dict | None:
    if not isinstance(params, dict):
        return None
    agent_route = params.get("agent_route")
    if not isinstance(agent_route, dict):
        return None
    if params.get("use_agent_approval_chain") is False:
        return None
    if agent_route.get("use_agent_approval_chain") is True:
        return None
    if not str(agent_route.get("agent_tool_name") or "").strip():
        return None
    return {
        "kind": "pending_action_safety",
        "recommendations": [
            {
                "kind": "route_upgrade_preview",
                "title": "可先生成路由升级审批契约",
                "message": "这只生成审批准备信息，不会执行当前待确认操作。",
                "severity": "info",
                "auto_execute": False,
                "guarded_apply": False,
            }
        ],
    }
```

Use this helper in `DialogMessageService._pending_action_payload` and all `PendingActionOut(...)` construction paths in `backend/app/api/dialogs.py`.

- [x] **Step 4: Run GREEN**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "safety_view or get_messages_includes_current_pending_action" -q
```

Expected: selected tests pass.

### Task 2: Frontend ActionCard Rendering

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/components/chat/ActionCard.vue`
- Test: `frontend/src/components/chat/ActionCard.test.ts`

- [x] **Step 1: Write failing frontend test**

Add a test that mounts `ActionCard` with:

```ts
safety_view: {
  kind: 'pending_action_safety',
  recommendations: [{
    kind: 'route_upgrade_preview',
    title: '可先生成路由升级审批契约',
    message: '这只生成审批准备信息，不会执行当前待确认操作。',
    severity: 'info',
    auto_execute: false,
    guarded_apply: false,
  }],
}
```

Expected rendered text contains the title and message, but does not contain `approval:` or `preview_pending_action_route_approval_opt_in_apply_contract`.

- [x] **Step 2: Run RED**

Run:

```powershell
npm --prefix frontend run test:unit -- ActionCard
```

Expected: fails because `ActionCard` does not render `safety_view`.

- [x] **Step 3: Implement safe hint rendering**

Update frontend type definitions with optional `safety_view`.

In `ActionCard.vue`, add a small read-only info block above buttons:

- display `title`;
- display `summary`;
- ignore any unrecognized fields.

Do not add a button that triggers the internal route opt-in tool in this phase.

- [x] **Step 4: Run GREEN**

Run:

```powershell
npm --prefix frontend run test:unit -- ActionCard
```

Expected: selected tests pass.

### Task 3: Validation, Review, Commit

**Files:**
- Modify: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase202-pending-action-agent-safe-hint.md`

- [x] **Step 1: Run T1/T2 validation**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "safety_view or get_messages_includes_current_pending_action" -q
npm --prefix frontend run test:unit -- ActionCard
git diff --check
rg -n "<real DeepSeek key prefix>" .
```

Expected: tests pass; diff check exits 0; real DeepSeek key prefix has no matches.

- [x] **Step 2: Request code review**

Ask a review subagent to inspect:

- no approval hash/contract leaks through `safety_view`;
- no UI button bypasses guarded apply;
- immediate chat response and historical message projection are consistent.

- [ ] **Step 3: Update report and commit**

Update the Phase202 report with RED/GREEN evidence, implementation summary, validation, review, and next phase.

Commit:

```powershell
git add backend/app/schemas/dialog.py backend/app/services/actions/pending_action_projection.py backend/app/services/dialog/messages.py backend/app/api/dialogs.py backend/tests/test_dialogs.py frontend/src/api/types.ts frontend/src/components/chat/ActionCard.vue frontend/src/components/chat/ActionCard.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase202-pending-action-agent-safe-hint.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase202-pending-action-agent-safe-hint.md
git commit -m "feat: show pending action agent hints"
git push
```
