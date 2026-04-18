# Full App UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved full-app redesign: heavy parchment app shell, chat-first project workspace, structured backend UI hints, and unified list/detail/settings experiences.

**Architecture:** FastAPI remains the source of truth for domain data, but now returns minimal structured UI hints so the frontend no longer guesses intent from prose. Vue/Pinia is split into `chat`, `workspace`, and `project` responsibilities; a new global shell and workspace components reuse the existing tabs data components instead of rewriting every domain panel.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, pytest, Vue 3, Pinia, TypeScript, Vite, Tailwind CSS, Vitest, agent-browser

---

## File Structure

```
novelv3/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dialogs.py                  # Chat + resolve-action responses gain ui_hint/refresh_targets
│   │   │   └── background_tasks_api.py     # Background task polling returns structured hint data
│   │   ├── core/
│   │   │   └── ui_hints.py                 # Central action->panel and action->refresh mapping
│   │   └── schemas/
│   │       ├── dialog.py                   # Pydantic models for ui_hint/refresh_targets
│   │       └── __init__.py                 # Export new dialog schema types
│   └── tests/
│       ├── test_dialogs.py                 # Contract tests for sendChat/resolveAction
│       └── test_background.py              # Contract tests for getBackgroundTask
├── frontend/
│   ├── package.json                        # Add Vitest script/dev dependency
│   └── src/
│       ├── App.vue                         # Route-aware app shell usage
│       ├── api/
│       │   ├── client.ts                   # Typed chat/background responses
│       │   └── types.ts                    # Shared frontend API contracts
│       ├── components/
│       │   ├── ActionCard.vue             # Parchment approval styles
│       │   ├── ChatMessage.vue            # Message bubble and action-result styling
│       │   ├── ProjectCard.vue            # Richer list card content
│       │   ├── QuickActions.vue           # Parchment chip styling
│       │   ├── layout/
│       │   │   ├── AppShell.vue           # Global shell, wide/narrow container logic
│       │   │   └── AppTopNav.vue          # Shared top navigation
│       │   ├── list/
│       │   │   ├── ProjectMatrixHero.vue  # List page heading, stats, create flow
│       │   │   └── ProjectFocusRail.vue   # Right rail summary / next-step card
│       │   └── workspace/
│       │       ├── ChatWorkspace.vue      # Context bar + messages + quick actions + input
│       │       ├── InspectorPanel.vue     # Toolbar + existing panel component switch
│       │       └── ProjectWorkspaceShell.vue
│       ├── stores/
│       │   ├── chat.ts                    # Return structured responses to page shell
│       │   ├── project.ts                 # Refresh only requested resources
│       │   ├── workspace.ts               # Inspector focus logic
│       │   └── workspace.test.ts          # Vitest coverage for auto/locked transitions
│       ├── style.css                      # Heavy parchment tokens and shared utility classes
│       └── views/
│           ├── ProjectDetail.vue          # Page assembly only; no local activeTab
│           ├── ProjectList.vue            # Matrix layout
│           └── SettingsView.vue           # Unified shell + section cards
└── scripts/
    └── verify_full_app_ui.sh              # Repeatable regression: tests + build + agent-browser smoke
```

## Task 1: Backend UI Hint Contract

**Files:**
- Create: `backend/app/core/ui_hints.py`
- Modify: `backend/app/schemas/dialog.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/api/background_tasks_api.py`
- Test: `backend/tests/test_dialogs.py`
- Test: `backend/tests/test_background.py`

- [ ] **Step 1: Write the failing backend contract tests**

`backend/tests/test_dialogs.py`
```python
def test_chat_button_action_returns_ui_hint(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    res = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
        "params": {"project_id": pid},
    })

    body = res.json()
    assert res.status_code == 200
    assert body["ui_hint"]["dialog_state"] == "PENDING_ACTION"
    assert body["ui_hint"]["active_action"]["target_panel"] == "setup"
    assert body["ui_hint"]["active_action"]["status"] == "pending"
    assert body["refresh_targets"] == []


@patch("app.api.setups.load_api_key", return_value="sk-test")
@patch("app.api.setups.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.setups.ai_service.parse_json")
def test_resolve_action_confirm_returns_running_hint(mock_parse, mock_complete, mock_key, client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    pending = client.post("/api/v1/dialog/chat", json={
        "project_id": pid,
        "input_type": "button",
        "action_type": "preview_setup",
    }).json()["pending_action"]["id"]

    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

    res = client.post("/api/v1/dialog/resolve-action", json={
        "action_id": pending,
        "decision": "confirm",
    })

    body = res.json()
    assert res.status_code == 200
    assert body["ui_hint"]["dialog_state"] == "RUNNING"
    assert body["ui_hint"]["active_action"]["target_panel"] == "setup"
    assert body["ui_hint"]["active_action"]["status"] == "running"
    assert body["refresh_targets"] == []
```

`backend/tests/test_background.py`
```python
from app.models import BackgroundTask


def test_get_background_task_returns_ui_hint_and_refresh_targets(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]

    task = BackgroundTask(
        project_id=pid,
        task_type="generate_outline",
        status="completed",
        result={"outline_id": "fake-outline"},
    )
    db_session.add(task)
    db_session.commit()

    res = client.get(f"/api/v1/background-tasks/{task.id}")
    body = res.json()

    assert res.status_code == 200
    assert body["ui_hint"]["dialog_state"] == "CHATTING"
    assert body["ui_hint"]["active_action"]["target_panel"] == "outline"
    assert body["ui_hint"]["active_action"]["status"] == "completed"
    assert body["refresh_targets"] == ["outline", "versions"]
```

- [ ] **Step 2: Run the targeted tests and watch them fail for missing fields**

Run:
```bash
cd backend && source .venv/bin/activate
pytest tests/test_dialogs.py tests/test_background.py -q
```
Expected: FAIL with `KeyError: 'ui_hint'` or assertion failures on `refresh_targets`.

- [ ] **Step 3: Implement centralized UI hint mapping and response schema changes**

`backend/app/core/ui_hints.py`
```python
from __future__ import annotations

ACTION_PANEL_MAP = {
    "preview_setup": "setup",
    "generate_setup": "setup",
    "preview_storyline": "storyline",
    "generate_storyline": "storyline",
    "preview_outline": "outline",
    "generate_outline": "outline",
    "chapter": "content",
    "deep_check": "content",
    "revise_content": "content",
    "version_diff": "versions",
    "rollback_version": "versions",
    "topology": "topology",
    "preferences": "preferences",
    "style_feedback": "preferences",
}

ACTION_REFRESH_MAP = {
    "generate_setup": ["setup", "versions"],
    "generate_storyline": ["storyline", "versions"],
    "generate_outline": ["outline", "versions"],
    "deep_check": ["content"],
    "rollback_version": ["versions"],
}


def target_panel_for_action(action_type: str | None) -> str | None:
    return ACTION_PANEL_MAP.get(action_type or "")


def refresh_targets_for_action(action_type: str | None, status: str) -> list[str]:
    if status not in {"completed", "success"}:
        return []
    return ACTION_REFRESH_MAP.get(action_type or "", [])


def build_ui_hint(dialog_state: str, action_type: str | None = None, status: str = "idle", reason: str = "") -> dict:
    active_action = None
    if action_type:
        active_action = {
            "type": action_type,
            "status": status,
            "target_panel": target_panel_for_action(action_type),
            "reason": reason,
        }
    return {
        "dialog_state": dialog_state.upper(),
        "active_action": active_action,
    }
```

`backend/app/schemas/dialog.py`
```python
from pydantic import BaseModel, Field

class ActiveActionOut(BaseModel):
    type: str
    status: str
    target_panel: str | None = None
    reason: str = ""


class UiHintOut(BaseModel):
    dialog_state: str
    active_action: ActiveActionOut | None = None


class ChatOut(BaseModel):
    message: str
    pending_action: PendingActionOut | None = None
    project_diagnosis: ProjectDiagnosisOut
    ui_hint: UiHintOut
    refresh_targets: list[str] = Field(default_factory=list)
```

`backend/app/schemas/__init__.py`
```python
from .dialog import (
    ActiveActionOut,
    ChatIn,
    ChatMessageOut,
    ChatOut,
    PendingActionOut,
    ProjectDiagnosisOut,
    ResolveActionIn,
    UiHintOut,
)
```

`backend/app/api/dialogs.py`
```python
from app.core.ui_hints import build_ui_hint, refresh_targets_for_action

return ChatOut(
    message=reply,
    pending_action=PendingActionOut(
        id=pending.id,
        type=pending.type,
        description=_action_description(pending.type),
        params=pending.params,
    ),
    project_diagnosis=diagnosis,
    ui_hint=build_ui_hint(
        dialog_state="pending_action",
        action_type=pending.type,
        status="pending",
        reason=_action_description(pending.type),
    ),
    refresh_targets=[],
)

return {
    "action_result": {
        "type": action_type,
        "status": result_data["status"],
        "data": result_data,
    },
    "dialog_state": dialog.state if dialog else "chatting",
    "message": resolve_msg,
    "ui_hint": build_ui_hint(
        dialog_state="running" if payload.decision == "confirm" else "chatting",
        action_type=action_type,
        status="running" if payload.decision == "confirm" else result_data["status"],
        reason=resolve_msg,
    ),
    "refresh_targets": [],
}
```

`backend/app/api/background_tasks_api.py`
```python
from app.core.ui_hints import build_ui_hint, refresh_targets_for_action

return {
    "task_id": task.id,
    "task_type": task.task_type,
    "status": task.status,
    "result": task.result,
    "error": task.error,
    "ui_hint": build_ui_hint(
        dialog_state="chatting",
        action_type=task.task_type,
        status=task.status,
        reason=task.error or "",
    ),
    "refresh_targets": refresh_targets_for_action(task.task_type, task.status),
    "created_at": task.created_at.isoformat() if task.created_at else None,
    "started_at": task.started_at.isoformat() if task.started_at else None,
    "finished_at": task.finished_at.isoformat() if task.finished_at else None,
}
```

- [ ] **Step 4: Run the targeted tests again and confirm green**

Run:
```bash
cd backend && source .venv/bin/activate
pytest tests/test_dialogs.py tests/test_background.py -q
```
Expected: PASS, with the new contract asserted explicitly.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/ui_hints.py backend/app/schemas/dialog.py backend/app/schemas/__init__.py backend/app/api/dialogs.py backend/app/api/background_tasks_api.py backend/tests/test_dialogs.py backend/tests/test_background.py
git commit -m "feat: add structured ui hints for dialog flows"
```

## Task 2: Frontend Typed Contract and Workspace Store

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/workspace.ts`
- Create: `frontend/src/stores/workspace.test.ts`
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/stores/project.ts`

- [ ] **Step 1: Add a failing workspace focus test and unit-test runner**

`frontend/package.json`
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "test:unit": "vitest run"
  },
  "devDependencies": {
    "vitest": "^2.1.8"
  }
}
```

`frontend/src/stores/workspace.test.ts`
```ts
import { describe, expect, it } from 'vitest'
import {
  createWorkspaceState,
  applyUserPanel,
  applyUiHint,
  settleUiAction,
} from './workspace'

describe('workspace focus transitions', () => {
  it('follows ai target in auto mode', () => {
    const state = createWorkspaceState()
    const next = applyUiHint(state, {
      dialog_state: 'RUNNING',
      active_action: {
        type: 'generate_outline',
        status: 'running',
        target_panel: 'outline',
        reason: 'AI 正在生成大纲',
      },
    })

    expect(next.panel).toBe('outline')
    expect(next.source).toBe('ai')
  })

  it('returns to locked panel after ai task settles', () => {
    const locked = applyUserPanel(createWorkspaceState(), 'versions', '用户切到版本历史')
    locked.mode = 'locked'
    locked.lockedPanel = 'versions'

    const running = applyUiHint(locked, {
      dialog_state: 'RUNNING',
      active_action: {
        type: 'generate_outline',
        status: 'running',
        target_panel: 'outline',
        reason: 'AI 正在生成大纲',
      },
    })

    const settled = settleUiAction(running, 'completed')
    expect(settled.panel).toBe('versions')
    expect(settled.lockedPanel).toBe('versions')
  })
})
```

- [ ] **Step 2: Run the new frontend test and confirm it fails because the store does not exist**

Run:
```bash
cd frontend && npm install
npm run test:unit -- workspace
```
Expected: FAIL with module-not-found for `./workspace` or missing exports.

- [ ] **Step 3: Implement typed API contracts, workspace reducer logic, and targeted refresh**

`frontend/src/api/types.ts`
```ts
export type WorkspacePanel =
  | 'overview'
  | 'setup'
  | 'storyline'
  | 'outline'
  | 'content'
  | 'topology'
  | 'versions'
  | 'preferences'

export type RefreshTarget =
  | 'project'
  | 'setup'
  | 'storyline'
  | 'outline'
  | 'content'
  | 'topology'
  | 'versions'
  | 'preferences'

export interface UiActionHint {
  type: string
  status: string
  target_panel: WorkspacePanel | null
  reason: string
}

export interface UiHint {
  dialog_state: string
  active_action: UiActionHint | null
}

export interface ChatResponse {
  message: string
  pending_action?: any
  project_diagnosis: any
  ui_hint: UiHint
  refresh_targets: RefreshTarget[]
}

export interface ResolveActionResponse {
  message: string
  action_result: Record<string, unknown>
  dialog_state: string
  ui_hint: UiHint
  refresh_targets: RefreshTarget[]
}

export interface BackgroundTaskResponse {
  task_id: string
  task_type: string
  status: string
  result: Record<string, unknown> | null
  error: string | null
  ui_hint: UiHint
  refresh_targets: RefreshTarget[]
}
```

`frontend/src/api/client.ts`
```ts
import type { BackgroundTaskResponse, ChatResponse, ResolveActionResponse } from './types'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json() as Promise<T>
}

export const api = {
  listProjects: () => request<any[]>('/projects'),
  getProject: (id: string) => request<any>(`/projects/${id}`),
  getMessages: (id: string) => request<any[]>(`/dialog/projects/${id}/messages`),
  sendChat: (data: any) => request<ChatResponse>('/dialog/chat', { method: 'POST', body: JSON.stringify(data) }),
  resolveAction: (data: any) => request<ResolveActionResponse>('/dialog/resolve-action', { method: 'POST', body: JSON.stringify(data) }),
  getBackgroundTask: (taskId: string) => request<BackgroundTaskResponse>(`/background-tasks/${taskId}`),
  getPreferences: (id: string) => request<any>(`/projects/${id}/preferences`),
}
```

`frontend/src/stores/workspace.ts`
```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { UiHint, WorkspacePanel } from '../api/types'

export interface WorkspaceState {
  mode: 'auto' | 'locked'
  panel: WorkspacePanel
  lockedPanel: WorkspacePanel | null
  source: 'user' | 'ai' | 'system'
  reason: string
  lastUserPanel: WorkspacePanel
  returnPanel: WorkspacePanel | null
}

export function createWorkspaceState(): WorkspaceState {
  return {
    mode: 'auto',
    panel: 'overview',
    lockedPanel: null,
    source: 'system',
    reason: '默认概览',
    lastUserPanel: 'overview',
    returnPanel: null,
  }
}

export function applyUserPanel(state: WorkspaceState, panel: WorkspacePanel, reason: string): WorkspaceState {
  return { ...state, panel, lastUserPanel: panel, source: 'user', reason }
}

export function applyUiHint(state: WorkspaceState, hint: UiHint): WorkspaceState {
  const target = hint.active_action?.target_panel
  if (!target) return { ...state, source: 'system', reason: hint.active_action?.reason ?? state.reason }
  if (state.mode === 'locked') {
    return {
      ...state,
      panel: target,
      source: 'ai',
      reason: hint.active_action?.reason ?? '',
      returnPanel: state.lockedPanel,
    }
  }
  return { ...state, panel: target, source: 'ai', reason: hint.active_action?.reason ?? '' }
}

export function settleUiAction(state: WorkspaceState, status: string): WorkspaceState {
  if (state.mode === 'locked' && status === 'completed' && state.returnPanel) {
    return { ...state, panel: state.returnPanel, returnPanel: null, source: 'system', reason: '恢复锁定面板' }
  }
  return state
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const state = ref<WorkspaceState>(createWorkspaceState())

  function selectPanel(panel: WorkspacePanel, reason: string) {
    state.value = applyUserPanel(state.value, panel, reason)
  }

  function toggleLock() {
    state.value = state.value.mode === 'auto'
      ? { ...state.value, mode: 'locked', lockedPanel: state.value.panel }
      : { ...state.value, mode: 'auto', lockedPanel: null, returnPanel: null }
  }

  function applyHint(hint: UiHint) {
    state.value = applyUiHint(state.value, hint)
  }

  function settle(status: string) {
    state.value = settleUiAction(state.value, status)
  }

  return { state, selectPanel, toggleLock, applyHint, settle }
})
```

`frontend/src/stores/project.ts`
```ts
import type { RefreshTarget } from '../api/types'

const preferences = ref<any>(null)

async function loadPreferences(id: string) {
  preferences.value = await api.getPreferences(id)
}

async function refreshTargets(id: string, targets: RefreshTarget[]) {
  for (const target of [...new Set(targets)]) {
    if (target === 'project') await loadProject(id)
    if (target === 'setup') await loadSetup(id)
    if (target === 'storyline') await loadStoryline(id)
    if (target === 'outline') await loadOutline(id)
    if (target === 'content') await loadChapters(id)
    if (target === 'topology') await loadTopology(id)
    if (target === 'versions') await loadVersions(id)
    if (target === 'preferences') await loadPreferences(id)
  }
}
```

`frontend/src/stores/chat.ts`
```ts
import type { BackgroundTaskResponse, ChatResponse, ResolveActionResponse } from '../api/types'

async function sendText(text: string): Promise<ChatResponse | null> {
  if (loading.value || !text.trim()) return null
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  try {
    const res = await api.sendChat({
      project_id: projectId.value,
      input_type: 'text',
      text,
    })
    messages.value.push({ role: 'assistant', content: res.message, pending_action: res.pending_action || null, diagnosis: res.project_diagnosis || null })
    if (res.pending_action) pendingAction.value = res.pending_action
    if (res.project_diagnosis) diagnosis.value = res.project_diagnosis
    return res
  } catch (e: any) {
    messages.value.push({ role: 'assistant', content: `出错了：${e.message}` })
    return null
  } finally {
    loading.value = false
  }
}

async function resolveAction(decision: 'confirm' | 'cancel' | 'revise', comment = ''): Promise<ResolveActionResponse | null> {
  if (!pendingAction.value || loading.value) return null
  loading.value = true
  try {
    const actionId = pendingAction.value.id
    const res = await api.resolveAction({ action_id: actionId, decision, comment })
    pendingAction.value = null
    messages.value.push({
      role: 'system',
      content: res.message,
      action_result: res.action_result || null,
    })
    return res
  } catch (e: any) {
    messages.value.push({ role: 'assistant', content: `操作失败：${e.message}` })
    return null
  } finally {
    loading.value = false
  }
}

async function getBackgroundTask(taskId: string): Promise<BackgroundTaskResponse> {
  return api.getBackgroundTask(taskId)
}
```

- [ ] **Step 4: Run the unit test and confirm green**

Run:
```bash
cd frontend
npm run test:unit -- workspace
```
Expected: PASS for the auto/locked transition coverage.

- [ ] **Step 5: Run the frontend build to verify the new types and imports**

Run:
```bash
cd frontend && npm run build
```
Expected: PASS with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/stores/workspace.ts frontend/src/stores/workspace.test.ts frontend/src/stores/chat.ts frontend/src/stores/project.ts
git commit -m "feat: add typed workspace state orchestration"
```

## Task 3: Global App Shell and Heavy Parchment Theme

**Files:**
- Create: `frontend/src/components/layout/AppShell.vue`
- Create: `frontend/src/components/layout/AppTopNav.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`

- [ ] **Step 1: Add the shared shell components and route-aware container logic**

`frontend/src/components/layout/AppTopNav.vue`
```vue
<template>
  <nav class="app-top-nav">
    <div class="app-top-nav__brand">
      <span class="app-top-nav__wordmark">墨舟</span>
      <span class="app-top-nav__meta">Heavy Parchment Workspace</span>
    </div>
    <div class="app-top-nav__links">
      <router-link to="/" active-class="is-active">项目矩阵</router-link>
      <router-link to="/settings" active-class="is-active">系统偏好</router-link>
    </div>
  </nav>
</template>
```

`frontend/src/components/layout/AppShell.vue`
```vue
<template>
  <div class="app-shell" :data-shell-mode="mode">
    <AppTopNav />
    <main :class="mode === 'workspace' ? 'app-shell__main app-shell__main--wide' : 'app-shell__main'">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppTopNav from './AppTopNav.vue'

defineProps<{ mode: 'default' | 'workspace' }>()
</script>
```

`frontend/src/App.vue`
```vue
<template>
  <AppShell :mode="shellMode">
    <router-view />
  </AppShell>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from './components/layout/AppShell.vue'

const route = useRoute()
const shellMode = computed(() => route.path.startsWith('/projects/') ? 'workspace' : 'default')
</script>
```

- [ ] **Step 2: Add heavy parchment design tokens without dirtying high-readability surfaces**

`frontend/src/style.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --mz-paper-950: #3e2917;
  --mz-paper-800: #5b3d22;
  --mz-paper-700: #7a5731;
  --mz-paper-300: #d4b384;
  --mz-paper-200: #e2c79b;
  --mz-paper-100: #f0dfbc;
  --mz-paper-050: #f8f0df;
  --mz-surface-soft: rgba(255, 249, 238, 0.72);
  --mz-surface-clean: rgba(255, 252, 246, 0.9);
  --mz-border-soft: rgba(73, 49, 25, 0.12);
}

body {
  @apply min-h-screen antialiased;
  color: var(--mz-paper-950);
  background:
    radial-gradient(circle at 12% 20%, rgba(255, 245, 220, 0.82), transparent 18%),
    radial-gradient(circle at 86% 74%, rgba(150, 104, 48, 0.16), transparent 22%),
    linear-gradient(180deg, var(--mz-paper-100), #dcc198);
}

.app-shell__main {
  @apply mx-auto px-4 py-6 sm:px-6 lg:px-8;
  max-width: 1180px;
}

.app-shell__main--wide {
  max-width: 1520px;
}

.mz-pane {
  border: 1px solid var(--mz-border-soft);
  background: var(--mz-surface-soft);
  border-radius: 1.25rem;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.mz-clean-surface {
  background: var(--mz-surface-clean);
}
```

- [ ] **Step 3: Run the frontend build as the shell/theme smoke test**

Run:
```bash
cd frontend && npm run build
```
Expected: PASS; no route/component import errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/AppShell.vue frontend/src/components/layout/AppTopNav.vue frontend/src/App.vue frontend/src/style.css
git commit -m "feat: add global parchment app shell"
```

## Task 4: Project Detail Workspace Refactor

**Files:**
- Create: `frontend/src/components/workspace/ProjectWorkspaceShell.vue`
- Create: `frontend/src/components/workspace/ChatWorkspace.vue`
- Create: `frontend/src/components/workspace/InspectorPanel.vue`
- Modify: `frontend/src/views/ProjectDetail.vue`
- Modify: `frontend/src/components/ChatMessage.vue`
- Modify: `frontend/src/components/QuickActions.vue`
- Modify: `frontend/src/components/ActionCard.vue`

- [ ] **Step 1: Extend the failing workspace test for locked-mode settle behavior**

`frontend/src/stores/workspace.test.ts`
```ts
it('stays on the failure panel when locked mode action fails', () => {
  const locked = applyUserPanel(createWorkspaceState(), 'versions', '用户切到版本历史')
  locked.mode = 'locked'
  locked.lockedPanel = 'versions'

  const running = applyUiHint(locked, {
    dialog_state: 'RUNNING',
    active_action: {
      type: 'deep_check',
      status: 'running',
      target_panel: 'content',
      reason: 'AI 正在检查章节',
    },
  })

  const settled = settleUiAction(running, 'failed')
  expect(settled.panel).toBe('content')
})
```

- [ ] **Step 2: Run the unit test and confirm the new locked failure case fails**

Run:
```bash
cd frontend && npm run test:unit -- workspace
```
Expected: FAIL because `settleUiAction()` still returns the wrong panel for failed actions.

- [ ] **Step 3: Replace the detail-page local tab state with workspace-driven components**

`frontend/src/components/workspace/ProjectWorkspaceShell.vue`
```vue
<template>
  <section class="grid min-h-[calc(100vh-6rem)] gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(360px,0.92fr)]">
    <slot name="chat" />
    <slot name="inspector" />
  </section>
</template>
```

`frontend/src/components/workspace/ChatWorkspace.vue`
```vue
<template>
  <div class="mz-pane flex min-h-0 flex-col overflow-hidden">
    <div class="border-b border-[color:var(--mz-border-soft)] px-4 py-3 text-xs text-[color:var(--mz-paper-800)]">
      当前查看：{{ panelLabel }} · 来源：{{ reason }}
    </div>
    <div ref="container" class="flex-1 overflow-y-auto px-4 py-4 space-y-3">
      <ChatMessage
        v-for="(message, index) in messages"
        :key="index"
        :msg="message"
        :is-latest="index === messages.length - 1"
        :loading="loading"
        @decide="$emit('decide', $event[0], $event[1])"
      />
    </div>
    <QuickActions :diagnosis="diagnosis" :disabled="loading || !!pendingAction" @action="$emit('quick-action', $event)" />
    <form class="mz-clean-surface border-t border-[color:var(--mz-border-soft)] p-3" @submit.prevent="$emit('send')">
      <div class="grid grid-cols-[1fr_auto] gap-2">
        <input :value="inputValue" class="rounded-xl border border-[color:var(--mz-border-soft)] bg-white/90 px-3 py-2" @input="$emit('update:inputValue', ($event.target as HTMLInputElement).value)" />
        <button class="rounded-xl bg-[color:var(--mz-paper-800)] px-4 py-2 text-white">发送</button>
      </div>
    </form>
  </div>
</template>
```

`frontend/src/components/workspace/InspectorPanel.vue`
```vue
<template>
  <aside class="mz-pane flex min-h-0 flex-col overflow-hidden">
    <header class="flex items-center justify-between border-b border-[color:var(--mz-border-soft)] px-4 py-3 text-xs text-[color:var(--mz-paper-800)]">
      <div>{{ panelTitle }}</div>
      <div class="flex items-center gap-2">
        <button class="rounded-full border px-2 py-1" @click="$emit('toggle-lock')">
          {{ mode === 'locked' ? 'Locked' : 'Auto' }}
        </button>
      </div>
    </header>
    <div class="flex-1 overflow-y-auto p-4">
      <component :is="panelComponent" v-bind="panelProps" />
    </div>
  </aside>
</template>
```

`frontend/src/views/ProjectDetail.vue`
```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import type { ChatResponse } from '../api/types'
import { useChatStore } from '../stores/chat'
import { useProjectStore } from '../stores/project'
import { useWorkspaceStore } from '../stores/workspace'
import ChatWorkspace from '../components/workspace/ChatWorkspace.vue'
import InspectorPanel from '../components/workspace/InspectorPanel.vue'
import ProjectWorkspaceShell from '../components/workspace/ProjectWorkspaceShell.vue'

const route = useRoute()
const pid = route.params.id as string
const chat = useChatStore()
const project = useProjectStore()
const workspace = useWorkspaceStore()
const input = ref('')

async function handleResponse(res: { ui_hint: any; refresh_targets: string[] } | null) {
  if (!res) return
  workspace.applyHint(res.ui_hint)
  await project.refreshTargets(pid, res.refresh_targets)
}

async function send() {
  if (!input.value.trim()) return
  const text = input.value
  input.value = ''
  await handleResponse(await chat.sendText(text))
}

async function decide(decision: 'confirm' | 'cancel' | 'revise', comment = '') {
  const res = await chat.resolveAction(decision, comment)
  await handleResponse(res)
}

onMounted(async () => {
  await project.loadProject(pid)
  chat.init(pid)
  await project.refreshTargets(pid, ['setup', 'storyline', 'outline', 'content', 'versions', 'topology'])
})
</script>
```

- [ ] **Step 4: Update message/quick-action styling to the parchment system and make the test pass**

`frontend/src/components/ChatMessage.vue`
```vue
<div class="max-w-[82%] rounded-[1.125rem] border px-4 py-3"
  :class="msg.role === 'user'
    ? 'ml-auto border-[color:var(--mz-paper-800)] bg-[color:var(--mz-paper-800)] text-[#fff7ed]'
    : 'border-[color:var(--mz-border-soft)] bg-[color:var(--mz-surface-clean)] text-[color:var(--mz-paper-950)]'">
```

`frontend/src/components/QuickActions.vue`
```vue
<div v-if="actions.length" class="flex flex-wrap gap-2 border-t border-[color:var(--mz-border-soft)] px-4 py-3">
  <button class="rounded-full border border-[color:var(--mz-border-soft)] bg-white/60 px-3 py-1 text-xs text-[color:var(--mz-paper-800)]">
```

`frontend/src/components/ActionCard.vue`
```vue
<div class="mt-2 rounded-2xl border border-[color:var(--mz-border-soft)] bg-[color:var(--mz-surface-clean)] p-4">
```

Then rerun:
```bash
cd frontend
npm run test:unit -- workspace
npm run build
```
Expected: PASS for the workspace test and PASS for the build.

- [ ] **Step 5: Run browser automation against the detail page**

Run:
```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000 &
cd frontend && npm run dev -- --host 127.0.0.1 --port 4173 &
PROJECT_ID="$(curl -s http://127.0.0.1:8000/api/v1/projects | python -c 'import json,sys; data=json.load(sys.stdin); print(data[0][\"id\"] if data else \"\")')"
if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID="$(curl -s -X POST http://127.0.0.1:8000/api/v1/projects -H 'Content-Type: application/json' -d '{"name":"Workspace Smoke"}' | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
fi
agent-browser open "http://127.0.0.1:4173/projects/${PROJECT_ID}"
agent-browser wait 1500
agent-browser snapshot -i
agent-browser errors
agent-browser console
```
Expected: Snapshot shows chat-first left column and right Inspector; `errors` and `console` output are empty.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/workspace frontend/src/views/ProjectDetail.vue frontend/src/components/ChatMessage.vue frontend/src/components/QuickActions.vue frontend/src/components/ActionCard.vue frontend/src/stores/workspace.test.ts
git commit -m "feat: refactor project detail into chat-first workspace"
```

## Task 5: List Page and Settings Page Redesign

**Files:**
- Create: `frontend/src/components/list/ProjectMatrixHero.vue`
- Create: `frontend/src/components/list/ProjectFocusRail.vue`
- Modify: `frontend/src/components/ProjectCard.vue`
- Modify: `frontend/src/views/ProjectList.vue`
- Modify: `frontend/src/views/SettingsView.vue`

- [ ] **Step 1: Replace the list page flat stack with matrix layout components**

`frontend/src/components/list/ProjectMatrixHero.vue`
```vue
<template>
  <section class="mz-pane p-5">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-xs uppercase tracking-[0.2em] text-[color:var(--mz-paper-700)]">Project Matrix</p>
        <h1 class="mt-2 text-3xl font-semibold text-[color:var(--mz-paper-950)]">继续写，不要先翻数据库</h1>
        <p class="mt-2 max-w-2xl text-sm text-[color:var(--mz-paper-800)]">列表页直接回答：哪个项目最值得继续、下一步是什么。</p>
      </div>
      <button class="rounded-2xl bg-[color:var(--mz-paper-800)] px-4 py-2 text-sm text-white">新建项目</button>
    </div>
  </section>
</template>
```

`frontend/src/components/list/ProjectFocusRail.vue`
```vue
<template>
  <aside class="space-y-4">
    <section class="mz-pane p-5">
      <p class="text-xs uppercase tracking-[0.18em] text-[color:var(--mz-paper-700)]">创作概况</p>
      <div class="mt-4 grid gap-3">
        <div class="rounded-2xl border border-[color:var(--mz-border-soft)] bg-white/50 p-4">活跃项目：{{ projects.length }}</div>
        <div class="rounded-2xl border border-[color:var(--mz-border-soft)] bg-white/50 p-4">优先继续：{{ projects[0]?.name || '暂无' }}</div>
      </div>
    </section>
    <section class="mz-pane p-5">
      <h2 class="text-lg font-semibold text-[color:var(--mz-paper-950)]">下一步推荐</h2>
      <p class="mt-2 text-sm text-[color:var(--mz-paper-800)]">优先进入最近更新、且还有明确下一步动作的项目。</p>
    </section>
  </aside>
</template>

<script setup lang="ts">
defineProps<{ projects: any[] }>()
</script>
```

`frontend/src/components/ProjectCard.vue`
```vue
<template>
  <article class="mz-pane p-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-xs uppercase tracking-[0.18em] text-[color:var(--mz-paper-700)]">{{ project.current_phase || 'draft' }}</p>
        <h3 class="mt-2 text-lg font-semibold text-[color:var(--mz-paper-950)]">{{ project.name }}</h3>
        <p class="mt-2 text-sm text-[color:var(--mz-paper-800)]">{{ project.genre }} · {{ project.current_word_count }} 字</p>
        <p class="mt-3 text-sm text-[color:var(--mz-paper-800)]">建议下一步：{{ nextStepLabel }}</p>
      </div>
      <router-link :to="`/projects/${project.id}`" class="rounded-xl border border-[color:var(--mz-border-soft)] bg-white/60 px-3 py-2 text-sm text-[color:var(--mz-paper-800)]">
        进入工作区
      </router-link>
    </div>
  </article>
</template>
```

`frontend/src/views/ProjectList.vue`
```vue
<template>
  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_360px]">
    <div class="space-y-5">
      <ProjectMatrixHero />
      <div class="space-y-4">
        <ProjectCard v-for="project in store.projects" :key="project.id" :project="project" />
      </div>
    </div>
    <ProjectFocusRail :projects="store.projects" />
  </div>
</template>
```

- [ ] **Step 2: Redesign the settings page into the same shell system**

`frontend/src/views/SettingsView.vue`
```vue
<template>
  <div class="grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
    <section class="mz-pane p-5">
      <p class="text-xs uppercase tracking-[0.2em] text-[color:var(--mz-paper-700)]">System Preferences</p>
      <h1 class="mt-2 text-3xl font-semibold text-[color:var(--mz-paper-950)]">模型、规则与默认偏好</h1>
      <p class="mt-2 text-sm text-[color:var(--mz-paper-800)]">这里和工作区共用同一套壳层，但输入区保持更干净。</p>
    </section>

    <section class="space-y-4">
      <div class="mz-pane mz-clean-surface p-5">
        <label class="mb-2 block text-sm font-medium text-[color:var(--mz-paper-900)]">DeepSeek API Key</label>
        <div class="grid grid-cols-[1fr_auto] gap-3">
          <input v-model="apiKey" type="password" class="rounded-xl border border-[color:var(--mz-border-soft)] bg-white px-3 py-2" />
          <button class="rounded-xl bg-[color:var(--mz-paper-800)] px-4 py-2 text-white" @click="save">保存</button>
        </div>
      </div>

      <div class="mz-pane p-5">
        <h2 class="text-lg font-semibold text-[color:var(--mz-paper-950)]">危险操作</h2>
        <p class="mt-2 text-sm text-[color:var(--mz-paper-800)]">重置、覆盖和清空类操作集中在这里，避免混进主表单。</p>
      </div>
    </section>
  </div>
</template>
```

- [ ] **Step 3: Verify the redesigned list/settings pages by building the frontend**

Run:
```bash
cd frontend && npm run build
```
Expected: PASS with no missing imports or template errors.

- [ ] **Step 4: Run browser automation on `/` and `/settings`**

Run:
```bash
agent-browser open http://127.0.0.1:4173/
agent-browser wait 1500
agent-browser snapshot -i
agent-browser open http://127.0.0.1:4173/settings
agent-browser wait 1500
agent-browser snapshot -i
agent-browser errors
agent-browser console
```
Expected: list/settings pages render in the same parchment system; `errors` and `console` are empty.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/list frontend/src/components/ProjectCard.vue frontend/src/views/ProjectList.vue frontend/src/views/SettingsView.vue
git commit -m "feat: redesign list and settings pages"
```

## Task 6: Repeatable Regression Script and Final Verification

**Files:**
- Create: `scripts/verify_full_app_ui.sh`

- [ ] **Step 1: Write a repeatable verification script instead of retyping commands**

`scripts/verify_full_app_ui.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACK_PID=""
FRONT_PID=""

cleanup() {
  [[ -n "$BACK_PID" ]] && kill "$BACK_PID" 2>/dev/null || true
  [[ -n "$FRONT_PID" ]] && kill "$FRONT_PID" 2>/dev/null || true
}
trap cleanup EXIT

cd "$ROOT/backend"
source .venv/bin/activate
pytest tests/test_dialogs.py tests/test_background.py tests/test_projects.py -q

cd "$ROOT/frontend"
npm run test:unit -- workspace
npm run build

cd "$ROOT/backend"
source .venv/bin/activate
uvicorn app.main:app --port 8000 > /tmp/mozhou-backend.log 2>&1 &
BACK_PID=$!

cd "$ROOT/frontend"
npm run dev -- --host 127.0.0.1 --port 4173 > /tmp/mozhou-frontend.log 2>&1 &
FRONT_PID=$!
sleep 3

PROJECT_ID="$(curl -s http://127.0.0.1:8000/api/v1/projects | python -c 'import json,sys; data=json.load(sys.stdin); print(data[0]["id"] if data else "")')"
if [[ -z "$PROJECT_ID" ]]; then
  PROJECT_ID="$(curl -s -X POST http://127.0.0.1:8000/api/v1/projects -H 'Content-Type: application/json' -d '{"name":"Smoke Test"}' | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
fi

agent-browser open http://127.0.0.1:4173/
agent-browser wait 1500
agent-browser open "http://127.0.0.1:4173/projects/${PROJECT_ID}"
agent-browser wait 1500
agent-browser open http://127.0.0.1:4173/settings
agent-browser wait 1500
agent-browser errors
agent-browser console
```

- [ ] **Step 2: Run the script after all tasks land**

Run:
```bash
chmod +x scripts/verify_full_app_ui.sh
./scripts/verify_full_app_ui.sh
```
Expected:
- backend pytest subset PASS
- frontend unit test PASS
- frontend build PASS
- agent-browser runs through `/`, `/projects/:id`, `/settings`
- final `agent-browser errors` and `agent-browser console` outputs are empty

- [ ] **Step 3: Commit**

```bash
git add scripts/verify_full_app_ui.sh
git commit -m "chore: add full app ui verification script"
```
