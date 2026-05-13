<script setup lang="ts">
import { computed } from 'vue'
import BaseButton from '../base/BaseButton.vue'
import type { AthenaNarrativeView } from '../../views/athenaNavigation'
import type {
  NarrativeAtlasEdge,
  NarrativeAtlasGraph,
  NarrativeAtlasNode,
  NarrativeAtlasWarning,
} from './narrativeAtlasGraph'

type AtlasSelection = { kind: 'node'; id: string } | { kind: 'edge'; id: string }

interface NavigatePayload {
  view: AthenaNarrativeView
  sourceKey: string
}

const props = defineProps<{
  graph: NarrativeAtlasGraph
  selected: AtlasSelection | null
}>()

const emit = defineEmits<{
  navigate: [payload: NavigatePayload]
}>()

const nodeById = computed(() => new Map(props.graph.nodes.map((node) => [node.id, node])))
const edgeById = computed(() => new Map(props.graph.edges.map((edge) => [edge.id, edge])))

const selectedNode = computed(() =>
  props.selected?.kind === 'node' ? nodeById.value.get(props.selected.id) ?? null : null,
)

const selectedEdge = computed(() =>
  props.selected?.kind === 'edge' ? edgeById.value.get(props.selected.id) ?? null : null,
)

const detail = computed(() => {
  if (selectedNode.value) return nodeDetail(selectedNode.value)
  if (selectedEdge.value) return edgeDetail(selectedEdge.value)
  return null
})

const relatedWarnings = computed(() => {
  const selection = props.selected
  if (!selection) return []
  return props.graph.warnings.filter((warning) => warningTouchesSelection(warning, selection))
})

function nodeDetail(node: NarrativeAtlasNode) {
  return {
    sourceKey: node.id,
    title: node.label,
    meta: node.chapterIndex !== undefined ? `第${node.chapterIndex}章` : typeLabel(node.type),
    status: statusLabel(node.status),
    summary: node.summary || rawText(node.raw, ['summary', 'description', 'event', 'hint', 'purpose']) || '暂无摘要',
    view: viewForNode(node),
  }
}

function edgeDetail(edge: NarrativeAtlasEdge) {
  const source = nodeById.value.get(edge.source)
  const target = nodeById.value.get(edge.target)
  return {
    sourceKey: edge.id,
    title: `${source?.label ?? edge.source} → ${target?.label ?? edge.target}`,
    meta: edgeLabel(edge.type),
    status: '叙事链路',
    summary: edge.label || `${edgeLabel(edge.type)}连接了两个叙事节点。`,
    view: viewForEdge(edge),
  }
}

function warningTouchesSelection(warning: NarrativeAtlasWarning, selection: AtlasSelection) {
  if (selection.kind === 'node') {
    return warning.sourceId === selection.id || warning.targetId === selection.id
  }
  const edge = edgeById.value.get(selection.id)
  if (!edge) return false
  return [edge.source, edge.target].includes(String(warning.sourceId))
    || [edge.source, edge.target].includes(String(warning.targetId))
}

function navigateToDetail() {
  if (!detail.value) return
  emit('navigate', { view: detail.value.view, sourceKey: detail.value.sourceKey })
}

function viewForNode(node: NarrativeAtlasNode): AthenaNarrativeView {
  if (node.type === 'chapter') return 'chapters'
  if (node.type === 'foreshadowing') return 'foreshadowing'
  if (node.type === 'event') return 'timeline'
  return 'storyline'
}

function viewForEdge(edge: NarrativeAtlasEdge): AthenaNarrativeView {
  if (edge.type === 'foreshadowing') return 'foreshadowing'
  if (edge.type === 'event_anchor') return 'timeline'
  if (edge.type === 'trunk') return 'chapters'
  return 'storyline'
}

function typeLabel(type: NarrativeAtlasNode['type']) {
  const labels: Record<NarrativeAtlasNode['type'], string> = {
    chapter: '章节',
    chapter_group: '章节组',
    plotline: '故事线',
    milestone: '里程碑',
    foreshadowing: '伏笔',
    event: '事件',
  }
  return labels[type]
}

function edgeLabel(type: NarrativeAtlasEdge['type']) {
  const labels: Record<NarrativeAtlasEdge['type'], string> = {
    trunk: '章节主干',
    branch: '故事线枝干',
    foreshadowing: '伏笔链路',
    event_anchor: '事件锚点',
  }
  return labels[type]
}

function statusLabel(status: string | undefined) {
  const normalized = status || 'unknown'
  const labels: Record<string, string> = {
    resolved: '已回收',
    planted: '已埋设',
    pending: '待回收',
    generated: '已生成',
    draft: '草稿',
    done: '已完成',
    completed: '已完成',
    active: '进行中',
    unknown: '未标注',
  }
  return labels[normalized] || normalized
}

function rawText(raw: Record<string, unknown> | undefined, keys: string[]) {
  if (!raw) return ''
  for (const key of keys) {
    const value = raw[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
    if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  }
  return ''
}
</script>

<template>
  <aside class="narrative-atlas-detail" data-testid="atlas-detail-panel" aria-label="叙事节点详情">
    <template v-if="detail">
      <header class="narrative-atlas-detail__header">
        <span>{{ detail.meta }}</span>
        <h2>{{ detail.title }}</h2>
      </header>

      <dl class="narrative-atlas-detail__facts">
        <div>
          <dt>状态</dt>
          <dd>{{ detail.status }}</dd>
        </div>
        <div>
          <dt>摘要</dt>
          <dd>{{ detail.summary }}</dd>
        </div>
      </dl>

      <div v-if="relatedWarnings.length" class="narrative-atlas-detail__warnings">
        <h3>提示</h3>
        <p v-for="warning in relatedWarnings" :key="warning.id">{{ warning.message }}</p>
      </div>

      <BaseButton
        size="sm"
        data-testid="atlas-detail-navigate"
        @click="navigateToDetail"
      >
        查看对应视图
      </BaseButton>
    </template>

    <div v-else class="narrative-atlas-detail__empty">
      选择一个节点或连接查看叙事详情
    </div>
  </aside>
</template>

<style scoped>
.narrative-atlas-detail {
  min-width: 0;
  overflow: auto;
  padding: var(--space-4);
  border-left: 1px solid var(--color-border);
  background: var(--color-bg-white);
}

.narrative-atlas-detail__header {
  display: grid;
  gap: var(--space-1);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.narrative-atlas-detail__header span {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.narrative-atlas-detail__header h2 {
  color: var(--color-text-primary);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
  overflow-wrap: anywhere;
}

.narrative-atlas-detail__facts {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4) 0;
}

.narrative-atlas-detail__facts div {
  display: grid;
  gap: var(--space-1);
}

.narrative-atlas-detail__facts dt,
.narrative-atlas-detail__warnings h3 {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.narrative-atlas-detail__facts dd,
.narrative-atlas-detail__warnings p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  overflow-wrap: anywhere;
}

.narrative-atlas-detail__warnings {
  display: grid;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-lg);
  background: var(--color-warning-light);
}

.narrative-atlas-detail__empty {
  padding: var(--space-8) 0;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
}
</style>
