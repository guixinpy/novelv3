<script setup lang="ts">
import { computed, ref } from 'vue'
import type { WorldProjection } from '../../api/types'

const props = defineProps<{
  projection: WorldProjection | null
}>()

const expandedEntities = ref<Set<string>>(new Set())

const entityEntries = computed(() => {
  if (!props.projection) return []
  return Object.entries(props.projection.entities || {})
})

const entityGroups = computed(() => {
  const groups: Record<string, Array<[string, WorldProjection['entities'][string]]>> = {}
  for (const entry of entityEntries.value) {
    const label = entityTypeLabel(entry[1].entity_type)
    groups[label] = groups[label] || []
    groups[label].push(entry)
  }
  return Object.entries(groups).map(([label, items]) => ({ label, items }))
})

const factGroups = computed(() => {
  if (!props.projection) return []
  return Object.entries(props.projection.facts || {}).map(([entity, facts]) => ({
    entity,
    items: Object.entries(facts || {}).map(([predicate, value]) => ({ predicate, value })),
  }))
})

const presenceEntries = computed(() => {
  if (!props.projection) return []
  return Object.entries(props.projection.presence || {})
})

const eventCount = computed(() => {
  if (!props.projection) return 0
  return Object.keys(props.projection.occurred_events || {}).length
})

function toggle(entity: string) {
  if (expandedEntities.value.has(entity)) {
    expandedEntities.value.delete(entity)
  } else {
    expandedEntities.value.add(entity)
  }
}

function formatValue(value: unknown) {
  if (value == null) return ''
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

function formatAttributes(value: Record<string, unknown>) {
  const entries = Object.entries(value || {})
  if (!entries.length) return '无结构化属性'
  return entries.map(([key, entry]) => `${key}: ${formatValue(entry)}`).join(' / ')
}

function entityTypeLabel(type: string) {
  if (type === 'character') return '人物'
  if (type === 'location') return '地点'
  if (type === 'faction') return '势力'
  if (type === 'artifact') return '物件'
  if (type === 'resource') return '资源'
  return '其他'
}
</script>

<template>
  <div class="projection-viewer">
    <div v-if="!projection" class="projection-viewer__empty">尚未建立正式 world-model 投影</div>
    <template v-else>
      <div class="projection-viewer__summary">
        <div class="projection-viewer__metric">
          <span>实体</span>
          <strong>{{ entityEntries.length }}</strong>
        </div>
        <div class="projection-viewer__metric">
          <span>事实主体</span>
          <strong>{{ factGroups.length }}</strong>
        </div>
        <div class="projection-viewer__metric">
          <span>在场</span>
          <strong>{{ presenceEntries.length }}</strong>
        </div>
        <div class="projection-viewer__metric">
          <span>事件</span>
          <strong>{{ eventCount }}</strong>
        </div>
      </div>

      <section v-if="entityGroups.length" class="projection-viewer__section">
        <h3 class="projection-viewer__section-title">实体状态</h3>
        <div v-for="group in entityGroups" :key="group.label" class="projection-viewer__entity-group">
          <div class="projection-viewer__group-label">{{ group.label }}</div>
          <div v-for="[entityRef, entity] in group.items" :key="entityRef" class="projection-viewer__group">
            <button class="projection-viewer__header" @click="toggle(entityRef)">
              <span class="projection-viewer__entity">{{ entityRef }}</span>
              <span class="projection-viewer__type">{{ entityTypeLabel(entity.entity_type) }}</span>
              <span class="projection-viewer__chevron">{{ expandedEntities.has(entityRef) ? '▾' : '▸' }}</span>
            </button>
            <div v-if="expandedEntities.has(entityRef)" class="projection-viewer__facts">
              <div class="projection-viewer__fact">
                <span class="projection-viewer__predicate">属性</span>
                <span class="projection-viewer__value">{{ formatAttributes(entity.attributes) }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="projection-viewer__section">
        <h3 class="projection-viewer__section-title">确认事实</h3>
        <div v-if="factGroups.length === 0" class="projection-viewer__empty">暂无确认事实</div>
        <div v-for="group in factGroups" :key="group.entity" class="projection-viewer__group">
          <div class="projection-viewer__header projection-viewer__header--static">
            <span class="projection-viewer__entity">{{ group.entity }}</span>
            <span class="projection-viewer__count">{{ group.items.length }} 条</span>
          </div>
          <div class="projection-viewer__facts">
            <div v-for="fact in group.items" :key="fact.predicate" class="projection-viewer__fact">
              <span class="projection-viewer__predicate">{{ fact.predicate }}</span>
              <span class="projection-viewer__value">{{ formatValue(fact.value) }}</span>
            </div>
          </div>
        </div>
      </section>

      <section v-if="presenceEntries.length" class="projection-viewer__section">
        <h3 class="projection-viewer__section-title">在场信息</h3>
        <div v-for="[entityRef, presence] in presenceEntries" :key="entityRef" class="projection-viewer__presence">
          <strong>{{ entityRef }}</strong>
          <span>{{ presence.location_ref || '未知位置' }} / {{ presence.presence_status || '未标注' }}</span>
        </div>
      </section>
    </template>
  </div>
</template>
<style scoped>
.projection-viewer {
  height: 100%;
  overflow: auto;
  padding: var(--space-4);
}

.projection-viewer__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.projection-viewer__metric {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.projection-viewer__metric span {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.projection-viewer__metric strong {
  color: var(--color-text-primary);
  font-size: var(--text-base);
}

.projection-viewer__section {
  margin-bottom: var(--space-5);
}

.projection-viewer__section-title {
  margin-bottom: var(--space-2);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.projection-viewer__group {
  border-bottom: 1px solid var(--color-border);
}

.projection-viewer__entity-group {
  margin-bottom: var(--space-3);
}

.projection-viewer__group-label {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  margin-bottom: var(--space-1);
}

.projection-viewer__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3) 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.projection-viewer__header--static {
  cursor: default;
}

.projection-viewer__entity {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.projection-viewer__count {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.projection-viewer__type {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.projection-viewer__chevron {
  margin-left: auto;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.projection-viewer__facts {
  padding: 0 0 var(--space-3) var(--space-4);
}

.projection-viewer__fact {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
}

.projection-viewer__predicate {
  color: var(--color-text-secondary);
  min-width: 100px;
}

.projection-viewer__value {
  color: var(--color-text-primary);
  min-width: 0;
  overflow-wrap: anywhere;
}

.projection-viewer__presence {
  display: grid;
  grid-template-columns: minmax(120px, 220px) minmax(0, 1fr);
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--text-sm);
}

.projection-viewer__presence strong {
  color: var(--color-text-primary);
}

.projection-viewer__presence span {
  color: var(--color-text-secondary);
}

.projection-viewer__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

@media (max-width: 720px) {
  .projection-viewer__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .projection-viewer__presence {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
