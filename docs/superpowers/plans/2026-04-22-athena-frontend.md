# Athena Frontend Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Athena frontend interface — a world monitoring dashboard with three-layer tabs (Ontology/State/Evolution) and a mini dialog sidebar, accessible via `/projects/:id/athena`.

**Architecture:** New `AthenaView.vue` route with `AthenaShell` layout (main content + mini dialog sidebar). New `stores/athena.ts` Pinia store fetches from `/athena/*` API endpoints. Three tab panels reuse existing world model components where possible. Mini dialog uses the chat store with `dialogType="athena"`. Top nav updated to show Hermes/Athena toggle when inside a project.

**Tech Stack:** Vue 3 (Composition API), Pinia, TypeScript, vue-router, Tailwind-adjacent custom CSS

---

### Task 1: Athena API Client Methods

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/types.ts`

- [ ] **Step 1: Add Athena types to `frontend/src/api/types.ts`**

Append after the existing world model types:

```typescript
export interface AthenaOntology {
  entities: Record<string, { id: string; name: string }[]>
  relations: { id: string; source_ref: string; target_ref: string; relation_type: string }[]
  rules: { id: string; rule_id: string; description: string }[]
  setup_summary: {
    characters: unknown
    world_building: unknown
    core_concept: unknown
  } | null
  profile_version: number | null
}

export interface AthenaTimeline {
  anchors: { id: string; anchor_id: string; chapter_index: number; intra_chapter_seq: number; label: string }[]
  events: { id: string; event_id: string; chapter_index: number; intra_chapter_seq: number; event_type: string; description: string }[]
}

export interface AthenaEvolutionPlan {
  outline: { id: string; status: string; total_chapters: number; chapters: unknown; plotlines: unknown } | null
  storyline: { id: string; status: string; plotlines: unknown; foreshadowing: unknown } | null
}
```

- [ ] **Step 2: Add Athena API methods to `frontend/src/api/client.ts`**

Add `AthenaOntology`, `AthenaTimeline`, `AthenaEvolutionPlan` to the import from `./types`.

Add these methods after the existing world model methods:

```typescript
getAthenaOntology: (id: string) =>
  request<AthenaOntology>(`/projects/${id}/athena/ontology`),
getAthenaState: (id: string) =>
  request<WorldModelOverview>(`/projects/${id}/athena/state`),
getAthenaTimeline: (id: string) =>
  request<AthenaTimeline>(`/projects/${id}/athena/state/timeline`),
getAthenaEvolutionPlan: (id: string) =>
  request<AthenaEvolutionPlan>(`/projects/${id}/athena/evolution/plan`),
getAthenaEvolutionProposals: (id: string, params?: { offset?: number; limit?: number; bundle_status?: string }) => {
  const query = new URLSearchParams()
  if (params?.offset !== undefined) query.set('offset', String(params.offset))
  if (params?.limit !== undefined) query.set('limit', String(params.limit))
  if (params?.bundle_status) query.set('bundle_status', params.bundle_status)
  const qs = query.toString()
  return request<PaginatedProposalBundles>(`/projects/${id}/athena/evolution/proposals${qs ? `?${qs}` : ''}`)
},
sendAthenaChat: (id: string, text: string) =>
  request<ChatResponse>(`/projects/${id}/athena/dialog/chat`, {
    method: 'POST',
    body: JSON.stringify({ project_id: id, input_type: 'text', text }),
  }),
getAthenaMessages: (id: string) =>
  request<DialogMessage[]>(`/projects/${id}/athena/dialog/messages`),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat: add Athena API client methods and types"
```

---

### Task 2: Athena Pinia Store

**Files:**
- Create: `frontend/src/stores/athena.ts`

- [ ] **Step 1: Create the store**

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type {
  AthenaEvolutionPlan,
  AthenaOntology,
  AthenaTimeline,
  DialogMessage,
  PaginatedProposalBundles,
  WorldProjection,
} from '../api/types'

function toErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

export const useAthenaStore = defineStore('athena', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  const ontology = ref<AthenaOntology | null>(null)
  const projection = ref<WorldProjection | null>(null)
  const timeline = ref<AthenaTimeline | null>(null)
  const evolutionPlan = ref<AthenaEvolutionPlan | null>(null)
  const proposals = ref<PaginatedProposalBundles | null>(null)

  const messages = ref<DialogMessage[]>([])
  const chatLoading = ref(false)

  async function loadOntology(projectId: string) {
    try {
      ontology.value = await api.getAthenaOntology(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadState(projectId: string) {
    try {
      const overview = await api.getAthenaState(projectId)
      projection.value = overview.projection
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadTimeline(projectId: string) {
    try {
      timeline.value = await api.getAthenaTimeline(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadEvolutionPlan(projectId: string) {
    try {
      evolutionPlan.value = await api.getAthenaEvolutionPlan(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadProposals(projectId: string, params?: { offset?: number; limit?: number; bundle_status?: string }) {
    try {
      proposals.value = await api.getAthenaEvolutionProposals(projectId, params)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadMessages(projectId: string) {
    try {
      messages.value = await api.getAthenaMessages(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function sendChat(projectId: string, text: string) {
    chatLoading.value = true
    try {
      await api.sendAthenaChat(projectId, text)
      await loadMessages(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      chatLoading.value = false
    }
  }

  function reset() {
    ontology.value = null
    projection.value = null
    timeline.value = null
    evolutionPlan.value = null
    proposals.value = null
    messages.value = []
    error.value = null
  }

  return {
    loading,
    error,
    ontology,
    projection,
    timeline,
    evolutionPlan,
    proposals,
    messages,
    chatLoading,
    loadOntology,
    loadState,
    loadTimeline,
    loadEvolutionPlan,
    loadProposals,
    loadMessages,
    sendChat,
    reset,
  }
})
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/athena.ts
git commit -m "feat: add Athena Pinia store"
```


---

### Task 3: Athena Mini Dialog Component

**Files:**
- Create: `frontend/src/components/athena/AthenaMiniDialog.vue`

- [ ] **Step 1: Create the mini dialog component**

```vue
<template>
  <aside class="athena-dialog">
    <header class="athena-dialog__header">
      <span class="athena-dialog__title">⏣ Athena 对话</span>
      <span class="athena-dialog__hint">世界构建专用</span>
    </header>
    <div ref="scrollArea" class="athena-dialog__messages">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="athena-dialog__bubble"
        :class="msg.role === 'user' ? 'is-user' : 'is-assistant'"
      >
        {{ msg.content }}
      </div>
      <div v-if="loading" class="athena-dialog__bubble is-assistant">思考中...</div>
    </div>
    <form class="athena-dialog__input" @submit.prevent="onSend">
      <input
        v-model="text"
        placeholder="讨论世界设定..."
        :disabled="loading"
      >
      <button type="submit" :disabled="!text.trim() || loading">发送</button>
    </form>
  </aside>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { DialogMessage } from '../../api/types'

const props = defineProps<{
  messages: DialogMessage[]
  loading: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const text = ref('')
const scrollArea = ref<HTMLElement | null>(null)

watch(() => props.messages.length, async () => {
  await nextTick()
  if (scrollArea.value) {
    scrollArea.value.scrollTop = scrollArea.value.scrollHeight
  }
})

function onSend() {
  const t = text.value.trim()
  if (!t) return
  emit('send', t)
  text.value = ''
}
</script>

<style scoped>
.athena-dialog {
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(111, 69, 31, 0.1);
  height: 100%;
}

.athena-dialog__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.1);
}

.athena-dialog__title {
  color: var(--accent-strong);
  font-size: 0.8rem;
  font-weight: 700;
}

.athena-dialog__hint {
  margin-left: auto;
  color: var(--ink-muted);
  font-size: 0.68rem;
}

.athena-dialog__messages {
  flex: 1;
  overflow-y: auto;
  padding: 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.athena-dialog__bubble {
  max-width: 90%;
  border-radius: 0.7rem;
  padding: 0.5rem 0.65rem;
  font-size: 0.76rem;
  line-height: 1.5;
  word-break: break-word;
}

.athena-dialog__bubble.is-user {
  align-self: flex-end;
  background: rgba(111, 69, 31, 0.06);
  color: var(--ink-strong);
}

.athena-dialog__bubble.is-assistant {
  align-self: flex-start;
  background: rgba(99, 102, 241, 0.08);
  color: var(--ink-strong);
}

.athena-dialog__input {
  display: flex;
  gap: 0.4rem;
  padding: 0.55rem 0.65rem;
  border-top: 1px solid rgba(111, 69, 31, 0.1);
}

.athena-dialog__input input {
  flex: 1;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 0.6rem;
  padding: 0.4rem 0.6rem;
  background: rgba(255, 252, 246, 0.92);
  color: var(--ink-strong);
  font-size: 0.76rem;
}

.athena-dialog__input button {
  border: none;
  border-radius: 0.6rem;
  padding: 0.4rem 0.75rem;
  background: var(--accent-strong);
  color: #fff;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}

.athena-dialog__input button:disabled {
  opacity: 0.5;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/athena/AthenaMiniDialog.vue
git commit -m "feat: add AthenaMiniDialog component"
```

---

### Task 4: Athena Tab Panels — Ontology, State, Evolution

**Files:**
- Create: `frontend/src/components/athena/AthenaOntologyPanel.vue`
- Create: `frontend/src/components/athena/AthenaStatePanel.vue`
- Create: `frontend/src/components/athena/AthenaEvolutionPanel.vue`

- [ ] **Step 1: Create AthenaOntologyPanel.vue**

```vue
<template>
  <div class="athena-panel">
    <div v-if="ontology" class="athena-panel__grid">
      <section class="athena-panel__card">
        <h4>角色实体</h4>
        <ul v-if="ontology.entities.characters?.length" class="athena-panel__list">
          <li v-for="c in ontology.entities.characters" :key="c.id">{{ c.name }}</li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card">
        <h4>地点</h4>
        <ul v-if="ontology.entities.locations?.length" class="athena-panel__list">
          <li v-for="loc in ontology.entities.locations" :key="loc.id">{{ loc.name }}</li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card">
        <h4>关系图谱</h4>
        <ul v-if="ontology.relations.length" class="athena-panel__list">
          <li v-for="r in ontology.relations" :key="r.id">
            {{ r.source_ref }} → {{ r.relation_type }} → {{ r.target_ref }}
          </li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card">
        <h4>世界规则</h4>
        <ul v-if="ontology.rules.length" class="athena-panel__list">
          <li v-for="r in ontology.rules" :key="r.id">{{ r.description }}</li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
    </div>
    <p v-else class="athena-panel__empty">加载中...</p>
  </div>
</template>

<script setup lang="ts">
import type { AthenaOntology } from '../../api/types'

defineProps<{
  ontology: AthenaOntology | null
}>()
</script>
```

- [ ] **Step 2: Create AthenaStatePanel.vue**

```vue
<template>
  <div class="athena-panel">
    <div v-if="projection" class="athena-panel__grid">
      <section class="athena-panel__card">
        <h4>实体状态</h4>
        <ul v-if="entityEntries.length" class="athena-panel__list">
          <li v-for="[ref, entity] in entityEntries" :key="ref">
            <strong>{{ ref }}</strong> — {{ formatAttrs(entity.attributes) }}
          </li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card">
        <h4>关键事实</h4>
        <ul v-if="factEntries.length" class="athena-panel__list">
          <li v-for="[subj, facts] in factEntries" :key="subj">
            <strong>{{ subj }}</strong> — {{ formatAttrs(facts) }}
          </li>
        </ul>
        <p v-else class="athena-panel__empty">无</p>
      </section>
      <section class="athena-panel__card" v-if="timeline">
        <h4>时间线 ({{ timeline.events.length }} 事件)</h4>
        <ul v-if="timeline.events.length" class="athena-panel__list">
          <li v-for="e in timeline.events.slice(0, 15)" :key="e.id">
            第{{ e.chapter_index }}章 — {{ e.description }}
          </li>
        </ul>
      </section>
    </div>
    <p v-else class="athena-panel__empty">加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AthenaTimeline, WorldProjection } from '../../api/types'

const props = defineProps<{
  projection: WorldProjection | null
  timeline: AthenaTimeline | null
}>()

const entityEntries = computed(() => props.projection ? Object.entries(props.projection.entities).slice(0, 10) : [])
const factEntries = computed(() => props.projection ? Object.entries(props.projection.facts).slice(0, 10) : [])

function formatAttrs(val: Record<string, unknown>) {
  return Object.entries(val).map(([k, v]) => `${k}: ${String(v)}`).join(' / ')
}
</script>
```

- [ ] **Step 3: Create AthenaEvolutionPanel.vue**

```vue
<template>
  <div class="athena-panel">
    <div class="athena-panel__grid">
      <section class="athena-panel__card">
        <h4>大纲</h4>
        <div v-if="evolutionPlan?.outline">
          <p class="athena-panel__meta">状态：{{ evolutionPlan.outline.status }} · {{ evolutionPlan.outline.total_chapters }} 章</p>
        </div>
        <p v-else class="athena-panel__empty">未生成</p>
      </section>
      <section class="athena-panel__card">
        <h4>故事线</h4>
        <div v-if="evolutionPlan?.storyline">
          <p class="athena-panel__meta">状态：{{ evolutionPlan.storyline.status }}</p>
        </div>
        <p v-else class="athena-panel__empty">未生成</p>
      </section>
      <section class="athena-panel__card">
        <h4>待审提案</h4>
        <div v-if="proposals">
          <p class="athena-panel__meta">共 {{ proposals.total }} 个 bundle</p>
          <ul v-if="proposals.items.length" class="athena-panel__list">
            <li v-for="b in proposals.items" :key="b.id">
              {{ b.title }} — {{ b.bundle_status }}
            </li>
          </ul>
        </div>
        <p v-else class="athena-panel__empty">加载中...</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AthenaEvolutionPlan, PaginatedProposalBundles } from '../../api/types'

defineProps<{
  evolutionPlan: AthenaEvolutionPlan | null
  proposals: PaginatedProposalBundles | null
}>()
</script>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/athena/AthenaOntologyPanel.vue frontend/src/components/athena/AthenaStatePanel.vue frontend/src/components/athena/AthenaEvolutionPanel.vue
git commit -m "feat: add Athena tab panel components (ontology, state, evolution)"
```

---

### Task 5: AthenaView + Route Registration

**Files:**
- Create: `frontend/src/views/AthenaView.vue`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Create AthenaView.vue**

```vue
<template>
  <div v-if="project.currentProject" class="athena-view">
    <div class="athena-view__main">
      <header class="athena-view__header">
        <span class="athena-view__brand">⏣ Athena</span>
        <nav class="athena-view__tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="athena-view__tab"
            :class="{ 'is-active': activeTab === tab.key }"
            @click="switchTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </nav>
        <span class="athena-view__meta">
          Profile v{{ athena.ontology?.profile_version ?? '—' }}
        </span>
      </header>
      <div class="athena-view__content">
        <AthenaOntologyPanel
          v-if="activeTab === 'ontology'"
          :ontology="athena.ontology"
        />
        <AthenaStatePanel
          v-else-if="activeTab === 'state'"
          :projection="athena.projection"
          :timeline="athena.timeline"
        />
        <AthenaEvolutionPanel
          v-else-if="activeTab === 'evolution'"
          :evolution-plan="athena.evolutionPlan"
          :proposals="athena.proposals"
        />
      </div>
    </div>
    <AthenaMiniDialog
      :messages="athena.messages"
      :loading="athena.chatLoading"
      @send="onSend"
    />
  </div>
  <div v-else class="athena-view__loading">加载中...</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useAthenaStore } from '../stores/athena'
import AthenaOntologyPanel from '../components/athena/AthenaOntologyPanel.vue'
import AthenaStatePanel from '../components/athena/AthenaStatePanel.vue'
import AthenaEvolutionPanel from '../components/athena/AthenaEvolutionPanel.vue'
import AthenaMiniDialog from '../components/athena/AthenaMiniDialog.vue'

const tabs = [
  { key: 'ontology', label: '本体' },
  { key: 'state', label: '状态' },
  { key: 'evolution', label: '演化' },
] as const

type TabKey = typeof tabs[number]['key']

const route = useRoute()
const project = useProjectStore()
const athena = useAthenaStore()
const pid = computed(() => route.params.id as string)
const activeTab = ref<TabKey>('ontology')

onMounted(() => void initialize(pid.value))

watch(pid, (next, prev) => {
  if (next && next !== prev) void initialize(next)
})

async function initialize(projectId: string) {
  athena.reset()
  await project.loadProject(projectId)
  await Promise.all([
    athena.loadOntology(projectId),
    athena.loadMessages(projectId),
  ])
}

async function switchTab(tab: TabKey) {
  activeTab.value = tab
  const id = pid.value
  if (tab === 'ontology' && !athena.ontology) await athena.loadOntology(id)
  if (tab === 'state') {
    if (!athena.projection) await athena.loadState(id)
    if (!athena.timeline) await athena.loadTimeline(id)
  }
  if (tab === 'evolution') {
    if (!athena.evolutionPlan) await athena.loadEvolutionPlan(id)
    if (!athena.proposals) await athena.loadProposals(id)
  }
}

async function onSend(text: string) {
  await athena.sendChat(pid.value, text)
}
</script>

<style scoped>
.athena-view {
  display: grid;
  grid-template-columns: 1fr 320px;
  height: calc(100svh - 5rem);
}

.athena-view__main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.athena-view__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 1rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.1);
}

.athena-view__brand {
  color: var(--accent-strong);
  font-size: 0.92rem;
  font-weight: 700;
}

.athena-view__tabs {
  display: flex;
  gap: 0;
}

.athena-view__tab {
  padding: 0.4rem 0.8rem;
  border: none;
  background: none;
  color: var(--ink-muted);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.athena-view__tab.is-active {
  color: var(--accent-strong);
  border-bottom-color: var(--accent-strong);
}

.athena-view__meta {
  margin-left: auto;
  color: var(--ink-muted);
  font-size: 0.7rem;
}

.athena-view__content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.athena-view__loading {
  padding: 3rem;
  text-align: center;
  color: var(--ink-muted);
}

@media (max-width: 1023px) {
  .athena-view {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 300px;
  }
}
</style>
```

- [ ] **Step 2: Add shared panel styles**

Create `frontend/src/components/athena/athena-panel.css`:

```css
.athena-panel__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
}

.athena-panel__card {
  border: 1px solid rgba(111, 69, 31, 0.1);
  border-radius: 0.8rem;
  padding: 0.85rem;
  background: rgba(255, 252, 246, 0.92);
}

.athena-panel__card h4 {
  margin: 0 0 0.5rem;
  color: var(--accent-strong);
  font-size: 0.82rem;
}

.athena-panel__list {
  display: grid;
  gap: 0.3rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.athena-panel__list li {
  color: var(--ink-strong);
  font-size: 0.76rem;
  line-height: 1.5;
}

.athena-panel__list strong {
  color: var(--accent-strong);
}

.athena-panel__empty {
  color: var(--ink-muted);
  font-size: 0.76rem;
}

.athena-panel__meta {
  color: var(--ink-muted);
  font-size: 0.74rem;
  margin: 0;
}
```

Import this CSS in each panel component by adding to their `<style>` blocks:

Actually, simpler: add `@import './athena-panel.css';` in each panel's `<style>` tag. Or just include the styles inline in each component since they're small. The panels already use these class names — just add the styles to each component's `<style scoped>` block.

Add to each of the three panel components (`AthenaOntologyPanel.vue`, `AthenaStatePanel.vue`, `AthenaEvolutionPanel.vue`):

```vue
<style scoped>
.athena-panel__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.8rem;
}
.athena-panel__card {
  border: 1px solid rgba(111, 69, 31, 0.1);
  border-radius: 0.8rem;
  padding: 0.85rem;
  background: rgba(255, 252, 246, 0.92);
}
.athena-panel__card h4 {
  margin: 0 0 0.5rem;
  color: var(--accent-strong);
  font-size: 0.82rem;
}
.athena-panel__list {
  display: grid;
  gap: 0.3rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.athena-panel__list li {
  color: var(--ink-strong);
  font-size: 0.76rem;
  line-height: 1.5;
}
.athena-panel__list strong { color: var(--accent-strong); }
.athena-panel__empty { color: var(--ink-muted); font-size: 0.76rem; }
.athena-panel__meta { color: var(--ink-muted); font-size: 0.74rem; margin: 0; }
</style>
```

- [ ] **Step 3: Register route in `frontend/src/router/index.ts`**

Add import:

```typescript
import AthenaView from '../views/AthenaView.vue'
```

Add route after the `/projects/:id` route:

```typescript
{
  path: '/projects/:id/athena',
  component: AthenaView,
  meta: {
    shellMode: 'default',
    shellSurface: 'none',
    navSection: 'projects',
  } satisfies AppRouteMeta,
},
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/AthenaView.vue frontend/src/components/athena/ frontend/src/router/index.ts
git commit -m "feat: add AthenaView with route and tab panels"
```

---

### Task 6: Update Top Navigation — Hermes/Athena Toggle

**Files:**
- Modify: `frontend/src/components/layout/AppTopNav.vue`

- [ ] **Step 1: Update AppTopNav to show Hermes/Athena links in project context**

Replace the entire file:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageMeta = computed(() => route.matched[route.matched.length - 1]?.meta ?? {})
const navSection = computed(() => (pageMeta.value.navSection === 'settings' ? 'settings' : 'projects'))

const projectId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : null
})

const isAthenaRoute = computed(() => route.path.endsWith('/athena'))
</script>

<template>
  <header class="app-top-nav">
    <div class="app-top-nav__inner">
      <router-link
        to="/"
        class="app-top-nav__brand"
      >
        <span class="app-top-nav__brand-mark">墨舟</span>
        <span class="app-top-nav__brand-text">创作中枢</span>
      </router-link>
      <nav
        class="app-top-nav__links"
        aria-label="主导航"
      >
        <router-link
          to="/"
          class="app-top-nav__link"
          :class="{ 'is-active': navSection === 'projects' && !projectId }"
        >
          项目
        </router-link>
        <template v-if="projectId">
          <router-link
            :to="`/projects/${projectId}`"
            class="app-top-nav__link app-top-nav__link--hermes"
            :class="{ 'is-active': !!projectId && !isAthenaRoute }"
          >
            ☿ Hermes
          </router-link>
          <router-link
            :to="`/projects/${projectId}/athena`"
            class="app-top-nav__link app-top-nav__link--athena"
            :class="{ 'is-active': isAthenaRoute }"
          >
            ⏣ Athena
          </router-link>
        </template>
        <router-link
          to="/settings"
          class="app-top-nav__link"
          :class="{ 'is-active': navSection === 'settings' }"
        >
          设置
        </router-link>
      </nav>
    </div>
  </header>
</template>
```

Add these styles to the existing `<style scoped>` block:

```css
.app-top-nav__link--hermes.is-active {
  color: var(--accent-strong);
}

.app-top-nav__link--athena.is-active {
  color: var(--accent-strong);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/layout/AppTopNav.vue
git commit -m "feat: add Hermes/Athena toggle to top navigation"
```

---

### Task 7: Verification

- [ ] **Step 1: Type check**

Run: `cd frontend && npx vue-tsc --noEmit`
Expected: PASS

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 3: Run tests**

Run: `cd frontend && npx vitest run`
Expected: PASS

- [ ] **Step 4: Browser verification**

Start dev server and verify:
1. Navigate to a project — top nav shows "☿ Hermes" and "⏣ Athena" links
2. Click "⏣ Athena" — navigates to `/projects/:id/athena`
3. Athena view shows three tabs: 本体 / 状态 / 演化
4. Mini dialog sidebar on the right
5. Click back to "☿ Hermes" — returns to normal workspace

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "chore: cleanup after Athena frontend implementation"
```
