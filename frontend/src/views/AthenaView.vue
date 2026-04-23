<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useAthenaStore } from '../stores/athena'
import { useUiStore, type AthenaSection } from '../stores/ui'
import BaseButton from '../components/base/BaseButton.vue'
import EntityTable from '../components/athena/EntityTable.vue'
import RelationTable from '../components/athena/RelationTable.vue'
import RuleList from '../components/athena/RuleList.vue'
import TimelineView from '../components/athena/TimelineView.vue'
import ProjectionViewer from '../components/athena/ProjectionViewer.vue'
import KnowledgeViewer from '../components/athena/KnowledgeViewer.vue'
import ProposalList from '../components/athena/ProposalList.vue'
import ConsistencyList from '../components/athena/ConsistencyList.vue'
import AthenaChatPanel from '../components/athena/AthenaChatPanel.vue'

interface NavSection {
  label: string
  items: { key: AthenaSection; label: string }[]
}

const sections: NavSection[] = [
  {
    label: '本体',
    items: [
      { key: 'characters', label: '角色' },
      { key: 'locations', label: '地点' },
      { key: 'factions', label: '势力' },
      { key: 'items', label: '物品' },
      { key: 'relations', label: '关系' },
      { key: 'rules', label: '规则' },
    ],
  },
  {
    label: '状态',
    items: [
      { key: 'projection', label: '真相投影' },
      { key: 'timeline', label: '时间线' },
      { key: 'knowledge', label: '主体认知' },
    ],
  },
  {
    label: '演化',
    items: [
      { key: 'outline', label: '大纲' },
      { key: 'storyline', label: '故事线' },
      { key: 'proposals', label: '提案' },
      { key: 'consistency', label: '一致性检查' },
    ],
  },
]
const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const athena = useAthenaStore()
const ui = useUiStore()
const pid = computed(() => route.params.id as string)
const chatOpen = ref(false)

const activeSection = computed<AthenaSection>(() => {
  const routeSection = route.params.section as string | undefined
  if (routeSection && isValidSection(routeSection)) return routeSection as AthenaSection
  return ui.activeAthenaSection
})

function isValidSection(s: string): boolean {
  return sections.some((sec) => sec.items.some((item) => item.key === s))
}

// Entity type mapping for ontology sections
const entityTypeMap: Record<string, string> = {
  characters: 'character',
  locations: 'location',
  factions: 'faction',
  items: 'item',
}

const entitySections = new Set(['characters', 'locations', 'factions', 'items'])

const entities = computed(() => {
  if (!entitySections.has(activeSection.value)) return []
  const type = entityTypeMap[activeSection.value]
  const allEntities = athena.ontology?.entities || []
  return allEntities.filter((e: any) => !type || e.type === type || e.entity_type === type)
})

const relations = computed(() => athena.ontology?.relations || [])
const rules = computed(() => athena.ontology?.rules || [])
const timelineEvents = computed(() => athena.timeline?.events || athena.timeline?.entries || [])
const timelineAnchors = computed(() => athena.timeline?.anchors || [])
const consistencyIssues = computed<any[]>(() => [])

onMounted(() => void initialize(pid.value))

watch(pid, (next, prev) => {
  if (next && next !== prev) void initialize(next)
})

watch(activeSection, (section) => {
  ui.setAthenaSection(section)
  void loadSectionData(section)
})

async function initialize(projectId: string) {
  athena.reset()
  await project.loadProject(projectId)
  await Promise.all([
    athena.loadOntology(projectId),
    athena.loadMessages(projectId),
  ])
  await loadSectionData(activeSection.value)
}

async function loadSectionData(section: AthenaSection) {
  const id = pid.value
  if (entitySections.has(section) || section === 'relations' || section === 'rules') {
    if (!athena.ontology) await athena.loadOntology(id)
  }
  if (section === 'projection') {
    if (!athena.projection) await athena.loadState(id)
  }
  if (section === 'timeline') {
    if (!athena.timeline) await athena.loadTimeline(id)
  }
  if (section === 'knowledge') {
    if (!athena.projection) await athena.loadState(id)
  }
  if (section === 'proposals') {
    if (!athena.proposals) await athena.loadProposals(id)
  }
  if (section === 'outline' || section === 'storyline') {
    if (!athena.evolutionPlan) await athena.loadEvolutionPlan(id)
  }
}

function navigateSection(section: AthenaSection) {
  router.push(`/projects/${pid.value}/athena/${section}`)
}
</script>

<template>
  <div v-if="project.currentProject" class="athena-view">
    <!-- Sub-nav content -->
    <Teleport to="[data-subnav-content]">
      <div class="athena-subnav">
        <div v-for="sec in sections" :key="sec.label" class="athena-subnav__section">
          <div class="athena-subnav__section-label">{{ sec.label }}</div>
          <button
            v-for="item in sec.items"
            :key="item.key"
            class="athena-subnav__item"
            :class="{ 'athena-subnav__item--active': activeSection === item.key }"
            @click="navigateSection(item.key)"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="athena-subnav__divider" />
        <div class="athena-subnav__actions">
          <BaseButton variant="ghost" size="sm" @click="chatOpen = true">
            Athena 对话
          </BaseButton>
        </div>
      </div>
    </Teleport>

    <!-- Main content: detail view based on active section -->
    <div class="athena-view__content">
      <EntityTable
        v-if="entitySections.has(activeSection)"
        :entities="entities"
        :entity-type="entityTypeMap[activeSection]"
      />
      <RelationTable v-else-if="activeSection === 'relations'" :relations="relations" />
      <RuleList v-else-if="activeSection === 'rules'" :rules="rules" />
      <ProjectionViewer v-else-if="activeSection === 'projection'" :projection="athena.projection" />
      <TimelineView
        v-else-if="activeSection === 'timeline'"
        :events="timelineEvents"
        :anchors="timelineAnchors"
      />
      <KnowledgeViewer v-else-if="activeSection === 'knowledge'" :knowledge="athena.projection" />
      <ProposalList v-else-if="activeSection === 'proposals'" :proposals="athena.proposals" />
      <ConsistencyList v-else-if="activeSection === 'consistency'" :issues="consistencyIssues" />
      <div v-else-if="activeSection === 'outline' || activeSection === 'storyline'" class="athena-view__placeholder">
        {{ activeSection === 'outline' ? '大纲' : '故事线' }}数据加载中...
      </div>
    </div>

    <!-- Chat slide-over -->
    <AthenaChatPanel
      :open="chatOpen"
      :project-id="pid"
      @close="chatOpen = false"
    />
  </div>
  <div v-else class="athena-view__loading">加载中...</div>
</template>
<style scoped>
.athena-view {
  height: 100%;
}

.athena-view__content {
  height: 100%;
}

.athena-view__loading,
.athena-view__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

/* Sub-nav styles */
.athena-subnav {
  display: flex;
  flex-direction: column;
}

.athena-subnav__section {
  margin-bottom: var(--space-1);
}

.athena-subnav__section-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-3) var(--space-1);
}

.athena-subnav__item {
  display: block;
  width: 100%;
  text-align: left;
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-3) var(--space-1) var(--space-5);
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.athena-subnav__item:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.athena-subnav__item--active {
  color: var(--color-brand);
  font-weight: var(--font-medium);
  background: var(--color-brand-light);
}

.athena-subnav__divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-2) 0;
}

.athena-subnav__actions {
  padding: var(--space-2) var(--space-3);
}
</style>
