<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import CatalogContextRail from './CatalogContextRail.vue'
import CatalogGraphPanel from './CatalogGraphPanel.vue'
import CatalogNodeDetail from './CatalogNodeDetail.vue'
import CatalogNodeList from './CatalogNodeList.vue'
import { buildCatalogNodes, filterCatalogNodes, normalizeRelations } from './catalogNodeModel'
import type { AthenaOntology, ProposalItem, WorldProjection } from '../../../api/types'
import type { AthenaCatalogView, AthenaNodeTypeFilter } from '../../../views/athenaNavigation'

const props = defineProps<{
  ontology: AthenaOntology | null
  projection: WorldProjection | null
  pendingProposalItems: ProposalItem[]
  nodeType: AthenaNodeTypeFilter
  view: AthenaCatalogView
}>()

const emit = defineEmits<{
  filterType: [nodeType: AthenaNodeTypeFilter]
}>()

const selectedRef = ref<string | null>(null)

const nodes = computed(() => buildCatalogNodes({
  ontology: props.ontology,
  projection: props.projection,
  pendingProposalItems: props.pendingProposalItems,
}))

const visibleNodes = computed(() => filterCatalogNodes(nodes.value, {
  nodeType: props.nodeType,
  search: '',
}))

const relations = computed(() => normalizeRelations([
  ...(props.ontology?.relations || []),
  ...Object.values(props.projection?.relations || {}),
]))

const selectedNode = computed(() =>
  visibleNodes.value.find((node) => node.ref === selectedRef.value) || null,
)

watch(visibleNodes, (nextNodes) => {
  if (nextNodes.some((node) => node.ref === selectedRef.value)) return

  selectedRef.value = nextNodes[0]?.ref || null
}, { immediate: true })

function selectNode(nodeRef: string) {
  selectedRef.value = nodeRef
}

function filterType(nodeType: AthenaNodeTypeFilter) {
  emit('filterType', nodeType)
}

function formatRuleValue(value: unknown) {
  if (value === null || value === undefined) return '无'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)

  try {
    return JSON.stringify(value, (_key, entry) => typeof entry === 'bigint' ? String(entry) : entry)
  } catch (_error) {
    return String(value)
  }
}
</script>

<template>
  <div class="catalog-workbench">
    <template v-if="view === 'nodes'">
      <CatalogNodeList
        :nodes="nodes"
        :node-type="nodeType"
        :selected-ref="selectedRef"
        @select="selectNode"
        @filter-type="filterType"
      />
      <CatalogNodeDetail :node="selectedNode" />
      <CatalogContextRail :node="selectedNode" :relations="relations" />
    </template>

    <CatalogGraphPanel v-else-if="view === 'graph'" :relations="relations" />

    <section v-else class="catalog-workbench__rules">
      <header class="catalog-workbench__rules-header">
        <h2>规则约束</h2>
        <span>{{ ontology?.rules.length || 0 }} 条</span>
      </header>
      <div v-if="!ontology?.rules.length" class="catalog-workbench__empty">暂无规则</div>
      <div v-else class="catalog-workbench__rule-list">
        <article v-for="rule in ontology.rules" :key="rule.id || rule.rule_id" class="catalog-workbench__rule">
          <h3>{{ rule.rule_id || rule.id }}</h3>
          <p>{{ rule.description }}</p>
          <dl>
            <template v-for="[key, value] in Object.entries(rule)" :key="key">
              <dt>{{ key }}</dt>
              <dd>{{ formatRuleValue(value) }}</dd>
            </template>
          </dl>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.catalog-workbench {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 280px;
  height: 100%;
  overflow: hidden;
  background: var(--color-surface, var(--color-bg-white));
}

.catalog-workbench__rules {
  grid-column: 1 / -1;
  height: 100%;
  overflow: auto;
  padding: var(--space-5);
}

.catalog-workbench__rules-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.catalog-workbench__rules-header h2 {
  color: var(--color-text-primary);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.catalog-workbench__rules-header span,
.catalog-workbench__empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.catalog-workbench__empty {
  padding: var(--space-8) 0;
  text-align: center;
}

.catalog-workbench__rule-list {
  display: grid;
}

.catalog-workbench__rule {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--color-border);
}

.catalog-workbench__rule h3 {
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.catalog-workbench__rule p {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.catalog-workbench__rule dl {
  display: grid;
  grid-template-columns: minmax(96px, auto) minmax(0, 1fr);
  gap: var(--space-1) var(--space-3);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.catalog-workbench__rule dd {
  overflow-wrap: anywhere;
  color: var(--color-text-secondary);
}

@media (max-width: 1080px) {
  .catalog-workbench {
    grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
    overflow: auto;
  }
}

@media (max-width: 760px) {
  .catalog-workbench {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
