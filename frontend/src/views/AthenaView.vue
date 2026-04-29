<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useAthenaStore } from '../stores/athena'
import { useWorldModelStore } from '../stores/worldModel'
import { useUiStore, type AthenaSection } from '../stores/ui'
import EntityTable from '../components/athena/EntityTable.vue'
import RelationTable from '../components/athena/RelationTable.vue'
import RuleList from '../components/athena/RuleList.vue'
import TimelineView from '../components/athena/TimelineView.vue'
import ProjectionViewer from '../components/athena/ProjectionViewer.vue'
import SubjectKnowledgePanel from '../components/athena/SubjectKnowledgePanel.vue'
import ProposalWorkbench from '../components/athena/ProposalWorkbench.vue'
import AthenaOverview from '../components/athena/AthenaOverview.vue'
import ConsistencyList from '../components/athena/ConsistencyList.vue'
import OptimizationPanel from '../components/athena/OptimizationPanel.vue'
import AthenaChatPanel from '../components/athena/AthenaChatPanel.vue'
import RetrievalPanel from '../components/athena/RetrievalPanel.vue'
import AthenaSubnav from '../components/athena/AthenaSubnav.vue'
import { createAthenaSectionLoader } from './athenaSectionLoader'

interface NavSection {
  label: string
  items: { key: AthenaSection; label: string }[]
}

const sections: NavSection[] = [
  {
    label: '总览',
    items: [
      { key: 'overview', label: '总览' },
    ],
  },
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
      { key: 'retrieval', label: '检索' },
    ],
  },
  {
    label: '演化',
    items: [
      { key: 'outline', label: '大纲' },
      { key: 'storyline', label: '故事线' },
      { key: 'proposals', label: '提案' },
      { key: 'consistency', label: '一致性检查' },
      { key: 'optimization', label: '自优化' },
    ],
  },
]
const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const athena = useAthenaStore()
const worldModel = useWorldModelStore()
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

// Entity display labels and backend ontology keys for ontology sections.
const entityTypeMap: Record<string, string> = {
  characters: '角色',
  locations: '地点',
  factions: '势力',
  items: '物品',
}

const entityDataKeyMap: Record<string, string> = {
  characters: 'characters',
  locations: 'locations',
  factions: 'factions',
  items: 'artifacts',
}

const entitySections = new Set(['characters', 'locations', 'factions', 'items'])
const { loadSectionData } = createAthenaSectionLoader({
  getProjectId: () => pid.value,
  athena,
  worldModel,
  entitySections,
})

const entities = computed(() => {
  if (!entitySections.has(activeSection.value)) return []
  const dataKey = entityDataKeyMap[activeSection.value]
  const entitiesMap = athena.ontology?.entities
  if (!entitiesMap || typeof entitiesMap !== 'object') return []
  const list = entitiesMap[dataKey] || entitiesMap[activeSection.value] || []
  return Array.isArray(list) ? list : []
})

const relations = computed(() => athena.ontology?.relations || [])
const rules = computed(() => athena.ontology?.rules || [])
const timelineEvents = computed(() => athena.timeline?.events || [])
const timelineAnchors = computed(() => athena.timeline?.anchors || [])
const consistencyIssues = computed<any[]>(() => athena.consistencyIssues || [])
const activeError = computed(() => athena.error || worldModel.error || '')
const canImportSetup = computed(() => athena.ontology?.profile_version === null && Boolean(athena.ontology?.setup_summary))
const entityNotice = computed(() => {
  if (!entitySections.has(activeSection.value)) return ''
  if (athena.ontology?.profile_version !== null) return ''
  if (!entities.value.length) return ''
  return 'Setup 草稿，尚未导入 world-model'
})
const latestChapterIndex = computed(() => {
  const indexes = (project.chapters || [])
    .map((chapter: any) => Number(chapter.chapter_index))
    .filter((index: number) => Number.isFinite(index))
  return indexes.length ? Math.max(...indexes) : null
})

onMounted(() => void initialize(pid.value))

watch(pid, (next, prev) => {
  if (next && next !== prev) void initialize(next)
})

watch(activeSection, (section) => {
  ui.setAthenaSection(section)
  void loadSectionData(section)
})

async function initialize(projectId: string) {
  athena.ensureProject(projectId)
  await project.loadProject(projectId)
  await project.loadChapters(projectId).catch(() => undefined)
  await Promise.all([
    athena.loadOntology(projectId),
    athena.loadMessages(projectId),
  ])
  await loadSectionData(activeSection.value)
}

function navigateSection(section: AthenaSection) {
  router.push(`/projects/${pid.value}/athena/${section}`)
}

async function importSetup() {
  await athena.importSetup(pid.value)
  await loadSectionData(activeSection.value)
  if (activeSection.value !== 'overview') {
    await worldModel.loadDashboard(pid.value).catch(() => undefined)
  }
}

async function analyzeLatestChapter() {
  if (!latestChapterIndex.value) return
  await athena.analyzeChapter(pid.value, latestChapterIndex.value)
  await worldModel.loadDashboard(pid.value).catch(() => undefined)
  navigateSection('proposals')
}

async function reindexRetrieval() {
  await athena.reindexRetrieval(pid.value)
}

async function searchRetrieval(query: string) {
  await athena.searchRetrieval(pid.value, query)
}

async function selectSubject(subjectRef: string) {
  if (!subjectRef) return
  await worldModel.loadSubjectKnowledge(pid.value, subjectRef)
}
</script>

<template>
  <div v-if="project.currentProject" class="athena-view" data-testid="workspace-athena">
    <!-- Sub-nav content -->
    <Teleport to="[data-subnav-content]">
      <AthenaSubnav
        :sections="sections"
        :active-section="activeSection"
        :can-import-setup="canImportSetup"
        :has-latest-chapter="Boolean(latestChapterIndex)"
        @navigate="navigateSection"
        @import-setup="importSetup"
        @analyze-latest-chapter="analyzeLatestChapter"
        @open-chat="chatOpen = true"
      />
    </Teleport>

    <!-- Main content: detail view based on active section -->
    <div class="athena-view__content">
      <div v-if="activeError" class="athena-view__error">{{ activeError }}</div>
      <AthenaOverview
        v-if="activeSection === 'overview'"
        :dashboard="worldModel.dashboard"
        :setup-preview="athena.setupImportPreview"
        :loading="worldModel.isLaneLoading('dashboard')"
        @navigate="navigateSection"
      />
      <EntityTable
        v-else-if="entitySections.has(activeSection)"
        :entities="entities"
        :entity-type="entityTypeMap[activeSection]"
        :notice="entityNotice"
      />
      <RelationTable v-else-if="activeSection === 'relations'" :relations="relations" />
      <RuleList v-else-if="activeSection === 'rules'" :rules="rules" />
      <ProjectionViewer v-else-if="activeSection === 'projection'" :projection="worldModel.projection" />
      <TimelineView
        v-else-if="activeSection === 'timeline'"
        :events="timelineEvents"
        :anchors="timelineAnchors"
      />
      <SubjectKnowledgePanel
        v-else-if="activeSection === 'knowledge'"
        :projection="worldModel.projection"
        :subject-knowledge="worldModel.subjectKnowledge"
        :selected-subject-ref="worldModel.selectedSubjectRef"
        @select-subject="selectSubject"
      />
      <RetrievalPanel
        v-else-if="activeSection === 'retrieval'"
        :diagnostics="athena.retrievalDiagnostics"
        :search="athena.retrievalSearch"
        :last-index-result="athena.retrievalLastIndexResult"
        :loading="athena.retrievalLoading"
        @reindex="reindexRetrieval"
        @search="searchRetrieval"
      />
      <ProposalWorkbench v-else-if="activeSection === 'proposals'" :project-id="pid" />
      <ConsistencyList v-else-if="activeSection === 'consistency'" :issues="consistencyIssues" />
      <OptimizationPanel v-else-if="activeSection === 'optimization'" :optimization="athena.optimization" />
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
  position: relative;
}

.athena-view__error {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-error);
  color: var(--color-error);
  background: var(--color-error-light);
  font-size: var(--text-sm);
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

</style>
