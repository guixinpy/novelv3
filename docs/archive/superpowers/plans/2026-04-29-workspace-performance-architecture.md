# Workspace Performance Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce workspace switch latency and request storms across Hermes, Athena, and Calliope while adding measurable performance guardrails for future changes.

**Architecture:** Add a small frontend request coordinator and project workspace session store, then migrate Hermes, Athena, and Manuscript one at a time from route-enter reset behavior to cache-aware ensure behavior. Add browser performance probes first so every phase can be measured before moving on.

**Tech Stack:** Vue 3, Pinia, Vite, Vitest, FastAPI, SQLAlchemy, pytest, agent-browser.

---

## Non-Negotiable Delivery Rules

- Run a browser request-count baseline before behavior changes.
- Each phase must leave the app runnable.
- Each behavior change starts with focused tests.
- Do not start the next phase if focused tests, build, or browser smoke fails.
- Do not rely on `KeepAlive` alone.
- Do not change backend 404 semantics for missing setup/storyline/outline.
- Preserve existing user drafts and unrelated working-tree changes.

## File Structure

Frontend files to create:

- `frontend/src/stores/requestCache.ts`: shared in-flight dedupe, freshness, invalidation.
- `frontend/src/stores/requestCache.test.ts`: unit tests for dedupe and freshness behavior.
- `frontend/src/stores/projectWorkspace.ts`: active project/workspace session, dirty targets, remembered routes/chapters.
- `frontend/src/stores/projectWorkspace.test.ts`: unit tests for workspace session behavior.
- `frontend/src/utils/workspacePerfProbe.ts`: browser-side helper for request counting.
- `frontend/src/utils/workspacePerfProbe.test.ts`: formatting/aggregation tests for probe output.

Frontend files to modify:

- `frontend/src/stores/project.ts`: use request cache for read APIs and expose safe scoped reset behavior.
- `frontend/src/stores/chat.ts`: split cold init from dirty refresh and prevent historical action replay.
- `frontend/src/stores/athena.ts`: add project scope, same-project cache reuse, section freshness.
- `frontend/src/stores/manuscript.ts`: preserve selected chapter by project and avoid same-chapter reload.
- `frontend/src/views/HermesView.vue`: enter via workspace session, suppress initial watcher replay, reduce duplicate refresh.
- `frontend/src/views/AthenaView.vue`: remove same-project reset and use section ensure.
- `frontend/src/views/ManuscriptView.vue`: restore last chapter and reuse cached chapter.
- `frontend/src/api/client.ts`: later add bootstrap/messages query params.
- `frontend/src/api/types.ts`: later add bootstrap response types.

Backend files to modify in later phases:

- `backend/app/api/projects.py` or new `backend/app/api/workspace.py`: workspace bootstrap endpoint.
- `backend/app/api/dialogs.py`: messages `limit` / `after_id` support.
- `backend/app/api/athena.py`: Athena messages forwards pagination params.
- `backend/tests/test_workspace_bootstrap.py`: backend contract tests.
- `backend/tests/test_dialog_messages_pagination.py`: message query contract tests.

## Phase 0: Performance Baseline And Probe

**Purpose:** Make performance measurable before code changes.

**Files:**

- Create: `frontend/src/utils/workspacePerfProbe.ts`
- Create: `frontend/src/utils/workspacePerfProbe.test.ts`

- [ ] **Step 1: Write failing probe aggregation tests**

Add `frontend/src/utils/workspacePerfProbe.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { summarizeWorkspaceRequests, type WorkspaceRequestRecord } from './workspacePerfProbe'

describe('workspace perf probe', () => {
  it('groups request counts and durations by phase', () => {
    const records: WorkspaceRequestRecord[] = [
      { phase: 'athena_to_hermes', method: 'GET', url: '/api/v1/projects/1', status: 200, durationMs: 20 },
      { phase: 'athena_to_hermes', method: 'GET', url: '/api/v1/projects/1/chapters', status: 200, durationMs: 30 },
      { phase: 'hermes_to_athena', method: 'GET', url: '/api/v1/projects/1/athena/ontology', status: 200, durationMs: 40 },
    ]

    const summary = summarizeWorkspaceRequests(records)

    expect(summary.athena_to_hermes.requestCount).toBe(2)
    expect(summary.athena_to_hermes.totalDurationMs).toBe(50)
    expect(summary.hermes_to_athena.urls).toEqual(['/api/v1/projects/1/athena/ontology'])
  })

  it('marks duplicate URLs inside a phase', () => {
    const records: WorkspaceRequestRecord[] = [
      { phase: 'return_hermes', method: 'GET', url: '/api/v1/projects/1/chapters', status: 200, durationMs: 10 },
      { phase: 'return_hermes', method: 'GET', url: '/api/v1/projects/1/chapters', status: 200, durationMs: 15 },
    ]

    const summary = summarizeWorkspaceRequests(records)

    expect(summary.return_hermes.duplicateUrls).toEqual(['/api/v1/projects/1/chapters'])
  })
})
```

- [ ] **Step 2: Run red test**

Run:

```bash
cd frontend && npm run test:unit -- workspacePerfProbe
```

Expected: fail because `workspacePerfProbe.ts` does not exist.

- [ ] **Step 3: Implement probe aggregation**

Create `frontend/src/utils/workspacePerfProbe.ts`:

```ts
export interface WorkspaceRequestRecord {
  phase: string
  method: string
  url: string
  status: number | string
  durationMs: number
}

export interface WorkspacePhaseSummary {
  requestCount: number
  totalDurationMs: number
  urls: string[]
  duplicateUrls: string[]
}

export function summarizeWorkspaceRequests(records: WorkspaceRequestRecord[]) {
  const summary: Record<string, WorkspacePhaseSummary> = {}

  for (const record of records) {
    const phase = record.phase || 'unknown'
    const item = summary[phase] ?? {
      requestCount: 0,
      totalDurationMs: 0,
      urls: [],
      duplicateUrls: [],
    }
    item.requestCount += 1
    item.totalDurationMs += record.durationMs
    item.urls.push(record.url)
    summary[phase] = item
  }

  for (const item of Object.values(summary)) {
    const counts = new Map<string, number>()
    for (const url of item.urls) {
      counts.set(url, (counts.get(url) || 0) + 1)
    }
    item.duplicateUrls = [...counts.entries()]
      .filter(([, count]) => count > 1)
      .map(([url]) => url)
  }

  return summary
}
```

- [ ] **Step 4: Run green test**

Run:

```bash
cd frontend && npm run test:unit -- workspacePerfProbe
```

Expected: tests pass.

- [ ] **Step 5: Browser baseline**

Use agent-browser against a real local project and record:

- `Athena -> Hermes` request count.
- `Hermes -> Athena` request count.
- `Athena -> Calliope` request count.
- `Calliope -> Hermes` request count.
- rapid switch 7-step total request count.
- console errors.

Expected before optimization: current baseline may be around `Athena -> Hermes = 10` and rapid switch around `46`.

## Phase 1: Hermes Request Storm Fix

**Purpose:** Remove duplicate project/chapter refreshes and prevent historical action replay.

**Files:**

- Modify: `frontend/src/views/HermesView.vue`
- Modify: `frontend/src/stores/chat.ts`
- Test: `frontend/src/stores/chat.workspace.test.ts`

- [ ] **Step 1: Add failing test for historical action replay guard**

Add a test in `frontend/src/stores/chat.workspace.test.ts` that mounts or exercises the fingerprint helper after `chat.init()` and verifies the latest historical terminal action is marked as already seen before watcher-driven refresh can run.

Expected assertion:

```ts
expect(shouldProcessActionFingerprint('3:generate_chapter:success')).toBe(false)
expect(shouldProcessActionFingerprint('4:generate_chapter:success')).toBe(true)
```

- [ ] **Step 2: Extract fingerprint guard**

Move action fingerprint handling into a small exported helper from `HermesView.vue` or a new `frontend/src/views/hermesActionReplay.ts`:

```ts
export function createActionReplayGuard() {
  let initialized = false
  let lastSeen = ''

  return {
    markInitial(fingerprint: string) {
      initialized = true
      lastSeen = fingerprint
    },
    shouldProcess(fingerprint: string) {
      if (!fingerprint || !initialized) return false
      if (fingerprint === lastSeen) return false
      lastSeen = fingerprint
      return true
    },
  }
}
```

- [ ] **Step 3: Use guard in HermesView**

During `initialize()` after `chat.init()` and before `ready.value = true`, call `actionReplayGuard.markInitial(latestActionFingerprint.value)`.

In the watcher, return unless `actionReplayGuard.shouldProcess(fingerprint)` is true.

- [ ] **Step 4: Remove duplicate initial content load**

In `HermesView.initialize()`, do not call both `ensurePanelData(workspace.panel)` and `project.loadChapters()` when the panel is `content`.

Use a local set of initial targets:

```ts
const initialTargets = new Set<RefreshTarget>(getInitialProjectHydrationTargets(chat.diagnosis))
for (const target of getPanelRefreshTargets(workspace.panel)) initialTargets.add(target)
initialTargets.add('content')
```

Then load each target once.

- [ ] **Step 5: Verify Phase 1**

Run:

```bash
cd frontend && npm run test:unit -- chat.workspace
cd frontend && npm run build
```

Then run browser smoke and verify `Athena -> Hermes` no longer refreshes stale historical action and duplicate `/chapters` is gone.

## Phase 2: Request Cache And Workspace Session

**Purpose:** Make duplicate same-resource requests share one in-flight request and remember project-level workspace state.

**Files:**

- Create: `frontend/src/stores/requestCache.ts`
- Create: `frontend/src/stores/requestCache.test.ts`
- Create: `frontend/src/stores/projectWorkspace.ts`
- Create: `frontend/src/stores/projectWorkspace.test.ts`
- Modify: `frontend/src/stores/project.ts`

- [ ] **Step 1: Write request cache tests**

Create `frontend/src/stores/requestCache.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest'
import { createRequestCache } from './requestCache'

describe('request cache', () => {
  it('dedupes in-flight requests by key', async () => {
    const cache = createRequestCache()
    const loader = vi.fn(async () => 'value')

    const [a, b] = await Promise.all([
      cache.dedupe('project:1', loader),
      cache.dedupe('project:1', loader),
    ])

    expect(a).toBe('value')
    expect(b).toBe('value')
    expect(loader).toHaveBeenCalledTimes(1)
  })

  it('does not cache failed requests as fresh', async () => {
    const cache = createRequestCache()
    await expect(cache.dedupe('project:1', async () => { throw new Error('boom') })).rejects.toThrow('boom')
    expect(cache.isFresh('project:1', 1000)).toBe(false)
  })

  it('marks successful requests fresh and supports invalidation', async () => {
    const cache = createRequestCache()
    await cache.dedupe('project:1:chapters', async () => [])

    expect(cache.isFresh('project:1:chapters', 1000)).toBe(true)
    cache.invalidate('project:1')
    expect(cache.isFresh('project:1:chapters', 1000)).toBe(false)
  })
})
```

- [ ] **Step 2: Implement request cache**

Create `frontend/src/stores/requestCache.ts` with `createRequestCache()`, `useRequestCacheStore()`, `dedupe`, `markFresh`, `isFresh`, and `invalidate`.

- [ ] **Step 3: Write workspace session tests**

Create `frontend/src/stores/projectWorkspace.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { createProjectWorkspaceState, enterProject, markDirty, rememberManuscriptChapter } from './projectWorkspace'

describe('project workspace session', () => {
  it('resets dirty state only when entering a different project', () => {
    const state = createProjectWorkspaceState()
    enterProject(state, 'p1')
    markDirty(state, ['content', 'versions'])
    enterProject(state, 'p1')
    expect([...state.dirtyTargets]).toEqual(['content', 'versions'])
    enterProject(state, 'p2')
    expect([...state.dirtyTargets]).toEqual([])
  })

  it('remembers manuscript chapter by project', () => {
    const state = createProjectWorkspaceState()
    rememberManuscriptChapter(state, 'p1', 3)
    expect(state.lastManuscriptChapterByProject.p1).toBe(3)
  })
})
```

- [ ] **Step 4: Implement workspace session store**

Create `frontend/src/stores/projectWorkspace.ts` with pure helper functions plus `useProjectWorkspaceStore()`.

- [ ] **Step 5: Wire project read methods through request cache**

Modify `project.ts` read functions (`loadProject`, `loadSetup`, `loadStoryline`, `loadOutline`, `loadTopology`, `loadChapters`, `loadVersions`, `loadPreferences`) so same-key concurrent calls reuse one Promise.

- [ ] **Step 6: Verify Phase 2**

Run:

```bash
cd frontend && npm run test:unit -- requestCache projectWorkspace project.workspace
cd frontend && npm run build
```

Then run browser rapid-switch smoke and compare request counts.

## Phase 3: Athena And Calliope Hot Switch

**Purpose:** Same-project hot switching keeps Athena data and Manuscript selected chapter.

**Files:**

- Modify: `frontend/src/stores/athena.ts`
- Modify: `frontend/src/views/AthenaView.vue`
- Modify: `frontend/src/stores/manuscript.ts`
- Modify: `frontend/src/views/ManuscriptView.vue`
- Test: `frontend/src/stores/athena.*.test.ts`
- Test: `frontend/src/stores/manuscript.test.ts`

- [ ] Add tests proving same-project Athena activation does not clear ontology/messages.
- [ ] Add tests proving project change still resets Athena state.
- [ ] Add tests proving Manuscript remembers selected chapter by project.
- [ ] Remove same-project `athena.reset()` from `AthenaView.initialize()`.
- [ ] Add `athena.ensureProject(projectId)` and `athena.resetProject(projectId)` semantics.
- [ ] Update `ManuscriptView` to use remembered chapter instead of always first chapter.
- [ ] Run focused tests, build, and browser smoke.

## Phase 4: Backend Workspace Bootstrap

**Purpose:** Reduce cold-start round trips.

**Files:**

- Create or modify: `backend/app/api/workspace.py`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/types.ts`
- Test: `backend/tests/test_workspace_bootstrap.py`

- [ ] Add backend test for `GET /api/v1/projects/{project_id}/workspace-bootstrap`.
- [ ] Implement bootstrap endpoint returning project, diagnosis, chapters, latest versions, dialog summaries.
- [ ] Wire frontend cold entry to use bootstrap before fallback individual requests.
- [ ] Run backend focused tests, frontend build, and browser cold-start smoke.

## Phase 5: Heavy Data Controls

**Purpose:** Keep large projects responsive.

**Files:**

- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/api/athena.py`
- Modify: `frontend/src/stores/chat.ts`
- Modify: `frontend/src/stores/athena.ts`
- Modify: `frontend/src/components/chat/ChatMessageList.vue`

- [ ] Add `limit` and `after_id` support to Hermes/Athena messages APIs.
- [ ] Load latest messages first, then older messages on demand.
- [ ] Preserve pending action restoration with limited history.
- [ ] Add frontend tests for append-only history refresh.
- [ ] Run backend tests, frontend tests, build, and browser long-history smoke.

## Phase 6: Performance Guardrail

**Purpose:** Prevent future regressions.

**Files:**

- Create: `scripts/workspace_perf_smoke.mjs` or `frontend/scripts/workspace_perf_smoke.mjs`
- Modify: `docs/manual-test-checklist.md` only if the user explicitly asks.

- [ ] Wrap the browser request-count smoke into a reusable script.
- [ ] Print JSON summary with request counts, duplicate URLs, console errors, and elapsed times.
- [ ] Document expected thresholds in the script.
- [ ] Run the script after final build.

## Final Verification

Run:

```bash
cd frontend && npm run test:unit
cd frontend && npm run build
cd backend && source .venv/bin/activate && pytest
```

Run browser smoke:

- Cold open Hermes.
- Switch Hermes -> Athena -> Hermes.
- Switch Athena -> Calliope -> Hermes.
- Rapid switch 7 steps.

Final acceptance:

- `Athena -> Hermes` API count <= 4.
- rapid switch 7-step API count <= 18.
- no browser console errors.
- build passes.
- focused tests pass.
