<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useAthenaStore } from '../stores/athena'
import { useWorldModelStore } from '../stores/worldModel'
import { useUiStore } from '../stores/ui'
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
import CatalogWorkbench from '../components/athena/catalog/CatalogWorkbench.vue'
import { createAthenaSectionLoader } from './athenaSectionLoader'
import {
  athenaPrimaryNav,
  buildAthenaRoute,
  resolveAthenaRoute,
  type AthenaCatalogView,
  type AthenaNodeTypeFilter,
  type AthenaPrimarySection,
  type AthenaRouteState,
} from './athenaNavigation'
import type { AthenaConsistencyIssue, ProposalItem } from '../api/types'

const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const athena = useAthenaStore()
const worldModel = useWorldModelStore()
const ui = useUiStore()
const pid = computed(() => route.params.id as string)
const chatOpen = ref(false)
const initializedProjectId = ref<string | null>(null)
let initializeRequestId = 0

const routeState = computed(() =>
  resolveAthenaRoute(
    route.params.section as string | undefined,
    route.query as unknown as Parameters<typeof resolveAthenaRoute>[1],
  ),
)

const { loadRouteData } = createAthenaSectionLoader({
  getProjectId: () => pid.value,
  athena,
  worldModel,
})

const timelineEvents = computed(() => athena.timeline?.events || [])
const timelineAnchors = computed(() => athena.timeline?.anchors || [])
const consistencyIssues = computed<AthenaConsistencyIssue[]>(() => athena.consistencyIssues || [])
const activeError = computed(() => athena.error || worldModel.error || '')
const canImportSetup = computed(() => athena.ontology?.profile_version === null && Boolean(athena.ontology?.setup_summary))
const latestChapterIndex = computed(() => {
  const indexes = (project.chapters || [])
    .map((chapter) => Number(chapter.chapter_index))
    .filter((index: number) => Number.isFinite(index))
  return indexes.length ? Math.max(...indexes) : null
})
const catalogPendingProposalItems = computed<ProposalItem[]>(() => {
  // Phase 1 has no full proposal item source; selected bundle items would show incomplete pending counts.
  return []
})
const catalogView = computed<AthenaCatalogView>(() => {
  const view = routeState.value.view
  if (view === 'graph' || view === 'rules') return view
  return 'nodes'
})

onMounted(() => void initialize(pid.value))

watch(pid, (next, prev) => {
  if (next && next !== prev) void initialize(next)
})

watch(routeState, (state) => {
  void syncRouteState(state)
})

async function initialize(projectId: string) {
  const requestId = ++initializeRequestId
  athena.ensureProject(projectId)

  await project.loadProject(projectId)
  if (!isCurrentInitialize(requestId, projectId)) return

  await project.loadChapters(projectId).catch(() => undefined)
  if (!isCurrentInitialize(requestId, projectId)) return

  await Promise.all([
    athena.loadOntology(projectId),
    athena.loadMessages(projectId),
  ])
  if (!isCurrentInitialize(requestId, projectId)) return

  initializedProjectId.value = projectId
  await syncRouteState(routeState.value)
}

function isCurrentInitialize(requestId: number, projectId: string) {
  return requestId === initializeRequestId && projectId === pid.value
}

async function syncRouteState(state: AthenaRouteState) {
  ui.setAthenaState({ section: state.section, view: state.view, nodeType: state.nodeType })
  if (!pid.value) return

  if (state.isLegacy) {
    await router.replace(buildAthenaRoute(pid.value, state))
    return
  }

  if (initializedProjectId.value !== pid.value) return

  await loadRouteData(state)
}

function navigateSection(section: AthenaPrimarySection) {
  const target = athenaPrimaryNav.find((item) => item.section === section)
  if (!target) return

  router.push(buildAthenaRoute(pid.value, {
    section,
    view: target.defaultView,
    nodeType: 'all',
    tool: null,
    panel: null,
    isLegacy: false,
  }))
}

function updateCatalogType(nodeType: AthenaNodeTypeFilter) {
  router.push(buildAthenaRoute(pid.value, {
    section: 'catalog',
    view: 'nodes',
    nodeType,
    tool: null,
    panel: null,
    isLegacy: false,
  }))
}

async function importSetup() {
  await athena.importSetup(pid.value)
  await worldModel.loadDashboard(pid.value).catch(() => undefined)
  await loadRouteData(routeState.value)
}

async function analyzeLatestChapter() {
  if (!latestChapterIndex.value) return
  await athena.analyzeChapter(pid.value, latestChapterIndex.value)
  await worldModel.loadDashboard(pid.value).catch(() => undefined)
  navigateSection('review')
}

async function runOverviewAction(action: string) {
  if (action === 'import_setup') {
    await importSetup()
    return
  }
  if (action === 'analyze_chapter') {
    await analyzeLatestChapter()
  }
}

async function reindexRetrieval() {
  await athena.reindexRetrieval(pid.value)
}

async function searchRetrieval(query: string, params?: { source_type?: string }) {
  await athena.searchRetrieval(pid.value, query, params)
}

async function selectSubject(subjectRef: string) {
  if (!subjectRef) return
  await worldModel.loadSubjectKnowledge(pid.value, subjectRef)
}

async function runConsistencyCheck(chapterIndex: number) {
  await athena.runConsistencyCheck(pid.value, chapterIndex)
}
</script>

<template>
  <div v-if="project.currentProject" class="athena-view" data-testid="workspace-athena">
    <Teleport to="[data-subnav-content]">
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
    </Teleport>

    <div class="athena-view__content">
      <div v-if="activeError" class="athena-view__error">{{ activeError }}</div>

      <template v-if="routeState.section === 'overview'">
        <OptimizationPanel
          v-if="routeState.panel === 'optimization'"
          :optimization="athena.optimization"
        />
        <AthenaOverview
          v-else
          :dashboard="worldModel.dashboard"
          :setup-preview="athena.setupImportPreview"
          :loading="worldModel.isLaneLoading('dashboard')"
          @navigate="navigateSection"
          @run-action="runOverviewAction"
        />
      </template>

      <div
        v-else-if="routeState.section === 'catalog'"
        class="athena-view__catalog"
        :class="{ 'athena-view__catalog--with-tool': routeState.tool === 'retrieval' }"
      >
        <RetrievalPanel
          v-if="routeState.tool === 'retrieval'"
          :diagnostics="athena.retrievalDiagnostics"
          :search="athena.retrievalSearch"
          :last-index-result="athena.retrievalLastIndexResult"
          :loading="athena.retrievalLoading"
          @reindex="reindexRetrieval"
          @search="searchRetrieval"
        />
        <CatalogWorkbench
          :ontology="athena.ontology"
          :projection="worldModel.projection"
          :pending-proposal-items="catalogPendingProposalItems"
          :pending-counts-available="false"
          :node-type="routeState.nodeType"
          :view="catalogView"
          @filter-type="updateCatalogType"
        />
      </div>

      <template v-else-if="routeState.section === 'truth'">
        <ProjectionViewer v-if="routeState.view === 'projection'" :projection="worldModel.projection" />
        <SubjectKnowledgePanel
          v-else-if="routeState.view === 'knowledge'"
          :projection="worldModel.projection"
          :subject-knowledge="worldModel.subjectKnowledge"
          :selected-subject-ref="worldModel.selectedSubjectRef"
          @select-subject="selectSubject"
        />
        <div v-else class="athena-view__placeholder">truth / {{ routeState.view }} 正在接入现有数据视图</div>
      </template>

      <template v-else-if="routeState.section === 'narrative'">
        <TimelineView
          v-if="routeState.view === 'timeline'"
          :events="timelineEvents"
          :anchors="timelineAnchors"
        />
        <div v-else class="athena-view__placeholder">
          narrative / {{ routeState.view }} 正在接入现有数据视图
        </div>
      </template>

      <template v-else-if="routeState.section === 'review'">
        <ProposalWorkbench v-if="routeState.view === 'proposals'" :project-id="pid" />
        <ConsistencyList
          v-else-if="routeState.view === 'conflicts'"
          :issues="consistencyIssues"
          :latest-chapter-index="latestChapterIndex"
          :loading="athena.loading"
          @run-check="runConsistencyCheck"
        />
        <div v-else class="athena-view__placeholder">review / {{ routeState.view }} 正在接入现有数据视图</div>
      </template>
    </div>

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

.athena-view__catalog {
  height: 100%;
  min-height: 0;
}

.athena-view__catalog--with-tool {
  display: grid;
  grid-template-rows: minmax(260px, 40%) minmax(0, 1fr);
}

.athena-view__catalog--with-tool :deep(.retrieval-panel) {
  min-height: 0;
  border-bottom: 1px solid var(--color-border);
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
