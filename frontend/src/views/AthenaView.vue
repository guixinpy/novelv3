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
import NarrativeWorkbench from '../components/athena/NarrativeWorkbench.vue'
import ReviewInsightPanel from '../components/athena/ReviewInsightPanel.vue'
import TruthLedger from '../components/athena/TruthLedger.vue'
import CatalogWorkbench from '../components/athena/catalog/CatalogWorkbench.vue'
import { createAthenaSectionLoader } from './athenaSectionLoader'
import {
  athenaPrimaryNav,
  buildAthenaRoute,
  isCanonicalAthenaRoute,
  resolveAthenaRoute,
  type AthenaCatalogView,
  type AthenaNarrativeView,
  type AthenaNodeTypeFilter,
  type AthenaPanel,
  type AthenaPrimarySection,
  type AthenaRouteState,
  type AthenaSubview,
  type AthenaTool,
} from './athenaNavigation'
import type { AthenaConsistencyIssue, ProposalItem } from '../api/types'

interface AthenaSectionViewOption {
  key: string
  label: string
  section: AthenaPrimarySection
  view: AthenaSubview
  nodeType: AthenaNodeTypeFilter
  tool: AthenaTool | null
  panel: AthenaPanel | null
}

const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const athena = useAthenaStore()
const worldModel = useWorldModelStore()
const ui = useUiStore()
const pid = computed(() => route.params.id as string)
const chatOpen = computed(() => routeState.value.panel === 'chat')
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
const narrativeFallbackSummary = computed(() => ({
  chapters: arrayCount(athena.evolutionPlan?.outline?.chapters),
  plotlines: arrayCount(athena.evolutionPlan?.storyline?.plotlines || athena.evolutionPlan?.outline?.plotlines),
  foreshadowing: arrayCount(athena.evolutionPlan?.storyline?.foreshadowing),
}))
const consistencyIssues = computed<AthenaConsistencyIssue[]>(() => athena.consistencyIssues || [])
const activeError = computed(() => athena.error || worldModel.error || '')
const activeNotice = computed(() => {
  const result = athena.lastAnalyzeChapterResult
  if (!result) return ''
  const created = Number(result.created?.proposal_items || 0)
  const duplicates = Number(result.skipped?.duplicates || 0)
  if (created > 0) return `第${result.chapter_index}章已生成 ${created} 条待审世界事实候选`
  if (duplicates > 0) return `第${result.chapter_index}章已有待审提案，未重复创建`
  return `第${result.chapter_index}章分析完成，未发现新的候选事实`
})
const canImportSetup = computed(() => athena.ontology?.profile_version === null && Boolean(athena.ontology?.setup_summary))
const latestChapterIndex = computed(() => {
  const indexes = (project.chapters || [])
    .map((chapter) => Number(chapter.chapter_index))
    .filter((index: number) => Number.isFinite(index))
  return indexes.length ? Math.max(...indexes) : null
})
const catalogPendingProposalItems = computed<ProposalItem[]>(() => {
  // Catalog hides pending counts unless a complete proposal item source is supplied.
  return []
})
const catalogView = computed<AthenaCatalogView>(() => {
  const view = routeState.value.view
  if (view === 'graph' || view === 'rules') return view
  return 'nodes'
})
const narrativeView = computed<AthenaNarrativeView>(() => {
  const view = routeState.value.view
  if (view === 'storyline' || view === 'chapters' || view === 'foreshadowing') return view
  return 'timeline'
})
const sectionViewOptions = computed<AthenaSectionViewOption[]>(() => {
  const current = routeState.value
  const catalogNodeType = current.section === 'catalog' ? current.nodeType : 'all'

  if (current.section === 'overview') {
    return [
      viewOption('overview-dashboard', '总览', 'overview', 'dashboard'),
      viewOption('overview-optimization', '自优化', 'overview', 'dashboard', { panel: 'optimization' }),
    ]
  }
  if (current.section === 'catalog') {
    return [
      viewOption('catalog-nodes', '节点', 'catalog', 'nodes', { nodeType: catalogNodeType }),
      viewOption('catalog-graph', '图谱', 'catalog', 'graph'),
      viewOption('catalog-rules', '规则', 'catalog', 'rules'),
      viewOption('catalog-retrieval', '检索', 'catalog', 'nodes', { nodeType: catalogNodeType, tool: 'retrieval' }),
    ]
  }
  if (current.section === 'narrative') {
    return [
      viewOption('narrative-timeline', '时间线', 'narrative', 'timeline'),
      viewOption('narrative-storyline', '故事线', 'narrative', 'storyline'),
      viewOption('narrative-chapters', '章节', 'narrative', 'chapters'),
      viewOption('narrative-foreshadowing', '伏笔', 'narrative', 'foreshadowing'),
    ]
  }
  if (current.section === 'truth') {
    return [
      viewOption('truth-projection', '真相投影', 'truth', 'projection'),
      viewOption('truth-knowledge', '主体认知', 'truth', 'knowledge'),
      viewOption('truth-facts', '事实', 'truth', 'facts'),
      viewOption('truth-disclosure', '披露', 'truth', 'disclosure'),
    ]
  }

  return [
    viewOption('review-proposals', '提案', 'review', 'proposals'),
    viewOption('review-conflicts', '一致性', 'review', 'conflicts'),
    viewOption('review-impact', '影响', 'review', 'impact'),
    viewOption('review-history', '历史', 'review', 'history'),
  ]
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

  await project.loadChapters(projectId, true).catch(() => undefined)
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

function arrayCount(value: unknown) {
  return Array.isArray(value) ? value.length : 0
}

async function syncRouteState(state: AthenaRouteState) {
  if (route.meta.workspace !== 'athena') return

  ui.setAthenaState(pid.value, {
    section: state.section,
    view: state.view,
    nodeType: state.nodeType,
    tool: state.tool,
    panel: state.panel === 'chat' ? null : state.panel,
  })
  if (!pid.value) return

  if (
    state.isLegacy
    || !isCanonicalAthenaRoute(
      pid.value,
      state,
      route.path,
      route.query as unknown as Parameters<typeof isCanonicalAthenaRoute>[3],
    )
  ) {
    await router.replace(buildAthenaRoute(pid.value, state))
    return
  }

  if (initializedProjectId.value !== pid.value) return

  await loadRouteData(state)
}

function navigateSection(section: AthenaPrimarySection) {
  const target = athenaPrimaryNav.find((item) => item.section === section)
  if (!target) return
  const lastState = ui.getAthenaSectionState(pid.value, section)

  router.push(buildAthenaRoute(pid.value, {
    section,
    view: lastState.view || target.defaultView,
    nodeType: lastState.nodeType,
    tool: lastState.tool,
    panel: lastState.panel,
  }))
}

function updateCatalogType(nodeType: AthenaNodeTypeFilter) {
  router.push(buildAthenaRoute(pid.value, {
    section: 'catalog',
    view: 'nodes',
    nodeType,
    tool: null,
    panel: null,
  }))
}

function viewOption(
  key: string,
  label: string,
  section: AthenaPrimarySection,
  view: AthenaSubview,
  overrides: Partial<Pick<AthenaSectionViewOption, 'nodeType' | 'tool' | 'panel'>> = {},
): AthenaSectionViewOption {
  return {
    key,
    label,
    section,
    view,
    nodeType: overrides.nodeType ?? 'all',
    tool: overrides.tool ?? null,
    panel: overrides.panel ?? null,
  }
}

function isSectionViewActive(option: AthenaSectionViewOption) {
  const current = routeState.value
  const currentPanel = current.panel === 'chat' ? null : current.panel
  return current.section === option.section
    && current.view === option.view
    && current.tool === option.tool
    && currentPanel === option.panel
}

function navigateSectionView(option: AthenaSectionViewOption) {
  router.push(buildAthenaRoute(pid.value, {
    section: option.section,
    view: option.view,
    nodeType: option.nodeType,
    tool: option.tool,
    panel: option.panel,
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

function openChat() {
  router.push(buildAthenaRoute(pid.value, {
    ...routeState.value,
    panel: 'chat',
  }))
}

function closeChat() {
  router.push(buildAthenaRoute(pid.value, {
    ...routeState.value,
    panel: null,
  }))
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
        @open-chat="openChat"
      />
    </Teleport>

    <div class="athena-view__content">
      <div v-if="activeError" class="athena-view__error">{{ activeError }}</div>
      <div v-if="activeNotice" class="athena-view__notice">{{ activeNotice }}</div>

      <nav class="athena-view__section-tabs" aria-label="Athena 当前分类视图">
        <button
          v-for="option in sectionViewOptions"
          :key="option.key"
          type="button"
          class="athena-view__section-tab"
          :class="{ 'athena-view__section-tab--active': isSectionViewActive(option) }"
          :aria-pressed="isSectionViewActive(option)"
          @click="navigateSectionView(option)"
        >
          {{ option.label }}
        </button>
      </nav>

      <div class="athena-view__body">
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
          <TruthLedger
            v-else-if="routeState.view === 'facts' || routeState.view === 'disclosure'"
            :projection="worldModel.projection"
            :fact-claims="worldModel.factClaims"
            :view="routeState.view"
          />
        </template>

        <template v-else-if="routeState.section === 'narrative'">
          <TimelineView
            v-if="routeState.view === 'timeline'"
            :events="timelineEvents"
            :anchors="timelineAnchors"
            :fallback-summary="narrativeFallbackSummary"
          />
          <NarrativeWorkbench
            v-else
            :plan="athena.evolutionPlan"
            :chapters="project.chapters"
            :view="narrativeView"
          />
        </template>

        <template v-else-if="routeState.section === 'review'">
          <ProposalWorkbench v-if="routeState.view === 'proposals'" :project-id="pid" />
          <ConsistencyList
            v-else-if="routeState.view === 'conflicts'"
            :issues="consistencyIssues"
            :latest-chapter-index="latestChapterIndex"
            :last-checked-chapter-index="athena.lastConsistencyCheck?.chapterIndex || null"
            :loading="athena.loading"
            @run-check="runConsistencyCheck"
          />
          <ReviewInsightPanel
            v-else-if="routeState.view === 'impact' || routeState.view === 'history'"
            :detail="worldModel.selectedBundleDetail"
            :bundles="worldModel.proposalBundles"
            :view="routeState.view"
          />
        </template>
      </div>
    </div>

    <AthenaChatPanel
      :open="chatOpen"
      :project-id="pid"
      @close="closeChat"
    />
  </div>
  <div v-else class="athena-view__loading">加载中...</div>
</template>

<style scoped>
.athena-view {
  height: 100%;
}

.athena-view__content {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.athena-view__body {
  flex: 1;
  min-height: 0;
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

.athena-view__notice {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-success);
  color: var(--color-success);
  background: var(--color-success-light);
  font-size: var(--text-sm);
}

.athena-view__section-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-primary);
}

.athena-view__section-tab {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-3);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  cursor: pointer;
}

.athena-view__section-tab--active {
  border-color: var(--color-brand);
  background: var(--color-brand-light);
  color: var(--color-brand-active);
  font-weight: var(--font-semibold);
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

.athena-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
