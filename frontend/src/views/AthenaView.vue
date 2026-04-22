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
.athena-view__tabs { display: flex; gap: 0; }
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
