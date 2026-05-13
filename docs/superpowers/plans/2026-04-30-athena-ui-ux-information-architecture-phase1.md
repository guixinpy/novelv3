# Athena UI/UX Information Architecture Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Athena's leaf-tab navigation with the approved five-section information architecture and deliver the Set Library three-column workbench for complete node information.

**Architecture:** Add a small Athena navigation model that resolves primary sections, subviews, filters, and legacy routes. Build the Set Library as focused Vue components backed by existing ontology/projection/proposal data. Keep existing truth, narrative, and review components wired through the new sections without deep rewrites in Phase 1.

**Tech Stack:** Vue 3 `<script setup lang="ts">`, Pinia, Vue Router, Vitest, existing CSS variables and BEM-style scoped classes.

---

## Scope Check

The approved design covers multiple subsystems: global Athena IA, Set Library, Truth Cognition, Narrative Context, Review Workflow, and tools. Phase 1 intentionally implements only:

- New Athena top-level IA and subnav.
- Legacy route compatibility for existing Athena leaf routes.
- Set Library `节点 / 图谱 / 规则` shell.
- Node list, node detail, and right context rail for complete node information.
- Existing component migration into new `叙事脉络 / 真相认知 / 待审变更` sections.

Out of scope for Phase 1:

- Fully interactive graph visualization.
- New backend APIs.
- Full information disclosure editor.
- Redesign of proposal review internals.
- Redesign of Athena chat.

## File Structure

Create:

- `frontend/src/views/athenaNavigation.ts`  
  Owns Athena primary sections, subviews, legacy route mapping, and route-building helpers.

- `frontend/src/components/athena/catalog/catalogNodeModel.ts`  
  Converts `AthenaOntology`, `WorldProjection`, and proposal summaries into UI-ready catalog nodes.

- `frontend/src/components/athena/catalog/CatalogWorkbench.vue`  
  Three-column Set Library workbench shell.

- `frontend/src/components/athena/catalog/CatalogNodeList.vue`  
  Left rail: type filters, search, node list.

- `frontend/src/components/athena/catalog/CatalogNodeDetail.vue`  
  Center panel: complete layered node detail.

- `frontend/src/components/athena/catalog/CatalogContextRail.vue`  
  Right rail: relationship, time/narrative, truth/knowledge, pending-change context.

- `frontend/src/components/athena/catalog/CatalogGraphPanel.vue`  
  Phase 1 graph shell using relation summaries and relation table behavior, without full graph layout.

- `frontend/src/components/athena/catalog/catalogNodeModel.test.ts`
- `frontend/src/views/athenaNavigation.test.ts`
- `frontend/src/components/athena/catalog/CatalogWorkbench.test.ts`
- `frontend/src/components/athena/catalog/CatalogNodeDetail.test.ts`

Modify:

- `frontend/src/stores/ui.ts`  
  Add Athena route state for primary section/subview/filter while keeping minimal compatibility where needed.

- `frontend/src/views/AthenaView.vue`  
  Use new route state, render five primary sections, and wire Set Library.

- `frontend/src/views/athenaSectionLoader.ts`  
  Load data by primary section/subview instead of old leaf section.

- `frontend/src/views/athenaSectionLoader.test.ts`
- `frontend/src/components/athena/AthenaSubnav.vue`
- `frontend/src/components/athena/AthenaSubnav.test.ts`
- `frontend/src/components/athena/AthenaOverview.vue`
- `frontend/src/components/athena/AthenaOverview.test.ts`

## Route Model

Canonical Athena routes:

```text
/projects/:id/athena
/projects/:id/athena/overview
/projects/:id/athena/catalog?view=nodes&type=characters
/projects/:id/athena/catalog?view=graph
/projects/:id/athena/catalog?view=rules
/projects/:id/athena/narrative?view=timeline
/projects/:id/athena/narrative?view=storyline
/projects/:id/athena/narrative?view=chapters
/projects/:id/athena/narrative?view=foreshadowing
/projects/:id/athena/truth?view=facts
/projects/:id/athena/truth?view=projection
/projects/:id/athena/truth?view=knowledge
/projects/:id/athena/truth?view=disclosure
/projects/:id/athena/review?view=proposals
/projects/:id/athena/review?view=impact
/projects/:id/athena/review?view=conflicts
/projects/:id/athena/review?view=history
```

Legacy route mapping:

```text
characters -> catalog?view=nodes&type=characters
locations -> catalog?view=nodes&type=locations
factions -> catalog?view=nodes&type=factions
items -> catalog?view=nodes&type=items
relations -> catalog?view=graph
rules -> catalog?view=rules
timeline -> narrative?view=timeline
storyline -> narrative?view=storyline
outline -> narrative?view=chapters
projection -> truth?view=projection
knowledge -> truth?view=knowledge
proposals -> review?view=proposals
consistency -> review?view=conflicts
retrieval -> catalog?view=nodes&tool=retrieval
optimization -> overview?panel=optimization
```

## Task 1: Athena Navigation Model

**Files:**

- Create: `frontend/src/views/athenaNavigation.ts`
- Create: `frontend/src/views/athenaNavigation.test.ts`

- [ ] **Step 1: Write route model tests**

Create `frontend/src/views/athenaNavigation.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import {
  buildAthenaRoute,
  resolveAthenaRoute,
  type AthenaRouteState,
} from './athenaNavigation'

describe('athenaNavigation', () => {
  it('resolves the default Athena route to overview', () => {
    expect(resolveAthenaRoute(undefined, {})).toEqual({
      section: 'overview',
      view: 'dashboard',
      nodeType: 'all',
      tool: null,
      panel: null,
      isLegacy: false,
    })
  })

  it('maps legacy entity routes to catalog node filters', () => {
    expect(resolveAthenaRoute('characters', {})).toMatchObject({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'characters',
      isLegacy: true,
    })
    expect(resolveAthenaRoute('locations', {})).toMatchObject({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'locations',
      isLegacy: true,
    })
  })

  it('maps legacy truth and review routes to new sections', () => {
    expect(resolveAthenaRoute('projection', {})).toMatchObject({
      section: 'truth',
      view: 'projection',
      isLegacy: true,
    })
    expect(resolveAthenaRoute('consistency', {})).toMatchObject({
      section: 'review',
      view: 'conflicts',
      isLegacy: true,
    })
  })

  it('uses query view and filters for canonical routes', () => {
    expect(resolveAthenaRoute('catalog', { view: 'rules' })).toMatchObject({
      section: 'catalog',
      view: 'rules',
      nodeType: 'all',
      isLegacy: false,
    })
    expect(resolveAthenaRoute('catalog', { view: 'nodes', type: 'factions' })).toMatchObject({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'factions',
      isLegacy: false,
    })
  })

  it('builds canonical route locations', () => {
    const state: AthenaRouteState = {
      section: 'catalog',
      view: 'nodes',
      nodeType: 'characters',
      tool: null,
      panel: null,
      isLegacy: false,
    }

    expect(buildAthenaRoute('project-1', state)).toEqual({
      path: '/projects/project-1/athena/catalog',
      query: { view: 'nodes', type: 'characters' },
    })
  })
})
```

- [ ] **Step 2: Run route model tests and verify failure**

Run:

```bash
cd frontend
npm run test:unit -- src/views/athenaNavigation.test.ts
```

Expected: FAIL because `athenaNavigation.ts` does not exist.

- [ ] **Step 3: Implement route model**

Create `frontend/src/views/athenaNavigation.ts`:

```ts
export type AthenaPrimarySection = 'overview' | 'catalog' | 'narrative' | 'truth' | 'review'
export type AthenaCatalogView = 'nodes' | 'graph' | 'rules'
export type AthenaNarrativeView = 'timeline' | 'storyline' | 'chapters' | 'foreshadowing'
export type AthenaTruthView = 'facts' | 'projection' | 'knowledge' | 'disclosure'
export type AthenaReviewView = 'proposals' | 'impact' | 'conflicts' | 'history'
export type AthenaOverviewView = 'dashboard'
export type AthenaSubview =
  | AthenaOverviewView
  | AthenaCatalogView
  | AthenaNarrativeView
  | AthenaTruthView
  | AthenaReviewView

export type AthenaNodeTypeFilter =
  | 'all'
  | 'characters'
  | 'locations'
  | 'factions'
  | 'items'
  | 'resources'
  | 'concepts'

export interface AthenaNavItem {
  section: AthenaPrimarySection
  label: string
  defaultView: AthenaSubview
}

export interface AthenaRouteState {
  section: AthenaPrimarySection
  view: AthenaSubview
  nodeType: AthenaNodeTypeFilter
  tool: string | null
  panel: string | null
  isLegacy: boolean
}

type QueryValue = string | string[] | null | undefined
type QueryLike = Record<string, QueryValue>

export const athenaPrimaryNav: AthenaNavItem[] = [
  { section: 'overview', label: '总览', defaultView: 'dashboard' },
  { section: 'catalog', label: '设定库', defaultView: 'nodes' },
  { section: 'narrative', label: '叙事脉络', defaultView: 'timeline' },
  { section: 'truth', label: '真相认知', defaultView: 'projection' },
  { section: 'review', label: '待审变更', defaultView: 'proposals' },
]

const primarySections = new Set<AthenaPrimarySection>(athenaPrimaryNav.map((item) => item.section))
const catalogViews = new Set<AthenaSubview>(['nodes', 'graph', 'rules'])
const narrativeViews = new Set<AthenaSubview>(['timeline', 'storyline', 'chapters', 'foreshadowing'])
const truthViews = new Set<AthenaSubview>(['facts', 'projection', 'knowledge', 'disclosure'])
const reviewViews = new Set<AthenaSubview>(['proposals', 'impact', 'conflicts', 'history'])
const nodeTypes = new Set<AthenaNodeTypeFilter>(['all', 'characters', 'locations', 'factions', 'items', 'resources', 'concepts'])

const legacyRoutes: Record<string, Partial<AthenaRouteState>> = {
  characters: { section: 'catalog', view: 'nodes', nodeType: 'characters' },
  locations: { section: 'catalog', view: 'nodes', nodeType: 'locations' },
  factions: { section: 'catalog', view: 'nodes', nodeType: 'factions' },
  items: { section: 'catalog', view: 'nodes', nodeType: 'items' },
  relations: { section: 'catalog', view: 'graph' },
  rules: { section: 'catalog', view: 'rules' },
  timeline: { section: 'narrative', view: 'timeline' },
  storyline: { section: 'narrative', view: 'storyline' },
  outline: { section: 'narrative', view: 'chapters' },
  projection: { section: 'truth', view: 'projection' },
  knowledge: { section: 'truth', view: 'knowledge' },
  proposals: { section: 'review', view: 'proposals' },
  consistency: { section: 'review', view: 'conflicts' },
  retrieval: { section: 'catalog', view: 'nodes', tool: 'retrieval' },
  optimization: { section: 'overview', view: 'dashboard', panel: 'optimization' },
}

export function resolveAthenaRoute(rawSection: string | undefined, query: QueryLike): AthenaRouteState {
  const base: AthenaRouteState = {
    section: 'overview',
    view: 'dashboard',
    nodeType: 'all',
    tool: singleQuery(query.tool),
    panel: singleQuery(query.panel),
    isLegacy: false,
  }

  if (!rawSection) return base

  const legacy = legacyRoutes[rawSection]
  if (legacy) return { ...base, ...legacy, isLegacy: true }

  const section = primarySections.has(rawSection as AthenaPrimarySection)
    ? rawSection as AthenaPrimarySection
    : 'overview'
  const requestedView = singleQuery(query.view)
  const nodeType = normalizeNodeType(singleQuery(query.type))

  return {
    ...base,
    section,
    view: normalizeView(section, requestedView),
    nodeType,
    tool: singleQuery(query.tool),
    panel: singleQuery(query.panel),
  }
}

export function buildAthenaRoute(projectId: string, state: AthenaRouteState) {
  const query: Record<string, string> = {}
  if (state.section !== 'overview') query.view = state.view
  if (state.section === 'catalog' && state.view === 'nodes' && state.nodeType !== 'all') query.type = state.nodeType
  if (state.tool) query.tool = state.tool
  if (state.panel) query.panel = state.panel

  return {
    path: `/projects/${projectId}/athena/${state.section}`,
    query,
  }
}

function normalizeView(section: AthenaPrimarySection, value: string | null): AthenaSubview {
  if (section === 'catalog') return catalogViews.has(value as AthenaSubview) ? value as AthenaSubview : 'nodes'
  if (section === 'narrative') return narrativeViews.has(value as AthenaSubview) ? value as AthenaSubview : 'timeline'
  if (section === 'truth') return truthViews.has(value as AthenaSubview) ? value as AthenaSubview : 'projection'
  if (section === 'review') return reviewViews.has(value as AthenaSubview) ? value as AthenaSubview : 'proposals'
  return 'dashboard'
}

function normalizeNodeType(value: string | null): AthenaNodeTypeFilter {
  return nodeTypes.has(value as AthenaNodeTypeFilter) ? value as AthenaNodeTypeFilter : 'all'
}

function singleQuery(value: QueryValue): string | null {
  if (Array.isArray(value)) return value[0] ?? null
  return value ?? null
}
```

- [ ] **Step 4: Run route model tests and verify pass**

Run:

```bash
cd frontend
npm run test:unit -- src/views/athenaNavigation.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit route model**

```bash
git add frontend/src/views/athenaNavigation.ts frontend/src/views/athenaNavigation.test.ts
git commit -m "feat: add athena navigation model"
```

## Task 2: UI Store Route State

**Files:**

- Modify: `frontend/src/stores/ui.ts`

- [ ] **Step 1: Update UI store Athena state**

Modify `frontend/src/stores/ui.ts` to import the new route types and replace the old active section state with route state:

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AthenaNodeTypeFilter, AthenaPrimarySection, AthenaSubview } from '../views/athenaNavigation'

export type Workspace = 'hermes' | 'athena' | 'manuscript'

export interface AthenaUiState {
  section: AthenaPrimarySection
  view: AthenaSubview
  nodeType: AthenaNodeTypeFilter
}

export const useUiStore = defineStore('ui', () => {
  const activeWorkspace = ref<Workspace>('hermes')
  const subNavCollapsed = ref(false)
  const activeAthenaState = ref<AthenaUiState>({
    section: 'overview',
    view: 'dashboard',
    nodeType: 'all',
  })
  const modals = ref<string[]>([])
  const lastProjectRoute = ref<string | null>(null)

  function toggleSubNav() {
    subNavCollapsed.value = !subNavCollapsed.value
  }

  function openModal(id: string) {
    if (!modals.value.includes(id)) modals.value.push(id)
  }

  function closeModal(id?: string) {
    if (id) {
      modals.value = modals.value.filter(m => m !== id)
    } else {
      modals.value.pop()
    }
  }

  function setWorkspace(ws: Workspace) {
    activeWorkspace.value = ws
  }

  function setAthenaState(state: AthenaUiState) {
    activeAthenaState.value = state
  }

  return {
    activeWorkspace,
    subNavCollapsed,
    activeAthenaState,
    modals,
    lastProjectRoute,
    toggleSubNav,
    openModal,
    closeModal,
    setWorkspace,
    setAthenaState,
  }
})
```

- [ ] **Step 2: Run TypeScript check and capture expected downstream failures**

Run:

```bash
cd frontend
npm run build
```

Expected: FAIL with imports or references to removed `AthenaSection` / `setAthenaSection`. These failures are resolved in the next tasks.

- [ ] **Step 3: Commit after downstream tasks**

Do not commit this task alone if the build is failing. Include it in the next integration commit after Athena view and subnav compile.

## Task 3: Athena Subnav Five-Section Navigation

**Files:**

- Modify: `frontend/src/components/athena/AthenaSubnav.vue`
- Modify: `frontend/src/components/athena/AthenaSubnav.test.ts`

- [ ] **Step 1: Write subnav test for five primary entries**

Replace `frontend/src/components/athena/AthenaSubnav.test.ts` with:

```ts
// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AthenaSubnav from './AthenaSubnav.vue'
import type { AthenaPrimarySection } from '../../views/athenaNavigation'

describe('AthenaSubnav', () => {
  it('renders the five Athena primary sections and emits navigation', async () => {
    const wrapper = mount(AthenaSubnav, {
      props: {
        items: [
          { section: 'overview', label: '总览', defaultView: 'dashboard' },
          { section: 'catalog', label: '设定库', defaultView: 'nodes' },
          { section: 'narrative', label: '叙事脉络', defaultView: 'timeline' },
          { section: 'truth', label: '真相认知', defaultView: 'projection' },
          { section: 'review', label: '待审变更', defaultView: 'proposals' },
        ],
        activeSection: 'catalog',
        canImportSetup: true,
        hasLatestChapter: true,
      },
    })

    expect(wrapper.text()).toContain('总览')
    expect(wrapper.text()).toContain('设定库')
    expect(wrapper.text()).toContain('叙事脉络')
    expect(wrapper.text()).toContain('真相认知')
    expect(wrapper.text()).toContain('待审变更')

    await wrapper.findAll('button.athena-subnav__item')[2].trigger('click')

    expect(wrapper.emitted('navigate')).toEqual([['narrative' satisfies AthenaPrimarySection]])
  })

  it('emits action events', async () => {
    const wrapper = mount(AthenaSubnav, {
      props: {
        items: [{ section: 'overview', label: '总览', defaultView: 'dashboard' }],
        activeSection: 'overview',
        canImportSetup: true,
        hasLatestChapter: true,
      },
    })

    await wrapper.findAllComponents({ name: 'BaseButton' })[0].trigger('click')
    await wrapper.findAllComponents({ name: 'BaseButton' })[1].trigger('click')
    await wrapper.findAllComponents({ name: 'BaseButton' })[2].trigger('click')

    expect(wrapper.emitted('importSetup')).toHaveLength(1)
    expect(wrapper.emitted('analyzeLatestChapter')).toHaveLength(1)
    expect(wrapper.emitted('openChat')).toHaveLength(1)
  })
})
```

- [ ] **Step 2: Run subnav test and verify failure**

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/AthenaSubnav.test.ts
```

Expected: FAIL because the component still expects grouped `sections`.

- [ ] **Step 3: Update subnav component**

Replace the script props/events in `frontend/src/components/athena/AthenaSubnav.vue` with:

```vue
<script setup lang="ts">
import BaseButton from '../base/BaseButton.vue'
import type { AthenaNavItem, AthenaPrimarySection } from '../../views/athenaNavigation'

defineProps<{
  items: AthenaNavItem[]
  activeSection: AthenaPrimarySection
  canImportSetup: boolean
  hasLatestChapter: boolean
}>()

const emit = defineEmits<{
  navigate: [section: AthenaPrimarySection]
  importSetup: []
  analyzeLatestChapter: []
  openChat: []
}>()
</script>
```

Replace the section loop in the template with:

```vue
<div class="athena-subnav__section">
  <div class="athena-subnav__section-label">Athena</div>
  <button
    v-for="item in items"
    :key="item.section"
    class="athena-subnav__item"
    :class="{ 'athena-subnav__item--active': activeSection === item.section }"
    @click="emit('navigate', item.section)"
  >
    {{ item.label }}
  </button>
</div>
```

Keep the existing action buttons and styles.

- [ ] **Step 4: Run subnav test and verify pass**

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/AthenaSubnav.test.ts
```

Expected: PASS.

## Task 4: Section Loader By Primary Section

**Files:**

- Modify: `frontend/src/views/athenaSectionLoader.ts`
- Modify: `frontend/src/views/athenaSectionLoader.test.ts`

- [ ] **Step 1: Replace section loader tests**

Update `frontend/src/views/athenaSectionLoader.test.ts` with tests that call primary route state:

```ts
import { describe, expect, it, vi } from 'vitest'
import { createAthenaSectionLoader } from './athenaSectionLoader'
import type { AthenaRouteState } from './athenaNavigation'

const state = (partial: Partial<AthenaRouteState>): AthenaRouteState => ({
  section: 'overview',
  view: 'dashboard',
  nodeType: 'all',
  tool: null,
  panel: null,
  isLegacy: false,
  ...partial,
})

describe('createAthenaSectionLoader', () => {
  it('loads dashboard and setup preview for overview when setup draft exists', async () => {
    const athena = {
      ontology: { entities: {}, relations: [], rules: [], setup_summary: { characters: [] }, profile_version: null },
      loadSetupImportPreview: vi.fn(async () => undefined),
    }
    const worldModel = {
      dashboard: null as any,
      loadDashboard: vi.fn(async () => {
        worldModel.dashboard = {
          project_profile: null,
          metrics: { entity_count: 0, fact_count: 0, presence_count: 0, event_count: 0, pending_bundle_count: 0, pending_item_count: 0 },
          next_action: { action: 'import_setup', label: '导入 Setup' },
        }
      }),
    }

    const loader = createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: athena as any,
      worldModel: worldModel as any,
    })

    await loader.loadRouteData(state({ section: 'overview' }))

    expect(worldModel.loadDashboard).toHaveBeenCalledWith('project-1')
    expect(athena.loadSetupImportPreview).toHaveBeenCalledWith('project-1')
  })

  it('loads ontology once for catalog nodes, graph, and rules', async () => {
    const athena = {
      ontology: null,
      loadOntology: vi.fn(async () => {
        athena.ontology = { entities: {}, relations: [], rules: [], setup_summary: null, profile_version: 1 }
      }),
    }
    const loader = createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: athena as any,
      worldModel: {} as any,
    })

    await loader.loadRouteData(state({ section: 'catalog', view: 'nodes' }))
    await loader.loadRouteData(state({ section: 'catalog', view: 'rules' }))

    expect(athena.loadOntology).toHaveBeenCalledTimes(1)
  })

  it('loads existing data for truth, narrative, and review sections', async () => {
    const athena = {
      timeline: null,
      evolutionPlan: null,
      consistencyIssues: [],
      loadTimeline: vi.fn(async () => undefined),
      loadEvolutionPlan: vi.fn(async () => undefined),
      loadConsistencyIssues: vi.fn(async () => undefined),
    }
    const worldModel = {
      projection: null,
      loaded: false,
      loadOverview: vi.fn(async () => undefined),
      loadSetupPanelData: vi.fn(async () => undefined),
    }
    const loader = createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: athena as any,
      worldModel: worldModel as any,
    })

    await loader.loadRouteData(state({ section: 'truth', view: 'projection' }))
    await loader.loadRouteData(state({ section: 'narrative', view: 'timeline' }))
    await loader.loadRouteData(state({ section: 'review', view: 'proposals' }))

    expect(worldModel.loadOverview).toHaveBeenCalledWith('project-1')
    expect(athena.loadTimeline).toHaveBeenCalledWith('project-1')
    expect(worldModel.loadSetupPanelData).toHaveBeenCalledWith('project-1')
  })
})
```

- [ ] **Step 2: Run loader tests and verify failure**

Run:

```bash
cd frontend
npm run test:unit -- src/views/athenaSectionLoader.test.ts
```

Expected: FAIL because `loadRouteData` does not exist.

- [ ] **Step 3: Implement primary-section loader**

Replace `frontend/src/views/athenaSectionLoader.ts` with:

```ts
import type { AthenaRouteState } from './athenaNavigation'
import type { useAthenaStore } from '../stores/athena'
import type { useWorldModelStore } from '../stores/worldModel'

type AthenaStore = ReturnType<typeof useAthenaStore>
type WorldModelStore = ReturnType<typeof useWorldModelStore>

interface AthenaSectionLoaderOptions {
  getProjectId: () => string
  athena: AthenaStore
  worldModel: WorldModelStore
}

export function createAthenaSectionLoader(options: AthenaSectionLoaderOptions) {
  async function loadRouteData(routeState: AthenaRouteState) {
    const id = options.getProjectId()

    if (routeState.section === 'overview') {
      await options.worldModel.loadDashboard(id)
      if (!options.worldModel.dashboard?.project_profile && options.athena.ontology?.setup_summary) {
        await options.athena.loadSetupImportPreview(id).catch(() => undefined)
      }
    }

    if (routeState.section === 'catalog') {
      if (!options.athena.ontology) await options.athena.loadOntology(id)
      if (routeState.tool === 'retrieval') await options.athena.loadRetrievalDiagnostics(id)
    }

    if (routeState.section === 'truth') {
      if (routeState.view === 'projection' || routeState.view === 'knowledge' || routeState.view === 'facts' || routeState.view === 'disclosure') {
        if (!options.worldModel.projection) await options.worldModel.loadOverview(id)
      }
    }

    if (routeState.section === 'narrative') {
      if (routeState.view === 'timeline') {
        if (!options.athena.timeline) await options.athena.loadTimeline(id)
      }
      if (routeState.view === 'storyline' || routeState.view === 'chapters' || routeState.view === 'foreshadowing') {
        if (!options.athena.evolutionPlan) await options.athena.loadEvolutionPlan(id)
      }
    }

    if (routeState.section === 'review') {
      if (routeState.view === 'proposals' || routeState.view === 'impact' || routeState.view === 'history') {
        if (!options.worldModel.loaded) await options.worldModel.loadSetupPanelData(id)
      }
      if (routeState.view === 'conflicts') {
        await options.athena.loadConsistencyIssues(id)
      }
    }
  }

  return { loadRouteData }
}
```

- [ ] **Step 4: Run loader tests and verify pass**

Run:

```bash
cd frontend
npm run test:unit -- src/views/athenaSectionLoader.test.ts
```

Expected: PASS.

## Task 5: Catalog Node Model

**Files:**

- Create: `frontend/src/components/athena/catalog/catalogNodeModel.ts`
- Create: `frontend/src/components/athena/catalog/catalogNodeModel.test.ts`

- [ ] **Step 1: Write node model tests**

Create `frontend/src/components/athena/catalog/catalogNodeModel.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { buildCatalogNodes, filterCatalogNodes } from './catalogNodeModel'
import type { AthenaOntology, WorldProjection } from '../../../api/types'

const ontology: AthenaOntology = {
  entities: {
    characters: [{ id: 'char.linche', name: '林澈', role_type: 'protagonist', core_drives: ['查清旧案'] } as any],
    locations: [{ id: 'loc.lighthouse', name: '旧灯塔', location_type: 'landmark', hazards: ['潮汐异常'] } as any],
    factions: [{ id: 'fac.tidegate', name: '潮汐门', faction_type: 'secret_order', hidden_agenda: '控制潮痕' } as any],
    artifacts: [{ id: 'art.lamp', name: '旧灯牌', artifact_type: 'token', function_summary: '打开旧门' } as any],
  },
  relations: [
    { id: 'rel-1', source_ref: 'char.linche', target_ref: 'loc.lighthouse', relation_type: 'guards' },
  ],
  rules: [{ id: 'rule-1', rule_id: 'rule.tide', description: '潮汐会吞没记忆' }],
  setup_summary: null,
  profile_version: 1,
}

const projection: WorldProjection = {
  view_type: 'current_truth',
  entities: {
    'char.linche': { entity_type: 'character', attributes: { public_persona: '守夜人' } },
  },
  relations: {},
  presence: { 'char.linche': { location_ref: 'loc.lighthouse', presence_status: 'active' } },
  occurred_events: {},
  event_links: {},
  facts: {
    'char.linche': { hidden_truth: '父亲失踪与潮汐门有关' },
  },
}

describe('catalogNodeModel', () => {
  it('builds catalog nodes with type, facts, relations, and presence', () => {
    const nodes = buildCatalogNodes({ ontology, projection, pendingProposalItems: [] })
    const character = nodes.find((node) => node.ref === 'char.linche')

    expect(character).toMatchObject({
      ref: 'char.linche',
      type: 'characters',
      label: '林澈',
      relationCount: 1,
      factCount: 1,
      pendingCount: 0,
    })
    expect(character?.presence?.location_ref).toBe('loc.lighthouse')
  })

  it('filters by node type and search text', () => {
    const nodes = buildCatalogNodes({ ontology, projection, pendingProposalItems: [] })

    expect(filterCatalogNodes(nodes, { nodeType: 'characters', search: '' }).map((node) => node.label)).toEqual(['林澈'])
    expect(filterCatalogNodes(nodes, { nodeType: 'all', search: '灯塔' }).map((node) => node.label)).toEqual(['旧灯塔'])
  })
})
```

- [ ] **Step 2: Run node model tests and verify failure**

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/catalog/catalogNodeModel.test.ts
```

Expected: FAIL because the model file does not exist.

- [ ] **Step 3: Implement node model**

Create `frontend/src/components/athena/catalog/catalogNodeModel.ts`:

```ts
import type { AthenaNodeTypeFilter } from '../../../views/athenaNavigation'
import type { AthenaOntology, ProposalItem, WorldProjection, WorldProjectionPresence } from '../../../api/types'

export type CatalogNodeType = 'characters' | 'locations' | 'factions' | 'items' | 'resources' | 'concepts'

export interface CatalogNode {
  ref: string
  id: string
  type: CatalogNodeType
  label: string
  aliases: string[]
  raw: Record<string, unknown>
  facts: Record<string, unknown>
  presence: WorldProjectionPresence | null
  relationCount: number
  factCount: number
  pendingCount: number
}

export interface CatalogRelation {
  id?: string
  source_ref?: string
  target_ref?: string
  source_entity_ref?: string
  target_entity_ref?: string
  relation_type?: string
  [key: string]: unknown
}

export interface BuildCatalogNodesInput {
  ontology: AthenaOntology | null
  projection: WorldProjection | null
  pendingProposalItems: ProposalItem[]
}

export function buildCatalogNodes(input: BuildCatalogNodesInput): CatalogNode[] {
  const ontologyEntities = input.ontology?.entities || {}
  const projectionEntities = input.projection?.entities || {}
  const projectionFacts = input.projection?.facts || {}
  const presence = input.projection?.presence || {}
  const relations = normalizeRelations(input.ontology?.relations || [])
  const pendingBySubject = countPendingBySubject(input.pendingProposalItems)
  const nodes: CatalogNode[] = []

  for (const [type, items] of Object.entries(ontologyEntities)) {
    const nodeType = normalizeNodeType(type)
    if (!nodeType || !Array.isArray(items)) continue

    for (const item of items as Record<string, unknown>[]) {
      const ref = resolveNodeRef(item)
      if (!ref) continue
      const facts = projectionFacts[ref] || {}
      nodes.push({
        ref,
        id: String(item.id || ref),
        type: nodeType,
        label: String(item.name || item.primary_alias || ref),
        aliases: Array.isArray(item.aliases) ? item.aliases.map(String) : [],
        raw: {
          ...projectionEntities[ref]?.attributes,
          ...item,
        },
        facts,
        presence: presence[ref] || null,
        relationCount: relations.filter((relation) => relation.source_ref === ref || relation.target_ref === ref).length,
        factCount: Object.keys(facts).length,
        pendingCount: pendingBySubject[ref] || 0,
      })
    }
  }

  return nodes.sort((a, b) => a.label.localeCompare(b.label, 'zh-Hans-CN'))
}

export function filterCatalogNodes(
  nodes: CatalogNode[],
  filters: { nodeType: AthenaNodeTypeFilter; search: string },
) {
  const search = filters.search.trim().toLowerCase()
  return nodes.filter((node) => {
    const matchesType = filters.nodeType === 'all' || filters.nodeType === node.type
    const matchesSearch = !search || [
      node.ref,
      node.label,
      ...node.aliases,
      JSON.stringify(node.raw),
      JSON.stringify(node.facts),
    ].some((value) => value.toLowerCase().includes(search))
    return matchesType && matchesSearch
  })
}

export function normalizeRelations(relations: unknown[]): CatalogRelation[] {
  return relations.map((relation) => {
    const item = relation as CatalogRelation
    return {
      ...item,
      source_ref: item.source_ref || item.source_entity_ref,
      target_ref: item.target_ref || item.target_entity_ref,
    }
  })
}

function countPendingBySubject(items: ProposalItem[]) {
  const counts: Record<string, number> = {}
  for (const item of items || []) {
    if (item.item_status !== 'pending') continue
    counts[item.subject_ref] = (counts[item.subject_ref] || 0) + 1
  }
  return counts
}

function normalizeNodeType(type: string): CatalogNodeType | null {
  if (type === 'characters') return 'characters'
  if (type === 'locations') return 'locations'
  if (type === 'factions') return 'factions'
  if (type === 'artifacts' || type === 'items') return 'items'
  if (type === 'resources') return 'resources'
  if (type === 'concepts') return 'concepts'
  return null
}

function resolveNodeRef(item: Record<string, unknown>) {
  return String(
    item.id ||
    item.character_id ||
    item.location_id ||
    item.faction_id ||
    item.artifact_id ||
    item.resource_id ||
    item.canonical_id ||
    '',
  )
}
```

- [ ] **Step 4: Run node model tests and verify pass**

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/catalog/catalogNodeModel.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit model**

```bash
git add frontend/src/components/athena/catalog/catalogNodeModel.ts frontend/src/components/athena/catalog/catalogNodeModel.test.ts
git commit -m "feat: normalize athena catalog nodes"
```

## Task 6: Catalog Components

**Files:**

- Create: `frontend/src/components/athena/catalog/CatalogWorkbench.vue`
- Create: `frontend/src/components/athena/catalog/CatalogNodeList.vue`
- Create: `frontend/src/components/athena/catalog/CatalogNodeDetail.vue`
- Create: `frontend/src/components/athena/catalog/CatalogContextRail.vue`
- Create: `frontend/src/components/athena/catalog/CatalogGraphPanel.vue`
- Create: `frontend/src/components/athena/catalog/CatalogWorkbench.test.ts`
- Create: `frontend/src/components/athena/catalog/CatalogNodeDetail.test.ts`

- [ ] **Step 1: Write catalog workbench test**

Create `frontend/src/components/athena/catalog/CatalogWorkbench.test.ts`:

```ts
// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CatalogWorkbench from './CatalogWorkbench.vue'
import type { AthenaOntology, WorldProjection } from '../../../api/types'

const ontology = {
  entities: {
    characters: [{ id: 'char.linche', name: '林澈', role_type: '主角', core_drives: ['查清旧案'] }],
    locations: [{ id: 'loc.lighthouse', name: '旧灯塔', location_type: '地标' }],
  },
  relations: [{ id: 'rel-1', source_ref: 'char.linche', target_ref: 'loc.lighthouse', relation_type: '常驻' }],
  rules: [{ id: 'rule-1', rule_id: 'rule.tide', description: '潮汐会吞没记忆' }],
  setup_summary: null,
  profile_version: 1,
} as AthenaOntology

const projection = {
  view_type: 'current_truth',
  entities: {},
  relations: {},
  presence: { 'char.linche': { location_ref: 'loc.lighthouse', presence_status: 'active' } },
  occurred_events: {},
  event_links: {},
  facts: { 'char.linche': { hidden_truth: '父亲失踪与潮汐门有关' } },
} as WorldProjection

describe('CatalogWorkbench', () => {
  it('renders nodes and selects the first matching node', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection,
        pendingProposalItems: [],
        nodeType: 'characters',
        view: 'nodes',
      },
    })

    expect(wrapper.text()).toContain('林澈')
    expect(wrapper.text()).toContain('完整节点信息')
    expect(wrapper.text()).toContain('父亲失踪与潮汐门有关')
    expect(wrapper.text()).toContain('关系摘要')
  })

  it('renders rules view', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection,
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'rules',
      },
    })

    expect(wrapper.text()).toContain('规则约束')
    expect(wrapper.text()).toContain('潮汐会吞没记忆')
  })
})
```

- [ ] **Step 2: Write node detail test**

Create `frontend/src/components/athena/catalog/CatalogNodeDetail.test.ts`:

```ts
// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CatalogNodeDetail from './CatalogNodeDetail.vue'
import type { CatalogNode } from './catalogNodeModel'

const node: CatalogNode = {
  ref: 'char.linche',
  id: 'char.linche',
  type: 'characters',
  label: '林澈',
  aliases: ['守夜人'],
  raw: {
    role_type: '主角',
    core_drives: ['查清旧案'],
    core_fears: ['记忆被潮汐吞没'],
    base_capabilities: ['读取潮痕残响'],
    hidden_truths: ['父亲失踪与潮汐门有关'],
  },
  facts: { identity: '旧灯塔守夜人' },
  presence: { location_ref: 'loc.lighthouse', presence_status: 'active' },
  relationCount: 2,
  factCount: 1,
  pendingCount: 1,
}

describe('CatalogNodeDetail', () => {
  it('renders complete layered node information', () => {
    const wrapper = mount(CatalogNodeDetail, { props: { node } })

    expect(wrapper.text()).toContain('林澈')
    expect(wrapper.text()).toContain('守夜人')
    expect(wrapper.text()).toContain('创作理解')
    expect(wrapper.text()).toContain('查清旧案')
    expect(wrapper.text()).toContain('事实账本')
    expect(wrapper.text()).toContain('identity')
    expect(wrapper.text()).toContain('待审 1')
  })
})
```

- [ ] **Step 3: Run catalog component tests and verify failure**

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/catalog/CatalogWorkbench.test.ts src/components/athena/catalog/CatalogNodeDetail.test.ts
```

Expected: FAIL because components do not exist.

- [ ] **Step 4: Implement `CatalogNodeList.vue`**

Create a left rail with `nodeType`, search, and selection:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AthenaNodeTypeFilter } from '../../../views/athenaNavigation'
import type { CatalogNode } from './catalogNodeModel'
import { filterCatalogNodes } from './catalogNodeModel'

const props = defineProps<{
  nodes: CatalogNode[]
  nodeType: AthenaNodeTypeFilter
  selectedRef: string | null
}>()

const emit = defineEmits<{
  select: [nodeRef: string]
  filterType: [nodeType: AthenaNodeTypeFilter]
}>()

const search = ref('')
const typeOptions: { key: AthenaNodeTypeFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'characters', label: '角色' },
  { key: 'locations', label: '地点' },
  { key: 'factions', label: '势力' },
  { key: 'items', label: '物品' },
  { key: 'resources', label: '资源' },
  { key: 'concepts', label: '概念' },
]

const visibleNodes = computed(() => filterCatalogNodes(props.nodes, { nodeType: props.nodeType, search: search.value }))
</script>

<template>
  <aside class="catalog-node-list">
    <div class="catalog-node-list__filters">
      <button
        v-for="option in typeOptions"
        :key="option.key"
        class="catalog-node-list__filter"
        :class="{ 'catalog-node-list__filter--active': nodeType === option.key }"
        @click="emit('filterType', option.key)"
      >
        {{ option.label }}
      </button>
    </div>
    <input v-model="search" class="catalog-node-list__search" aria-label="搜索节点、别名、事实" />
    <button
      v-for="node in visibleNodes"
      :key="node.ref"
      class="catalog-node-list__item"
      :class="{ 'catalog-node-list__item--active': selectedRef === node.ref }"
      @click="emit('select', node.ref)"
    >
      <strong>{{ node.label }}</strong>
      <span>{{ node.factCount }} 事实 · {{ node.relationCount }} 关系 · {{ node.pendingCount }} 待审</span>
    </button>
    <div v-if="visibleNodes.length === 0" class="catalog-node-list__empty">暂无匹配节点</div>
  </aside>
</template>
```

Add scoped styles using existing variables: `display: flex`, `gap: var(--space-2)`, borders with `var(--color-border)`, active state with `var(--color-brand-light)`.

- [ ] **Step 5: Implement `CatalogNodeDetail.vue`**

Create a layered detail panel:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { CatalogNode } from './catalogNodeModel'

const props = defineProps<{ node: CatalogNode | null }>()

const coreSummary = computed(() => {
  const raw = props.node?.raw || {}
  return [
    { label: '定位', value: raw.role_type || raw.location_type || raw.faction_type || raw.artifact_type || raw.resource_type || raw.rule_type || props.node?.type },
    { label: '动机/目标', value: raw.core_drives || raw.mission_or_doctrine || raw.function_summary },
    { label: '限制/危险', value: raw.core_fears || raw.hazards || raw.usage_constraints || raw.constraints },
    { label: '隐藏信息', value: raw.hidden_truths || raw.hidden_agenda || raw.risk_or_side_effects },
  ].filter((item) => item.value != null && item.value !== '')
})

function formatValue(value: unknown) {
  if (Array.isArray(value)) return value.join('、')
  if (value && typeof value === 'object') return JSON.stringify(value)
  return String(value ?? '')
}
</script>

<template>
  <section class="catalog-node-detail">
    <div v-if="!node" class="catalog-node-detail__empty">选择一个节点查看完整信息</div>
    <template v-else>
      <header class="catalog-node-detail__header">
        <span class="catalog-node-detail__eyebrow">{{ node.ref }} · {{ node.type }}</span>
        <h2>{{ node.label }}</h2>
        <div class="catalog-node-detail__badges">
          <span>{{ node.factCount }} 事实</span>
          <span>{{ node.relationCount }} 关系</span>
          <span>待审 {{ node.pendingCount }}</span>
        </div>
      </header>

      <section class="catalog-node-detail__section">
        <h3>完整节点信息</h3>
        <div class="catalog-node-detail__summary-grid">
          <div v-for="item in coreSummary" :key="item.label" class="catalog-node-detail__summary-item">
            <span>{{ item.label }}</span>
            <strong>{{ formatValue(item.value) }}</strong>
          </div>
        </div>
      </section>

      <section class="catalog-node-detail__section">
        <h3>创作理解</h3>
        <div class="catalog-node-detail__field-grid">
          <div v-for="[key, value] in Object.entries(node.raw)" :key="key" class="catalog-node-detail__field">
            <span>{{ key }}</span>
            <strong>{{ formatValue(value) }}</strong>
          </div>
        </div>
      </section>

      <section class="catalog-node-detail__section">
        <h3>事实账本</h3>
        <div v-if="Object.keys(node.facts).length === 0" class="catalog-node-detail__empty-row">暂无确认事实</div>
        <div v-for="[key, value] in Object.entries(node.facts)" :key="key" class="catalog-node-detail__fact">
          <span>{{ key }}</span>
          <strong>{{ formatValue(value) }}</strong>
        </div>
      </section>
    </template>
  </section>
</template>
```

Use scoped styles to create a scrollable center panel, compact field grid, and clear section separators.

- [ ] **Step 6: Implement context rail, graph panel, and workbench shell**

`CatalogContextRail.vue` props:

```ts
defineProps<{
  node: CatalogNode | null
  relations: CatalogRelation[]
}>()
```

Render four sections with exact headings:

```text
关系摘要
时间与叙事
真相/认知状态
待审变更
```

`CatalogGraphPanel.vue` props:

```ts
defineProps<{
  relations: CatalogRelation[]
}>()
```

Render relation rows as a Phase 1 graph shell with heading `图谱` and relation count.

`CatalogWorkbench.vue` props:

```ts
defineProps<{
  ontology: AthenaOntology | null
  projection: WorldProjection | null
  pendingProposalItems: ProposalItem[]
  nodeType: AthenaNodeTypeFilter
  view: AthenaCatalogView
}>()
```

The workbench should:

- Build nodes with `buildCatalogNodes`.
- Select the first visible node when selected node is missing.
- Emit `filterType` when the left rail filter changes.
- Render `CatalogNodeList + CatalogNodeDetail + CatalogContextRail` for `view === 'nodes'`.
- Render `CatalogGraphPanel` for `view === 'graph'`.
- Render `RuleList` for `view === 'rules'`.

- [ ] **Step 7: Run catalog tests and verify pass**

Run:

```bash
cd frontend
npm run test:unit -- src/components/athena/catalog/CatalogWorkbench.test.ts src/components/athena/catalog/CatalogNodeDetail.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit catalog components**

```bash
git add frontend/src/components/athena/catalog
git commit -m "feat: add athena catalog workbench"
```

## Task 7: Athena View Integration

**Files:**

- Modify: `frontend/src/views/AthenaView.vue`
- Modify: `frontend/src/components/athena/AthenaOverview.vue`
- Modify: `frontend/src/components/athena/AthenaOverview.test.ts`

- [ ] **Step 1: Update overview next action tests**

Modify the existing `AthenaOverview.test.ts` expected navigation:

```ts
expect(wrapper.emitted('navigate')).toEqual([['review']])
```

for `review_proposals`, and add:

```ts
it('maps inspect projection to the truth section', async () => {
  const wrapper = mount(AthenaOverview, {
    props: {
      dashboard: {
        project_profile: null,
        metrics: { entity_count: 0, fact_count: 0, presence_count: 0, event_count: 0, pending_bundle_count: 0, pending_item_count: 0 },
        next_action: { action: 'inspect_projection', label: '检查真相投影' },
      },
      loading: false,
    },
  })

  await wrapper.get('[data-testid="athena-overview-next-action"]').trigger('click')

  expect(wrapper.emitted('navigate')).toEqual([['truth']])
})
```

- [ ] **Step 2: Update overview component emits**

Change `AthenaOverview.vue` from `AthenaSection` to `AthenaPrimarySection` and map:

```ts
const nextActionSection = computed<AthenaPrimarySection>(() => {
  const action = props.dashboard?.next_action.action
  if (action === 'review_proposals') return 'review'
  if (action === 'inspect_projection') return 'truth'
  return 'catalog'
})
```

- [ ] **Step 3: Integrate route state in AthenaView**

In `AthenaView.vue`:

- Import `athenaPrimaryNav`, `buildAthenaRoute`, `resolveAthenaRoute`.
- Import `CatalogWorkbench`.
- Replace `sections` with `athenaPrimaryNav`.
- Replace `activeSection` with `routeState`.
- On legacy route, call `router.replace(buildAthenaRoute(pid.value, routeState.value))`.
- On `navigateSection(section)`, build route with the primary section default view.

Core code shape:

```ts
const routeState = computed(() => resolveAthenaRoute(route.params.section as string | undefined, route.query))

watch(routeState, (state) => {
  ui.setAthenaState({ section: state.section, view: state.view, nodeType: state.nodeType })
  if (state.isLegacy) void router.replace(buildAthenaRoute(pid.value, state))
  void loadRouteData(state)
}, { immediate: true })

function navigateSection(section: AthenaPrimarySection) {
  const navItem = athenaPrimaryNav.find((item) => item.section === section)
  if (!navItem) return
  router.push(buildAthenaRoute(pid.value, {
    section,
    view: navItem.defaultView,
    nodeType: 'all',
    tool: null,
    panel: null,
    isLegacy: false,
  }))
}

function updateCatalogType(nodeType: AthenaNodeTypeFilter) {
  router.push(buildAthenaRoute(pid.value, {
    ...routeState.value,
    section: 'catalog',
    view: 'nodes',
    nodeType,
    isLegacy: false,
  }))
}
```

Template mapping:

```vue
<AthenaSubnav
  :items="athenaPrimaryNav"
  :active-section="routeState.section"
  :can-import-setup="canImportSetup"
  :has-latest-chapter="Boolean(latestChapterIndex)"
  @navigate="navigateSection"
  @import-setup="importSetup"
  @analyze-latest-chapter="analyzeLatestChapter"
  @open-chat="chatOpen = true"
/>
```

Render catalog:

```vue
<CatalogWorkbench
  v-else-if="routeState.section === 'catalog'"
  :ontology="athena.ontology"
  :projection="worldModel.projection"
  :pending-proposal-items="worldModel.proposalItems || []"
  :node-type="routeState.nodeType"
  :view="routeState.view === 'graph' || routeState.view === 'rules' ? routeState.view : 'nodes'"
  @filter-type="updateCatalogType"
/>
```

Render existing sections through new IA:

```vue
<ProjectionViewer v-else-if="routeState.section === 'truth' && routeState.view === 'projection'" :projection="worldModel.projection" />
<SubjectKnowledgePanel v-else-if="routeState.section === 'truth' && routeState.view === 'knowledge'" ... />
<TimelineView v-else-if="routeState.section === 'narrative' && routeState.view === 'timeline'" ... />
<ProposalWorkbench v-else-if="routeState.section === 'review' && routeState.view === 'proposals'" :project-id="pid" />
<ConsistencyList v-else-if="routeState.section === 'review' && routeState.view === 'conflicts'" ... />
```

For Phase 1 subviews that are routed but not redesigned in this plan, use concise state blocks:

```vue
<div v-else class="athena-view__empty-state">
  {{ routeState.section }} / {{ routeState.view }} 正在接入现有数据视图
</div>
```

- [ ] **Step 4: Run targeted tests and build**

Run:

```bash
cd frontend
npm run test:unit -- src/views/athenaNavigation.test.ts src/views/athenaSectionLoader.test.ts src/components/athena/AthenaSubnav.test.ts src/components/athena/AthenaOverview.test.ts src/components/athena/catalog/CatalogWorkbench.test.ts src/components/athena/catalog/CatalogNodeDetail.test.ts
npm run build
```

Expected: targeted tests PASS, build PASS.

- [ ] **Step 5: Commit Athena integration**

```bash
git add frontend/src/views/AthenaView.vue frontend/src/views/athenaSectionLoader.ts frontend/src/views/athenaSectionLoader.test.ts frontend/src/components/athena/AthenaSubnav.vue frontend/src/components/athena/AthenaSubnav.test.ts frontend/src/components/athena/AthenaOverview.vue frontend/src/components/athena/AthenaOverview.test.ts frontend/src/stores/ui.ts
git commit -m "feat: integrate athena information architecture"
```

## Task 8: Browser Verification

**Files:**

- No source files expected.

- [ ] **Step 1: Ensure dev servers are running**

Backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

Expected:

- Backend serves `http://127.0.0.1:8000`.
- Frontend serves `http://localhost:5173`.

- [ ] **Step 2: Verify Athena catalog in browser**

Open an existing project:

```bash
agent-browser open http://127.0.0.1:5173/projects/<project-id>/athena/catalog?view=nodes&type=characters
agent-browser wait --load networkidle
agent-browser snapshot -i -c -d 3
agent-browser console
agent-browser errors
agent-browser network requests --filter "world-model"
```

Expected:

- Page shows `设定库`.
- Node list shows character nodes when character data exists.
- No page errors.
- Network requests for world-model/ontology return 200.

- [ ] **Step 3: Verify legacy route redirect**

```bash
agent-browser open http://127.0.0.1:5173/projects/<project-id>/athena/characters
agent-browser wait --load networkidle
agent-browser get url
```

Expected URL:

```text
http://127.0.0.1:5173/projects/<project-id>/athena/catalog?view=nodes&type=characters
```

- [ ] **Step 4: Final verification**

Run:

```bash
cd frontend
npm run test:unit
npm run build
```

Expected: all frontend unit tests PASS, build PASS.

- [ ] **Step 5: Commit verification-only adjustments if needed**

If verification exposes small UI or route issues, fix only those issues, rerun Step 4, then commit:

```bash
git add frontend/src
git commit -m "fix: stabilize athena catalog navigation"
```

If no source changes are needed, do not create an empty commit.

## Completion Criteria

- Athena left navigation shows exactly five primary entries: `总览 / 设定库 / 叙事脉络 / 真相认知 / 待审变更`.
- Old entity routes redirect to Set Library node filters.
- Set Library uses three-column layout.
- Node detail shows complete layered information from ontology, projection facts, relations, presence, and pending counts.
- Existing projection, subject knowledge, timeline, proposals, and consistency views remain reachable through the new IA.
- `npm run test:unit` passes.
- `npm run build` passes.
