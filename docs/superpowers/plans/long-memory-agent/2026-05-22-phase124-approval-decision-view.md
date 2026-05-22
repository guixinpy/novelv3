# Phase124 Approval Decision View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface approval decision metadata as a concise Chinese audit summary in dialog action result views.

**Architecture:** Phase123 stores `approval_decision` inside `action_result.data`; Phase124 projects that backend data through `action_result_view` and lets `ChatMessage` render optional detail rows. The UI must not expose raw approval hashes, only human-readable audit state.

**Tech Stack:** FastAPI backend projection, Vue 3 chat component, pytest, Vitest, Vite build.

---

## Scope

This phase serves the long-memory Writing Agent goal by making tool approval evidence visible in the conversation surface. It does not introduce a new Trace page or change action execution.

## Files

- Modify: `backend/app/services/actions/action_result_view.py`
  - Add optional `detail_items` for `approval_decision`.
  - Localize decision values.
  - Do not include raw `approval_contract_hash`.
- Modify: `backend/tests/test_dialogs.py`
  - Extend Phase123 approval confirm test to verify `action_result_view.detail_items`.
- Modify: `frontend/src/api/types.ts`
  - Add optional `detail_items` field to `ActionResultView`.
- Modify: `frontend/src/components/chat/ChatMessage.vue`
  - Render optional backend-projected detail rows under the action result label.
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`
  - Add a test that detail rows render and raw approval hashes remain hidden.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase124-approval-decision-view.md`
  - Record changes and validation.

## Validation Level

T2 subset:

- Backend/frontend contract changes are involved.
- No data model or task execution semantics change.

Commands:

- Backend targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q`
- Frontend targeted RED/GREEN:
  - `npm run test:unit -- ChatMessage.test.ts`
- Backend dialog regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py -q`
- Build:
  - `npm run build`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Backend Projection TDD

**Files:**
- Modify: `backend/tests/test_dialogs.py`

- [ ] **Step 1: Extend approval decision test**

In `test_chapter_approval_followup_resolve_action_records_decision_metadata`, assert:

```python
view = response.json()["action_result_view"]
assert view["detail_items"] == [
    {"label": "用户决策", "value": "已确认"},
    {"label": "审批模式", "value": "单次确认"},
    {"label": "审批契约", "value": "已绑定"},
]
assert pending.params["approval_contract_hash"] not in str(view)
```

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py::test_chapter_approval_followup_resolve_action_records_decision_metadata -q
```

Expected: FAIL because `detail_items` is missing.

## Task 2: Frontend Rendering TDD

**Files:**
- Modify: `frontend/src/components/chat/ChatMessage.test.ts`

- [ ] **Step 1: Add failing UI test**

Add:

```ts
it('renders backend-projected approval decision details without raw hashes', () => {
  const wrapper = mount(ChatMessage, {
    props: {
      msg: {
        role: 'system',
        message_type: 'plain',
        content: '操作已确认，正在生成中...',
        action_result: {
          type: 'generate_chapter',
          status: 'generating',
          data: {
            approval_decision: {
              approval_contract_hash: 'approval:secret-hash',
            },
          },
        },
        action_result_view: {
          type: 'generate_chapter',
          status: 'generating',
          label: '正文生成中...',
          variant: 'neutral',
          detail_items: [
            { label: '用户决策', value: '已确认' },
            { label: '审批契约', value: '已绑定' },
          ],
        },
      },
      isLatest: false,
      loading: false,
    },
  })

  expect(wrapper.text()).toContain('用户决策')
  expect(wrapper.text()).toContain('已确认')
  expect(wrapper.text()).toContain('审批契约')
  expect(wrapper.text()).toContain('已绑定')
  expect(wrapper.text()).not.toContain('approval:secret-hash')
})
```

- [ ] **Step 2: Run RED**

Run:

```powershell
npm run test:unit -- ChatMessage.test.ts
```

Expected: FAIL because detail rows are not rendered.

## Task 3: Implement Backend and Frontend

**Files:**
- Modify: `backend/app/services/actions/action_result_view.py`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/components/chat/ChatMessage.vue`

- [ ] **Step 1: Add backend detail projection**

In `action_result_view`, add `detail_items` only when `action_result.data.approval_decision` is present. Values:

- `confirm` -> `已确认`
- `cancel` -> `已取消`
- `revise` -> `要求修改`
- fallback -> original decision text

Do not include `approval_contract_hash`; use `审批契约: 已绑定` when a hash exists.

- [ ] **Step 2: Add TypeScript type**

Add:

```ts
detail_items?: Array<{ label: string; value: string }>
```

- [ ] **Step 3: Render detail rows**

Render rows under `.chat-msg__result` when `action_result_view.detail_items` is a non-empty array.

## Task 4: Verify, Document, Commit

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase124-approval-decision-view.md`

- [ ] Run targeted backend and frontend tests.
- [ ] Run backend dialog regression.
- [ ] Run frontend build.
- [ ] Run hygiene checks.
- [ ] Write report.
- [ ] Commit:

```powershell
git add backend/app/services/actions/action_result_view.py backend/tests/test_dialogs.py frontend/src/api/types.ts frontend/src/components/chat/ChatMessage.vue frontend/src/components/chat/ChatMessage.test.ts docs/superpowers/plans/long-memory-agent/2026-05-22-phase124-approval-decision-view.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase124-approval-decision-view.md
git commit -m "feat: show approval decision audit details"
git push origin main
```
