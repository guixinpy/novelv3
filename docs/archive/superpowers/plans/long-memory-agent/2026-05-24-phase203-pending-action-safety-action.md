# Phase203 Pending Action Safety Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users trigger the safe route-upgrade preparation from a pending action card without confirming the pending action or executing guarded apply.

**Architecture:** Extend the existing `safety_view` projection with a sanitized abstract action, not an internal tool call. The frontend renders a "生成审批契约" button and maps that abstract action to a read-only Agent run using `preview_pending_action_route_approval_opt_in_apply_contract`.

**Tech Stack:** FastAPI/Pydantic backend projection, Vue ActionCard/ChatMessage/ChatMessageList, Pinia chat store, pytest, Vitest.

---

### Task 1: Backend Safety Action Projection

**Files:**
- Modify: `backend/app/services/actions/pending_action_projection.py`
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/services/dialog/messages.py`
- Test: `backend/tests/test_dialogs.py`

- [x] **Step 1: Write failing backend tests**

Add assertions to `test_pending_action_exposes_route_opt_in_safety_view_without_contract_hash`:

```python
action = recommendation["action"]
assert action == {
    "kind": "prepare_route_upgrade_contract",
    "label": "生成审批契约",
    "pending_action_id": pending["id"],
    "auto_execute": False,
    "guarded_apply": False,
}
assert "preview_pending_action_route_approval_opt_in_apply_contract" not in str(safety_view)
```

Update `test_pending_action_safety_view_omits_non_upgradeable_routes` so it calls:

```python
pending_action_safety_view(action_type, params, pending_action_id="pending-1")
```

Add one pure helper test:

```python
def test_pending_action_safety_view_omits_action_without_pending_action_id():
    from app.services.actions.pending_action_projection import pending_action_safety_view

    view = pending_action_safety_view(
        "preview_setup",
        {"agent_route": {"agent_tool_name": "generate_setup"}},
        pending_action_id="",
    )

    assert view is not None
    recommendation = view["recommendations"][0]
    assert "action" not in recommendation
```

- [x] **Step 2: Run RED**

```powershell
pytest backend/tests/test_dialogs.py -k "safety_view" -q
```

Expected: fails because `pending_action_safety_view` does not accept `pending_action_id` and does not output an abstract action.

- [x] **Step 3: Implement backend projection**

Change the helper signature:

```python
def pending_action_safety_view(
    action_type: str | None,
    params: dict | None,
    *,
    pending_action_id: str | None = None,
) -> dict | None:
```

Build the existing recommendation, then attach:

```python
action_id = str(pending_action_id or "").strip()
if action_id:
    recommendation["action"] = {
        "kind": "prepare_route_upgrade_contract",
        "label": "生成审批契约",
        "pending_action_id": action_id,
        "auto_execute": False,
        "guarded_apply": False,
    }
```

Update `_pending_action_out()` and `DialogMessageService._pending_action_payload()` to pass `pending.id`.

- [x] **Step 4: Run GREEN**

```powershell
pytest backend/tests/test_dialogs.py -k "safety_view" -q
```

Expected: safety view tests pass.

### Task 2: Frontend Safety Action Button

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/components/chat/ActionCard.vue`
- Modify: `frontend/src/components/chat/ActionCard.test.ts`
- Modify: `frontend/src/components/chat/ChatMessage.vue`
- Modify: `frontend/src/components/chat/ChatMessageList.vue`
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
- Modify: `frontend/src/components/chat/ChatMessageList.test.ts`

- [x] **Step 1: Write failing component tests**

In `ActionCard.test.ts`, add a safety action to the existing safety view fixture and click the new button:

```ts
await wrapper.get('[data-testid="pending-action-safety-prepare"]').trigger('click')
expect(wrapper.emitted('safetyAction')?.[0]?.[0]).toEqual({
  kind: 'prepare_route_upgrade_contract',
  label: '生成审批契约',
  pending_action_id: 'action-1',
  auto_execute: false,
  guarded_apply: false,
})
```

Assert the rendered text still does not contain the internal tool name.

In `ChatMessage.test.ts`, assert `safetyAction` is re-emitted from the child card.

In `ChatMessageList.test.ts`, assert `safetyAction` is forwarded to the parent list.

- [x] **Step 2: Run RED**

```powershell
npm --prefix frontend run test:unit -- ActionCard ChatMessage ChatMessageList
```

Expected: fails because no button/event exists.

- [x] **Step 3: Implement component event flow**

Add frontend type:

```ts
export interface PendingActionSafetyAction {
  kind: string
  label: string
  pending_action_id: string
  auto_execute?: boolean
  guarded_apply?: boolean
}
```

In `ActionCard.vue`, sanitize recommendation actions and render a button only when:

- `kind === "prepare_route_upgrade_contract"`;
- `pending_action_id === props.action.id`;
- `auto_execute !== true`;
- `guarded_apply !== true`.

Emit `safetyAction` with the sanitized action. Forward the event through `ChatMessage.vue` and `ChatMessageList.vue`.

- [x] **Step 4: Run GREEN**

```powershell
npm --prefix frontend run test:unit -- ActionCard ChatMessage ChatMessageList
```

Expected: component tests pass.

### Task 3: Store and Hermes Integration

**Files:**
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/stores/chat.workspace.test.ts`
- Modify: `frontend/src/views/HermesView.vue`
- Test: `frontend/src/stores/chat.workspace.test.ts`

- [x] **Step 1: Write failing store test**

Add a test that sets `pendingAction.value` with the safety action and calls `preparePendingActionSafetyAction(action)`.

Expected assertions:

```ts
expect(api.createAgentRun).toHaveBeenCalledWith(projectId, {
  goal: '生成待确认操作的路由升级审批契约',
  entrypoint: 'pending_action_safety_action',
  tools: [{
    tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
    params: { pending_action_id: 'action-1' },
  }],
  input: {
    safety_action: { kind: 'prepare_route_upgrade_contract' },
    pending_action_id: 'action-1',
  },
})
expect(store.pendingAction?.id).toBe('action-1')
expect(store.messages.at(-1)?.action_result?.type).toBe('preview_pending_action_route_approval_opt_in_apply_contract')
expect(JSON.stringify(store.messages.at(-1))).not.toContain('approval:secret')
```

- [x] **Step 2: Run RED**

```powershell
npm --prefix frontend run test:unit -- chat.workspace
```

Expected: fails because the store method does not exist.

- [x] **Step 3: Implement store and Hermes hook**

Add `preparePendingActionSafetyAction(action)` to the chat store:

- verify `pendingAction.value.id === action.pending_action_id`;
- reject actions with `auto_execute === true` or `guarded_apply === true`;
- call `api.createAgentRun()` with the read-only preview contract tool;
- append a local system message with sanitized action result data and `action_result_view`;
- keep `pendingAction` unchanged.

In `HermesView.vue`, handle `@safety-action` and call the store method. Apply a user panel reason like `你请求生成审批契约`.

- [x] **Step 4: Run GREEN**

```powershell
npm --prefix frontend run test:unit -- chat.workspace HermesView
```

Expected: store/Hermes tests pass.

### Task 4: Validation, Review, Report, Commit

**Files:**
- Modify: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase203-pending-action-safety-action.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-24-phase203-pending-action-safety-action.md`

- [x] **Step 1: Run T2 validation**

```powershell
pytest backend/tests/test_dialogs.py -k "safety_view or pending_action" -q
npm --prefix frontend run test:unit -- ActionCard ChatMessage ChatMessageList chat.workspace HermesView agentRunProjection
npm --prefix frontend run build
python -m compileall backend/app/services/actions backend/app/services/dialog backend/app/api/dialogs.py
git diff --check
rg -n "<real DeepSeek key prefix>" .
```

Expected: selected tests/build pass; diff check exits 0; key prefix scan has no matches.

- [x] **Step 2: Request review**

Ask a review subagent to verify:

- the new button cannot execute guarded apply;
- no approval hash/contract/internal tool call is rendered in the pending card;
- the store keeps the original pending action active after generating the contract preview;
- the generated Agent run is read-only.

- [ ] **Step 3: Update report and commit**

Update the report with RED/GREEN/T2 evidence, review findings, novel progress, and next phase.

Commit:

```powershell
git add backend/app/services/actions/pending_action_projection.py backend/app/api/dialogs.py backend/app/services/dialog/messages.py backend/tests/test_dialogs.py frontend/src/api/types.ts frontend/src/components/chat/ActionCard.vue frontend/src/components/chat/ActionCard.test.ts frontend/src/components/chat/ChatMessage.vue frontend/src/components/chat/ChatMessage.test.ts frontend/src/components/chat/ChatMessageList.vue frontend/src/components/chat/ChatMessageList.test.ts frontend/src/stores/chat.ts frontend/src/stores/chat.workspace.test.ts frontend/src/views/HermesView.vue docs/superpowers/plans/long-memory-agent/2026-05-24-phase203-pending-action-safety-action.md docs/superpowers/notes/long-memory-agent/2026-05-24-phase203-pending-action-safety-action.md
git commit -m "feat: trigger pending action safety preparation"
git push
```
