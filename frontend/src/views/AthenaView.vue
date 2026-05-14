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
import NarrativeAtlasView from '../components/athena/NarrativeAtlasView.vue'
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
import type { AthenaConsistencyIssue, AthenaEvolutionPlan, AthenaTimeline, ProposalItem } from '../api/types'

type AthenaNarrativeWorkbenchView = Exclude<AthenaNarrativeView, 'timeline' | 'graph'>
type AthenaTimelineEvent = AthenaTimeline['events'][number]
type RecordValue = Record<string, unknown>

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
const routeDataLoading = ref(false)
let initializeRequestId = 0
let routeDataRequestId = 0

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

const narrativePlanTimelineEvents = computed<AthenaTimelineEvent[]>(() => buildNarrativePlanTimeline(athena.evolutionPlan))
const timelineEvents = computed<AthenaTimelineEvent[]>(() => {
  const events = athena.timeline?.events || []
  return events.length > 0 ? events : narrativePlanTimelineEvents.value
})
const timelineAnchors = computed(() => athena.timeline?.anchors || [])
const narrativeFallbackSummary = computed(() => ({
  chapters: countWithTotal(athena.evolutionPlan?.outline?.chapters_total, athena.evolutionPlan?.outline?.chapters),
  plotlines: countWithTotal(
    athena.evolutionPlan?.storyline?.plotlines_total ?? athena.evolutionPlan?.outline?.plotlines_total,
    athena.evolutionPlan?.storyline?.plotlines || athena.evolutionPlan?.outline?.plotlines,
  ),
  foreshadowing: countWithTotal(
    athena.evolutionPlan?.storyline?.foreshadowing_total,
    athena.evolutionPlan?.storyline?.foreshadowing,
  ),
}))
const narrativePlanLoading = computed(() => routeDataLoading.value && !athena.evolutionPlan)
const timelineLoading = computed(() => routeDataLoading.value && !athena.timeline)
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
const latestLoadedChapterIndex = computed(() => {
  const indexes = (project.chapters || [])
    .map((chapter) => Number(chapter.chapter_index))
    .filter((index: number) => Number.isFinite(index))
  return indexes.length ? Math.max(...indexes) : null
})
const latestChapterIndex = computed(() => project.chaptersLatestIndex ?? latestLoadedChapterIndex.value)
const catalogPendingProposalItems = computed<ProposalItem[]>(() => {
  // Catalog hides pending counts unless a complete proposal item source is supplied.
  return []
})
const catalogView = computed<AthenaCatalogView>(() => {
  const view = routeState.value.view
  if (view === 'graph' || view === 'rules') return view
  return 'nodes'
})
const narrativeView = computed<AthenaNarrativeWorkbenchView>(() => {
  const view = routeState.value.view
  if (view === 'storyline' || view === 'chapters' || view === 'foreshadowing') return view
  return 'storyline'
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
      viewOption('narrative-graph', '图谱', 'narrative', 'graph'),
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
  routeDataLoading.value = true
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

function countWithTotal(total: unknown, value: unknown) {
  const totalValue = toNumber(total)
  return totalValue !== null && totalValue >= 0 ? totalValue : arrayCount(value)
}

function buildNarrativePlanTimeline(plan: AthenaEvolutionPlan | null): AthenaTimelineEvent[] {
  return asRecords(plan?.outline?.chapters)
    .map((chapter) => {
      const chapterIndex = toNumber(chapter.chapter_index ?? chapter.chapter)
      if (chapterIndex === null) return null
      const title = toText(chapter.title, `第${chapterIndex}章`)
      const summary = toOptionalText(chapter.summary)

      return {
        id: `plan-chapter-${chapterIndex}`,
        event_id: `plan.chapter.${chapterIndex}`,
        chapter_index: chapterIndex,
        intra_chapter_seq: 0,
        event_type: 'chapter_plan',
        description: summary ? `${title}：${summary}` : title,
      }
    })
    .filter((event): event is AthenaTimelineEvent => event !== null)
}

function asRecords(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.filter(isRecord) : []
}

function isRecord(value: unknown): value is RecordValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function toText(value: unknown, fallback = '') {
  return toOptionalText(value) ?? fallback
}

function toOptionalText(value: unknown) {
  if (typeof value === 'string' && value.trim()) return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  return undefined
}

function toNumber(value: unknown) {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
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
    routeDataLoading.value = true
    await router.replace(buildAthenaRoute(pid.value, state))
    return
  }

  if (initializedProjectId.value !== pid.value) return

  const requestId = ++routeDataRequestId
  routeDataLoading.value = true
  try {
    await loadRouteData(state)
  } finally {
    if (requestId === routeDataRequestId) routeDataLoading.value = false
  }
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

function navigateNarrativeAtlas(payload: { view: AthenaNarrativeView; sourceKey: string }) {
  if (payload.view === 'graph') return
  router.push(buildAthenaRoute(pid.value, {
    section: 'narrative',
    view: payload.view,
    nodeType: 'all',
    tool: null,
    panel: null,
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

async function repairLongformMaintenance() {
  await athena.repairLongformMaintenance(pid.value)
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
            :maintenance-diagnostics="athena.longformMaintenanceDiagnostics"
            :maintenance-repairing="athena.longformMaintenanceRepairing"
            :loading="worldModel.isLaneLoading('dashboard')"
            @navigate="navigateSection"
            @run-action="runOverviewAction"
            @repair-maintenance="repairLongformMaintenance"
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
            :has-more="worldModel.factClaimsHasMore"
            :loading-more="worldModel.loadingMoreFactClaims"
            @load-more="worldModel.loadMoreFactClaims(pid)"
          />
        </template>

        <template v-else-if="routeState.section === 'narrative'">
          <TimelineView
            v-if="routeState.view === 'timeline'"
            :events="timelineEvents"
            :anchors="timelineAnchors"
            :loading="timelineLoading"
            :fallback-summary="narrativeFallbackSummary"
          />
          <NarrativeAtlasView
            v-else-if="routeState.view === 'graph'"
            :plan="athena.evolutionPlan"
            :chapters="project.chapters"
            :timeline="athena.timeline"
            :loading="narrativePlanLoading"
            @navigate="navigateNarrativeAtlas"
          />
          <NarrativeWorkbench
            v-else
            :plan="athena.evolutionPlan"
            :chapters="project.chapters"
            :view="narrativeView"
            :loading="narrativePlanLoading"
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
